package vn.hoicon.sentinel.data

import androidx.room.testing.MigrationTestHelper
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import vn.hoicon.sentinel.data.local.SentinelDatabase

/** Spec 026 T021: `sentinel.db` 1 → 2 drops `threat_hashes`, adds `threat_snapshot`, and keeps the queued outbox. */
@RunWith(AndroidJUnit4::class)
class SentinelMigrationTest {
    @get:Rule
    val helper = MigrationTestHelper(InstrumentationRegistry.getInstrumentation(), SentinelDatabase::class.java)

    private val dbName = "migration-test"

    @Test
    fun outboxSurvivesTheUpgradeAndTheThreatTableIsReplaced() {
        helper.createDatabase(dbName, 1).apply {
            execSQL("INSERT INTO outbox_events (id, payloadJsonEncrypted, status, retryCount, createdAt) VALUES ('e-1', 'ciphertext-1', 'PENDING', 2, 111)")
            execSQL("INSERT INTO outbox_events (id, payloadJsonEncrypted, status, retryCount, createdAt) VALUES ('e-2', 'ciphertext-2', 'SENT', 0, 222)")
            execSQL("INSERT INTO risk_window_state (id, isOpen, openedAt, callActive, expiresAt) VALUES (1, 1, 5, 1, 9)")
            close()
        }

        val db = helper.runMigrationsAndValidate(dbName, 2, true, SentinelDatabase.MIGRATION_1_2)

        db.query("SELECT id, payloadJsonEncrypted, status, retryCount, createdAt FROM outbox_events ORDER BY id").use { c ->
            assertEquals(2, c.count)
            c.moveToFirst()
            assertEquals(listOf("e-1", "ciphertext-1", "PENDING", "2", "111"), (0..4).map { c.getString(it) })
            c.moveToNext()
            assertEquals(listOf("e-2", "ciphertext-2", "SENT", "0", "222"), (0..4).map { c.getString(it) })
        }
        db.query("SELECT isOpen, expiresAt FROM risk_window_state WHERE id = 1").use { c ->
            assertTrue(c.moveToFirst())
            assertEquals(1, c.getInt(0))
            assertEquals(9L, c.getLong(1))
        }
        db.query("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'threat_hashes'").use { assertFalse(it.moveToFirst()) }
        db.query("SELECT COUNT(*) FROM threat_snapshot").use { c ->
            c.moveToFirst()
            assertEquals(0, c.getInt(0))
        }
    }
}
