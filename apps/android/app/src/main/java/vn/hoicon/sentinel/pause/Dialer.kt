package vn.hoicon.sentinel.pause

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import vn.hoicon.sentinel.sensing.HcSpikeLog

/**
 * "Hỏi con" opens the phone's dialer, empty: HỏiCon has no contacts permission and never reads the address book
 * (CLAUDE.md rule 3), so the person dials the child themselves. The family is told through the `ask_child_pressed` event.
 */
object Dialer {
    fun open(context: Context): Boolean = open { action ->
        context.startActivity(Intent(action).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    }

    /** [start] gets the action only (never a number or data): `ACTION_DIAL` with nothing else. A phone without a dialer ⇒ false, never a throw. */
    internal fun open(onMissing: (Exception) -> Unit = { HcSpikeLog.w("no dialer", it) }, start: (action: String) -> Unit): Boolean = try {
        start(Intent.ACTION_DIAL)
        true
    } catch (e: ActivityNotFoundException) {
        onMissing(e)
        false
    }
}

/** One press of "Hỏi con": the event goes to the family queue first, then the dialer is tried (a missing dialer never hides the press). */
class AskChild(private val record: () -> Unit, private val dial: () -> Boolean) {
    fun press(): Boolean {
        record()
        return dial()
    }
}
