package vn.hoicon.sentinel

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import vn.hoicon.sentinel.data.consent.ConsentLedger
import vn.hoicon.sentinel.data.consent.ConsentSync
import vn.hoicon.sentinel.data.consent.consentTexts
import vn.hoicon.sentinel.data.local.TokenStorage
import vn.hoicon.sentinel.data.remote.PairingApiClient
import vn.hoicon.sentinel.domain.rules.RiskWindowManager
import vn.hoicon.sentinel.sensing.SensorPermission
import vn.hoicon.sentinel.sensing.SensorPermissions
import vn.hoicon.sentinel.ui.PermissionsScreen
import vn.hoicon.sentinel.ui.ProtectionStatusScreen
import vn.hoicon.sentinel.ui.ProtectionUiState
import vn.hoicon.sentinel.ui.theme.HoiConTheme
import vn.hoicon.sentinel.work.HeartbeatScheduler
import vn.hoicon.sentinel.work.OutboxScheduler
import vn.hoicon.sentinel.work.ThreatSyncScheduler

/**
 * Home = E6 "Đang bảo vệ" (Spec 022). A device that is not paired yet, or has not accepted the current disclosure, is
 * sent to [OnboardingActivity] first (spec 020). Once paired, the background senders (outbox, heartbeat) are
 * scheduled here; they only run with a network and never touch the safe pause.
 */
class MainActivity : ComponentActivity() {
    private var granted by mutableStateOf(emptySet<SensorPermission>())
    private var familyName by mutableStateOf("")
    private var windowOpen by mutableStateOf(false)
    private var askChildSent by mutableStateOf(false)
    private var dialerFailed by mutableStateOf(false)
    private var needsRepair by mutableStateOf(false)
    private var tokens: TokenStorage? = null
    private var showPermissions by mutableStateOf(false)
    private var consents: ConsentSync? = null

    private val permissions = PermissionOpener(this, onChanged = ::refresh)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val tokens = TokenStorage.create(this).also { this.tokens = it }
        val session = tokens.load()
        if (session == null || tokens.acceptedDisclosureVersion != ConsentLedger.VERSION) {
            startActivity(Intent(this, OnboardingActivity::class.java))
            finish()
            return
        }
        familyName = session.familyName
        consents = ConsentSync(tokens, PairingApiClient(BuildConfig.API_BASE_URL))
        HeartbeatScheduler.schedule(this)
        ThreatSyncScheduler.schedule(this)
        OutboxScheduler.schedulePeriodic(this)
        OutboxScheduler.kick(this) // events queued while the phone was not paired (or offline) go out now
        watchRiskWindow()
        enableEdgeToEdge()
        setContent {
            HoiConTheme {
                BackHandler(enabled = showPermissions) { showPermissions = false }
                if (showPermissions) {
                    PermissionsScreen(granted = granted, onOpen = permissions::open, onBack = { showPermissions = false })
                } else {
                    ProtectionStatusScreen(
                        state = ProtectionUiState(
                            familyName = familyName,
                            missingPermissions = missingCore(),
                            windowOpen = windowOpen,
                            askChildSent = askChildSent,
                            dialerFailed = dialerFailed,
                            needsRepair = needsRepair,
                        ),
                        onAskChild = ::askChild,
                        onPermissions = { showPermissions = true },
                        onReconnect = ::reconnect,
                        onLookup = { startActivity(Intent(this, LookupActivity::class.java)) },
                    )
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        refresh()
    }

    /** A permission the protection needs (one the consent ledger tracks) that is not granted right now. */
    private fun missingCore(): Boolean = SensorPermission.entries.any { ConsentLedger.purposeOf(it) != null && it !in granted }

    /** The device token was refused: forget the pairing, drop the queued events (they belong to the family being left) and start again from E1. */
    private fun reconnect() {
        SentinelServices.of(this).wipeOutbox()
        tokens?.clear()
        startActivity(Intent(this, OnboardingActivity::class.java))
        finish()
    }

    private fun refresh() {
        needsRepair = tokens?.needsRepair ?: false
        granted = SensorPermissions.granted(this)
        val sync = consents ?: return
        // A permission turned off in Settings becomes a new granted=false ledger row (the ledger only grows).
        val texts = consentTexts(resources)
        val now = granted
        lifecycleScope.launch {
            val outcome = withContext(Dispatchers.IO) { sync.run(now, texts) }
            // The grant is on the server's ledger now: events may go out (they were not queued before this point).
            if (outcome == ConsentSync.Outcome.UP_TO_DATE) OutboxScheduler.kick(this@MainActivity)
        }
    }

    /** E6 shows the risk-window banner while the Sentinel's window row says a stranger's call is being watched. */
    private fun watchRiskWindow() {
        val dao = SentinelServices.of(this).database.riskWindow()
        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                dao.observe().collect { windowOpen = RiskWindowManager.isOpen(it, System.currentTimeMillis()) }
            }
        }
    }

    /** "Hỏi con": queue `ask_child_pressed` for the family and open the dialer so the person can call at once. */
    private fun askChild() {
        dialerFailed = !SentinelServices.of(this).askChild(this)
        askChildSent = true
    }
}
