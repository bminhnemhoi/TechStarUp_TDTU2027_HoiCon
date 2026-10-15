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

/** A flagged number from the server threat list (`GET /v1/threat-list`): hash + last 3 digits only (ADR-006). */
@Entity(tableName = "threat_hashes")
data class ThreatHashEntity(
    @PrimaryKey val h1: String,
    val last3: String,
    val version: String,
)

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
interface ThreatHashDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertAll(items: List<ThreatHashEntity>)

    @Query("SELECT COUNT(*) FROM threat_hashes WHERE h1 = :h1")
    suspend fun countOf(h1: String): Int

    @Query("SELECT MAX(version) FROM threat_hashes")
    suspend fun latestVersion(): String?
}

/**
 * `sentinel.db` (Spec 022). Version 1; the schema is exported to `app/schemas` so later versions ship with a
 * checked migration. Excluded from backup (data_extraction_rules.xml). Open it off the main thread.
 */
@Database(
    entities = [OutboxEventEntity::class, ThreatHashEntity::class, RiskWindowState::class],
    version = 1,
    exportSchema = true,
)
abstract class SentinelDatabase : RoomDatabase() {
    abstract fun outbox(): OutboxDao
    abstract fun riskWindow(): RiskWindowDao
    abstract fun threats(): ThreatHashDao

    companion object {
        const val FILE = "sentinel.db"

        fun open(context: Context): SentinelDatabase =
            Room.databaseBuilder(context.applicationContext, SentinelDatabase::class.java, FILE).build()
    }
}
