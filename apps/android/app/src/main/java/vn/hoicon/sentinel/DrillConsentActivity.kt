package vn.hoicon.sentinel

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.lifecycle.AndroidViewModel
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import android.app.Application
import android.view.accessibility.AccessibilityManager
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import vn.hoicon.sentinel.data.consent.ConsentSync
import vn.hoicon.sentinel.data.consent.DrillConsent
import vn.hoicon.sentinel.data.consent.consentTexts
import vn.hoicon.sentinel.data.local.TokenStorage
import vn.hoicon.sentinel.data.remote.PairingApiClient
import vn.hoicon.sentinel.pause.Speaker
import vn.hoicon.sentinel.sensing.SensorPermissions
import vn.hoicon.sentinel.ui.DrillConsentScreen
import vn.hoicon.sentinel.ui.theme.HoiConTheme

/**
 * Asks, just in time and only when the person opens it from E6, whether HỏiCon may invite her/him to practice calls
 * (purpose `drills`). Never exported; nothing here is on the safe-pause path. "Để lúc khác" just closes it.
 */
class DrillConsentActivity : ComponentActivity() {
    private val model: DrillConsentModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            HoiConTheme {
                val screenReader = getSystemService(AccessibilityManager::class.java).isTouchExplorationEnabled
                LaunchedEffect(Unit) { if (!screenReader && !model.spoken) { model.spoken = true; speak() } }
                DisposableEffect(Unit) { onDispose { Speaker.stop() } }
                DrillConsentScreen(
                    adultConfirmed = model.adultConfirmed,
                    needsAdultNotice = model.needsAdultNotice,
                    onAdultChange = model::setAdult,
                    onAccept = { if (model.accept(resources)) finish() },
                    onDecline = ::finish,
                    onListen = ::speak,
                )
            }
        }
    }

    private fun speak() = Speaker.speak(this, resources.getStringArray(R.array.drills_consent_speech).toList())
}

class DrillConsentModel(private val app: Application) : AndroidViewModel(app) {
    private val storage = TokenStorage.create(app)
    private val consent = DrillConsent(storage)
    private val sync = ConsentSync(storage, PairingApiClient(BuildConfig.API_BASE_URL))

    var adultConfirmed by mutableStateOf(false)
        private set
    var needsAdultNotice by mutableStateOf(false)
        private set
    var spoken = false

    fun setAdult(value: Boolean) {
        adultConfirmed = value
        if (value) needsAdultNotice = false
    }

    /** True when agreed (the activity closes); false when the 18+ box was not ticked (a calm notice shows). */
    fun accept(res: android.content.res.Resources): Boolean {
        if (consent.accept(adultConfirmed) != DrillConsent.Result.AGREED) {
            needsAdultNotice = true
            return false
        }
        val texts = consentTexts(res)
        viewModelScope.launch(Dispatchers.IO) { sync.run(SensorPermissions.granted(app), texts) }
        return true
    }
}
