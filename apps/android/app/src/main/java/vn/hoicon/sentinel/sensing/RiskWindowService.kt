package vn.hoicon.sentinel.sensing

import android.app.Service
import android.app.usage.UsageEvents
import android.app.usage.UsageStatsManager
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.SystemClock
import android.provider.Settings
import vn.hoicon.rules.AppCategory
import vn.hoicon.rules.AppForeground
import vn.hoicon.rules.Decision
import vn.hoicon.rules.ForegroundTracker
import vn.hoicon.rules.RiskEngine
import vn.hoicon.sentinel.R
import vn.hoicon.sentinel.pause.SafePauseActivity
import vn.hoicon.sentinel.pause.Speaker

/**
 * Risk window (ARCHITECTURE §3, ADR-007): foreground service `specialUse` while a call with an unknown number is
 * active and up to 10 minutes after it (absolute cap [RiskEngine.MAX_WINDOW_MS]). Every second: call state +
 * UsageStats activity events ⇒ RiskEngine ⇒ SafePauseActivity. No network, no LLM on this path.
 *
 * Two triggers: a financial app RESUMED inside the window (H4), or — GAP — it was already in front before the call
 * and is still in front once the call connects (answering from the heads-up produces no new RESUMED event).
 */
class RiskWindowService : Service() {
    private val handler = Handler(Looper.getMainLooper())
    private lateinit var callState: CallStateMonitor
    private lateinit var usage: UsageStatsManager
    private val foregroundTracker = ForegroundTracker()
    private var polling = false
    private var foreground = false
    private var queriedUntilMs = 0L
    private var lastResumeTs = 0L

    /** Resume time of the foreground app a pause was already requested for (one pause per "app in front" stint). */
    private var handledForegroundAtMs = 0L

    private val tick = object : Runnable {
        override fun run() {
            poll()
            if (polling) handler.postDelayed(this, POLL_INTERVAL_MS)
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        usage = getSystemService(UsageStatsManager::class.java)
        callState = CallStateMonitor(this).also { it.start() }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val wantsForeground = intent?.getBooleanExtra(EXTRA_BACKGROUND, false) != true
        if (wantsForeground && !foreground) foreground = tryStartForeground()
        HcTiming.mark(if (foreground) "window_opened" else "window_opened_bg")
        HcSpikeLog.i("window open fgs=$foreground restart=${intent == null} saw=${Settings.canDrawOverlays(this)}")
        Speaker.warmUp(this) // TTS engine binding takes 100s of ms (seconds when cold): do it before a pause is needed.
        if (!polling) {
            seedForeground(System.currentTimeMillis())
            polling = true
            handler.post(tick)
        }
        return START_STICKY
    }

    override fun onDestroy() {
        polling = false
        handler.removeCallbacksAndMessages(null)
        callState.stop()
        if (!SafePauseActivity.isVisible) Speaker.shutdown()
        super.onDestroy()
    }

    private fun tryStartForeground(): Boolean = try {
        val notification = Notifications.protecting(this)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            startForeground(
                Notifications.ID_PROTECTING,
                notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE,
            )
        } else {
            startForeground(Notifications.ID_PROTECTING, notification)
        }
        true
    } catch (e: IllegalStateException) {
        // ForegroundServiceStartNotAllowedException (API 31+) is an IllegalStateException.
        HcTiming.mark("fgs_denied")
        HcSpikeLog.w("startForeground refused in service: ${e.javaClass.simpleName}")
        false
    } catch (e: SecurityException) {
        HcTiming.mark("fgs_denied")
        HcSpikeLog.w("startForeground refused in service: ${e.javaClass.simpleName}")
        false
    }

    /** GAP: learn which app is in front even if it was opened long before the call. Once per window. */
    private fun seedForeground(now: Long) {
        val started = SystemClock.uptimeMillis()
        val count = readEvents(now - SEED_LOOKBACK_MS, now)
        lastResumeTs = maxOf(lastResumeTs, foregroundTracker.current()?.second ?: 0L)
        val category = foregroundTracker.current()?.first?.let(BankApps::categoryOf)?.wire ?: "other"
        HcSpikeLog.i("seeded $count events in ${SystemClock.uptimeMillis() - started} ms, in front: $category")
    }

    private fun poll() {
        val now = System.currentTimeMillis()
        val stored = CallSignalStore.load(this) ?: return close("no call")
        val inCall = callState.inCall()
        val connected = callState.connected()
        val call = if (inCall) stored.copy(lastInCallAtMs = now).also { CallSignalStore.save(this, it) } else stored
        val signal = call.toSignal(inCallNow = inCall)
        if (!RiskEngine.inWindow(signal, now)) return close("expired")

        val newestResumeBefore = lastResumeTs
        readEvents(queriedUntilMs - LOOKBACK_MS, now)
        val resumed = newFinancialResume(newestResumeBefore)
        if (call.continuedAtMs != null) {
            if (resumed != null) HcSpikeLog.i("pause suppressed: user already continued in this window")
            return
        }
        if (resumed != null) {
            HcTiming.mark("app_foreground", resumed.atMs)
            maybePause(RiskEngine.evaluate(signal, resumed), resumed, inCall, trigger = "resumed")
            return
        }
        // GAP: financial app still in front from before the call, call now connected.
        val (pkg, resumedAt) = foregroundTracker.current() ?: return
        if (resumedAt <= handledForegroundAtMs) return
        val category = BankApps.categoryOf(pkg) ?: return
        val inFront = AppForeground(pkg, category, resumedAt)
        val decision = RiskEngine.evaluateForegroundDuringCall(signal, inFront, connected, now)
        if (decision.pausesUser) HcTiming.mark("app_in_front_on_connect", now)
        maybePause(decision, inFront, inCall, trigger = "already_in_front")
    }

    /** Feeds activity events in [fromMs, toMs] to the tracker; returns how many were read. */
    private fun readEvents(fromMs: Long, toMs: Long): Int {
        // Re-read a few seconds back: UsageStats writes events asynchronously. The tracker is idempotent.
        val events = usage.queryEvents(fromMs, toMs + 1) ?: return 0
        val event = UsageEvents.Event()
        var count = 0
        while (events.hasNextEvent()) {
            events.getNextEvent(event)
            val resumed = when (event.eventType) {
                UsageEvents.Event.ACTIVITY_RESUMED -> true
                UsageEvents.Event.ACTIVITY_PAUSED, UsageEvents.Event.ACTIVITY_STOPPED -> false
                else -> continue
            }
            foregroundTracker.onEvent(event.packageName, resumed, event.timeStamp)
            count++
        }
        queriedUntilMs = maxOf(queriedUntilMs, toMs)
        return count
    }

    /** The financial app resumed most recently after [afterTs], if any; advances [lastResumeTs]. */
    private fun newFinancialResume(afterTs: Long): AppForeground? {
        val (pkg, resumedAt) = foregroundTracker.current() ?: return null
        if (resumedAt <= afterTs) return null
        lastResumeTs = resumedAt
        val category = BankApps.categoryOf(pkg) ?: return null
        return AppForeground(pkg, category, resumedAt)
    }

    private fun maybePause(decision: Decision, app: AppForeground, inCall: Boolean, trigger: String) {
        if (trigger == "resumed" || decision.pausesUser) {
            HcSpikeLog.i(
                "decision level=${decision.level.wire} rule=${decision.ruleId?.wire ?: "-"} cat=${app.category.wire} " +
                    "trigger=$trigger inCall=$inCall rules=${RiskEngine.VERSION}",
            )
        }
        if (!decision.pausesUser) return
        handledForegroundAtMs = app.atMs
        HcTiming.mark("risk_detected")
        showPause(decision, app.category, inCall)
    }

    private fun showPause(decision: Decision, category: AppCategory, callActive: Boolean) {
        val requestedAt = System.currentTimeMillis()
        // Direct start from the service: allowed in the background only with "display over other apps"
        // (BAL exemption). No PendingIntent on this path (API 34+ opt-in rules).
        startActivity(SafePauseActivity.intent(this, decision.level, category, callActive))
        handler.postDelayed({
            if (SafePauseActivity.lastShownAtMs < requestedAt) {
                HcTiming.mark("pause_fallback")
                HcSpikeLog.w("SafePause not shown after $PAUSE_WATCHDOG_MS ms: heads-up + TTS fallback")
                Notifications.showPauseFallback(this, decision.level, category, callActive)
                val speech = resources.getStringArray(R.array.pause_speech).toList() +
                    getString(R.string.pause_fallback_speech_extra)
                Speaker.speak(this, speech)
            }
        }, PAUSE_WATCHDOG_MS)
    }

    private fun close(reason: String) {
        HcTiming.mark("window_closed")
        HcSpikeLog.i("window closed: $reason")
        polling = false
        CallSignalStore.clear(this)
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    companion object {
        private const val POLL_INTERVAL_MS = 1_000L
        private const val LOOKBACK_MS = 5_000L
        private const val SEED_LOOKBACK_MS = 6 * 60 * 60 * 1000L // a bank app left open for hours, screen on
        private const val PAUSE_WATCHDOG_MS = 1_500L
        private const val EXTRA_BACKGROUND = "background"

        /** Called from onScreenCall. Records whether Android lets us start the FGS from there (H3). */
        fun open(context: Context) {
            val intent = Intent(context, RiskWindowService::class.java)
            try {
                context.startForegroundService(intent)
            } catch (e: IllegalStateException) {
                HcTiming.mark("fgs_denied")
                HcSpikeLog.w("startForegroundService refused: ${e.javaClass.simpleName}")
                try {
                    context.startService(intent.putExtra(EXTRA_BACKGROUND, true))
                } catch (e2: IllegalStateException) {
                    HcTiming.mark("window_failed")
                    HcSpikeLog.w("startService refused too: ${e2.javaClass.simpleName}")
                }
            }
        }
    }
}
