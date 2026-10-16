package vn.hoicon.sentinel.data.consent

import java.util.concurrent.atomic.AtomicBoolean
import vn.hoicon.sentinel.data.local.TokenStorage
import vn.hoicon.sentinel.data.remote.ConsentResult
import vn.hoicon.sentinel.data.remote.PairingApiClient
import vn.hoicon.sentinel.sensing.SensorPermission

/**
 * Brings the server's consent ledger up to date with what the phone knows: the E3 disclosure (once accepted for the
 * current [ConsentLedger.VERSION]) and every system permission that maps to a purpose. Safe to call often: nothing
 * is sent when nothing changed, and only one run happens at a time. Blocking: call off the main thread.
 */
class ConsentSync(private val storage: TokenStorage, private val api: PairingApiClient) {
    enum class Outcome { UP_TO_DATE, PENDING, SKIPPED }

    private val busy = AtomicBoolean(false)

    fun run(granted: Set<SensorPermission>, texts: Map<String, String>): Outcome {
        val session = storage.load() ?: return Outcome.SKIPPED
        if (!busy.compareAndSet(false, true)) return Outcome.SKIPPED
        try {
            val purposes = buildSet {
                if (storage.acceptedDisclosureVersion == ConsentLedger.VERSION) {
                    add(ConsentLedger.CORE_PROTECTION)
                    add(ConsentLedger.GUARDIAN_ALERTS)
                }
                granted.mapNotNullTo(this) { ConsentLedger.purposeOf(it) }
            }
            val items = ConsentLedger.changes(storage.recordedConsents, purposes, texts)
            if (items.isEmpty()) return Outcome.UP_TO_DATE
            return when (api.recordConsents(session.accessToken, items)) {
                is ConsentResult.Recorded -> {
                    storage.recordedConsents = purposes.mapTo(mutableSetOf()) { ConsentLedger.key(it, texts.getValue(it)) }
                    Outcome.UP_TO_DATE
                }
                else -> Outcome.PENDING
            }
        } finally {
            busy.set(false)
        }
    }
}
