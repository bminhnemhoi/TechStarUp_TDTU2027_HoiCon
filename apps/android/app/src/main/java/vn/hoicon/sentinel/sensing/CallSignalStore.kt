package vn.hoicon.sentinel.sensing

import android.content.Context
import vn.hoicon.rules.CallDirection
import vn.hoicon.rules.CallSignal
import vn.hoicon.rules.HashedPhone
import vn.hoicon.sentinel.BuildConfig

/**
 * The call(s) behind the open risk window (numbers not in contacts). Holds only h1 + last3, never the raw number.
 *
 * @property screenedAtMs earliest start among merged calls (SEC-6: merging never shortens a call).
 * @property latestScreenedAtMs start of the most recent call (absolute window cap counts from here, SEC-9).
 * @property lastInCallAtMs last moment a call was seen ringing/active; the window ends 10 min after it.
 * @property continuedAtMs set when the user chose "Vẫn tiếp tục": no more pauses for this window.
 */
data class ScreenedCall(
    val phone: HashedPhone?,
    val direction: CallDirection,
    val verificationStatus: Int,
    val flagged: Boolean,
    val trusted: Boolean,
    val screenedAtMs: Long,
    val latestScreenedAtMs: Long = screenedAtMs,
    val lastInCallAtMs: Long,
    val continuedAtMs: Long? = null,
    val continuedVia: String? = null,
) {
    fun toSignal(inCallNow: Boolean) = CallSignal(
        phone = phone,
        direction = direction,
        trusted = trusted,
        flagged = flagged,
        startedAtMs = screenedAtMs,
        endedAtMs = if (inCallNow) null else lastInCallAtMs,
        latestStartAtMs = latestScreenedAtMs,
    )

    companion object {
        /** A window rebuilt from a merged [CallSignal] (new risk ⇒ any earlier "Vẫn tiếp tục" no longer applies). */
        fun from(signal: CallSignal, verificationStatus: Int, nowMs: Long) = ScreenedCall(
            phone = signal.phone,
            direction = signal.direction,
            verificationStatus = verificationStatus,
            flagged = signal.flagged,
            trusted = signal.trusted,
            screenedAtMs = signal.startedAtMs,
            latestScreenedAtMs = signal.latestStartAtMs,
            lastInCallAtMs = nowMs,
        )
    }
}

/**
 * Spike persistence in private SharedPreferences (survives a process kill; excluded from backup by
 * data_extraction_rules). Replaced by the Room `risk_window` table + Tink (DATA-MODEL §5) in P2-05.
 */
object CallSignalStore {
    private const val PREFS = "risk_window"

    private fun prefs(context: Context) = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun save(context: Context, call: ScreenedCall) {
        prefs(context).edit()
            .clear()
            .putBoolean("present", true)
            .putString("h1", call.phone?.h1)
            .putString("last3", call.phone?.last3)
            .putString("direction", call.direction.name)
            .putInt("verification", call.verificationStatus)
            .putBoolean("flagged", call.flagged)
            .putBoolean("trusted", call.trusted)
            .putLong("screened_at", call.screenedAtMs)
            .putLong("latest_screened_at", call.latestScreenedAtMs)
            .putLong("last_in_call_at", call.lastInCallAtMs)
            .putLong("continued_at", call.continuedAtMs ?: 0L)
            .putString("continued_via", call.continuedVia)
            .apply()
    }

    fun load(context: Context): ScreenedCall? {
        val p = prefs(context)
        if (!p.getBoolean("present", false)) return null
        val h1 = p.getString("h1", null)
        val last3 = p.getString("last3", null)
        val direction = runCatching { CallDirection.valueOf(p.getString("direction", null) ?: "") }
            .getOrDefault(CallDirection.INCOMING)
        val screenedAt = p.getLong("screened_at", 0L)
        return ScreenedCall(
            phone = if (h1 != null && last3 != null) HashedPhone(h1, last3) else null,
            direction = direction,
            verificationStatus = p.getInt("verification", -1),
            flagged = p.getBoolean("flagged", false),
            trusted = p.getBoolean("trusted", false),
            screenedAtMs = screenedAt,
            latestScreenedAtMs = p.getLong("latest_screened_at", screenedAt),
            lastInCallAtMs = p.getLong("last_in_call_at", 0L),
            continuedAtMs = p.getLong("continued_at", 0L).takeIf { it > 0L },
            continuedVia = p.getString("continued_via", null),
        )
    }

    fun update(context: Context, change: (ScreenedCall) -> ScreenedCall): ScreenedCall? =
        load(context)?.let(change)?.also { save(context, it) }

    fun clear(context: Context) {
        prefs(context).edit().clear().apply()
    }
}

/** Local h1 lists. Real threat list (server, ADR-006) and trusted contacts (E4) come later; both empty in prod. */
object LocalLists {
    /**
     * h1 of `flagged_caller` in data/fixtures/phones.json — a FICTIONAL number, debug builds only (SEC-7, is_demo),
     * so the emulator scenario exercises the "critical" variant of R1.
     */
    private val demoFlaggedH1 = setOf("aa1b1fcd5c51853e998738c59cffa5a4d95bd39ef7ef3b6d905c9c6c3af987e4")

    fun isFlagged(h1: String): Boolean = BuildConfig.DEBUG && h1 in demoFlaggedH1

    @Suppress("UNUSED_PARAMETER")
    fun isTrusted(h1: String): Boolean = false
}
