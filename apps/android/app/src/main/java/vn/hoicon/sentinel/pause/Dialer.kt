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
    fun open(context: Context): Boolean = try {
        context.startActivity(Intent(Intent.ACTION_DIAL).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        true
    } catch (e: ActivityNotFoundException) {
        HcSpikeLog.w("no dialer", e)
        false
    }
}
