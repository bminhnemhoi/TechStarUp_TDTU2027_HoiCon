package vn.hoicon.sentinel.data.local

import android.content.Context
import androidx.room.Dao
import androidx.room.Database
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.PrimaryKey
import androidx.room.Query
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase
import kotlinx.coroutines.flow.Flow

/** Delivery state of an [OutboxEventEntity]. Stored as text so the schema stays readable. */
object OutboxStatus {
    const val PENDING = "PENDING"
    const val SENDING = "SENDING"
    const val SENT = "SENT"

    /** The server refused this event for good (invalid against the contract); kept a few days for diagnosis. */
    const val FAILED = "FAILED"
}

/**
 * One risk event waiting to reach `POST /v1/events`. The JSON (caller h1 + last3, rule, app category, timings) is
 * AEAD-encrypted by Tink with the row [id] as associated data, so a ciphertext cannot be moved to another row.
 *
 * @property id UUIDv7 made on the device; the server de-duplicates on it, so re-sending is always safe.
 */
@Entity(tableName = "outbox_events")
data class OutboxEventEntity(
    @PrimaryKey val id: String,
    val payloadJsonEncrypted: String,
    val status: String,
    val retryCount: Int,
    val createdAt: Long,
)

/**
 * The server's threat list as of the last sync (Spec 026, ADR-011): ONE row holding the packed k-anonymous buckets
 * (`buckets`: [count] big-endian uint24, ascending), not one row per number. It is a set of 22-bit buckets of `h1`,
 * each shared by ~86 real numbers, so unlike the v1 `threat_hashes` table (h1 + last3, which was reversible and never
 * written) it can sit in an unencrypted table. The in-memory `ThreatBucketIndex` is built from it at process start.
 */
@Entity(tableName = "threat_snapshot")
data class ThreatSnapshotEntity(
    @PrimaryKey val id: Int = SINGLETON_ID,
    val version: String,
    val bucketBits: Int,
    val count: Int,
    val buckets: ByteArray,
    /** Wall clock of the last successful sync (a `304` also moves it). */
    val fetchedAt: Long,
) {
    // A ByteArray field needs value equality, or two equal snapshots would compare unequal.
    override fun equals(other: Any?) = other is ThreatSnapshotEntity && id == other.id && version == other.version &&
        bucketBits == other.bucketBits && count == other.count && buckets.contentEquals(other.buckets) &&
        fetchedAt == other.fetchedAt

    override fun hashCode() = 31 * (31 * version.hashCode() + bucketBits) + buckets.contentHashCode()

    companion object {
        const val SINGLETON_ID = 1
    }
}

/**
 * The risk window as the rest of the app sees it (singleton row, [id] = 1): written by the sensing chain when a
 * window opens or closes, read by E6. The live engine state, which must survive a process kill and be read every
 * second, stays in `CallSignalStore`; this row is only its observable projection and holds no caller at all (an
 * unsalted `h1` of a phone number is reversible, so it is kept out of tables that are not encrypted).
 */
@Entity(tableName = "risk_window_state")
data class RiskWindowState(
    @PrimaryKey val id: Int = SINGLETON_ID,
    val isOpen: Boolean,
    val openedAt: Long,
    /** A call is on right now: the window stays open however long it lasts (until the absolute cap). */
    val callActive: Boolean,
    /** Wall-clock end of the window once the call is over (end + 10 min, capped); 0 when closed. */
    val expiresAt: Long,
) {
    companion object {
        const val SINGLETON_ID = 1
        val CLOSED = RiskWindowState(
            isOpen = false, openedAt = 0, callActive = false, expiresAt = 0,
        )
    }
}

@Dao
interface OutboxDao {
    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insert(event: OutboxEventEntity): Long

    /** Oldest first. SENDING rows are included: a worker killed mid-send leaves them behind, and re-sending is safe. */
    @Query("SELECT * FROM outbox_events WHERE status IN ('PENDING', 'SENDING') ORDER BY createdAt, id LIMIT :limit")
    suspend fun deliverable(limit: Int): List<OutboxEventEntity>

    @Query("UPDATE outbox_events SET status = :status WHERE id IN (:ids)")
    suspend fun setStatus(ids: List<String>, status: String)

    /** A failed attempt: back to PENDING with one more retry on the counter. */
    @Query("UPDATE outbox_events SET status = 'PENDING', retryCount = retryCount + 1 WHERE id IN (:ids)")
    suspend fun retryLater(ids: List<String>)

    @Query("SELECT COUNT(*) FROM outbox_events WHERE status IN ('PENDING', 'SENDING')")
    suspend fun deliverableCount(): Int

    @Query("SELECT COUNT(*) FROM outbox_events")
    suspend fun count(): Int

    @Query(
        "DELETE FROM outbox_events WHERE (status = 'SENT' AND createdAt < :sentBefore) " +
            "OR (status = 'FAILED' AND createdAt < :failedBefore)",
    )
    suspend fun purge(sentBefore: Long, failedBefore: Long): Int

    /** Keeps the table bounded when the phone stays offline for weeks: drops the oldest finished rows first. */
    @Query(
        "DELETE FROM outbox_events WHERE id IN " +
            "(SELECT id FROM outbox_events WHERE status IN ('SENT', 'FAILED') ORDER BY createdAt LIMIT :n)",
    )
    suspend fun dropOldestFinished(n: Int): Int

    @Query("DELETE FROM outbox_events")
    suspend fun deleteAll(): Int

    @Query("DELETE FROM outbox_events WHERE id IN (SELECT id FROM outbox_events ORDER BY createdAt LIMIT :n)")
    suspend fun dropOldest(n: Int): Int
}

@Dao
interface RiskWindowDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun put(state: RiskWindowState)

    @Query("SELECT * FROM risk_window_state WHERE id = 1")
    suspend fun get(): RiskWindowState?

    @Query("SELECT * FROM risk_window_state WHERE id = 1")
    fun observe(): Flow<RiskWindowState?>
}

@Dao
interface ThreatSnapshotDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun put(snapshot: ThreatSnapshotEntity)

    @Query("SELECT * FROM threat_snapshot WHERE id = 1")
    suspend fun get(): ThreatSnapshotEntity?

    @Query("SELECT version FROM threat_snapshot WHERE id = 1")
    suspend fun latestVersion(): String?

    /** `304 Not Modified`: the list is unchanged, only the time of the last successful check moves. */
    @Query("UPDATE threat_snapshot SET fetchedAt = :fetchedAt WHERE id = 1")
    suspend fun touch(fetchedAt: Long): Int

    /** Drops a snapshot that failed validation when loaded, so the next sync downloads a whole new one. */
    @Query("DELETE FROM threat_snapshot")
    suspend fun clear(): Int
}

/**
 * `sentinel.db` (Spec 022; v2 in Spec 026). The schema is exported to `app/schemas` so every version ships with a
 * checked migration. Excluded from backup (data_extraction_rules.xml). Open it off the main thread.
 */
@Database(
    entities = [OutboxEventEntity::class, ThreatSnapshotEntity::class, RiskWindowState::class],
    version = 2,
    exportSchema = true,
)
abstract class SentinelDatabase : RoomDatabase() {
    abstract fun outbox(): OutboxDao
    abstract fun riskWindow(): RiskWindowDao
    abstract fun threats(): ThreatSnapshotDao

    companion object {
        const val FILE = "sentinel.db"

        /**
         * v1 → v2: the never-written `threat_hashes` (h1 + last3, reversible) is dropped and `threat_snapshot` added.
         * `outbox_events` and `risk_window_state` are not touched: queued events must survive the upgrade, which is
         * why there is no `fallbackToDestructiveMigration` (it would erase the outbox).
         */
        val MIGRATION_1_2 = object : Migration(1, 2) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("DROP TABLE IF EXISTS `threat_hashes`")
                db.execSQL(
                    "CREATE TABLE IF NOT EXISTS `threat_snapshot` (`id` INTEGER NOT NULL, `version` TEXT NOT NULL, " +
                        "`bucketBits` INTEGER NOT NULL, `count` INTEGER NOT NULL, `buckets` BLOB NOT NULL, " +
                        "`fetchedAt` INTEGER NOT NULL, PRIMARY KEY(`id`))",
                )
            }
        }

        fun open(context: Context): SentinelDatabase =
            Room.databaseBuilder(context.applicationContext, SentinelDatabase::class.java, FILE)
                .addMigrations(MIGRATION_1_2)
                .build()
    }
}
