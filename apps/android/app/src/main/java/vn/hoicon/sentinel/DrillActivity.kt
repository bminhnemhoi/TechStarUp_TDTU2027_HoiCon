package vn.hoicon.sentinel

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.view.accessibility.AccessibilityManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import kotlinx.coroutines.launch
import vn.hoicon.sentinel.domain.rules.RiskWindowManager
import vn.hoicon.sentinel.domain.drill.DrillUi
import vn.hoicon.sentinel.pause.Speaker
import vn.hoicon.sentinel.ui.DrillScreen
import vn.hoicon.sentinel.ui.theme.HoiConTheme

/**
 * E11 "Luyện tập nhận biết lừa đảo" (Spec 028). Opened by tapping the invitation notification, never exported and never
 * started on its own: no full-screen intent, so it cannot cover a real call or the safe pause. It does not depend on the
 * network; the saved offer carries the whole script.
 */
class DrillActivity : ComponentActivity() {
    private val model: DrillModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        watchRiskWindow()
        setContent {
            HoiConTheme {
                val ui = model.ui
                // Back: on the invitation it is "Để lúc khác"; during the drill "Dừng luyện tập"; on the debrief "Xong".
                when (ui) {
                    DrillUi.Invite -> BackHandler(onBack = ::decline)
                    is DrillUi.Step -> BackHandler(onBack = model::stop)
                    is DrillUi.Debrief -> BackHandler(onBack = ::complete)
                    else -> Unit
                }
                ReadAloud(ui)
                DrillScreen(
                    ui = ui,
                    onStart = model::start,
                    onLater = ::decline,
                    onChoose = model::choose,
                    onNext = model::next,
                    onStop = model::stop,
                    onDone = ::complete,
                    onClose = ::finish,
                    onListen = { if (!model.realCallOn) speak(ui) },
                )
            }
        }
    }

    /**
     * The voice is shared with the safe pause (one TTS for the whole app). While a risk window is open this screen gives
     * way: it ends the drill, stays silent and never stops the speaker (Spec 028 FR-008, constitution I).
     */
    private fun watchRiskWindow() {
        val dao = SentinelServices.of(this).database.riskWindow()
        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.CREATED) {
                dao.observe().collect { model.onRealCall(RiskWindowManager.isOpen(it, System.currentTimeMillis())) }
            }
        }
    }

    private fun decline() {
        model.decline()
        finish()
    }

    private fun complete() {
        model.complete()
        finish()
    }

    /** The AI disclosure first, then what is on screen: the same words as the screen (and the feedback, once it shows). */
    private fun sentences(ui: DrillUi): List<String> = when (ui) {
        DrillUi.Invite -> listOf(getString(R.string.drill_ai), getString(R.string.drill_invite_title), getString(R.string.drill_invite_body))
        is DrillUi.Step -> ui.feedback?.let { listOf(getString(if (it.correct) R.string.drill_right else R.string.drill_wrong), it.text) }
            ?: buildList {
                add(getString(R.string.drill_caller_says))
                add(ui.lineVi)
                add(getString(R.string.drill_pick))
                // The options in the order on screen, so a person who only listens can still choose.
                ui.choices.forEachIndexed { i, c -> add(getString(R.string.drill_option, i + 1, c.labelVi)) }
            }
        is DrillUi.Debrief -> buildList {
            add(getString(R.string.drill_ai))
            add(ui.evaluation.praiseVi)
            add(getString(R.string.drill_debrief_score, ui.evaluation.correctCount, ui.evaluation.total))
            add(getString(R.string.drill_debrief_flags))
            addAll(ui.evaluation.redFlagsVi)
            add(getString(R.string.drill_debrief_family))
            add(getString(R.string.drill_debrief_speech_end))
        }
        is DrillUi.Stopped -> listOf(getString(R.string.drill_ai), getString(R.string.drill_stopped_title), getString(R.string.drill_stopped_body))
    }

    private fun speak(ui: DrillUi) = Speaker.speak(this, sentences(ui))

    @Composable
    private fun ReadAloud(ui: DrillUi) {
        // One read per screen: the feedback after a choice is a new thing to hear, so it is part of the key.
        val key = when (ui) {
            is DrillUi.Step -> Triple(ui.index, ui.feedback?.chosenId, "step")
            else -> ui
        }
        LaunchedEffect(key) {
            // TalkBack users already hear the screen; two voices at once is worse than one.
            val screenReader = getSystemService(AccessibilityManager::class.java).isTouchExplorationEnabled
            if (!screenReader && !model.realCallOn && model.lastSpoken != key) {
                model.lastSpoken = key
                speak(ui)
            }
        }
        // Never cut the safe pause's own words: only stop what this screen said.
        DisposableEffect(key) { onDispose { if (!model.realCallOn) Speaker.stop() } }
    }

    companion object {
        fun intent(context: Context): Intent = Intent(context, DrillActivity::class.java)
    }
}
