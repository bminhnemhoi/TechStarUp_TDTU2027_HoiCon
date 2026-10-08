package vn.hoicon.sentinel.pause

import android.annotation.SuppressLint
import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.HapticFeedbackConstants
import android.view.MotionEvent
import android.view.View
import android.view.accessibility.AccessibilityManager
import android.view.accessibility.AccessibilityNodeInfo
import android.view.accessibility.AccessibilityNodeInfo.AccessibilityAction
import android.widget.Button
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import java.io.File
import vn.hoicon.rules.AppCategory
import vn.hoicon.rules.RiskLevel
import vn.hoicon.sentinel.BuildConfig
import vn.hoicon.sentinel.R
import vn.hoicon.sentinel.sensing.CallSignalStore
import vn.hoicon.sentinel.sensing.HcSpikeLog
import vn.hoicon.sentinel.sensing.HcTiming
import vn.hoicon.sentinel.ui.SafePauseActions
import vn.hoicon.sentinel.ui.SafePauseScreen
import vn.hoicon.sentinel.ui.theme.HoiConTheme

/**
 * E7 "Khoan chuyển tiền đã" — spike version (final UI in P2-05). Opened directly by RiskWindowService on top of
 * the bank app's task (own task, never drawn as an overlay over the bank app). Never blocks for good: "Vẫn tiếp
 * tục" works after a 3 s hold (or the accessible countdown + confirm) and the choice is recorded.
 * Offline: no network, no LLM. Hardened against overlays/tapjacking (SEC-1).
 */
class SafePauseActivity : ComponentActivity(), HoldToContinue.Listener {
    private val handler = Handler(Looper.getMainLooper())
    private lateinit var hold: HoldToContinue
    private var level = RiskLevel.HIGH
    private var category = AppCategory.BANK
    private var callActive = true
    private var useCompose = false

    // View variant
    private var progressBar: View? = null
    private var statusView: TextView? = null
    private var confirmButton: View? = null

    // Compose variant (debug A/B only)
    private var composeStatus by mutableStateOf<HoldToContinue.Status>(HoldToContinue.Status.Idle)
    private var composeProgress by mutableFloatStateOf(0f)

    private val speakAll = Runnable { Speaker.speak(this, speech()) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        title = getString(R.string.pause_window_title) // read first by TalkBack (UX-7)
        // SEC-1: hide other apps' overlay windows while E7 is shown (API 31+, normal permission HIDE_OVERLAY_WINDOWS).
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) window.setHideOverlayWindows(true)
        readIntent(intent)
        hold = HoldToContinue(handler, this)
        // Spike A/B (SEC-7: debug only, so release never touches the disk here):
        // `adb shell run-as vn.hoicon.sentinel touch files/spike_compose_pause` ⇒ Compose UI.
        useCompose = BuildConfig.DEBUG && File(filesDir, SPIKE_COMPOSE_FLAG).exists()
        HcSpikeLog.i("safe pause ui=${if (useCompose) "compose" else "views"}")
        // Back does not skip the pause (that would bypass the hold); it repeats the spoken message instead.
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() = Speaker.speak(this@SafePauseActivity, speech())
        })
        if (useCompose) renderCompose() else renderViews()
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        readIntent(intent)
        hold.reset()
        if (useCompose) renderCompose() else bindTexts()
    }

    override fun onResume() {
        super.onResume()
        isVisible = true
        HcTiming.mark("pause_resumed")
        // "pause_shown" = first frame handed to the display after onResume.
        window.decorView.viewTreeObserver.registerFrameCommitCallback {
            val shownAt = System.currentTimeMillis()
            lastShownAtMs = shownAt
            HcTiming.mark("pause_shown", shownAt)
        }
        // UX-7: with TalkBack on, let it read the window title before our own voice starts.
        val touchExploration = getSystemService(AccessibilityManager::class.java).isTouchExplorationEnabled
        handler.postDelayed(speakAll, if (touchExploration) TALKBACK_SPEECH_DELAY_MS else 0L)
    }

    override fun onPause() {
        isVisible = false
        handler.removeCallbacks(speakAll)
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
        finish()
    }

    // ---- rendering -----------------------------------------------------------------------------------------

    private fun renderCompose() = setContent {
        HoiConTheme {
            SafePauseScreen(
                level = level,
                reason = reasonText(),
                status = composeStatus,
                statusText = statusText(composeStatus),
                progress = composeProgress,
                actions = SafePauseActions(
                    onReplay = ::replay,
                    onAskChild = ::askChild,
                    onHoldPress = hold::press,
                    onHoldRelease = hold::release,
                    onHoldTap = hold::tap,
                    onAccessibleContinue = hold::requestAccessibleContinue,
                    onConfirm = hold::confirm,
                ),
            )
        }
    }

    /** Framework Views: already in the boot image, so a cold process doesn't pay Compose's first-frame cost. */
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
            if (level == RiskLevel.CRITICAL) R.string.pause_level_critical else R.string.pause_level_high,
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

    private fun askChild() {
        HcTiming.mark("ask_child_pressed")
        // Spike: open the dialer. P2-06 replaces this with the "Hỏi con" flow (notify guardians, E9).
        try {
            startActivity(Intent(Intent.ACTION_DIAL).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        } catch (e: ActivityNotFoundException) {
            HcSpikeLog.w("no dialer", e)
        }
        finish()
    }

    private fun speech(): List<String> = resources.getStringArray(R.array.pause_speech).toList()

    private fun reasonText(): String = getString(
        if (callActive) R.string.pause_reason_active else R.string.pause_reason_ended,
        getString(appKind(category)),
    )

    private fun statusText(status: HoldToContinue.Status): String = when (status) {
        HoldToContinue.Status.Idle -> "" // the hint lives inside the button
        HoldToContinue.Status.Holding -> getString(R.string.pause_continue_holding)
        HoldToContinue.Status.TooShort -> getString(R.string.pause_continue_too_short)
        is HoldToContinue.Status.Counting -> getString(R.string.pause_confirm_counting, status.secondsLeft)
        HoldToContinue.Status.ConfirmReady -> getString(R.string.pause_confirm_ready)
    }

    private fun readIntent(intent: Intent?) {
        level = RiskLevel.entries.firstOrNull { it.wire == intent?.getStringExtra(EXTRA_LEVEL) } ?: RiskLevel.HIGH
        category = AppCategory.entries.firstOrNull { it.wire == intent?.getStringExtra(EXTRA_CATEGORY) } ?: AppCategory.BANK
        callActive = intent?.getBooleanExtra(EXTRA_CALL_ACTIVE, true) ?: true
    }

    companion object {
        private const val EXTRA_LEVEL = "level"
        private const val EXTRA_CATEGORY = "category"
        private const val EXTRA_CALL_ACTIVE = "call_active"
        private const val SPIKE_COMPOSE_FLAG = "spike_compose_pause"
        private const val TALKBACK_SPEECH_DELAY_MS = 1_500L

        @Volatile
        var lastShownAtMs: Long = 0L
            private set

        @Volatile
        var isVisible: Boolean = false
            private set

        fun intent(context: Context, level: RiskLevel, category: AppCategory, callActive: Boolean): Intent =
            Intent(context, SafePauseActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                .putExtra(EXTRA_LEVEL, level.wire)
                .putExtra(EXTRA_CATEGORY, category.wire)
                .putExtra(EXTRA_CALL_ACTIVE, callActive)

        /** "%1$s" of the reason line (UX-3). */
        fun appKind(category: AppCategory): Int = when (category) {
            AppCategory.WALLET -> R.string.app_kind_wallet
            AppCategory.SECURITIES -> R.string.app_kind_securities
            else -> R.string.app_kind_bank
        }
    }
}
