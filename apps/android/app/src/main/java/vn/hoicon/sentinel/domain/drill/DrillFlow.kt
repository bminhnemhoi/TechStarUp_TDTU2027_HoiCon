package vn.hoicon.sentinel.domain.drill

import kotlin.random.Random

/** What E11 shows. Four screens (Spec 028 FR-009); every one of them carries `[DIỄN TẬP]`. */
sealed interface DrillUi {
    /** Deliberately without the script title: "Giả danh cơ quan điều tra" would give the answer away. */
    data object Invite : DrillUi

    /** [feedback] is null while the person is choosing and set once they have chosen. */
    data class Step(
        val index: Int,
        val total: Int,
        val lineVi: String,
        val choices: List<DrillChoice>,
        val feedback: DrillFeedback?,
    ) : DrillUi

    data class Debrief(val evaluation: DrillEvaluation) : DrillUi

    data class Stopped(val reason: StopReason) : DrillUi
}

data class DrillFeedback(
    val chosenId: String,
    val chosenLabel: String,
    val correct: Boolean,
    val text: String,
    /** The label of the right choice, only when the person chose the other one: "Cách an toàn: …". */
    val safeWayLabel: String?,
    val isLastStep: Boolean,
)

enum class StopReason {
    /** The person pressed "Dừng luyện tập". */
    BY_PERSON,

    /** No drill to play: it ran out of time, was answered already, or was never saved. */
    UNAVAILABLE,
}

/**
 * The order of E11 without Android: invitation → one screen per step (choose, then see the answer) → debrief, or stopped.
 * Wraps a [DrillEngine]; the screen only renders [ui] and calls these. A drill that cannot be played ([script] null)
 * starts as "stopped / unavailable".
 */
class DrillFlow(script: DrillScript?) {
    private val engine = script?.let(::DrillEngine)

    var ui: DrillUi = script?.let { DrillUi.Invite } ?: DrillUi.Stopped(StopReason.UNAVAILABLE)
        private set

    val answers: List<DrillAnswer> get() = engine?.answers.orEmpty()

    fun start() {
        if (ui == DrillUi.Invite) ui = stepUi(0, feedback = null)
    }

    /** A tap on a choice. Ignored unless a step is waiting for it, so a double tap cannot answer twice. */
    fun choose(choiceId: String) {
        val engine = engine ?: return
        val current = ui as? DrillUi.Step ?: return
        if (current.feedback != null) return
        val result = engine.recordChoice(current.index, choiceId) as? DrillStepResult.Recorded ?: return
        val chosen = current.choices.first { it.id == choiceId }
        ui = current.copy(
            feedback = DrillFeedback(
                chosenId = choiceId,
                chosenLabel = chosen.labelVi,
                correct = result.correct,
                text = result.feedbackVi,
                safeWayLabel = if (result.correct) null else current.choices.firstOrNull { it.correct }?.labelVi,
                isLastStep = result.nextStep == null,
            ),
        )
    }

    /** "Tiếp tục" / "Xem tổng kết". */
    fun next() {
        val engine = engine ?: return
        val current = ui as? DrillUi.Step ?: return
        if (current.feedback == null) return
        ui = engine.currentStep?.let { stepUi(it, feedback = null) } ?: DrillUi.Debrief(engine.evaluate())
    }

    fun stop() {
        if (ui == DrillUi.Invite || ui is DrillUi.Step) ui = DrillUi.Stopped(StopReason.BY_PERSON)
    }

    /** A real call is on: same as stopping, but the reason is "no drill now", not "the person stopped". */
    fun interrupt() {
        if (ui == DrillUi.Invite || ui is DrillUi.Step) ui = DrillUi.Stopped(StopReason.UNAVAILABLE)
    }

    private fun stepUi(index: Int, feedback: DrillFeedback?): DrillUi.Step {
        val script = checkNotNull(engine).script
        // The server lists the right choice wherever it likes; the person must not learn "press the top button". The order is
        // fixed per drill and step (same after a rotation), and answers travel as letters, so it never changes the result.
        val choices = script.steps[index].choices.shuffled(Random("${script.id}:$index".hashCode()))
        return DrillUi.Step(index, script.steps.size, script.steps[index].lineVi, choices, feedback)
    }
}
