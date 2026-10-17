package vn.hoicon.sentinel.data

import kotlinx.coroutines.runBlocking
import org.junit.Test
import vn.hoicon.rules.ThreatBucketIndex
import vn.hoicon.sentinel.data.local.ThreatSnapshotDao
import vn.hoicon.sentinel.data.local.ThreatSnapshotEntity
import vn.hoicon.sentinel.data.remote.ThreatListFetcher
import vn.hoicon.sentinel.data.remote.ThreatListResult
import vn.hoicon.sentinel.data.threat.ThreatIndexHolder
import vn.hoicon.sentinel.data.threat.ThreatSyncOutcome
import vn.hoicon.sentinel.data.threat.ThreatSyncer
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertSame
import kotlin.test.assertTrue

/** Spec 026 T022: sync keeps the last good list, handles 304, and "not loaded yet" matches nothing. */
class ThreatSyncerTest {
    private val flaggedH1 = "aa1b1fcd5c51853e998738c59cffa5a4d95bd39ef7ef3b6d905c9c6c3af987e4"
    private val otherH1 = "0123456789abcdef".repeat(4)
    private val bits = 22

    private fun pack(vararg buckets: Int) = ByteArray(buckets.size * 3).also { out ->
        buckets.forEachIndexed { i, v ->
            out[i * 3] = (v ushr 16).toByte(); out[i * 3 + 1] = (v ushr 8).toByte(); out[i * 3 + 2] = v.toByte()
        }
    }

    private fun fresh(version: String, vararg buckets: Int, count: Int = buckets.size) =
        ThreatListResult.Fresh(version, bits, count, pack(*buckets))

    private class FakeDao : ThreatSnapshotDao {
        var row: ThreatSnapshotEntity? = null
        var cleared = 0
        override suspend fun put(snapshot: ThreatSnapshotEntity) { row = snapshot }
        override suspend fun get() = row
        override suspend fun latestVersion() = row?.version
        override suspend fun touch(fetchedAt: Long): Int { row = row?.copy(fetchedAt = fetchedAt); return if (row == null) 0 else 1 }
        override suspend fun clear(): Int { cleared++; row = null; return 1 }
    }

    private class FakeApi(var next: ThreatListResult) : ThreatListFetcher {
        var lastSince: String? = "unset"
        override fun fetch(accessToken: String, since: String?): ThreatListResult { lastSince = since; return next }
    }

    private val flaggedBucket = ThreatBucketIndex.bucket(flaggedH1, bits)

    @Test
    fun beforeAnythingIsLoadedNothingIsFlagged() {
        val holder = ThreatIndexHolder()
        assertFalse(holder.current.contains(flaggedH1))
        assertSame(ThreatBucketIndex.EMPTY, holder.current)
    }

    @Test
    fun aFreshSnapshotIsStoredAndSwappedIn() = runBlocking {
        val dao = FakeDao(); val holder = ThreatIndexHolder(); val api = FakeApi(fresh("a".repeat(16), flaggedBucket))
        val outcome = ThreatSyncer(dao, api, holder, clock = { 1_000L }).sync("t")
        assertEquals(ThreatSyncOutcome.UPDATED, outcome)
        assertNull(api.lastSince)
        assertTrue(holder.current.contains(flaggedH1))
        assertFalse(holder.current.contains(otherH1))
        assertEquals("a".repeat(16), dao.row?.version)
        assertEquals(1_000L, dao.row?.fetchedAt)
    }

    @Test
    fun notModifiedOnlyMovesTheClockAndSendsTheStoredVersion() = runBlocking {
        val dao = FakeDao(); val holder = ThreatIndexHolder()
        val api = FakeApi(fresh("b".repeat(16), flaggedBucket))
        var now = 1_000L
        val syncer = ThreatSyncer(dao, api, holder, clock = { now })
        syncer.sync("t")
        val before = holder.current
        api.next = ThreatListResult.NotModified; now = 9_000L
        assertEquals(ThreatSyncOutcome.NOT_MODIFIED, syncer.sync("t"))
        assertEquals("b".repeat(16), api.lastSince)
        assertSame(before, holder.current)
        assertEquals(9_000L, dao.row?.fetchedAt)
        assertEquals("b".repeat(16), dao.row?.version)
    }

    @Test
    fun aCorruptDownloadKeepsTheOldList() = runBlocking {
        val dao = FakeDao(); val holder = ThreatIndexHolder(); val api = FakeApi(fresh("c".repeat(16), flaggedBucket))
        val syncer = ThreatSyncer(dao, api, holder)
        syncer.sync("t")
        val before = holder.current
        for (bad in listOf(
            fresh("d".repeat(16), 9, 3),                       // not ascending
            fresh("d".repeat(16), flaggedBucket, count = 2),   // count does not match the bytes
            fresh("d".repeat(16), 1 shl bits),                 // does not fit in the bits
            ThreatListResult.Fresh("d".repeat(16), 31, 1, pack(1)), // bits out of range
            ThreatListResult.Fresh("d".repeat(16), bits, 1, ByteArray(2)), // not a multiple of 3
        )) {
            api.next = bad
            assertEquals(ThreatSyncOutcome.KEPT_OLD, syncer.sync("t"))
            assertSame(before, holder.current)
            assertEquals("c".repeat(16), dao.row?.version)
        }
    }

    @Test
    fun transportAndAuthFailuresChangeNothing() = runBlocking {
        val dao = FakeDao(); val holder = ThreatIndexHolder(); val api = FakeApi(fresh("e".repeat(16), flaggedBucket))
        val syncer = ThreatSyncer(dao, api, holder)
        syncer.sync("t")
        val before = holder.current
        val expected = mapOf(
            ThreatListResult.NetworkError to ThreatSyncOutcome.RETRY,
            ThreatListResult.ServerError to ThreatSyncOutcome.RETRY,
            ThreatListResult.Unauthorized to ThreatSyncOutcome.UNAUTHORIZED,
            ThreatListResult.RateLimited to ThreatSyncOutcome.LATER,
        )
        for ((result, outcome) in expected) {
            api.next = result
            assertEquals(outcome, syncer.sync("t"))
            assertSame(before, holder.current)
        }
    }

    @Test
    fun theStoredSnapshotLoadsAtProcessStart() = runBlocking {
        val dao = FakeDao()
        dao.row = ThreatSnapshotEntity(version = "f".repeat(16), bucketBits = bits, count = 1, buckets = pack(flaggedBucket), fetchedAt = 5)
        val holder = ThreatIndexHolder()
        ThreatSyncer(dao, FakeApi(ThreatListResult.NetworkError), holder).loadFromDisk()
        assertTrue(holder.current.contains(flaggedH1))
    }

    @Test
    fun aCorruptStoredRowIsDeletedNotTrusted() = runBlocking {
        val dao = FakeDao()
        dao.row = ThreatSnapshotEntity(version = "f".repeat(16), bucketBits = bits, count = 5, buckets = pack(1), fetchedAt = 5)
        val holder = ThreatIndexHolder()
        ThreatSyncer(dao, FakeApi(ThreatListResult.NetworkError), holder).loadFromDisk()
        assertSame(ThreatBucketIndex.EMPTY, holder.current)
        assertEquals(1, dao.cleared)
        assertNull(dao.row)
    }

    @Test
    fun aNotModifiedAfterAColdStartStillLoadsTheStoredList() = runBlocking {
        val dao = FakeDao()
        dao.row = ThreatSnapshotEntity(version = "9".repeat(16), bucketBits = bits, count = 1, buckets = pack(flaggedBucket), fetchedAt = 5)
        val holder = ThreatIndexHolder()
        val outcome = ThreatSyncer(dao, FakeApi(ThreatListResult.NotModified), holder).sync("t")
        assertEquals(ThreatSyncOutcome.NOT_MODIFIED, outcome)
        assertTrue(holder.current.contains(flaggedH1))
    }
}
