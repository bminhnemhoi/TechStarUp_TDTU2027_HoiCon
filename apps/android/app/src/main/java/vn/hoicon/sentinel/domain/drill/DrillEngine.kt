package vn.hoicon.sentinel.domain.drill

/**
 * One scam-awareness drill, as the server hands it over (`drill_script.v1`, Spec 028). Pure data: every name, agency
 * and number in it is fictional, and `callerLast3Fictional` is the only "number" there is.
 *
 * The shape is checked here as well as by the schema: 2 to 5 steps, exactly two choices per step with distinct ids and
 * exactly one correct. A script that is not like that is refused (an [IllegalArgumentException]) instead of being run.
 */
data class DrillScript(
    val id: String,
    val scenarioRef: String,
    val title: String,
    val agencyFictional: String,
    val callerLast3Fictional: String?,
    val steps: List<DrillStep>,
    val debrief: DrillDebrief,
) {
    init {
        require(steps.size in MIN_STEPS..MAX_STEPS) { "a drill has $MIN_STEPS to $MAX_STEPS steps" }
    }

    private companion object {
        const val MIN_STEPS = 2
        const val MAX_STEPS = 5
    }
}

/** What the fictional caller says ([lineVi]) and the two things the person can answer. */
data class DrillStep(val lineVi: String, val choices: List<DrillChoice>) {
    init {
        require(choices.size == 2) { "a step has exactly two choices" }
        require(choices.map { it.id }.distinct().size == 2) { "the two choice ids differ" }
        require(choices.count { it.correct } == 1) { "exactly one choice is right" }
    }
}

/** [id] is one lower-case letter: the only thing about an answer that ever leaves the phone. */
data class DrillChoice(val id: String, val labelVi: String, val correct: Boolean, val feedbackVi: String) {
    init {
        require(id.length == 1 && id[0] in 'a'..'z') { "choice id is one letter" }
    }
}

data class DrillDebrief(val redFlagsVi: List<String>, val praiseVi: String)

/** One answer: [step] counts from 0, [choiceId] is the letter of the choice. This is what `drill_result.v1` carries. */
data class DrillAnswer(val step: Int, val choiceId: String)

/** What happened to one tap on a choice. */
sealed interface DrillStepResult {
    /** [nextStep] is null after the last step: time for the debrief. */
    data class Recorded(val correct: Boolean, val feedbackVi: String, val nextStep: Int?) : DrillStepResult

    /** Not accepted, nothing changed: out of order, unknown choice, or the drill is already over. */
    data class Invalid(val reason: Reason) : DrillStepResult

    enum class Reason { FINISHED, WRONG_STEP, UNKNOWN_CHOICE }
}

/** How the drill went. [redFlagsVi] is what the person should remember either way: the debrief shows it every time. */
data class DrillEvaluation(
    val correctCount: Int,
    val total: Int,
    val isPassed: Boolean,
    val praiseVi: String,
    val redFlagsVi: List<String>,
    val wrongSteps: List<Int>,
)

/**
 * Walks one drill and scores it, on the phone and without the network (Spec 028 D4). The server scores again on its
 * own from the choice letters, so this score only decides what the person is shown; it is never trusted upstream.
 * Not thread-safe: one drill is run from the main thread.
 */
class DrillEngine(val script: DrillScript) {
    private val recorded = mutableListOf<DrillAnswer>()

    val answers: List<DrillAnswer> get() = recorded.toList()

    /** The step waiting for an answer, or null when every step has one. */
    val currentStep: Int? get() = recorded.size.takeIf { it < script.steps.size }

    val isFinished: Boolean get() = recorded.size == script.steps.size

    fun recordChoice(step: Int, choiceId: String): DrillStepResult {
        val expected = currentStep ?: return DrillStepResult.Invalid(DrillStepResult.Reason.FINISHED)
        if (step != expected) return DrillStepResult.Invalid(DrillStepResult.Reason.WRONG_STEP)
        val choice = script.steps[step].choices.firstOrNull { it.id == choiceId }
            ?: return DrillStepResult.Invalid(DrillStepResult.Reason.UNKNOWN_CHOICE)
        recorded += DrillAnswer(step, choice.id)
        return DrillStepResult.Recorded(choice.correct, choice.feedbackVi, nextStep = currentStep)
    }

    /** Valid at any time; [DrillEvaluation.isPassed] needs every step answered and every answer right. */
    fun evaluate(): DrillEvaluation {
        val wrong = recorded.filter { answer ->
            script.steps[answer.step].choices.first { it.id == answer.choiceId }.correct.not()
        }.map { it.step }
        val correct = recorded.size - wrong.size
        return DrillEvaluation(
            correctCount = correct,
            total = script.steps.size,
            isPassed = isFinished && wrong.isEmpty(),
            praiseVi = script.debrief.praiseVi,
            redFlagsVi = script.debrief.redFlagsVi,
            wrongSteps = wrong,
        )
    }
}

/** The answers as one short string ("0a,1b,2a") so WorkManager can carry them without JSON. */
object DrillAnswers {
    private val ITEM = Regex("^([0-9]{1,2})([a-z])$")

    fun encode(answers: List<DrillAnswer>): String = answers.joinToString(",") { "${it.step}${it.choiceId}" }

    /** Anything that is not `<step><letter>` is dropped: a damaged string never turns into a made-up answer. */
    fun decode(text: String?): List<DrillAnswer> = text.orEmpty().split(',').mapNotNull { part ->
        ITEM.matchEntire(part.trim())?.let { DrillAnswer(it.groupValues[1].toInt(), it.groupValues[2]) }
    }
}

/** Time arithmetic of a drill window, kept apart from Android so it can be tested. */
object DrillTiming {
    /** The end of the window, or null when [windowEnd] is not an ISO-8601 date-time with an offset. */
    fun parseEnd(windowEnd: String): java.time.Instant? =
        runCatching { java.time.OffsetDateTime.parse(windowEnd).toInstant() }.getOrNull()

    /** Whether the window is over. A date that cannot be read counts as over: an unreadable drill is not played. */
    fun isOver(windowEnd: String, now: java.time.Instant): Boolean = parseEnd(windowEnd)?.let { now.isAfter(it) } ?: true

    /** Milliseconds left in the window, or null when unreadable or already over. */
    fun millisUntil(windowEnd: String, now: java.time.Instant = java.time.Instant.now()): Long? =
        parseEnd(windowEnd)?.let { java.time.Duration.between(now, it).toMillis() }?.takeIf { it > 0 }
}
