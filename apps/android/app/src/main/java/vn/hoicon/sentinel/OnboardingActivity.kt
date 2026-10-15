package vn.hoicon.sentinel

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
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import vn.hoicon.sentinel.pause.Speaker
import vn.hoicon.sentinel.sensing.SensorPermission
import vn.hoicon.sentinel.sensing.SensorPermissions
import vn.hoicon.sentinel.ui.DisclosureDeclinedScreen
import vn.hoicon.sentinel.ui.PairingScreen
import vn.hoicon.sentinel.ui.PermissionStepScreen
import vn.hoicon.sentinel.ui.ProminentDisclosureScreen
import vn.hoicon.sentinel.ui.WelcomeScreen
import vn.hoicon.sentinel.ui.theme.HoiConTheme

/**
 * First-run flow E1 Chào mừng → E2 Ghép đôi → E3 Công bố nổi bật → E4 Cấp quyền → [MainActivity].
 * [MainActivity] sends the user here until the device is paired and the current disclosure is accepted. The safe-pause
 * path never goes through here and works without it (no network, no pairing needed).
 */
class OnboardingActivity : ComponentActivity() {
    private val model: OnboardingModel by viewModels()
    private var granted by mutableStateOf(emptySet<SensorPermission>())
    private val permissions = PermissionOpener(this, onChanged = ::refresh)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            HoiConTheme {
                when (model.step) {
                    OnboardingStep.WELCOME -> {
                        ReadAloud(OnboardingStep.WELCOME, R.array.welcome_speech)
                        WelcomeScreen(onStart = model::start, onListen = { speak(R.array.welcome_speech) })
                    }
                    OnboardingStep.PAIRING -> {
                        BackHandler(onBack = model::backToWelcome)
                        PairingScreen(
                            code = model.code,
                            state = model.pairing,
                            onCodeChange = model::onCodeChange,
                            onSubmit = model::submit,
                            onBack = model::backToWelcome,
                        )
                    }
                    OnboardingStep.DISCLOSURE -> {
                        BackHandler(onBack = model::declineDisclosure)
                        ReadAloud(OnboardingStep.DISCLOSURE, R.array.disclosure_speech)
                        ProminentDisclosureScreen(
                            familyName = model.familyName,
                            onAccept = { model.acceptDisclosure(resources, granted) },
                            onDecline = model::declineDisclosure,
                            onListen = { speak(R.array.disclosure_speech) },
                        )
                    }
                    OnboardingStep.DISCLOSURE_DECLINED -> DisclosureDeclinedScreen(
                        onReview = model::reviewDisclosure,
                        onClose = ::finishAffinity,
                    )
                    OnboardingStep.PERMISSIONS -> PermissionStepScreen(
                        granted = granted,
                        consentPending = model.consentPending,
                        onOpen = permissions::open,
                        onFinish = ::finishOnboarding,
                    )
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        refresh()
    }

    private fun refresh() {
        granted = SensorPermissions.granted(this)
        // E4: record each permission the user just turned on (or off), once the disclosure has been accepted.
        if (model.step == OnboardingStep.PERMISSIONS) model.syncConsents(resources, granted)
    }

    private fun speak(array: Int) = Speaker.speak(this, resources.getStringArray(array).toList())

    @Composable
    private fun ReadAloud(step: OnboardingStep, array: Int) {
        LaunchedEffect(step) {
            // TalkBack users already hear the screen; two voices at once is worse than one.
            val screenReader = getSystemService(AccessibilityManager::class.java).isTouchExplorationEnabled
            if (!screenReader && model.lastSpokenStep != step) {
                model.lastSpokenStep = step
                speak(array)
            }
        }
        DisposableEffect(step) { onDispose { Speaker.stop() } }
    }

    private fun finishOnboarding() {
        startActivity(Intent(this, MainActivity::class.java))
        finish()
    }
}
