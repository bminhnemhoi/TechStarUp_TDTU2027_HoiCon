package vn.hoicon.sentinel.domain.drill

import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertIs
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

/** Spec 028 T017: the order of the four E11 screens, without Android. Script is made up. */
class DrillFlowTest {
    private fun step(line: String) = DrillStep(
        line,
        listOf(DrillChoice("a", "Cúp máy", true, "Đúng, cúp máy."), DrillChoice("b", "Làm theo", false, "Đừng làm theo.")),
    )

    private val script = DrillScript(
        "drill_mau", "scn_mau", "Mẫu", "Phòng Điều tra Mẫu", "000",
        listOf(step("Một"), step("Hai")), DrillDebrief(listOf("Dấu hiệu 1"), "Bác làm tốt."),
    )

    @Test
    fun startsWithTheInvitationAndOnlyStartMovesOn() {
        val flow = DrillFlow(script)
        assertEquals(DrillUi.Invite, flow.ui)
        flow.choose("a"); flow.next()
        assertEquals(DrillUi.Invite, flow.ui)
        flow.start()
        val step = assertIs<DrillUi.Step>(flow.ui)
        assertEquals(0, step.index); assertEquals(2, step.total); assertEquals("Một", step.lineVi)
        assertNull(step.feedback)
    }

    @Test
    fun aChoiceShowsFeedbackAndNextMovesOn() {
        val flow = DrillFlow(script).also { it.start() }
        flow.choose("b")
        val answered = assertIs<DrillUi.Step>(flow.ui)
        val feedback = assertNotNull(answered.feedback)
        assertEquals(false, feedback.correct); assertEquals("Đừng làm theo.", feedback.text); assertEquals(false, feedback.isLastStep)
        flow.next()
        val second = assertIs<DrillUi.Step>(flow.ui)
        assertEquals(1, second.index); assertNull(second.feedback)
    }

    @Test
    fun aSecondTapOnTheSameStepDoesNotAnswerTwice() {
        val flow = DrillFlow(script).also { it.start() }
        flow.choose("a"); flow.choose("b")
        assertEquals(listOf(DrillAnswer(0, "a")), flow.answers)
        assertEquals(true, assertIs<DrillUi.Step>(flow.ui).feedback?.correct)
    }

    @Test
    fun nextBeforeAnsweringChangesNothing() {
        val flow = DrillFlow(script).also { it.start() }
        flow.next()
        assertEquals(0, assertIs<DrillUi.Step>(flow.ui).index)
    }

    @Test
    fun theLastFeedbackLeadsToTheDebrief() {
        val flow = DrillFlow(script).also { it.start() }
        flow.choose("a"); flow.next(); flow.choose("b")
        assertTrue(assertNotNull(assertIs<DrillUi.Step>(flow.ui).feedback).isLastStep)
        flow.next()
        val debrief = assertIs<DrillUi.Debrief>(flow.ui)
        assertEquals(1, debrief.evaluation.correctCount)
        assertEquals(false, debrief.evaluation.isPassed)
        assertEquals(listOf(1), debrief.evaluation.wrongSteps)
        assertEquals(listOf("Dấu hiệu 1"), debrief.evaluation.redFlagsVi)
    }

    @Test
    fun stoppingKeepsTheAnswersSoFar() {
        val flow = DrillFlow(script).also { it.start() }
        flow.choose("a"); flow.next()
        flow.stop()
        assertEquals(DrillUi.Stopped(StopReason.BY_PERSON), flow.ui)
        assertEquals(listOf(DrillAnswer(0, "a")), flow.answers)
        flow.start(); flow.choose("a")
        assertEquals(DrillUi.Stopped(StopReason.BY_PERSON), flow.ui)
    }

    @Test
    fun aRealCallEndsTheDrillAsUnavailableAndKeepsTheAnswers() {
        val flow = DrillFlow(script).also { it.start() }
        flow.choose("a")
        flow.interrupt()
        assertEquals(DrillUi.Stopped(StopReason.UNAVAILABLE), flow.ui)
        assertEquals(listOf(DrillAnswer(0, "a")), flow.answers)
        val debriefed = DrillFlow(script).also { f -> f.start(); f.choose("a"); f.next(); f.choose("a"); f.next() }
        debriefed.interrupt()
        assertIs<DrillUi.Debrief>(debriefed.ui) // the debrief is not cut off: the drill was over already
    }

    @Test
    fun feedbackNamesWhatWasChosenAndTheSafeWayWhenWrong() {
        val wrong = DrillFlow(script).also { it.start(); it.choose("b") }
        val feedback = assertNotNull(assertIs<DrillUi.Step>(wrong.ui).feedback)
        assertEquals("Làm theo", feedback.chosenLabel)
        assertEquals("Cúp máy", feedback.safeWayLabel)
        val right = DrillFlow(script).also { it.start(); it.choose("a") }
        val ok = assertNotNull(assertIs<DrillUi.Step>(right.ui).feedback)
        assertEquals("Cúp máy", ok.chosenLabel)
        assertNull(ok.safeWayLabel)
    }

    @Test
    fun theOrderOfTheChoicesIsStablePerDrillAndStep() {
        val a = DrillFlow(script).also { it.start() }.ui as DrillUi.Step
        val b = DrillFlow(script).also { it.start() }.ui as DrillUi.Step
        assertEquals(a.choices, b.choices) // same after a rotation or a reopened screen
        assertEquals(setOf("a", "b"), a.choices.map { it.id }.toSet()) // shuffled, never lost
    }

    @Test
    fun theRightChoiceDoesNotAlwaysSitInTheSamePlace() {
        // The server may put the right choice first in every step of every script; across drills it must not stay first.
        val positions = (1..40).flatMap { n ->
            val flow = DrillFlow(script.copy(id = "drill_mau_$n")).also { it.start() }
            val first = (flow.ui as DrillUi.Step).choices
            flow.choose(first[0].id); flow.next()
            val second = (flow.ui as DrillUi.Step).choices
            listOf(first.indexOfFirst { it.correct }, second.indexOfFirst { it.correct })
        }.toSet()
        assertEquals(setOf(0, 1), positions)
    }

    @Test
    fun withoutAScriptTheDrillIsUnavailable() {
        val flow = DrillFlow(null)
        assertEquals(DrillUi.Stopped(StopReason.UNAVAILABLE), flow.ui)
        flow.start(); flow.choose("a"); flow.next()
        assertEquals(DrillUi.Stopped(StopReason.UNAVAILABLE), flow.ui)
        assertTrue(flow.answers.isEmpty())
    }
}
