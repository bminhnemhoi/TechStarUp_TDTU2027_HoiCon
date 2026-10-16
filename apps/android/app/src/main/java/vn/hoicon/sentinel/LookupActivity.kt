package vn.hoicon.sentinel

import android.content.ClipboardManager
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
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import vn.hoicon.sentinel.data.lookup.LookupOutcome
import vn.hoicon.sentinel.pause.Speaker
import vn.hoicon.sentinel.ui.LookupConsentScreen
import vn.hoicon.sentinel.ui.LookupLook
import vn.hoicon.sentinel.ui.LookupResultScreen
import vn.hoicon.sentinel.ui.LookupScreen
import vn.hoicon.sentinel.ui.QrScan
import vn.hoicon.sentinel.ui.theme.HoiConTheme

/**
 * E10 "Kiểm tra số hay đường link" (Spec 026). Opened from E6 only ([MainActivity] has already made sure the device is
 * paired and the current disclosure accepted), never exported. Nothing here is on the safe-pause path: the pause
 * works without it, and a lookup that cannot reach the server falls back to the on-device list.
 */
class LookupActivity : ComponentActivity() {
    private val model: LookupModel by viewModels()
    private var askChildMessage by mutableStateOf<Int?>(null)
    private val canScan by lazy { QrScan.available(this) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        model.incidentId = intent.getStringExtra(EXTRA_INCIDENT_ID)
        setContent {
            HoiConTheme {
                when (model.step) {
                    LookupStep.CONSENT -> {
                        ReadAloud(LookupStep.CONSENT) { resources.getStringArray(R.array.lookups_consent_speech).toList() }
                        LookupConsentScreen(
                            onAccept = { model.acceptConsent(resources) },
                            onDecline = ::finish,
                            onListen = { speak(resources.getStringArray(R.array.lookups_consent_speech).toList()) },
                        )
                    }
                    LookupStep.INPUT -> LookupScreen(
                        text = model.text,
                        error = model.error,
                        checking = model.checking,
                        onTextChange = model::onTextChange,
                        onCheck = model::check,
                        onBack = ::finish,
                        canScan = canScan,
                        onScan = { QrScan.scan(this) { raw -> if (raw == null) model.scanFailed() else model.onScanned(raw) } },
                        onPaste = ::paste,
                    )
                    LookupStep.RESULT -> model.outcome?.let { outcome ->
                        BackHandler(onBack = ::backToInput)
                        ReadAloud(outcome) { sentences(outcome) }
                        LookupResultScreen(
                            outcome = outcome,
                            askChildMessage = askChildMessage,
                            onAskChild = ::askChild,
                            onDone = ::finish,
                            onListen = { speak(sentences(outcome)) },
                        )
                    }
                }
            }
        }
    }

    /** Reads the clipboard only when the person taps "Dán đường link". */
    private fun paste() {
        val clip = getSystemService(ClipboardManager::class.java).primaryClip
        model.paste(clip?.takeIf { it.itemCount > 0 }?.getItemAt(0)?.coerceToText(this))
    }

    private fun backToInput() {
        askChildMessage = null
        model.backToInput()
    }

    /** "Hỏi con": the same as on E6: tell the family, open the empty dialer. */
    private fun askChild() {
        val opened = SentinelServices.of(this).askChild(this)
        askChildMessage = if (opened) R.string.e6_ask_child_sent else R.string.e6_dialer_failed
    }

    /** The AI disclosure first, then the verdict and what to do, exactly the words on the screen. */
    private fun sentences(outcome: LookupOutcome): List<String> {
        val disclosure = (outcome as? LookupOutcome.Answer)?.answer?.disclaimer ?: getString(R.string.lookup_offline_ai)
        val look = LookupLook.of(outcome) ?: return listOf(disclosure)
        return listOf(disclosure, getString(look.title), getString(look.action))
    }

    private fun speak(sentences: List<String>) = Speaker.speak(this, sentences)

    @Composable
    private fun ReadAloud(key: Any, sentences: () -> List<String>) {
        LaunchedEffect(key) {
            // TalkBack users already hear the screen; two voices at once is worse than one.
            val screenReader = getSystemService(AccessibilityManager::class.java).isTouchExplorationEnabled
            if (!screenReader && model.lastSpoken != key) {
                model.lastSpoken = key
                speak(sentences())
            }
        }
        DisposableEffect(key) { onDispose { Speaker.stop() } }
    }

    companion object {
        /** An open incident this check belongs to (optional): a dangerous answer then also raises the family's level. */
        const val EXTRA_INCIDENT_ID = "vn.hoicon.extra.LOOKUP_INCIDENT_ID"
    }
}
