package vn.hoicon.sentinel

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.res.stringResource
import androidx.compose.runtime.setValue
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import vn.hoicon.sentinel.data.consent.ConsentLedger
import vn.hoicon.sentinel.data.consent.ConsentSwitches
import vn.hoicon.sentinel.data.consent.ConsentSync
import vn.hoicon.sentinel.data.consent.consentTexts
import vn.hoicon.sentinel.data.local.TokenStorage
import vn.hoicon.sentinel.data.remote.DataRequestApiClient
import vn.hoicon.sentinel.data.remote.PairingApiClient
import vn.hoicon.sentinel.data.remote.PrivacyDelete
import vn.hoicon.sentinel.domain.rules.RiskWindowManager
import vn.hoicon.sentinel.sensing.Notifications
import vn.hoicon.sentinel.sensing.SensorPermission
import vn.hoicon.sentinel.sensing.SensorPermissions
import vn.hoicon.sentinel.ui.ConsentSwitchScreen
import vn.hoicon.sentinel.ui.PermissionsScreen
import vn.hoicon.sentinel.ui.PrivacyDeleteScreen
import vn.hoicon.sentinel.ui.deleteTimeText
import vn.hoicon.sentinel.ui.switchNoun
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
    private var drillsOffer by mutableStateOf(false)
    private var tokens: TokenStorage? = null
    private var showPermissions by mutableStateOf(false)
    private var consents: ConsentSync? = null
    private var switches: ConsentSwitches? = null
    private var switchStates by mutableStateOf(emptyMap<String, Boolean>())

    /** E12 confirmation in progress: purpose to "turning off" (false = asking again before switching `guardian_alerts` back on). */
    private var privacyDelete: PrivacyDelete? = null
    private var deleteScreen by mutableStateOf(false)
    private var deleteSending by mutableStateOf(false)
    private var deleteMessage by mutableStateOf<Int?>(null)
    private var deletePendingAt by mutableStateOf<Long?>(null)
    private var switchNotice by mutableStateOf<String?>(null)
    private var pendingSwitch by mutableStateOf<Pair<String, Boolean>?>(null)

    private val permissions = PermissionOpener(this, onChanged = ::refresh)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val tokens = TokenStorage.create(this).also { this.tokens = it }
        val session = tokens.load()
        if (session == null || tokens.acceptedDisclosureVersion != ConsentLedger.DISCLOSURE_VERSION) {
            startActivity(Intent(this, OnboardingActivity::class.java))
            finish()
            return
        }
        familyName = session.familyName
        consents = ConsentSync(tokens, PairingApiClient(BuildConfig.API_BASE_URL))
        switches = ConsentSwitches(tokens)
        privacyDelete = PrivacyDelete(tokens, DataRequestApiClient(BuildConfig.API_BASE_URL))
        HeartbeatScheduler.schedule(this)
        ThreatSyncScheduler.schedule(this)
        OutboxScheduler.schedulePeriodic(this)
        OutboxScheduler.kick(this) // events queued while the phone was not paired (or offline) go out now
        watchRiskWindow()
        enableEdgeToEdge()
        setContent {
            HoiConTheme {
                BackHandler(enabled = showPermissions) {
                    if (deleteScreen) deleteScreen = false else if (pendingSwitch != null) pendingSwitch = null else showPermissions = false
                }
                val pending = pendingSwitch
                if (deleteScreen) {
                    PrivacyDeleteScreen(
                        guardianNotified = switchStates[ConsentLedger.GUARDIAN_ALERTS] == true,
                        sending = deleteSending,
                        messageRes = deleteMessage,
                        onHeld = ::sendDeleteRequest,
                        onBack = { deleteScreen = false },
                    )
                } else if (pending != null) {
                    ConsentSwitchScreen(
                        purpose = pending.first,
                        turningOff = pending.second,
                        onConfirm = { confirmSwitch(pending.first, pending.second) },
                        onBack = { pendingSwitch = null },
                    )
                } else if (showPermissions) {
                    PermissionsScreen(
                        granted = granted,
                        onOpen = permissions::open,
                        onBack = { showPermissions = false },
                        onSwitchOff = permissions::openToDisable,
                        switches = switchStates,
                        onTurnOff = { pendingSwitch = it to true },
                        onTurnOn = ::turnOn,
                        notice = switchNotice,
                        deletePendingAt = deletePendingAt?.let(::deleteTimeText),
                        onDelete = { deleteMessage = null; deleteScreen = true },
                        onCancelDelete = ::cancelDeleteRequest,
                    )
                } else {
                    ProtectionStatusScreen(
                        state = ProtectionUiState(
                            familyName = familyName,
                            missingPermissions = missingCore(),
                            windowOpen = windowOpen,
                            askChildSent = askChildSent,
                            dialerFailed = dialerFailed,
                            needsRepair = needsRepair,
                            drillsOffer = drillsOffer,
                        ),
                        onAskChild = ::askChild,
                        onPermissions = { switchNotice = null; showPermissions = true },
                        onReconnect = ::reconnect,
                        onLookup = { startActivity(Intent(this, LookupActivity::class.java)) },
                        onDrills = { startActivity(Intent(this, DrillConsentActivity::class.java)) },
                    )
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        refresh()
    }

    /** Back on: `guardian_alerts` shows its words again first; `lookups` and `drills` go through their own consent screens. */
    private fun turnOn(purpose: String) {
        when (purpose) {
            ConsentLedger.GUARDIAN_ALERTS -> pendingSwitch = purpose to false
            ConsentLedger.LOOKUPS -> startActivity(Intent(this, LookupActivity::class.java))
            ConsentLedger.DRILLS -> startActivity(Intent(this, DrillConsentActivity::class.java))
        }
    }

    /** E12: the request goes out only after the 3-second hold; the phone keeps everything until the server has purged (spec 038 FR-006). */
    private fun sendDeleteRequest() {
        val delete = privacyDelete ?: return
        if (deleteSending) return
        deleteSending = true
        deleteMessage = null
        lifecycleScope.launch {
            val outcome = withContext(Dispatchers.IO) { delete.request() }
            deleteSending = false
            when (outcome) {
                is PrivacyDelete.Outcome.Sent -> {
                    deletePendingAt = outcome.executeAfterMs
                    deleteScreen = false
                    switchNotice = null
                }
                PrivacyDelete.Outcome.Offline -> deleteMessage = R.string.delete_offline
                is PrivacyDelete.Outcome.Busy -> deleteMessage = R.string.delete_busy
                PrivacyDelete.Outcome.Refused -> deleteMessage = R.string.delete_refused
                else -> deleteMessage = R.string.delete_failed
            }
        }
    }

    private fun cancelDeleteRequest() {
        val delete = privacyDelete ?: return
        lifecycleScope.launch {
            val outcome = withContext(Dispatchers.IO) { delete.cancel() }
            when (outcome) {
                PrivacyDelete.Outcome.Cancelled -> { deletePendingAt = null; switchNoticeRes(R.string.delete_cancelled) }
                PrivacyDelete.Outcome.TooLate -> switchNoticeRes(R.string.delete_cancel_too_late)
                PrivacyDelete.Outcome.Offline -> switchNoticeRes(R.string.delete_offline)
                else -> switchNoticeRes(R.string.delete_cancel_unavailable)
            }
        }
    }

    private fun switchNoticeRes(res: Int) { switchNotice = getString(res) }

    /** The server refused the token after the waiting time of the request we sent: it has purged, so the phone clears its own data too and goes back to E1. */
    private fun wipeAfterPurge() {
        SentinelServices.of(this).wipeOutbox()
        vn.hoicon.sentinel.data.drill.PrefsDrillStore(this).clearAll()
        Notifications.cancelDrillInvitation(this)
        tokens?.clear()
        startActivity(Intent(this, OnboardingActivity::class.java).putExtra(OnboardingActivity.EXTRA_PURGED, true))
        finish()
    }

    private fun confirmSwitch(purpose: String, turningOff: Boolean) {
        val switches = switches ?: return
        if (turningOff) switches.turnOff(purpose) else switches.turnOn(purpose)
        pendingSwitch = null
        switchNotice = getString(if (turningOff) R.string.switch_notice_off else R.string.switch_notice_on, getString(switchNoun(purpose)))
        refresh() // appends the ledger row (or queues it when offline: the next resume retries)
    }

    /** A permission the protection needs (one the consent ledger tracks) that is not granted right now. */
    private fun missingCore(): Boolean = SensorPermission.entries.any { ConsentLedger.purposeOf(it) != null && it !in granted }

    /** The device token was refused: forget the pairing, drop the queued events (they belong to the family being left) and start again from E1. */
    private fun reconnect() {
        SentinelServices.of(this).wipeOutbox()
        vn.hoicon.sentinel.data.drill.PrefsDrillStore(this).clearAll()
        Notifications.cancelDrillInvitation(this)
        tokens?.clear()
        startActivity(Intent(this, OnboardingActivity::class.java))
        finish()
    }

    private fun refresh() {
        needsRepair = tokens?.needsRepair ?: false
        privacyDelete?.let { pd ->
            if (pd.serverHasPurged(System.currentTimeMillis())) return wipeAfterPurge()
            deletePendingAt = pd.pending()?.executeAfterMs
        }
        drillsOffer = tokens != null && tokens?.acceptedDrillsVersion != ConsentLedger.VERSION
        granted = SensorPermissions.granted(this)
        switches?.let { sw -> switchStates = ConsentSwitches.SWITCHABLE.associateWith(sw::isOn) }
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
