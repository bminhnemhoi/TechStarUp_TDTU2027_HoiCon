package vn.hoicon.sentinel

import android.app.Application
import android.content.res.Resources
import android.os.Build
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import vn.hoicon.rules.RiskEngine
import vn.hoicon.sentinel.data.consent.ConsentLedger
import vn.hoicon.sentinel.data.consent.ConsentSync
import vn.hoicon.sentinel.data.consent.consentTexts
import vn.hoicon.sentinel.data.local.TokenStorage
import vn.hoicon.sentinel.data.remote.PairResult
import vn.hoicon.sentinel.data.remote.PairingApiClient
import vn.hoicon.sentinel.sensing.SensorPermission
import vn.hoicon.sentinel.ui.PairingError
import vn.hoicon.sentinel.ui.PairingUi

enum class OnboardingStep { WELCOME, PAIRING, DISCLOSURE, DISCLOSURE_DECLINED, PERMISSIONS }

/** Where onboarding is in the E1 → E2 → E3 → E4 flow; survives rotation and font-scale changes. */
class OnboardingModel(app: Application) : AndroidViewModel(app) {
    private val storage = TokenStorage.create(app)
    private val api = PairingApiClient(BuildConfig.API_BASE_URL)
    private val consents = ConsentSync(storage, api)

    var step by mutableStateOf(initialStep(storage))
        private set
    var code by mutableStateOf("")
        private set
    var pairing by mutableStateOf<PairingUi>(PairingUi.Idle)
        private set
    var familyName by mutableStateOf(storage.load()?.familyName.orEmpty())
        private set
    var consentPending by mutableStateOf(false)
        private set

    /** The step whose text was already read aloud (rotation or a font-scale change recreates the activity). */
    var lastSpokenStep: OnboardingStep? = null

    fun start() {
        step = OnboardingStep.PAIRING
    }

    /** "Chưa đồng ý" at E3: nothing is recorded and nothing else is asked; the user can read it again or leave. */
    fun declineDisclosure() {
        step = OnboardingStep.DISCLOSURE_DECLINED
    }

    fun reviewDisclosure() {
        step = OnboardingStep.DISCLOSURE
    }

    fun backToWelcome() {
        if (step == OnboardingStep.PAIRING && pairing !is PairingUi.Loading) step = OnboardingStep.WELCOME
    }

    fun onCodeChange(raw: String) {
        if (pairing is PairingUi.Loading) return
        code = raw.filter { it in '0'..'9' }.take(CODE_LENGTH)
        pairing = PairingUi.Idle
        if (code.length == CODE_LENGTH) submit()
    }

    fun submit() {
        if (pairing is PairingUi.Loading) return
        val entered = code
        if (entered.length != CODE_LENGTH) {
            pairing = PairingUi.Failed(PairingError.INCOMPLETE)
            return
        }
        pairing = PairingUi.Loading
        viewModelScope.launch {
            val result = withContext(Dispatchers.IO) {
                api.pair(entered, appVersion(), RiskEngine.VERSION, Build.MODEL)
            }
            when (result) {
                is PairResult.Paired -> if (!storage.save(result.session)) {
                    // The code is already spent and nothing was stored: the child must send a new one.
                    pairing = PairingUi.Failed(PairingError.INVALID)
                } else {
                    familyName = result.session.familyName
                    code = ""
                    pairing = PairingUi.Idle
                    step = OnboardingStep.DISCLOSURE
                }
                PairResult.InvalidCode -> pairing = PairingUi.Failed(PairingError.INVALID)
                PairResult.RateLimited -> pairing = PairingUi.Failed(PairingError.RATE_LIMITED)
                PairResult.NetworkError -> pairing = PairingUi.Failed(PairingError.NETWORK)
                PairResult.ServerError -> pairing = PairingUi.Failed(PairingError.SERVER)
            }
        }
    }

    /** E3 → E4: remember the acceptance, tell the server, only then does the user see any permission page. */
    fun acceptDisclosure(res: Resources, granted: Set<SensorPermission>) {
        storage.acceptedDisclosureVersion = ConsentLedger.DISCLOSURE_VERSION
        step = OnboardingStep.PERMISSIONS
        syncConsents(res, granted)
    }

    fun syncConsents(res: Resources, granted: Set<SensorPermission>) {
        val texts = consentTexts(res)
        viewModelScope.launch {
            when (withContext(Dispatchers.IO) { consents.run(granted, texts) }) {
                ConsentSync.Outcome.UP_TO_DATE -> consentPending = false
                ConsentSync.Outcome.PENDING -> consentPending = true
                ConsentSync.Outcome.SKIPPED -> Unit
            }
        }
    }

    private fun appVersion() = BuildConfig.VERSION_NAME + if (BuildConfig.DEBUG) "-debug" else ""

    private companion object {
        const val CODE_LENGTH = 6

        fun initialStep(storage: TokenStorage) = when {
            !storage.hasValidToken() -> OnboardingStep.WELCOME
            storage.acceptedDisclosureVersion != ConsentLedger.DISCLOSURE_VERSION -> OnboardingStep.DISCLOSURE
            else -> OnboardingStep.PERMISSIONS
        }
    }
}
