package vn.hoicon.sentinel.data.outbox

import vn.hoicon.sentinel.data.remote.EventUploader
import vn.hoicon.sentinel.data.remote.EventsResult
import vn.hoicon.sentinel.data.remote.PairingApiClient

/** How one [OutboxSender.flush] run ended; the worker maps it to success / retry. */
enum class FlushOutcome {
    /** Nothing left to send. */
    EMPTY,

    /** Not paired yet: events wait in the queue. */
    WAITING,

    /** The server refused the device token: events wait, and the phone must be paired again. */
    TOKEN_REFUSED,

    /** The family withdrew a consent (403 `consent_withdrawn`): events wait; the token stays and no re-pairing is asked. */
    CONSENT_REQUIRED,

    /** Offline or the server is down: the rest stays queued; retry with backoff. */
    RETRY,
}

/**
 * Sends the queue in batches of up to [PairingApiClient.MAX_EVENTS_PER_BATCH] (Spec 022 FR-002). Pure logic over
 * [OutboxRepository] and an [EventUploader], so "no event is lost" is a JVM test, not a hope.
 *
 * A batch the server rejects as a whole is split and re-sent one event at a time, so one malformed event cannot
 * hold back the others; only the event the server refuses alone is marked FAILED.
 */
class OutboxSender(
    private val outbox: OutboxRepository,
    private val uploader: EventUploader,
    private val accessToken: () -> String?,
) {
    suspend fun flush(): FlushOutcome {
        outbox.housekeeping()
        while (true) {
            val token = accessToken() ?: return FlushOutcome.WAITING
            val batch = outbox.nextBatch(PairingApiClient.MAX_EVENTS_PER_BATCH)
            if (batch.isEmpty()) return FlushOutcome.EMPTY
            val outcome = send(token, batch)
            if (outcome != null) return outcome
        }
    }

    /** Null = this batch is settled, keep going. */
    private suspend fun send(token: String, batch: List<OutboxItem>): FlushOutcome? {
        val ids = batch.map { it.id }
        return when (uploader.sendEvents(token, batch.map { it.json })) {
            EventsResult.Accepted -> {
                outbox.markSent(ids)
                null
            }
            EventsResult.Rejected -> if (batch.size == 1) {
                outbox.markFailed(ids)
                null
            } else {
                sendOneByOne(token, batch)
            }
            EventsResult.Unauthorized -> {
                outbox.release(ids)
                FlushOutcome.TOKEN_REFUSED
            }
            EventsResult.ConsentWithdrawn -> {
                outbox.release(ids)
                FlushOutcome.CONSENT_REQUIRED
            }
            EventsResult.NetworkError, EventsResult.ServerError -> {
                outbox.markRetry(ids)
                FlushOutcome.RETRY
            }
        }
    }

    private suspend fun sendOneByOne(token: String, batch: List<OutboxItem>): FlushOutcome? {
        val refused = ArrayList<String>()
        var accepted = 0
        for ((index, item) in batch.withIndex()) {
            when (val result = uploader.sendEvents(token, listOf(item.json))) {
                EventsResult.Accepted -> {
                    outbox.markSent(listOf(item.id))
                    accepted++
                }
                EventsResult.Rejected -> refused += item.id
                else -> {
                    // Stop at the first transient failure, refused token or withdrawn consent; what was not tried yet goes back untouched.
                    settleRefused(refused, accepted)
                    val rest = batch.drop(index).map { it.id }
                    if (result == EventsResult.Unauthorized) {
                        outbox.release(rest)
                        return FlushOutcome.TOKEN_REFUSED
                    }
                    if (result == EventsResult.ConsentWithdrawn) {
                        outbox.release(rest)
                        return FlushOutcome.CONSENT_REQUIRED
                    }
                    outbox.markRetry(rest.take(1))
                    outbox.release(rest.drop(1))
                    return FlushOutcome.RETRY
                }
            }
        }
        return if (settleRefused(refused, accepted)) FlushOutcome.RETRY else null
    }

    /**
     * Events the server refused one by one. If it refused EVERY event of a multi-event batch, the likelier cause is
     * a contract mismatch between this app and the server, not several broken events: keep them for a later try
     * instead of discarding them for good. Returns true when they were kept.
     */
    private suspend fun settleRefused(refused: List<String>, accepted: Int): Boolean {
        if (refused.isEmpty()) return false
        if (accepted == 0 && refused.size >= DRIFT_THRESHOLD) {
            outbox.markRetry(refused)
            return true
        }
        outbox.markFailed(refused)
        return false
    }

    private companion object {
        const val DRIFT_THRESHOLD = 3
    }
}
