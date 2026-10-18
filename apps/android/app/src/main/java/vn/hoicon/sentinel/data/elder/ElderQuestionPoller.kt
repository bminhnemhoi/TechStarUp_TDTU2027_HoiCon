package vn.hoicon.sentinel.data.elder

import android.content.Context
import vn.hoicon.sentinel.data.remote.ElderQuestion
import vn.hoicon.sentinel.data.remote.PendingQuestionResult

sealed interface PollOutcome {
    data class Ask(val question: ElderQuestion) : PollOutcome

    /** No question yet (the graph may not have reached `ask_elder`) or none any more: nothing to show. */
    data object None : PollOutcome

    /** No connection or a server error: try the whole thing again later. */
    data object Retry : PollOutcome

    data object Unauthorized : PollOutcome
}

/**
 * Spec 024 T013, without Firebase: right after an incident was opened by the events we sent, the phone asks the server for
 * the question the AI has for the person (`GET /v1/incidents/{id}/pending-question`) and E8 opens from the answer. The graph
 * reaches `ask_elder` a moment AFTER the batch is stored, so "no question" is asked again a few times before giving up.
 * A real push (FCM, waiting for P0-08) would call the same [ElderQuestionStore]/E8 path; nothing here depends on how the
 * phone learned that a question exists.
 */
class ElderQuestionPoller(
    private val fetch: (incidentId: String) -> PendingQuestionResult,
    private val attempts: Int = ATTEMPTS,
    private val pauseMs: Long = PAUSE_MS,
    private val pause: suspend (Long) -> Unit = { kotlinx.coroutines.delay(it) },
) {
    suspend fun poll(incidentId: String): PollOutcome {
        repeat(attempts) { attempt ->
            when (val result = fetch(incidentId)) {
                is PendingQuestionResult.Question -> return PollOutcome.Ask(result.question)
                PendingQuestionResult.NoQuestion -> if (attempt < attempts - 1) pause(pauseMs)
                PendingQuestionResult.Unauthorized -> return PollOutcome.Unauthorized
                PendingQuestionResult.NetworkError, PendingQuestionResult.ServerError -> return PollOutcome.Retry
            }
        }
        return PollOutcome.None
    }

    companion object {
        const val ATTEMPTS = 6
        const val PAUSE_MS = 2_000L
    }
}

/** Remembers which question E8 was last opened for, so the same one is never put in front of the person twice. */
interface ElderQuestionStore {
    var lastShown: String?
}

class PrefsElderQuestionStore(context: Context) : ElderQuestionStore {
    private val prefs = context.applicationContext.getSharedPreferences("hoicon_elder", Context.MODE_PRIVATE)

    override var lastShown: String?
        get() = prefs.getString(KEY, null)
        set(value) = prefs.edit().putString(KEY, value).apply()

    private companion object {
        const val KEY = "last_shown_question"
    }
}

/** True the first time this question comes up; the key holds ids only (no text, nothing about the person). */
fun ElderQuestionStore.claim(question: ElderQuestion): Boolean {
    val key = "${question.incidentId}:${question.questionId}"
    if (lastShown == key) return false
    lastShown = key
    return true
}
