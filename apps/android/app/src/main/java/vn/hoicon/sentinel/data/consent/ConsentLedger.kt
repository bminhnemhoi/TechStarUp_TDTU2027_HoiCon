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
    /** Bump whenever any text the user agrees to changes (CLAUDE.md rule 7); the E3 screen is then shown again. */
    const val VERSION = "2026.10-v1"

    /** The E3 prominent disclosure itself. */
    const val CORE_PROTECTION = "core_protection"

    /** Android's own permission pages (E4) that map to a consent purpose; notification/battery settings do not. */
    fun purposeOf(permission: SensorPermission): String? = when (permission) {
        SensorPermission.CALL_SCREENING_ROLE -> "call_screening"
        SensorPermission.USAGE_ACCESS -> "usage_monitoring"
        SensorPermission.DISPLAY_OVER_APPS -> "overlay_pause"
        SensorPermission.NOTIFICATIONS, SensorPermission.BATTERY_UNRESTRICTED -> null
    }

    fun sha256Hex(text: String): String =
        MessageDigest.getInstance("SHA-256").digest(text.toByteArray(Charsets.UTF_8))
            .joinToString("") { "%02x".format(it) }

    /** What identifies one recorded grant: a new version OR new wording of the same purpose is a new key. */
    fun key(purpose: String, text: String) = "$purpose|$VERSION|${sha256Hex(text)}"

    /**
     * @param recorded keys ([key]) the server already holds as granted
     * @param granted purposes granted right now
     * @param texts the exact words shown to the user for every purpose (hashed into `text_sha256`)
     */
    fun changes(recorded: Set<String>, granted: Set<String>, texts: Map<String, String>): List<ConsentItem> {
        fun item(purpose: String, value: Boolean) = ConsentItem(
            purpose = purpose,
            granted = value,
            consentVersion = VERSION,
            textSha256 = sha256Hex(texts.getValue(purpose)),
        )
        val recordedPurposes = recorded.mapTo(mutableSetOf()) { it.substringBefore('|') }
        val newGrants = granted.filter { key(it, texts.getValue(it)) !in recorded }.sorted()
        return newGrants.map { item(it, true) } + (recordedPurposes - granted).sorted().map { item(it, false) }
    }
}
