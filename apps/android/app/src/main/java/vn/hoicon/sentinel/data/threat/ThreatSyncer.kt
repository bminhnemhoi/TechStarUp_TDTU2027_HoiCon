package vn.hoicon.sentinel.data.threat

import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import vn.hoicon.rules.ThreatBucketIndex
import vn.hoicon.sentinel.data.local.ThreatSnapshotDao
import vn.hoicon.sentinel.data.local.ThreatSnapshotEntity
import vn.hoicon.sentinel.data.remote.ThreatListFetcher
import vn.hoicon.sentinel.data.remote.ThreatListResult

/**
 * The index the call-screening callback reads (Spec 026 FR-010). One immutable [ThreatBucketIndex] behind a
 * `@Volatile` reference: a sync replaces it whole, a reader never sees a half-built list, and "not loaded yet" is just
 * an empty list that matches nothing (safe: the server still checks the exact h1 when the event arrives).
 */
class ThreatIndexHolder {
    @Volatile
    var current: ThreatBucketIndex = ThreatBucketIndex.EMPTY
        private set

    fun swap(index: ThreatBucketIndex) {
        current = index
    }
}

/** The process-wide holder; tests make their own [ThreatIndexHolder]. */
object ThreatIndexes {
    val shared = ThreatIndexHolder()
}

enum class ThreatSyncOutcome {
    /** A new snapshot was stored and is live. */
    UPDATED,

    /** `304`: nothing changed. */
    NOT_MODIFIED,

    /** The download did not pass validation: the list the phone already had stays in force. */
    KEPT_OLD,

    /** The server refused the device token. */
    UNAUTHORIZED,

    /** Too many requests today: try again with the next period. */
    LATER,

    /** Network or server trouble: worth a retry with backoff. */
    RETRY,
}

/** Downloads the threat list and swaps the in-memory index; any bad download keeps the last good list. Blocking-free: suspend. */
class ThreatSyncer(
    private val dao: ThreatSnapshotDao,
    private val api: ThreatListFetcher,
    private val holder: ThreatIndexHolder,
    private val clock: () -> Long = System::currentTimeMillis,
) {
    /** Builds the in-memory index from the stored snapshot (process start). A corrupt row is deleted, never trusted. */
    suspend fun loadFromDisk() {
        val row = dao.get() ?: return
        val index = try {
            ThreatBucketIndex.fromPacked(row.buckets, row.bucketBits, row.count)
        } catch (_: IllegalArgumentException) {
            dao.clear()
            return
        }
        holder.swap(index)
    }

    // The periodic and the one-off worker can start together: one at a time, so the second just gets a 304.
    private val lock = Mutex()

    suspend fun sync(accessToken: String): ThreatSyncOutcome = lock.withLock {
        if (holder.current === ThreatBucketIndex.EMPTY) loadFromDisk()
        val since = dao.latestVersion()
        when (val result = api.fetch(accessToken, since)) {
            is ThreatListResult.NotModified -> {
                dao.touch(clock())
                ThreatSyncOutcome.NOT_MODIFIED
            }
            is ThreatListResult.Fresh -> store(result)
            is ThreatListResult.Unauthorized -> ThreatSyncOutcome.UNAUTHORIZED
            is ThreatListResult.RateLimited -> ThreatSyncOutcome.LATER
            is ThreatListResult.NetworkError, is ThreatListResult.ServerError -> ThreatSyncOutcome.RETRY
        }
    }

    private suspend fun store(fresh: ThreatListResult.Fresh): ThreatSyncOutcome {
        val index = try {
            ThreatBucketIndex.fromPacked(fresh.packed, fresh.bucketBits, fresh.count)
        } catch (_: IllegalArgumentException) {
            return ThreatSyncOutcome.KEPT_OLD
        }
        dao.put(ThreatSnapshotEntity(version = fresh.version, bucketBits = fresh.bucketBits, count = fresh.count, buckets = fresh.packed, fetchedAt = clock()))
        holder.swap(index)
        return ThreatSyncOutcome.UPDATED
    }
}
