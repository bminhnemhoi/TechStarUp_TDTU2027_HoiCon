package vn.hoicon.sentinel

import android.app.Application
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import java.time.Instant
import vn.hoicon.sentinel.data.drill.DrillStore
import vn.hoicon.sentinel.data.drill.PrefsDrillStore
import vn.hoicon.sentinel.data.remote.DrillOffer
import vn.hoicon.sentinel.data.remote.DrillStatus
import vn.hoicon.sentinel.domain.drill.DrillFlow
import vn.hoicon.sentinel.domain.drill.DrillTiming
import vn.hoicon.sentinel.domain.drill.DrillUi
import vn.hoicon.sentinel.pause.Speaker
import vn.hoicon.sentinel.sensing.Notifications
import vn.hoicon.sentinel.work.DrillResultScheduler

/**
 * E11 (Spec 028): runs the saved drill offer through [DrillFlow] and hands every ending to [DrillResultScheduler].
 * Nothing here touches the network itself: the script came with the offer, so a drill started on a good connection
 * plays on to the end without one, and the result goes out whenever the phone is online again.
 */
// One constructor taking only the Application: the default ViewModel factory cannot see Kotlin default arguments.
class DrillModel(private val app: Application) : AndroidViewModel(app) {
    private val store: DrillStore = PrefsDrillStore(app)
    private val offer: DrillOffer? = store.pending()?.takeUnless { isOver(it) }
    private val flow = DrillFlow(offer?.script)
    private var startedAt: String? = null
    private var sent = false

    var ui: DrillUi by mutableStateOf(flow.ui)
        private set

    /** What was last read aloud, so rotating the phone does not read it again. */
    var lastSpoken: Any? = null

    fun start() {
        startedAt = Instant.now().toString()
        flow.start()
        ui = flow.ui
    }

    fun choose(choiceId: String) {
        flow.choose(choiceId)
        ui = flow.ui
    }

    fun next() {
        flow.next()
        ui = flow.ui
    }

    /** "Để lúc khác": the drill is turned down; nothing more is asked in this window. */
    fun decline() = finish(DrillStatus.DECLINED)

    /** True while a risk window is open: a real call is going on, and the drill must neither speak nor stay on screen. */
    var realCallOn: Boolean by mutableStateOf(false)
        private set

    /** False until the risk window has been read once: until then the screen cannot know whether a call is going on, so it stays quiet. */
    var riskWindowKnown: Boolean by mutableStateOf(false)
        private set

    /**
     * The risk window changed. When a real call starts the drill ends silently and gives the screen and the voice back:
     * a drill already begun reports `aborted` with its answers so far; one still on the invitation reports nothing and is
     * offered again at a later beat, since the person never saw it.
     */
    fun onRealCall(open: Boolean) {
        val started = open && !realCallOn && riskWindowKnown
        realCallOn = open
        riskWindowKnown = true
        if (started) Speaker.stop() // only what this screen was saying: the safe pause cannot be speaking before the window opens
        if (open && (ui is DrillUi.Step || ui == DrillUi.Invite)) {
            val playing = flow.interrupt()
            ui = flow.ui
            if (playing) finish(DrillStatus.ABORTED) else offerAgainLater()
        }
    }

    private fun offerAgainLater() {
        store.notifiedDrillId = null // the next beat may show the invitation again (it is still in its window)
        Notifications.cancelDrillInvitation(app)
    }

    /** Back during the drill: on the last answer it goes to the debrief, otherwise it stops with the answers so far. */
    fun back() {
        flow.back()
        ui = flow.ui
        if (ui is DrillUi.Stopped) finish(DrillStatus.ABORTED)
    }

    /** "Dừng luyện tập": the answers so far still count as a result (`aborted`). */
    fun stop() {
        flow.stop()
        ui = flow.ui
        finish(DrillStatus.ABORTED)
    }

    /** "Đã hiểu — Xong" on the debrief. */
    fun complete() = finish(DrillStatus.COMPLETED)

    private fun finish(status: DrillStatus) {
        val offer = offer ?: return
        if (sent) return // a double tap, or Back right after a button
        sent = true
        val completedAt = if (status == DrillStatus.COMPLETED) Instant.now().toString() else null
        DrillResultScheduler.submit(app, offer.drillId, status, flow.answers, startedAt, completedAt)
        store.markHandled(offer.drillId)
        Notifications.cancelDrillInvitation(app)
    }

    private companion object {
        /** The server also expires drills; this just keeps a stale notification from opening a drill whose time is gone. */
        fun isOver(offer: DrillOffer): Boolean = DrillTiming.isOver(offer.windowEnd, Instant.now())
    }
}
