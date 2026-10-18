package vn.hoicon.sentinel.data.elder

import kotlinx.coroutines.runBlocking
import org.junit.Test
import vn.hoicon.sentinel.data.remote.ElderQuestion
import vn.hoicon.sentinel.data.remote.PendingQuestionResult
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

/** Spec 024 T013 without Firebase: the phone pulls `pending-question` itself after the events opened an incident. */
class ElderQuestionPollerTest {
    private val question = ElderQuestion("inc-1", "q_asked_transfer", "Đây là trợ lý AI HỏiCon. Bác có đang được yêu cầu chuyển tiền không ạ?", false, listOf("yes", "no", "unsure"), "")
    private val pauses = ArrayList<Long>()

    private fun poller(attempts: Int = 6, vararg answers: PendingQuestionResult): ElderQuestionPoller {
        val queue = ArrayDeque(answers.toList())
        return ElderQuestionPoller({ queue.removeFirstOrNull() ?: PendingQuestionResult.NoQuestion }, attempts, 2_000) { pauses += it }
    }

    @Test
    fun theQuestionIsFoundOnceTheGraphHasReachedAskElder() = runBlocking {
        val outcome = poller(6, PendingQuestionResult.NoQuestion, PendingQuestionResult.NoQuestion, PendingQuestionResult.Question(question)).poll("inc-1")
        assertEquals(PollOutcome.Ask(question), outcome)
        assertEquals(listOf(2_000L, 2_000L), pauses)
    }

    @Test
    fun noQuestionAfterAllTheTriesIsNothingToShowAndNeverWaitsAfterTheLastTry() = runBlocking {
        assertEquals(PollOutcome.None, poller(3).poll("inc-1"))
        assertEquals(2, pauses.size)
    }

    @Test
    fun aDeadConnectionOrServerAsksForALaterRetryAtOnce() = runBlocking {
        assertEquals(PollOutcome.Retry, poller(6, PendingQuestionResult.NetworkError).poll("inc-1"))
        assertEquals(PollOutcome.Retry, poller(6, PendingQuestionResult.NoQuestion, PendingQuestionResult.ServerError).poll("inc-1"))
    }

    @Test
    fun aRefusedTokenStopsTheAsking() = runBlocking {
        assertEquals(PollOutcome.Unauthorized, poller(6, PendingQuestionResult.Unauthorized).poll("inc-1"))
        assertTrue(pauses.isEmpty())
    }

    @Test
    fun theSameQuestionIsNeverOpenedTwiceButANewOneIs() {
        val store = object : ElderQuestionStore {
            override var lastShown: String? = null
        }
        assertTrue(store.claim(question))
        assertFalse(store.claim(question))
        assertTrue(store.claim(question.copy(questionId = "q_other")))
        assertTrue(store.claim(question.copy(incidentId = "inc-2")))
    }
}
