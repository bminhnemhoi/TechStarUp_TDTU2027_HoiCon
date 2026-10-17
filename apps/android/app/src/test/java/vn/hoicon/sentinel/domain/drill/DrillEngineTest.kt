package vn.hoicon.sentinel.domain.drill

import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertIs
import kotlin.test.assertNull
import kotlin.test.assertTrue

/** Spec 028 T014. The script is made up (fictional agency, three-digit tail); nothing here is a real organisation. */
class DrillEngineTest {
    private fun step(line: String, rightId: String = "a") = DrillStep(
        lineVi = line,
        choices = listOf(
            DrillChoice("a", "Cúp máy", correct = rightId == "a", feedbackVi = "Cúp máy là đúng" .takeIf { rightId == "a" } ?: "Nên cúp máy"),
            DrillChoice("b", "Làm theo", correct = rightId == "b", feedbackVi = "Làm theo thì nguy hiểm".takeIf { rightId == "a" } ?: "Làm theo là đúng"),
        ),
    )

    private val script = DrillScript(
        id = "drill_mau_cong_an",
        scenarioRef = "scn_mau",
        title = "Giả danh cơ quan điều tra",
        agencyFictional = "Phòng Điều tra Mẫu",
        callerLast3Fictional = "000",
        steps = listOf(step("Bác đang bị điều tra."), step("Bác đọc mã xác thực."), step("Bác chuyển tiền vào tài khoản an toàn.", rightId = "a")),
        debrief = DrillDebrief(redFlagsVi = listOf("Người lạ dọa bắt giữ", "Đòi mã xác thực"), praiseVi = "Bác đã bình tĩnh."),
    )

    @Test
    fun startsAtTheFirstStep() {
        val engine = DrillEngine(script)
        assertEquals(0, engine.currentStep)
        assertFalse(engine.isFinished)
        assertTrue(engine.answers.isEmpty())
    }

    @Test
    fun aRightAnswerMovesOnAndSaysWhy() {
        val engine = DrillEngine(script)
        val result = assertIs<DrillStepResult.Recorded>(engine.recordChoice(0, "a"))
        assertTrue(result.correct)
        assertEquals("Cúp máy là đúng", result.feedbackVi)
        assertEquals(1, result.nextStep)
        assertEquals(1, engine.currentStep)
    }

    @Test
    fun aWrongAnswerIsRecordedToo() {
        val engine = DrillEngine(script)
        val result = assertIs<DrillStepResult.Recorded>(engine.recordChoice(0, "b"))
        assertFalse(result.correct)
        assertEquals(listOf(DrillAnswer(0, "b")), engine.answers)
    }

    @Test
    fun theLastStepHasNoNextStep() {
        val engine = DrillEngine(script)
        engine.recordChoice(0, "a"); engine.recordChoice(1, "a")
        val last = assertIs<DrillStepResult.Recorded>(engine.recordChoice(2, "a"))
        assertNull(last.nextStep)
        assertTrue(engine.isFinished)
        assertNull(engine.currentStep)
    }

    @Test
    fun answersOutOfOrderOrWithAnUnknownLetterChangeNothing() {
        val engine = DrillEngine(script)
        assertEquals(DrillStepResult.Invalid(DrillStepResult.Reason.WRONG_STEP), engine.recordChoice(1, "a"))
        assertEquals(DrillStepResult.Invalid(DrillStepResult.Reason.WRONG_STEP), engine.recordChoice(-1, "a"))
        assertEquals(DrillStepResult.Invalid(DrillStepResult.Reason.UNKNOWN_CHOICE), engine.recordChoice(0, "x"))
        assertEquals(DrillStepResult.Invalid(DrillStepResult.Reason.UNKNOWN_CHOICE), engine.recordChoice(0, ""))
        assertTrue(engine.answers.isEmpty())
        assertEquals(0, engine.currentStep)
    }

    @Test
    fun nothingIsAcceptedOnceTheDrillIsOver() {
        val engine = DrillEngine(script)
        repeat(3) { engine.recordChoice(it, "a") }
        assertEquals(DrillStepResult.Invalid(DrillStepResult.Reason.FINISHED), engine.recordChoice(3, "a"))
        assertEquals(3, engine.answers.size)
    }

    @Test
    fun allRightMeansPassed() {
        val engine = DrillEngine(script)
        repeat(3) { engine.recordChoice(it, "a") }
        val result = engine.evaluate()
        assertTrue(result.isPassed)
        assertEquals(3, result.correctCount)
        assertEquals(3, result.total)
        assertTrue(result.wrongSteps.isEmpty())
        assertEquals("Bác đã bình tĩnh.", result.praiseVi)
    }

    @Test
    fun oneMistakeMeansNotPassedAndNamesTheStep() {
        val engine = DrillEngine(script)
        engine.recordChoice(0, "a"); engine.recordChoice(1, "b"); engine.recordChoice(2, "a")
        val result = engine.evaluate()
        assertFalse(result.isPassed)
        assertEquals(2, result.correctCount)
        assertEquals(listOf(1), result.wrongSteps)
    }

    @Test
    fun anUnfinishedDrillIsNeverPassed() {
        val engine = DrillEngine(script)
        engine.recordChoice(0, "a")
        assertFalse(engine.evaluate().isPassed)
    }

    @Test
    fun theRedFlagsAreRemindedWhetherOrNotThePersonPassed() {
        val passed = DrillEngine(script).also { e -> repeat(3) { e.recordChoice(it, "a") } }.evaluate()
        val failed = DrillEngine(script).also { e -> repeat(3) { e.recordChoice(it, "b") } }.evaluate()
        assertEquals(listOf("Người lạ dọa bắt giữ", "Đòi mã xác thực"), passed.redFlagsVi)
        assertEquals(passed.redFlagsVi, failed.redFlagsVi)
    }

    @Test
    fun aMalformedScriptIsRefused() {
        assertFailsWith<IllegalArgumentException> { script.copy(steps = listOf(step("một bước"))) }
        assertFailsWith<IllegalArgumentException> { script.copy(steps = List(6) { step("bước $it") }) }
        assertFailsWith<IllegalArgumentException> {
            DrillStep("x", listOf(DrillChoice("a", "A", true, "f"), DrillChoice("b", "B", false, "f"), DrillChoice("c", "C", false, "f")))
        }
        assertFailsWith<IllegalArgumentException> { DrillStep("x", listOf(DrillChoice("a", "A", true, "f"), DrillChoice("a", "B", false, "f"))) }
        assertFailsWith<IllegalArgumentException> { DrillStep("x", listOf(DrillChoice("a", "A", true, "f"), DrillChoice("b", "B", true, "f"))) }
        assertFailsWith<IllegalArgumentException> { DrillStep("x", listOf(DrillChoice("a", "A", false, "f"), DrillChoice("b", "B", false, "f"))) }
        assertFailsWith<IllegalArgumentException> { DrillChoice("x1", "X", true, "f") }
        assertFailsWith<IllegalArgumentException> { DrillChoice("A", "X", true, "f") }
    }
}
