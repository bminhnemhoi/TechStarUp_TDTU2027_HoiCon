package vn.hoicon.sentinel.outbox

import com.google.crypto.tink.Aead
import com.google.crypto.tink.KeyTemplates
import com.google.crypto.tink.KeysetHandle
import com.google.crypto.tink.RegistryConfiguration
import com.google.crypto.tink.aead.AeadConfig
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOf
import org.json.JSONObject
import vn.hoicon.rules.AppCategory
import vn.hoicon.rules.AppForeground
import vn.hoicon.rules.CallDirection
import vn.hoicon.rules.CallSignal
import vn.hoicon.rules.HashedPhone
import vn.hoicon.rules.RiskLevel
import vn.hoicon.sentinel.data.local.OutboxDao
import vn.hoicon.sentinel.data.local.OutboxEventEntity
import vn.hoicon.sentinel.data.local.OutboxStatus
import vn.hoicon.sentinel.data.local.RiskWindowDao
import vn.hoicon.sentinel.data.local.RiskWindowState
import vn.hoicon.sentinel.data.local.TinkCryptoHelper
import vn.hoicon.sentinel.data.remote.EventUploader
import vn.hoicon.sentinel.data.remote.EventsResult
import vn.hoicon.sentinel.domain.events.EventFactory
import vn.hoicon.sentinel.domain.events.RiskEvent
import vn.hoicon.sentinel.domain.events.RiskEventType

/** In-memory [OutboxDao] with the same semantics as the SQL in `SentinelDatabase.kt`. */
class FakeOutboxDao : OutboxDao {
    val rows = LinkedHashMap<String, OutboxEventEntity>()

    override suspend fun insert(event: OutboxEventEntity): Long =
        if (event.id in rows) -1 else { rows[event.id] = event; rows.size.toLong() }

    override suspend fun deliverable(limit: Int) = rows.values
        .filter { it.status == OutboxStatus.PENDING || it.status == OutboxStatus.SENDING }
        .sortedWith(compareBy({ it.createdAt }, { it.id })).take(limit)

    override suspend fun setStatus(ids: List<String>, status: String) {
        ids.forEach { id -> rows[id]?.let { rows[id] = it.copy(status = status) } }
    }

    override suspend fun retryLater(ids: List<String>) {
        ids.forEach { id -> rows[id]?.let { rows[id] = it.copy(status = OutboxStatus.PENDING, retryCount = it.retryCount + 1) } }
    }

    override suspend fun deliverableCount() = rows.values.count { it.status == OutboxStatus.PENDING || it.status == OutboxStatus.SENDING }

    override suspend fun count() = rows.size

    override suspend fun purge(sentBefore: Long, failedBefore: Long): Int {
        val gone = rows.values.filter {
            (it.status == OutboxStatus.SENT && it.createdAt < sentBefore) ||
                (it.status == OutboxStatus.FAILED && it.createdAt < failedBefore)
        }
        gone.forEach { rows.remove(it.id) }
        return gone.size
    }

    override suspend fun deleteAll(): Int = rows.size.also { rows.clear() }

    override suspend fun dropOldestFinished(n: Int): Int {
        val gone = rows.values.filter { it.status == OutboxStatus.SENT || it.status == OutboxStatus.FAILED }
            .sortedBy { it.createdAt }.take(n)
        gone.forEach { rows.remove(it.id) }
        return gone.size
    }

    override suspend fun dropOldest(n: Int): Int {
        val gone = rows.values.sortedBy { it.createdAt }.take(n)
        gone.forEach { rows.remove(it.id) }
        return gone.size
    }
}

class FakeRiskWindowDao : RiskWindowDao {
    var state: RiskWindowState? = null

    override suspend fun put(state: RiskWindowState) { this.state = state }

    override suspend fun get() = state

    override fun observe(): Flow<RiskWindowState?> = flowOf(state)
}

/** An [EventUploader] whose answers the test scripts; remembers every batch it was handed. */
class FakeUploader(private val answer: (List<JSONObject>) -> EventsResult) : EventUploader {
    val batches = ArrayList<List<String>>()
    var lastToken: String? = null

    /** Ids the "server" stores, de-duplicated like `ON CONFLICT (id) DO NOTHING`. */
    val stored = LinkedHashSet<String>()

    override fun sendEvents(accessToken: String, events: List<JSONObject>): EventsResult {
        lastToken = accessToken
        batches += events.map { it.getString("id") }
        val result = answer(events)
        if (result == EventsResult.Accepted || result is EventsResult.AcceptedWithIncident) events.forEach { stored += it.getString("id") }
        return result
    }
}

fun jvmAead(): Aead {
    AeadConfig.register()
    return KeysetHandle.generateNew(KeyTemplates.get("AES256_GCM")).getPrimitive(RegistryConfiguration.get(), Aead::class.java)
}

fun jvmCrypto() = TinkCryptoHelper(jvmAead())

const val APP_VERSION = "0.1.0-test"
const val RULES_VERSION = "0.2.0"

/** Deterministic ids: 00000000-0000-7000-8000-<n as 12 hex digits>. */
fun sequentialFactory(): EventFactory {
    var n = 0
    return EventFactory(APP_VERSION, RULES_VERSION) { "00000000-0000-7000-8000-%012x".format(++n) }
}

val stranger = HashedPhone(h1 = "ab".repeat(32), last3 = "678")

fun unknownCall(startedAt: Long = 1_760_000_000_000L, flagged: Boolean = false, endedAt: Long? = null) = CallSignal(
    phone = stranger,
    direction = CallDirection.INCOMING,
    trusted = false,
    flagged = flagged,
    startedAtMs = startedAt,
    endedAtMs = endedAt,
)

fun sampleEvent(factory: EventFactory, atMs: Long = 1_760_000_000_000L): RiskEvent = factory.build(
    type = RiskEventType.BANKING_APP_FOREGROUND,
    nowMs = atMs,
    floor = RiskLevel.HIGH,
    call = unknownCall(atMs - 60_000),
    app = AppForeground("vn.hoicon.demobank", AppCategory.BANK, atMs - 100),
)
