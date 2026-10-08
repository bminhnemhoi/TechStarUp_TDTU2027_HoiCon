package vn.hoicon.sentinel.pause

import android.os.Handler
import android.os.SystemClock

/**
 * "Vẫn tiếp tục" state machine shared by the View and Compose E7. Never a one-tap skip:
 *  - touch: hold 3 s (timed here, not by an animator, so "remove animations" can't shorten it);
 *  - TalkBack / Switch Access (SEC-2): a 3 s countdown read aloud, then a separate confirm button.
 * Main thread only.
 */
class HoldToContinue(private val handler: Handler, private val listener: Listener) {
    sealed interface Status {
        data object Idle : Status
        data object Holding : Status
        data object TooShort : Status
        data class Counting(val secondsLeft: Int) : Status
        data object ConfirmReady : Status
    }

    interface Listener {
        fun onStatus(status: Status)

        /** 0..1 fill of the solid bar at the bottom of the button. */
        fun onProgress(fraction: Float)

        /** Light tick when a hold starts, stronger confirm when it completes. */
        fun onHaptic(completed: Boolean)

        /** Spoken countdown for the accessible path (skipped by the activity when TalkBack already reads it). */
        fun onCountdown(secondsLeft: Int)

        /** [via] = "hold" or "a11y"; recorded with the outcome. */
        fun onContinue(via: String)
    }

    var status: Status = Status.Idle
        private set
    private var holdStartedAt = 0L

    private val tick = object : Runnable {
        override fun run() {
            if (status != Status.Holding) return
            val fraction = ((SystemClock.uptimeMillis() - holdStartedAt).toFloat() / HOLD_MS).coerceAtMost(1f)
            listener.onProgress(fraction)
            if (fraction < 1f) {
                handler.postDelayed(this, FRAME_MS)
            } else {
                setStatus(Status.Idle)
                listener.onHaptic(completed = true)
                listener.onContinue("hold")
            }
        }
    }

    /** Finger down on the button. */
    fun press() {
        if (status is Status.Counting || status == Status.ConfirmReady) return
        holdStartedAt = SystemClock.uptimeMillis()
        setStatus(Status.Holding)
        listener.onHaptic(completed = false)
        handler.post(tick)
    }

    /** Finger up / gesture cancelled / finger slid off the button before 3 s. */
    fun release() {
        if (status != Status.Holding) return
        stopTicking()
        setStatus(Status.TooShort)
    }

    /** A plain tap or accessibility click: explain how to continue, never continue. */
    fun tap() {
        if (status == Status.Idle || status == Status.TooShort) setStatus(Status.TooShort)
    }

    /** Custom accessibility action / long-click action: countdown read aloud, then a confirm button. */
    fun requestAccessibleContinue() {
        stopTicking()
        handler.removeCallbacksAndMessages(COUNTDOWN_TOKEN)
        countdown(SECONDS)
    }

    /** The confirm button of the accessible path. Ignored unless the countdown finished. */
    fun confirm() {
        if (status != Status.ConfirmReady) return
        setStatus(Status.Idle)
        listener.onContinue("a11y")
    }

    /** Screen left or re-shown: nothing in progress may carry over. */
    fun reset() {
        stopTicking()
        handler.removeCallbacksAndMessages(COUNTDOWN_TOKEN)
        setStatus(Status.Idle)
    }

    private fun countdown(secondsLeft: Int) {
        if (secondsLeft == 0) {
            setStatus(Status.ConfirmReady)
            return
        }
        setStatus(Status.Counting(secondsLeft))
        listener.onCountdown(secondsLeft)
        handler.postAtTime({ countdown(secondsLeft - 1) }, COUNTDOWN_TOKEN, SystemClock.uptimeMillis() + 1_000L)
    }

    private fun stopTicking() {
        handler.removeCallbacks(tick)
        listener.onProgress(0f)
    }

    private fun setStatus(next: Status) {
        status = next
        listener.onStatus(next)
    }

    companion object {
        const val HOLD_MS = 3_000L
        private const val SECONDS = 3
        private const val FRAME_MS = 32L
        private val COUNTDOWN_TOKEN = Any()
    }
}
