package vn.hoicon.sentinel.work

import org.junit.Test
import vn.hoicon.sentinel.data.remote.DrillResultOutcome
import vn.hoicon.sentinel.domain.drill.DrillAnswer
import vn.hoicon.sentinel.domain.drill.DrillAnswers
import kotlin.test.assertEquals
import kotlin.test.assertTrue

/** Spec 028 T016: which server answers are worth another try, and the way the answers cross WorkManager. */
class DrillResultWorkerTest {
    @Test
    fun successAndConflictAreDone() {
        assertEquals(DrillResultAction.DONE, drillResultAction(DrillResultOutcome.Accepted))
    }

    @Test
    fun onlyTransportTroubleAndServerErrorsAreRetried() {
        assertEquals(DrillResultAction.RETRY, drillResultAction(DrillResultOutcome.NetworkError))
        assertEquals(DrillResultAction.RETRY, drillResultAction(DrillResultOutcome.ServerError))
    }

    @Test
    fun whatTheServerRefusedForGoodIsDropped() {
        assertEquals(DrillResultAction.DROP, drillResultAction(DrillResultOutcome.Rejected))
        assertEquals(DrillResultAction.DROP, drillResultAction(DrillResultOutcome.NotFound))
        assertEquals(DrillResultAction.DROP, drillResultAction(DrillResultOutcome.Unauthorized))
    }

    @Test
    fun everyOutcomeHasAnAction() {
        // A new outcome must be decided here, not fall through: `when` is exhaustive, this lists them for the reader.
        val all = listOf(
            DrillResultOutcome.Accepted, DrillResultOutcome.Unauthorized, DrillResultOutcome.NotFound,
            DrillResultOutcome.Rejected, DrillResultOutcome.NetworkError, DrillResultOutcome.ServerError,
        )
        assertTrue(all.map(::drillResultAction).toSet().size == 3)
    }

    @Test
    fun answersSurviveTheTripThroughWorkData() {
        val answers = listOf(DrillAnswer(0, "a"), DrillAnswer(1, "b"), DrillAnswer(2, "a"))
        assertEquals("0a,1b,2a", DrillAnswers.encode(answers))
        assertEquals(answers, DrillAnswers.decode("0a,1b,2a"))
        assertEquals(emptyList(), DrillAnswers.decode(""))
        assertEquals(emptyList(), DrillAnswers.decode(null))
    }

    @Test
    fun aDamagedAnswerStringNeverMakesUpAnAnswer() {
        assertEquals(listOf(DrillAnswer(1, "b")), DrillAnswers.decode("zz,1b,3,x9,4A, 5c9"))
    }
}
