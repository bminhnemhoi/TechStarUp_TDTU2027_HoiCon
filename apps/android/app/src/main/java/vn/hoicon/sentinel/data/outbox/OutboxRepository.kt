package vn.hoicon.sentinel.data.outbox

import org.json.JSONException
import org.json.JSONObject
import vn.hoicon.sentinel.data.local.OutboxDao
import vn.hoicon.sentinel.data.local.OutboxEventEntity
import vn.hoicon.sentinel.data.local.OutboxStatus
import vn.hoicon.sentinel.data.local.TinkCryptoHelper
import vn.hoicon.sentinel.domain.events.RiskEvent

/** An event ready to send: the decrypted `risk_event.v1.json` document and its row id. */
class OutboxItem(val id: String, val json: JSONObject)

/**
 * The phone-side queue of risk events (Spec 022 FR-002). Events are written here first and sent later, so losing
 * the network, the server or the whole process never loses one: a row leaves the queue only when the server has
 * confirmed it, or has refused it for good.
 *
 * Every payload is AEAD-encrypted with its id as associated data. Suspend functions only touch Room: call them from
 * a background dispatcher, never from the safe-pause path.
 */
class OutboxRepository(
    private val dao: OutboxDao,
    private val crypto: TinkCryptoHelper,
    private val clock: () -> Long = System::currentTimeMillis,
) {
    /** Stores [event]. False when it could not be encrypted (no key): it is dropped, never kept as plain text. */
    suspend fun enqueue(event: RiskEvent): Boolean {
        val encrypted = crypto.encrypt(event.toJson().toString(), event.id) ?: return false
        trimIfFull()
        dao.insert(OutboxEventEntity(event.id, encrypted, OutboxStatus.PENDING, retryCount = 0, createdAt = clock()))
        return true
    }

    /**
     * Up to [limit] events to send, oldest first, marked SENDING. Rows that can no longer be decrypted (key reset,
     * altered file) or parsed are marked FAILED here so they cannot block the queue.
     */
    suspend fun nextBatch(limit: Int): List<OutboxItem> {
        // No key right now (the key store is busy or broke): keep every row as it is. Failing them would destroy
        // events that a later, working key store can still read.
        if (!crypto.isAvailable) return emptyList()
        val rows = dao.deliverable(limit)
        val items = ArrayList<OutboxItem>(rows.size)
        val unreadable = ArrayList<String>()
        for (row in rows) {
            val json = crypto.decrypt(row.payloadJsonEncrypted, row.id)?.let(::parse)
            if (json == null) unreadable += row.id else items += OutboxItem(row.id, json)
        }
        if (unreadable.isNotEmpty()) dao.setStatus(unreadable, OutboxStatus.FAILED)
        if (items.isNotEmpty()) dao.setStatus(items.map { it.id }, OutboxStatus.SENDING)
        return items
    }

    suspend fun markSent(ids: List<String>) = update(ids) { dao.setStatus(it, OutboxStatus.SENT) }

    /** The attempt failed for a reason that may pass (offline, 5xx): back to PENDING, one more retry counted. */
    suspend fun markRetry(ids: List<String>) = update(ids) { dao.retryLater(it) }

    /** Back to PENDING untouched: they were handed out but never tried (token refused, or an earlier event failed). */
    suspend fun release(ids: List<String>) = update(ids) { dao.setStatus(it, OutboxStatus.PENDING) }

    /** The server refused these events for good. They are kept (as FAILED) for a few days, not retried. */
    suspend fun markFailed(ids: List<String>) = update(ids) { dao.setStatus(it, OutboxStatus.FAILED) }

    suspend fun hasDeliverable(): Boolean = dao.deliverableCount() > 0

    /** Drops confirmed rows after a day and refused rows after a week. Cheap; call it once per worker run. */
    suspend fun housekeeping() {
        val now = clock()
        dao.purge(sentBefore = now - SENT_KEEP_MS, failedBefore = now - FAILED_KEEP_MS)
    }

    private suspend fun update(ids: List<String>, block: suspend (List<String>) -> Unit) {
        // SQLite caps the number of bound variables; batches are 50, but stay safe for any caller.
        ids.chunked(CHUNK).forEach { block(it) }
    }

    /** Offline for weeks must not fill the disk: finished rows go first, then the oldest unsent ones. */
    private suspend fun trimIfFull() {
        val excess = dao.count() - (MAX_ROWS - 1)
        if (excess <= 0) return
        val dropped = dao.dropOldestFinished(excess)
        if (dropped < excess) dao.dropOldest(excess - dropped)
    }

    private fun parse(text: String): JSONObject? = try {
        JSONObject(text)
    } catch (_: JSONException) {
        null
    }

    companion object {
        const val MAX_ROWS = 1_000
        private const val CHUNK = 500
        private const val SENT_KEEP_MS = 24 * 60 * 60 * 1000L
        private const val FAILED_KEEP_MS = 7 * 24 * 60 * 60 * 1000L
    }
}
