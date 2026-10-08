package vn.hoicon.rules

import java.security.MessageDigest

/** The only form of a phone number allowed outside the screening callback (ADR-006): hash + last 3 digits. */
data class HashedPhone(val h1: String, val last3: String) {
    override fun toString(): String = "…$last3"
}

/**
 * E.164 normalisation and `h1 = SHA-256("hoicon:v1:" + e164)` (lowercase hex), see ADR-006 and DATA-MODEL §3.
 * Callers keep the E.164 string only long enough to hash it; never log, persist or send it.
 */
object PhoneHasher {
    private const val H1_PREFIX = "hoicon:v1:"
    private const val VN_COUNTRY_CODE = "84"
    // Visual separators plus invisible ones that arrive with copy-pasted numbers: any Unicode space (\p{Z}: NBSP,
    // narrow NBSP…) and format characters (\p{Cf}: LRM U+200E, LRE/PDF U+202A/U+202C, zero-width space, BOM).
    private val SEPARATORS = Regex("""[\p{Z}\p{Cf}\s.\-()/]""")
    private val E164 = Regex("""^\+[1-9]\d{7,14}$""")

    /**
     * Normalises a dialable number to E.164 (`+<country><number>`), or null when it can't be one
     * (hidden number, short/service code, letters, wrong length).
     *
     * Vietnamese forms accepted: national `0…`, `+84…`, `0084…`, bare `84…`; the national significant number
     * must be 9 (mobile) or 10 (landline) digits. Other international numbers (`+`/`00`) are kept when 8–15 digits.
     */
    fun toE164(raw: String): String? {
        val s = raw.trim().replace(SEPARATORS, "")
        val (digits, international) = when {
            s.startsWith("+") -> s.substring(1) to true
            s.startsWith("00") -> s.substring(2) to true
            else -> s to false
        }
        if (digits.isEmpty() || !digits.all { it in '0'..'9' }) return null

        val vnNationalNumber = when {
            international && digits.startsWith(VN_COUNTRY_CODE) -> digits.substring(2).removePrefix("0")
            international -> return "+$digits".takeIf { E164.matches(it) }
            digits.startsWith("0") -> digits.substring(1)
            digits.startsWith(VN_COUNTRY_CODE) && digits.length in 11..12 -> digits.substring(2)
            else -> return null
        }
        return vnNationalNumber
            .takeIf { it.length in 9..10 && it[0] != '0' }
            ?.let { "+$VN_COUNTRY_CODE$it" }
    }

    /** `SHA-256("hoicon:v1:" + e164)` as 64 lowercase hex chars. */
    fun h1(e164: String): String {
        require(E164.matches(e164)) { "not an E.164 number" }
        val digest = MessageDigest.getInstance("SHA-256").digest((H1_PREFIX + e164).toByteArray(Charsets.UTF_8))
        return digest.joinToString(separator = "") { byte -> "%02x".format(byte) }
    }

    /** Normalises and hashes in one step so the E.164 string never escapes; null when [raw] isn't a phone number. */
    fun hash(raw: String): HashedPhone? = toE164(raw)?.let { HashedPhone(h1 = h1(it), last3 = it.takeLast(3)) }
}
