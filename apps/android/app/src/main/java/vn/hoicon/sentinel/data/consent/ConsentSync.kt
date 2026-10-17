package vn.hoicon.sentinel.data.consent

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

    private val lock = Any()

    // One run at a time, and a second caller WAITS and then sees what the first one recorded (it finds nothing left to send):
    // E10 presses "Kiểm tra" right after "Đồng ý", and must not read "still running" as "not recorded".
    fun run(granted: Set<SensorPermission>, texts: Map<String, String>): Outcome = synchronized(lock) {
        val session = storage.load() ?: return@synchronized Outcome.SKIPPED
        run {
            val purposes = buildSet {
                if (storage.acceptedDisclosureVersion == ConsentLedger.VERSION) {
                    add(ConsentLedger.CORE_PROTECTION)
                    add(ConsentLedger.GUARDIAN_ALERTS)
                }
                // E10, asked just in time on first use: recorded under the current words, never forces the others again.
                if (storage.acceptedLookupsVersion == ConsentLedger.VERSION) add(ConsentLedger.LOOKUPS)
                granted.mapNotNullTo(this) { ConsentLedger.purposeOf(it) }
            }
            val items = ConsentLedger.changes(storage.recordedConsents, purposes, texts)
            if (items.isEmpty()) return@synchronized Outcome.UP_TO_DATE
            when (api.recordConsents(session.accessToken, items)) {
                is ConsentResult.Recorded -> {
                    storage.recordedConsents = purposes.mapTo(mutableSetOf()) { ConsentLedger.key(it, texts.getValue(it)) }
                    Outcome.UP_TO_DATE
                }
                else -> Outcome.PENDING
            }
        }
    }
}
