package vn.hoicon.sentinel

import android.annotation.SuppressLint
import android.content.Context
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import vn.hoicon.rules.RiskEngine
import vn.hoicon.sentinel.data.consent.ConsentLedger
import vn.hoicon.sentinel.data.consent.consentTexts
import vn.hoicon.sentinel.data.local.SentinelDatabase
import vn.hoicon.sentinel.data.local.TinkCryptoHelper
import vn.hoicon.sentinel.data.local.TokenStorage
import vn.hoicon.sentinel.data.outbox.FlushOutcome
import vn.hoicon.sentinel.data.outbox.OutboxRepository
import vn.hoicon.sentinel.data.outbox.OutboxSender
import vn.hoicon.sentinel.data.remote.PairingApiClient
import vn.hoicon.sentinel.data.remote.ThreatListApiClient
import vn.hoicon.sentinel.data.threat.ThreatIndexes
import vn.hoicon.sentinel.data.threat.ThreatSyncer
import vn.hoicon.sentinel.domain.events.EventFactory
import vn.hoicon.sentinel.domain.events.RiskEvent
import vn.hoicon.sentinel.domain.events.RiskEventType
import vn.hoicon.sentinel.domain.events.Uuid7
import vn.hoicon.sentinel.domain.rules.LocalRulesEvaluator
import vn.hoicon.sentinel.domain.rules.RiskWindowManager
import vn.hoicon.sentinel.pause.Dialer
import vn.hoicon.sentinel.sensing.CallSignalStore
import vn.hoicon.sentinel.sensing.HcSpikeLog
import vn.hoicon.sentinel.work.OutboxScheduler

/**
 * The Sentinel's process-wide parts (Spec 022): `sentinel.db`, the outbox, the rules evaluator and the risk-window
 * manager. Everything that touches the database runs on ONE background thread, in order, so a window that opens and
 * closes within a second reaches the table in that order, and no database or key work ever happens on the main
 * thread or in front of the safe pause. Nothing here throws into the caller: losing an event beats crashing the
 * service that also guards the user.
 */
class SentinelServices private constructor(private val app: Context) {
    @OptIn(ExperimentalCoroutinesApi::class)
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO.limitedParallelism(1))
    private val flushLock = Mutex()

    val database: SentinelDatabase by lazy { SentinelDatabase.open(app) }
    val outbox: OutboxRepository by lazy { OutboxRepository(database.outbox(), TinkCryptoHelper.create(app)) }

    /** Threat-list sync (Spec 026). Declared before `init`, which already uses it from the background thread. */
    val threatSyncer: ThreatSyncer by lazy {
        ThreatSyncer(database.threats(), ThreatListApiClient(BuildConfig.API_BASE_URL), ThreatIndexes.shared)
    }

    init {
        // Warm up the id generator's random source now, in the background, not on the first pause.
        launch { Uuid7.generate() }
        // Load the stored threat list into memory, off the main thread, so onScreenCall only reads a volatile field.
        launch { threatSyncer.loadFromDisk() }
    }

    val events = EventFactory(appVersion = BuildConfig.VERSION_NAME, rulesVersion = RiskEngine.VERSION)
    val evaluator = LocalRulesEvaluator(events, ::record)
    val riskWindow: RiskWindowManager by lazy { RiskWindowManager(database.riskWindow(), events, ::record) }

    /** Queues [event] for the server. Returns at once; the write and the send happen in the background. */
    fun record(event: RiskEvent) = launch {
        // Not agreed (or not yet recorded) ⇒ not even queued: events from before the consent never reach the family.
        if (mayShare() && outbox.enqueue(event)) OutboxScheduler.kick(app)
    }

    /** See [ConsentLedger.mayShareWithFamily]. Reads small private prefs: call from the background thread. */
    fun mayShare(): Boolean {
        val tokens = TokenStorage.create(app)
        return tokens.load() != null &&
            ConsentLedger.mayShareWithFamily(tokens.acceptedDisclosureVersion, tokens.recordedConsents, consentTexts(app.resources))
    }

    /**
     * "Hỏi con": queues `ask_child_pressed` for the family and opens the dialer, empty, so the person can call at once
     * (no contacts permission: they dial the child themselves). Returns false when the phone has no dialer that opens.
     */
    fun askChild(context: Context): Boolean {
        val call = CallSignalStore.load(app)?.toSignal(inCallNow = false)
        record(events.build(RiskEventType.ASK_CHILD_PRESSED, System.currentTimeMillis(), call = call))
        return Dialer.open(context)
    }

    /** Forgets every queued event (pairing ended): they belonged to the family that was just left. */
    fun wipeOutbox() = launch { outbox.wipe() }

    /** Runs [block] on the serial background thread; any failure is swallowed (and noted in debug logs). */
    fun launch(block: suspend () -> Unit) {
        scope.launch {
            try {
                block()
            } catch (e: Exception) {
                HcSpikeLog.w("sentinel background work failed: ${e.javaClass.simpleName}")
            }
        }
    }

    /** One send pass over the queue. Safe to call from several workers at once: they take turns. */
    suspend fun flushOutbox(): FlushOutcome = flushLock.withLock {
        val tokens = TokenStorage.create(app)
        // Nothing leaves the phone unless the CURRENT disclosure is accepted and its ledger row is recorded.
        OutboxSender(outbox, PairingApiClient(BuildConfig.API_BASE_URL)) {
            if (mayShare()) tokens.load()?.accessToken else null
        }.flush()
    }

    companion object {
        // Holds the APPLICATION context only (see of()), so it cannot leak an Activity.
        @SuppressLint("StaticFieldLeak")
        @Volatile
        private var instance: SentinelServices? = null

        fun of(context: Context): SentinelServices = instance ?: synchronized(this) {
            instance ?: SentinelServices(context.applicationContext).also { instance = it }
        }
    }
}
