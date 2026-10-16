package vn.hoicon.sentinel.domain.lookup

import java.net.IDN

/**
 * Cuts a pasted or scanned link down to what the server needs before anything leaves the phone (Spec 026 FR-012):
 * `scheme://host[:port]/path`. User-info (`user:pass@`), the query string and the fragment are dropped here, because
 * they carry tokens and personal data and play no part in the verdict. The host is lower-cased and punycoded (IDNA), so
 * a look-alike domain shows up as `xn--…`.
 *
 * Personal data that hides in a link never leaves the phone either (CLAUDE.md rule 1): a host holding a phone-number-sized
 * run of digits is refused, and a long digit run in the path (an account or phone number) is replaced by `*`.
 *
 * A link typed without a scheme is taken as `https://`. Anything that is not a plain web link (`javascript:`, `file:`,
 * spaces, no host) gives null.
 */
object UrlSanitizer {
    private const val MAX_LENGTH = 2048
    private val WEB_SCHEME = Regex("^(https?)://", RegexOption.IGNORE_CASE)
    // "javascript:", "file:", "tel:" …: a scheme-like prefix whose colon is not followed by a port number.
    private val OTHER_SCHEME = Regex("^[A-Za-z][A-Za-z0-9+.-]*:(?![0-9])")
    private val DIGIT_RUN = Regex("""[0-9](?:[._-]?[0-9]){6,}""")
    private const val PHONE_SIZED_DIGITS = 7
    private val HOST = Regex("^(?:[a-z0-9]([a-z0-9-]*[a-z0-9])?)(?:\\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*$|^\\[[0-9a-f:.]+]$")

    fun sanitize(raw: String): String? {
        val text = raw.trim()
        if (text.isEmpty() || text.any { it.isWhitespace() || it.isISOControl() }) return null
        val web = WEB_SCHEME.find(text)
        val scheme = web?.groupValues?.get(1)?.lowercase() ?: run {
            if (OTHER_SCHEME.containsMatchIn(text)) return null
            "https"
        }
        val rest = if (web != null) text.substring(web.value.length) else text
        val authorityEnd = rest.indexOfFirst { it == '/' || it == '?' || it == '#' }.let { if (it < 0) rest.length else it }
        val authority = rest.substring(0, authorityEnd).substringAfterLast('@')
        val path = rest.substring(authorityEnd).substringBefore('#').substringBefore('?').replace(DIGIT_RUN, "*")
        val (hostRaw, port) = splitPort(authority) ?: return null
        val host = try {
            IDN.toASCII(hostRaw, IDN.ALLOW_UNASSIGNED).lowercase()
        } catch (_: IllegalArgumentException) {
            return null
        }
        if (host.isEmpty() || host.length > 253 || !HOST.matches(host)) return null
        if (host.count { it in '0'..'9' } >= PHONE_SIZED_DIGITS) return null
        val clean = "$scheme://$host${port?.let { ":$it" }.orEmpty()}$path"
        return clean.takeIf { it.length <= MAX_LENGTH }
    }

    private fun splitPort(authority: String): Pair<String, Int?>? {
        if (authority.startsWith("[")) return authority to null
        val colon = authority.lastIndexOf(':')
        if (colon < 0) return authority to null
        val port = authority.substring(colon + 1).toIntOrNull()?.takeIf { it in 1..65535 } ?: return null
        return authority.substring(0, colon) to port
    }
}
