package vn.hoicon.sentinel.outbox

import kotlinx.coroutines.runBlocking
import org.junit.Test
import vn.hoicon.sentinel.data.local.OutboxStatus
import vn.hoicon.sentinel.data.local.TinkCryptoHelper
import vn.hoicon.sentinel.data.outbox.OutboxRepository
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class OutboxRepositoryTest {
    private val dao = FakeOutboxDao()
    private var now = 1_000_000L
    private val repo = OutboxRepository(dao, jvmCrypto()) { now }
    private val factory = sequentialFactory()

    @Test
    fun storedPayloadIsEncryptedAndHoldsNoPlainCallerData() = runBlocking {
        val event = sampleEvent(factory)
        assertTrue(repo.enqueue(event))
        val row = dao.rows.getValue(event.id)
        assertEquals(OutboxStatus.PENDING, row.status)
        val raw = row.payloadJsonEncrypted
        assertFalse(event.caller!!.h1 in raw || "last3" in raw || "vn.hoicon" in raw || "high" in raw, raw)
    }

    @Test
    fun nextBatchDecryptsOldestFirstAndMarksSending() = runBlocking {
        val a = sampleEvent(factory).also { repo.enqueue(it); now += 10 }
        val b = sampleEvent(factory).also { repo.enqueue(it); now += 10 }
        val batch = repo.nextBatch(10)
        assertEquals(listOf(a.id, b.id), batch.map { it.id })
        assertEquals(a.toJson().toString(), batch[0].json.toString())
        assertTrue(dao.rows.values.all { it.status == OutboxStatus.SENDING })
    }

    @Test
    fun sendingRowsLeftByAKilledWorkerAreDeliveredAgain() = runBlocking {
        repo.enqueue(sampleEvent(factory))
        repo.nextBatch(10) // worker "dies" here: row stays SENDING
        assertEquals(1, repo.nextBatch(10).size)
    }

    @Test
    fun anUnreadableRowIsFailedNotAllowedToBlockTheQueue() = runBlocking {
        val lost = sampleEvent(factory).also { repo.enqueue(it); now += 10 }
        val fine = sampleEvent(factory).also { repo.enqueue(it) }
        val otherKey = OutboxRepository(dao, TinkCryptoHelper(jvmAead())) { now } // the key was reset
        val batch = otherKey.nextBatch(10)
        assertTrue(batch.isEmpty())
        assertEquals(OutboxStatus.FAILED, dao.rows.getValue(lost.id).status)
        assertEquals(OutboxStatus.FAILED, dao.rows.getValue(fine.id).status)
        assertEquals(0, repo.nextBatch(10).size)
    }

    @Test
    fun withoutAKeyTheEventIsDroppedNotStoredInThePlain() = runBlocking {
        val noKey = OutboxRepository(dao, TinkCryptoHelper(null)) { now }
        assertFalse(noKey.enqueue(sampleEvent(factory)))
        assertEquals(0, dao.rows.size)
    }

    @Test
    fun markRetryCountsTheAttemptAndReleaseDoesNot() = runBlocking {
        val e = sampleEvent(factory).also { repo.enqueue(it) }
        repo.nextBatch(10)
        repo.markRetry(listOf(e.id))
        assertEquals(1, dao.rows.getValue(e.id).retryCount)
        repo.nextBatch(10)
        repo.release(listOf(e.id))
        assertEquals(1, dao.rows.getValue(e.id).retryCount)
        assertEquals(OutboxStatus.PENDING, dao.rows.getValue(e.id).status)
    }

    @Test
    fun housekeepingDropsConfirmedRowsAfterADayAndRefusedOnesAfterAWeek() = runBlocking {
        val sent = sampleEvent(factory).also { repo.enqueue(it); now += 1 }
        val failed = sampleEvent(factory).also { repo.enqueue(it); now += 1 }
        val pending = sampleEvent(factory).also { repo.enqueue(it) }
        repo.markSent(listOf(sent.id))
        repo.markFailed(listOf(failed.id))
        now += 2 * 24 * 3_600_000L
        repo.housekeeping()
        assertEquals(setOf(failed.id, pending.id), dao.rows.keys, "sent is gone after a day, failed stays a week")
        now += 6 * 24 * 3_600_000L
        repo.housekeeping()
        assertEquals(setOf(pending.id), dao.rows.keys, "an unsent event is never purged by age")
    }

    @Test
    fun aFullQueueDropsFinishedRowsBeforeUnsentOnes() = runBlocking {
        repeat(OutboxRepository.MAX_ROWS) { i ->
            val e = sampleEvent(factory, atMs = 1_760_000_000_000L + i)
            repo.enqueue(e)
            now += 1
            if (i == 0) repo.markSent(listOf(e.id))
        }
        assertEquals(OutboxRepository.MAX_ROWS, dao.count())
        val newest = sampleEvent(factory).also { repo.enqueue(it) }
        assertEquals(OutboxRepository.MAX_ROWS, dao.count())
        assertTrue(newest.id in dao.rows)
        assertTrue(dao.rows.values.none { it.status == OutboxStatus.SENT }, "the confirmed row went first")
    }

    @Test
    fun enqueueingTheSameIdTwiceKeepsOneRow() = runBlocking {
        val e = sampleEvent(factory)
        repo.enqueue(e)
        repo.enqueue(e)
        assertEquals(1, dao.count())
    }

    @Test
    fun noKeyRightNowKeepsEveryRowInsteadOfFailingThem() = runBlocking {
        val a = sampleEvent(factory).also { repo.enqueue(it) }
        val noKey = OutboxRepository(dao, TinkCryptoHelper(null)) { now }
        assertTrue(noKey.nextBatch(10).isEmpty())
        assertEquals(OutboxStatus.PENDING, dao.rows.getValue(a.id).status, "a later, working key store can still read it")
        assertEquals(1, repo.nextBatch(10).size)
    }
}
