package vn.hoicon.rules

/**
 * The only way personal numbers leave the code that read them (CLAUDE.md rule 1, ADR-006): a phone, account or ID
 * number is shown as `…123` (last 3 digits) or sent as `h1`, never as itself.
 *
 * [mask] is a safety net for free text that may carry a number (log lines, exception messages). It cannot know the
 * context, so it masks every run of 8+ digits, also when they were only a timestamp: over-masking beats a leak.
 */
object PiiMasker {
    private const val MIN_DIGITS = 8
    private const val KEEP = 3

    // Digits with the separators people type inside numbers (+84 912 345 678, 091-234-5678, (028) 3822 1234).
    private val NUMBER = Regex("""[+(]?\d(?:[\d\s.\-()]*\d)?""")

    /** [text] with every run of 8+ digits replaced by `…` + its last 3 digits. */
    fun mask(text: String): String = NUMBER.replace(text) { match ->
        val digits = match.value.filter(Char::isDigit)
        if (digits.length < MIN_DIGITS) match.value else "…" + digits.takeLast(KEEP)
    }

    /** True when [text] still holds a run of 8+ digits, i.e. [mask] would change it. */
    fun containsNumber(text: String): Boolean = NUMBER.findAll(text).any { m -> m.value.count(Char::isDigit) >= MIN_DIGITS }

    /** The caller as it may be stored or sent: hash + last 3 digits; null when [raw] is not a dialable number. */
    fun caller(raw: String?): HashedPhone? = raw?.let(PhoneHasher::hash)
}
