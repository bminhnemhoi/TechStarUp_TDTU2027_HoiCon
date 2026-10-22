package vn.hoicon.sentinel.data.consent

import java.security.MessageDigest
import vn.hoicon.sentinel.sensing.SensorPermission

/** One row to append to the server's consent ledger (docs/schemas/consent_record.v1.json). */
data class ConsentItem(
    val purpose: String,
    val granted: Boolean,
    val consentVersion: String,
    val textSha256: String,
    val channel: String = "app",
)

/**
 * Which consent rows the phone still owes the server. The ledger only ever grows: a permission that was turned
 * off later becomes a new `granted=false` row, never an edit (spec 020, FR-002).
 */
object ConsentLedger {
    /**
     * The version of every text that has not been reworded since `2026.10-v3`. A text that changed carries its own
     * version (the `version` of its entry in docs/legal/consent/manifest.json): ask [versionOf]. Bump a purpose's version
     * whenever its text changes (CLAUDE.md rule 7); the screen that asks for it is then shown again.
     */
    const val VERSION = "2026.10-v3"

    /** `guardian_alerts` was merged with the case-file and weekly-summary promises (Spec 031 + 032): `2026.10-v4`. */
    private const val GUARDIAN_ALERTS_VERSION = "2026.10-v4"

    /** What E3 (core protection + the family cards) stores once accepted: the newest text on that screen. */
    const val DISCLOSURE_VERSION = GUARDIAN_ALERTS_VERSION

    /** The version of one purpose's current text, as in manifest.json. */
    fun versionOf(purpose: String): String = if (purpose == GUARDIAN_ALERTS) GUARDIAN_ALERTS_VERSION else VERSION

    /** The E3 prominent disclosure itself. */
    const val CORE_PROTECTION = "core_protection"

    /**
     * Sending the events and the heartbeat to the family (Spec 022): agreed in the same E3 screen, recorded as its own
     * purpose so it can be withdrawn on its own, with the words of the two "what is sent / who gets it" cards.
     */
    const val GUARDIAN_ALERTS = "guardian_alerts"

    /**
     * Checking a number or a link the person typed (Spec 026, E10). Asked just in time, on first use, not at onboarding,
     * and recorded under the SAME [VERSION]: a new purpose does not reword any existing text, so nobody has to agree
     * to the others again ([mayShareWithFamily] does not look at it).
     */
    const val LOOKUPS = "lookups"

    /**
     * Practice calls (Spec 028): the server invites a drill only while the ledger holds this grant. Asked just in time,
     * never at onboarding (see [vn.hoicon.sentinel.DrillConsentModel]); same [VERSION] as the others.
     */
    const val DRILLS = "drills"

    const val CALL_SCREENING = "call_screening"
    const val USAGE_MONITORING = "usage_monitoring"
    const val OVERLAY_PAUSE = "overlay_pause"

    /**
     * Texts that exist in docs/legal/consent/ (Spec 011) but promise something the code does not do yet, so no screen
     * asks for them and the phone never records them: the server will not use them either until a spec makes it so.
     */
    const val LLM_PROCESSING = "llm_processing"
    const val VOICE_INPUT = "voice_input"
    const val PILOT_RESEARCH = "pilot_research"

    /** Android's own permission pages (E4) that map to a consent purpose; notification/battery settings do not. */
    fun purposeOf(permission: SensorPermission): String? = when (permission) {
        SensorPermission.CALL_SCREENING_ROLE -> CALL_SCREENING
        SensorPermission.USAGE_ACCESS -> USAGE_MONITORING
        SensorPermission.DISPLAY_OVER_APPS -> OVERLAY_PAUSE
        SensorPermission.NOTIFICATIONS, SensorPermission.BATTERY_UNRESTRICTED -> null
    }

    /**
     * May events and heartbeats leave the phone for the family? Only after the CURRENT disclosure was accepted AND
     * the server's ledger holds the `guardian_alerts` grant for the exact current words: until then, nothing is sent
     * (and [vn.hoicon.sentinel.SentinelServices] does not even queue).
     */
    fun mayShareWithFamily(accepted: String?, recorded: Set<String>, texts: Map<String, String>): Boolean {
        val words = texts[GUARDIAN_ALERTS] ?: return false
        return accepted == DISCLOSURE_VERSION && key(GUARDIAN_ALERTS, words) in recorded
    }

    fun sha256Hex(text: String): String =
        MessageDigest.getInstance("SHA-256").digest(text.toByteArray(Charsets.UTF_8))
            .joinToString("") { "%02x".format(it) }

    /** What identifies one recorded grant: a new version OR new wording of the same purpose is a new key. */
    fun key(purpose: String, text: String) = "$purpose|${versionOf(purpose)}|${sha256Hex(text)}"

    /**
     * @param recorded keys ([key]) the server already holds as granted
     * @param granted purposes granted right now
     * @param texts the exact words shown to the user for every purpose (hashed into `text_sha256`)
     */
    fun changes(recorded: Set<String>, granted: Set<String>, texts: Map<String, String>): List<ConsentItem> {
        fun item(purpose: String, value: Boolean) = ConsentItem(
            purpose = purpose,
            granted = value,
            consentVersion = versionOf(purpose),
            textSha256 = sha256Hex(texts.getValue(purpose)),
        )
        val recordedPurposes = recorded.mapTo(mutableSetOf()) { it.substringBefore('|') }
        val newGrants = granted.filter { key(it, texts.getValue(it)) !in recorded }.sorted()
        return newGrants.map { item(it, true) } + (recordedPurposes - granted).sorted().map { item(it, false) }
    }
}
