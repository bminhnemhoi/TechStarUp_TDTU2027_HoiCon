package vn.hoicon.sentinel

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import vn.hoicon.sentinel.data.consent.ConsentLedger
import vn.hoicon.sentinel.data.consent.ConsentSync
import vn.hoicon.sentinel.data.consent.consentTexts
import vn.hoicon.sentinel.data.local.TokenStorage
import vn.hoicon.sentinel.data.remote.PairingApiClient
import vn.hoicon.sentinel.sensing.SensorPermission
import vn.hoicon.sentinel.sensing.SensorPermissions
import vn.hoicon.sentinel.ui.PermissionsScreen
import vn.hoicon.sentinel.ui.theme.HoiConTheme

/**
 * Home (placeholder for E6 until P2-05): the sensing status list. A device that is not paired yet, or has not accepted
 * the current disclosure, is sent to [OnboardingActivity] first (spec 020).
 */
class MainActivity : ComponentActivity() {
    private var granted by mutableStateOf(emptySet<SensorPermission>())
    private var consents: ConsentSync? = null

    private val permissions = PermissionOpener(this, onChanged = ::refresh)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val tokens = TokenStorage.create(this)
        if (!tokens.hasValidToken() || tokens.acceptedDisclosureVersion != ConsentLedger.VERSION) {
            startActivity(Intent(this, OnboardingActivity::class.java))
            finish()
            return
        }
        consents = ConsentSync(tokens, PairingApiClient(BuildConfig.API_BASE_URL))
        enableEdgeToEdge()
        setContent {
            HoiConTheme {
                PermissionsScreen(granted = granted, onOpen = permissions::open)
            }
        }
    }

    override fun onResume() {
        super.onResume()
        refresh()
    }

    private fun refresh() {
        granted = SensorPermissions.granted(this)
        val sync = consents ?: return
        // A permission turned off in Settings becomes a new granted=false ledger row (the ledger only grows).
        val texts = consentTexts(resources)
        val now = granted
        lifecycleScope.launch { withContext(Dispatchers.IO) { sync.run(now, texts) } }
    }
}
