package vn.hoicon.sentinel.pause

import android.annotation.SuppressLint
import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.view.HapticFeedbackConstants
import android.view.MotionEvent
import android.view.View
import android.view.accessibility.AccessibilityManager
import android.view.accessibility.AccessibilityNodeInfo
import android.view.accessibility.AccessibilityNodeInfo.AccessibilityAction
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import java.io.File
import vn.hoicon.rules.AppCategory
import vn.hoicon.rules.AppForeground
import vn.hoicon.sentinel.BuildConfig
import vn.hoicon.sentinel.R
import vn.hoicon.sentinel.SentinelServices
import vn.hoicon.sentinel.domain.events.EventTiming
import vn.hoicon.sentinel.domain.events.RiskEventType
import vn.hoicon.sentinel.sensing.CallSignalStore
import vn.hoicon.sentinel.sensing.HcSpikeLog
import vn.hoicon.sentinel.sensing.HcTiming
import vn.hoicon.sentinel.ui.PAUSE_COUNTDOWN_SECONDS
import vn.hoicon.sentinel.ui.SafePauseActions
import vn.hoicon.sentinel.ui.SafePauseScreen
import vn.hoicon.sentinel.ui.theme.HoiConTheme

/**
 * E7 "Khoan chuyển tiền đã" (Spec 022). Opened directly by RiskWindowService on top of the bank (or remote-control)
 * app's task (own task, never drawn as an overlay over that app). Never blocks for good: "Vẫn tiếp tục" works after a
 * 3 s hold (or the accessible countdown + confirm) and the choice is recorded. The calm minute is advice, not a lock.
 * Offline: no network, no LLM; the events it records go to the on-device outbox in the background, after the frame.
 * Hardened against overlays/tapjacking (SEC-1).
 */
class SafePauseActivity : ComponentActivity(), HoldToContinue.Listener {
    private val handler = Handler(Looper.getMainLooper())
    private lateinit var hold: HoldToContinue
    private var request = PauseRequest.from(null)
    private var useViews = false

    // Calm minute: counted from the first moment E7 is visible, per request.
    private var countdownStartedAt = 0L
    private var secondsLeft by mutableIntStateOf(PAUSE_COUNTDOWN_SECONDS)
    private var shownRecorded = false

    // View variant (debug A/B only)
    private var progressBar: View? = null
    private var statusView: TextView? = null
    private var confirmButton: View? = null

    private var composeStatus by mutableStateOf<HoldToContinue.Status>(HoldToContinue.Status.Idle)
    private var composeProgress by mutableFloatStateOf(0f)

    private val speakAll = Runnable { Speaker.speak(this, speech()) }

    private val countdownTick = object : Runnable {
        override fun run() {
            val elapsed = (SystemClock.elapsedRealtime() - countdownStartedAt) / 1000
            secondsLeft = (PAUSE_COUNTDOWN_SECONDS - elapsed).toInt().coerceAtLeast(0)
            if (secondsLeft > 0) handler.postDelayed(this, COUNTDOWN_STEP_MS)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        title = getString(R.string.pause_window_title) // read first by TalkBack (UX-7)
        // SEC-1: hide other apps' overlay windows while E7 is shown (API 31+, normal permission HIDE_OVERLAY_WINDOWS).
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) window.setHideOverlayWindows(true)
        readIntent(intent)
        hold = HoldToContinue(handler, this)
        // Debug A/B of spec 001 (SEC-7: debug only, so release never touches the disk here):
        // `adb shell run-as vn.hoicon.sentinel touch files/spike_view_pause` ⇒ the old View layout.
        useViews = BuildConfig.DEBUG && File(filesDir, SPIKE_VIEW_FLAG).exists()
        HcSpikeLog.i("safe pause ui=${if (useViews) "views" else "compose"}")
        // Back never skips the pause by itself (that would bypass the hold): it does what the safe button does,
        // "back to the home screen", so a press always has a visible, safe result.
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() = cancel()
        })
        if (useViews) renderViews() else renderCompose()
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        readIntent(intent)
        hold.reset()
        startCountdown()
        if (useViews) bindTexts()
        if (isVisible) onNextFrameShown() // already on screen: a new pause replaces the content in place
    }

    override fun onResume() {
        super.onResume()
        isVisible = true
        HcTiming.mark("pause_resumed")
        onNextFrameShown()
        if (countdownStartedAt == 0L) startCountdown() else handler.post(countdownTick)
        // UX-7: with TalkBack on, let it read the window title before our own voice starts.
        val touchExploration = getSystemService(AccessibilityManager::class.java).isTouchExplorationEnabled
        handler.postDelayed(speakAll, if (touchExploration) TALKBACK_SPEECH_DELAY_MS else 0L)
    }

    /** "pause_shown" = first frame handed to the display; the `safe_pause_shown` event is queued once per pause. */
    private fun onNextFrameShown() {
        window.decorView.viewTreeObserver.registerFrameCommitCallback {
            val shownAt = System.currentTimeMillis()
            lastShownAtMs = shownAt
            HcTiming.mark("pause_shown", shownAt)
            if (!shownRecorded) {
                shownRecorded = true
                val pauseMs = if (request.appAtMs > 0) (shownAt - request.appAtMs).coerceAtLeast(0) else null
                record(RiskEventType.SAFE_PAUSE_SHOWN, shownAt, EventTiming(pauseMs = pauseMs))
            }
        }
    }

    override fun onPause() {
        isVisible = false
        handler.removeCallbacks(speakAll)
        handler.removeCallbacks(countdownTick)
        hold.reset() // a hold or countdown interrupted by leaving the screen never counts
        Speaker.stop()
        super.onPause()
    }

    override fun onStop() {
        super.onStop()
        // Left via Home/another app: drop this instance; reopening the bank app inside the window shows a fresh one.
        if (!isFinishing && !isChangingConfigurations) {
            HcTiming.mark("pause_left")
            finish()
        }
    }

    /**
     * SEC-1: a touch that went through (or next to) another app's window is dropped; in-progress gestures get a
     * CANCEL so a hold can't be completed under an overlay. Covers both the View and the Compose variant.
     */
    override fun dispatchTouchEvent(ev: MotionEvent): Boolean {
        val obscured = MotionEvent.FLAG_WINDOW_IS_OBSCURED or MotionEvent.FLAG_WINDOW_IS_PARTIALLY_OBSCURED
        if (ev.flags and obscured == 0) return super.dispatchTouchEvent(ev)
        if (ev.actionMasked == MotionEvent.ACTION_DOWN) {
            HcTiming.mark("pause_obscured")
            HcSpikeLog.w("touch ignored: window obscured by another app")
        }
        val cancel = MotionEvent.obtain(ev).apply { action = MotionEvent.ACTION_CANCEL }
        super.dispatchTouchEvent(cancel)
        cancel.recycle()
        return true
    }

    // ---- HoldToContinue.Listener ---------------------------------------------------------------------------

    override fun onStatus(status: HoldToContinue.Status) {
        composeStatus = status
        statusView?.let { view ->
            if (status == HoldToContinue.Status.Idle) {
                view.visibility = View.GONE
            } else {
                // Visible first, text next frame: a text change on a shown live region is always announced.
                view.visibility = View.VISIBLE
                val text = statusText(status)
                view.post { view.text = text }
            }
        }
        // The live-region status announces the confirm button; focus is not forced (it would fight the screen reader).
        confirmButton?.visibility = if (status == HoldToContinue.Status.ConfirmReady) View.VISIBLE else View.GONE
    }

    override fun onProgress(fraction: Float) {
        composeProgress = fraction
        progressBar?.scaleX = fraction
    }

    override fun onHaptic(completed: Boolean) {
        val constant = when {
            !completed -> HapticFeedbackConstants.VIRTUAL_KEY
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.R -> HapticFeedbackConstants.CONFIRM
            else -> HapticFeedbackConstants.LONG_PRESS
        }
        window.decorView.performHapticFeedback(constant)
    }

    override fun onCountdown(secondsLeft: Int) {
        // TalkBack already reads the live-region status; speak only for Switch Access and other non-speech users.
        if (!getSystemService(AccessibilityManager::class.java).isTouchExplorationEnabled) {
            Speaker.speak(this, listOf(secondsLeft.toString()))
        }
    }

    override fun onContinue(via: String) {
        val now = System.currentTimeMillis()
        HcTiming.mark("pause_continued", now)
        HcSpikeLog.i("continue_via=$via")
        CallSignalStore.update(this) { it.copy(continuedAtMs = now, continuedVia = via) }
        record(RiskEventType.SAFE_PAUSE_CONTINUED, now)
        finish()
    }

    // ---- rendering -----------------------------------------------------------------------------------------

    private fun renderCompose() = setContent {
        HoiConTheme {
            SafePauseScreen(
                level = request.level,
                kind = request.kind,
                reason = reasonText(),
                secondsLeft = secondsLeft,
                status = composeStatus,
                statusText = statusText(composeStatus),
                progress = composeProgress,
                actions = SafePauseActions(
                    onReplay = ::replay,
                    onAskChild = ::askChild,
                    onCancel = ::cancel,
                    onHoldPress = hold::press,
                    onHoldRelease = hold::release,
                    onHoldTap = hold::tap,
                    onAccessibleContinue = hold::requestAccessibleContinue,
                    onConfirm = hold::confirm,
                ),
            )
        }
    }

    /** Framework Views: the spec 001 layout, kept as the debug A/B variant (no calm minute, no cancel button). */
    private fun renderViews() {
        setContentView(R.layout.activity_safe_pause)
        bindTexts()
        findViewById<View>(R.id.pause_replay).setOnClickListener { replay() }
        findViewById<View>(R.id.pause_ask_child).setOnClickListener { askChild() }
        progressBar = findViewById<View>(R.id.pause_continue_progress).also { it.pivotX = 0f }
        statusView = findViewById(R.id.pause_continue_status)
        confirmButton = findViewById<View>(R.id.pause_confirm).also { it.setOnClickListener { hold.confirm() } }
        bindHoldButton(findViewById(R.id.pause_continue))
    }

    private fun bindTexts() {
        findViewById<TextView>(R.id.pause_level)?.setText(
            if (request.level == vn.hoicon.rules.RiskLevel.CRITICAL) R.string.pause_level_critical else R.string.pause_level_high,
        )
        findViewById<TextView>(R.id.pause_reason)?.text = reasonText()
    }

    @SuppressLint("ClickableViewAccessibility") // accessibility goes through the delegate below (SEC-2)
    private fun bindHoldButton(button: View) {
        button.clipToOutline = true // keep the progress bar inside the rounded border
        button.setOnTouchListener { view, event ->
            when (event.actionMasked) {
                MotionEvent.ACTION_DOWN -> {
                    // UX-2: the finger may wander a little; never let a parent steal the gesture.
                    view.parent?.requestDisallowInterceptTouchEvent(true)
                    hold.press()
                }
                MotionEvent.ACTION_MOVE -> {
                    val inside = event.x >= 0 && event.y >= 0 && event.x <= view.width && event.y <= view.height
                    if (!inside) hold.release()
                }
                MotionEvent.ACTION_UP -> {
                    hold.release()
                    view.performClick()
                }
                MotionEvent.ACTION_CANCEL -> hold.release()
            }
            true
        }
        button.setOnClickListener { /* a click alone never continues; status already explains the hold */ }
        val longClickLabel = getString(R.string.pause_continue_long_click_label)
        val customLabel = getString(R.string.pause_continue_a11y_action)
        button.accessibilityDelegate = object : View.AccessibilityDelegate() {
            override fun onInitializeAccessibilityNodeInfo(host: View, info: AccessibilityNodeInfo) {
                super.onInitializeAccessibilityNodeInfo(host, info)
                info.className = Button::class.java.name
                info.isLongClickable = true
                info.addAction(AccessibilityAction(AccessibilityNodeInfo.ACTION_LONG_CLICK, longClickLabel))
                info.addAction(AccessibilityAction(R.id.a11y_continue, customLabel))
            }

            override fun performAccessibilityAction(host: View, action: Int, args: Bundle?): Boolean = when (action) {
                AccessibilityNodeInfo.ACTION_CLICK -> { hold.tap(); true }
                AccessibilityNodeInfo.ACTION_LONG_CLICK, R.id.a11y_continue -> { hold.requestAccessibleContinue(); true }
                else -> super.performAccessibilityAction(host, action, args)
            }
        }
    }

    // ---- actions & copy ------------------------------------------------------------------------------------

    private fun replay() {
        HcTiming.mark("pause_replay")
        Speaker.speak(this, speech())
    }

    /** "Hỏi con": queue `ask_child_pressed` for the family, then open the dialer so the person can call right away. */
    private fun askChild() {
        HcTiming.mark("ask_child_pressed")
        record(RiskEventType.ASK_CHILD_PRESSED, System.currentTimeMillis())
        if (!Dialer.open(this)) Toast.makeText(applicationContext, R.string.e6_dialer_failed, Toast.LENGTH_LONG).show()
        finish()
    }

    /**
     * "Về màn hình chính": back to the home screen, which takes the bank (or remote-control) app out of
     * the way. We cannot, and do not, touch the other app (CLAUDE.md rule 3).
     */
    private fun cancel() {
        HcTiming.mark("pause_cancelled")
        record(RiskEventType.SAFE_PAUSE_CANCELLED, System.currentTimeMillis())
        try {
            startActivity(
                Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
            )
        } catch (e: ActivityNotFoundException) {
            HcSpikeLog.w("no home activity", e)
        }
        finish()
    }

    /** Queues one event about this pause; returns at once (the write happens on the Sentinel's background thread). */
    private fun record(type: RiskEventType, atMs: Long, timing: EventTiming? = null) = try {
        recordUnsafe(type, atMs, timing)
    } catch (e: Exception) {
        HcSpikeLog.w("event not queued: ${e.javaClass.simpleName}") // never let telemetry break the pause
    }

    private fun recordUnsafe(type: RiskEventType, atMs: Long, timing: EventTiming?) {
        val services = SentinelServices.of(this)
        val call = CallSignalStore.load(this)?.toSignal(inCallNow = request.callActive)
        services.record(
            services.events.build(
                type = type,
                nowMs = atMs,
                floor = request.level,
                rule = request.ruleId,
                call = call,
                callActive = request.callActive,
                app = AppForeground(request.packageName, request.category, request.appAtMs),
                timing = timing,
            ),
        )
    }

    private fun startCountdown() {
        handler.removeCallbacks(countdownTick)
        countdownStartedAt = SystemClock.elapsedRealtime()
        secondsLeft = PAUSE_COUNTDOWN_SECONDS
        shownRecorded = false
        handler.postDelayed(countdownTick, COUNTDOWN_STEP_MS)
    }

    private fun speech(): List<String> = resources.getStringArray(
        if (request.kind == PauseKind.REMOTE_CONTROL) R.array.pause_speech_remote else R.array.pause_speech,
    ).toList()

    private fun reasonText(): String = when (request.kind) {
        PauseKind.REMOTE_CONTROL -> getString(
            if (request.callActive) R.string.pause_reason_remote_active else R.string.pause_reason_remote_ended,
        )
        PauseKind.FINANCIAL -> getString(
            if (request.callActive) R.string.pause_reason_active else R.string.pause_reason_ended,
            getString(appKind(request.category)),
        )
    }

    private fun statusText(status: HoldToContinue.Status): String = when (status) {
        HoldToContinue.Status.Idle -> "" // the hint lives inside the button
        HoldToContinue.Status.Holding -> getString(R.string.pause_continue_holding)
        HoldToContinue.Status.TooShort -> getString(R.string.pause_continue_too_short)
        is HoldToContinue.Status.Counting -> getString(R.string.pause_confirm_counting, status.secondsLeft)
        HoldToContinue.Status.ConfirmReady -> getString(R.string.pause_confirm_ready)
    }

    private fun readIntent(intent: Intent?) {
        request = PauseRequest.from(intent)
    }

    companion object {
        private const val SPIKE_VIEW_FLAG = "spike_view_pause"
        private const val TALKBACK_SPEECH_DELAY_MS = 1_500L
        private const val COUNTDOWN_STEP_MS = 1_000L

        @Volatile
        var lastShownAtMs: Long = 0L
            private set

        @Volatile
        var isVisible: Boolean = false
            private set

        fun intent(context: Context, request: PauseRequest): Intent =
            request.putInto(Intent(context, SafePauseActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))

        /** "%1$s" of the reason line (UX-3). */
        fun appKind(category: AppCategory): Int = when (category) {
            AppCategory.WALLET -> R.string.app_kind_wallet
            AppCategory.SECURITIES -> R.string.app_kind_securities
            else -> R.string.app_kind_bank
        }
    }
}
