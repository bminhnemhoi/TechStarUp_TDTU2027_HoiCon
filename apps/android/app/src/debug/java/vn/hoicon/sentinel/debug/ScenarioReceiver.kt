package vn.hoicon.sentinel.debug

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import vn.hoicon.rules.CallDirection
import vn.hoicon.sentinel.SentinelServices
import vn.hoicon.sentinel.sensing.CallSignalStore
import vn.hoicon.sentinel.sensing.HcSpikeLog
import vn.hoicon.sentinel.sensing.HcTiming
import vn.hoicon.sentinel.sensing.RiskWindowService
import vn.hoicon.sentinel.sensing.ScreenedCall

/**
 * Debug-only test hook (P1-S2): stands in for `onScreenCall` on devices that can't receive a call (no SIM, e.g.
 * Firebase Test Lab). Opens a risk window for a call that "just ended" from a hidden number (no h1 at all), so R1
 * fires when a financial app opens within 10 minutes. Everything after this point is the production path.
 *
 *   adb shell am broadcast -f 0x20 -n vn.hoicon.sentinel/.debug.ScenarioReceiver -a vn.hoicon.debug.CALL
 *   adb shell am broadcast -f 0x20 -n vn.hoicon.sentinel/.debug.ScenarioReceiver -a vn.hoicon.debug.CLEAR
 *
 * (`-f 0x20` = FLAG_INCLUDE_STOPPED_PACKAGES, so it also reaches a force-stopped app.)
 */
class ScenarioReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        when (intent.action) {
            ACTION_CALL -> {
                val now = System.currentTimeMillis()
                HcTiming.mark("call_simulated", now)
                CallSignalStore.save(
                    context,
                    ScreenedCall(
                        phone = null,
                        direction = CallDirection.INCOMING,
                        verificationStatus = -1,
                        flagged = false,
                        trusted = false,
                        screenedAtMs = now,
                        lastInCallAtMs = now,
                    ),
                )
                RiskWindowService.open(context)
                val sentinel = SentinelServices.of(context)
                val signal = CallSignalStore.load(context)?.toSignal(inCallNow = false)
                if (signal != null) sentinel.launch { sentinel.riskWindow.onCallScreened(signal, now) }
            }
            // The window notices the missing call on its next tick and closes itself.
            ACTION_CLEAR -> CallSignalStore.clear(context)
            else -> HcSpikeLog.w("scenario: unknown action ${intent.action}")
        }
    }

    private companion object {
        const val ACTION_CALL = "vn.hoicon.debug.CALL"
        const val ACTION_CLEAR = "vn.hoicon.debug.CLEAR"
    }
}
