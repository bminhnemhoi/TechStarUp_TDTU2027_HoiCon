package vn.hoicon.sentinel.outbox

import kotlinx.coroutines.runBlocking
import org.junit.Test
import vn.hoicon.sentinel.data.local.OutboxStatus
import vn.hoicon.sentinel.data.outbox.FlushOutcome
import vn.hoicon.sentinel.data.outbox.OutboxRepository
import vn.hoicon.sentinel.data.outbox.OutboxSender
import vn.hoicon.sentinel.data.remote.EventsResult
import kotlin.test.assertEquals
import kotlin.test.assertTrue

/** SC-002: events survive a dead network, a dead server and a killed worker; none is lost, none is sent twice as new. */
class OutboxSenderTest {
    private val dao = FakeOutboxDao()
    private var now = 1_000L
    private val repo = OutboxRepository(dao, jvmCrypto()) { now }
    private val factory = sequentialFactory()
    private var token: String? = "device-token"

    private suspend fun queue(n: Int): List<String> = List(n) {
        sampleEvent(factory).also { repo.enqueue(it); now += 1 }.id
    }

    private fun sender(uploader: FakeUploader) = OutboxSender(repo, uploader) { token }

    private fun statuses() = dao.rows.values.map { it.status }

    @Test
    fun sendsEverythingInBatchesOfFiftyWithTheDeviceToken() = runBlocking {
        val ids = queue(120)
        val server = FakeUploader { EventsResult.Accepted }
        assertEquals(FlushOutcome.EMPTY, sender(server).flush())
        assertEquals(listOf(50, 50, 20), server.batches.map { it.size })
        assertEquals(ids.toSet(), server.stored)
        assertEquals("device-token", server.lastToken)
        assertTrue(statuses().all { it == OutboxStatus.SENT })
    }

    @Test
    fun offlineThenOnlineLosesNothing() = runBlocking {
        val ids = queue(7)
        var online = false
        val server = FakeUploader { if (online) EventsResult.Accepted else EventsResult.NetworkError }
        assertEquals(FlushOutcome.RETRY, sender(server).flush())
        assertEquals(0, server.stored.size)
        assertTrue(statuses().all { it == OutboxStatus.PENDING }, "kept for the next attempt")
        assertTrue(dao.rows.values.all { it.retryCount == 1 })

        online = true
        assertEquals(FlushOutcome.EMPTY, sender(server).flush())
        assertEquals(ids.toSet(), server.stored, "0 lost events")
    }

    @Test
    fun serverDownOrEndpointNotDeployedKeepsTheQueue() = runBlocking {
        queue(3)
        val server = FakeUploader { EventsResult.ServerError }
        assertEquals(FlushOutcome.RETRY, sender(server).flush())
        assertEquals(3, dao.deliverableCount())
    }

    @Test
    fun aResentBatchIsHarmlessBecauseIdsAreStable() = runBlocking {
        val ids = queue(4)
        // The server stores the batch but the reply is lost: the phone sees a network error and re-sends it.
        var first = true
        val server = FakeUploader { if (first) { first = false; EventsResult.NetworkError } else EventsResult.Accepted }
        sender(server).flush()
        server.stored.addAll(ids) // what the server did store before the reply was lost
        sender(server).flush()
        assertEquals(ids.toSet(), server.stored, "the same ids, no duplicates")
        assertEquals(ids, server.batches.last(), "re-sent with the same ids")
    }

    @Test
    fun notPairedWaitsAndKeepsEverything() = runBlocking {
        queue(2)
        token = null
        val server = FakeUploader { EventsResult.Accepted }
        assertEquals(FlushOutcome.WAITING, sender(server).flush())
        assertTrue(server.batches.isEmpty())
        assertEquals(2, dao.deliverableCount())
        token = "now-paired"
        assertEquals(FlushOutcome.EMPTY, sender(server).flush())
        assertEquals(2, server.stored.size)
    }

    @Test
    fun refusedTokenIsReportedAndKeepsEverythingWithoutBurningRetries() = runBlocking {
        queue(2)
        val server = FakeUploader { EventsResult.Unauthorized }
        assertEquals(FlushOutcome.TOKEN_REFUSED, sender(server).flush())
        assertEquals(2, dao.deliverableCount())
        assertTrue(dao.rows.values.all { it.retryCount == 0 })
    }

    @Test
    fun oneBadEventIsIsolatedAndTheRestStillArrive() = runBlocking {
        val ids = queue(5)
        val bad = ids[2]
        val server = FakeUploader { batch ->
            if (batch.any { it.getString("id") == bad }) EventsResult.Rejected else EventsResult.Accepted
        }
        assertEquals(FlushOutcome.EMPTY, sender(server).flush())
        assertEquals((ids - bad).toSet(), server.stored)
        assertEquals(OutboxStatus.FAILED, dao.rows.getValue(bad).status)
        assertEquals(4, statuses().count { it == OutboxStatus.SENT })
    }

    @Test
    fun aTransientFailureWhileIsolatingKeepsTheUntriedEvents() = runBlocking {
        val ids = queue(4)
        var calls = 0
        val server = FakeUploader {
            calls++
            when {
                calls == 1 -> EventsResult.Rejected // the whole batch
                calls == 2 -> EventsResult.Accepted // first one alone
                else -> EventsResult.NetworkError // network drops during isolation
            }
        }
        assertEquals(FlushOutcome.RETRY, sender(server).flush())
        assertEquals(listOf(ids[0]), server.stored.toList())
        assertEquals(3, dao.deliverableCount(), "nothing lost: three still queued")
        assertEquals(OutboxStatus.SENT, dao.rows.getValue(ids[0]).status)
    }

    @Test
    fun emptyQueueIsEmpty() = runBlocking {
        val server = FakeUploader { EventsResult.Accepted }
        assertEquals(FlushOutcome.EMPTY, sender(server).flush())
        assertTrue(server.batches.isEmpty())
    }

    @Test
    fun everyEventRefusedLooksLikeAContractMismatchAndIsKeptNotDiscarded() = runBlocking {
        val ids = queue(4)
        val server = FakeUploader { EventsResult.Rejected }
        assertEquals(FlushOutcome.RETRY, sender(server).flush())
        assertEquals(4, dao.deliverableCount(), "kept for a later try, e.g. after the server is updated")
        assertTrue(ids.none { dao.rows.getValue(it).status == OutboxStatus.FAILED })
    }

    @Test
    fun aRefusedTokenWhileIsolatingStopsAndKeepsTheRest() = runBlocking {
        val ids = queue(3)
        var calls = 0
        val server = FakeUploader {
            calls++
            when (calls) {
                1 -> EventsResult.Rejected
                2 -> EventsResult.Accepted
                else -> EventsResult.Unauthorized
            }
        }
        assertEquals(FlushOutcome.TOKEN_REFUSED, sender(server).flush())
        assertEquals(2, dao.deliverableCount())
        assertEquals(OutboxStatus.SENT, dao.rows.getValue(ids[0]).status)
    }
}
