package vn.hoicon.sentinel.data.lookup

import vn.hoicon.rules.HashedPhone
import vn.hoicon.rules.PhoneHasher
import vn.hoicon.sentinel.data.remote.LookupAnswer
import vn.hoicon.sentinel.data.remote.LookupGateway
import vn.hoicon.sentinel.data.remote.LookupKind
import vn.hoicon.sentinel.data.remote.LookupResult
import vn.hoicon.sentinel.data.remote.LookupVia
import vn.hoicon.sentinel.data.threat.ThreatIndexHolder
import vn.hoicon.sentinel.domain.lookup.UrlSanitizer

/** What the person typed, after it was cut down to what may leave the phone. The raw text is not kept anywhere in here. */
sealed interface LookupInput {
    data class Phone(val phone: HashedPhone) : LookupInput

    /** [url] is already `scheme://host[:port]/path`; [host] is shown back to the person. */
    data class Link(val url: String, val host: String) : LookupInput

    data object Empty : LookupInput

    /** Looks like a phone number but is not one this app can hash (hidden, too short, letters mixed in). */
    data object BadPhone : LookupInput

    data object BadLink : LookupInput

    companion object {
        // Digits and the separators people type or paste between them (spaces, dots, dashes, brackets, plus).
        private val PHONE_LIKE = Regex("""^[+\p{N}\p{Z}\p{Cf}\s.()/-]+$""")

        fun parse(raw: String): LookupInput {
            val text = raw.trim()
            if (text.isEmpty()) return Empty
            val number = if (text.startsWith("tel:", ignoreCase = true)) text.substring(4) else text
            if (PHONE_LIKE.matches(number)) return PhoneHasher.hash(number)?.let(::Phone) ?: BadPhone
            val url = UrlSanitizer.sanitize(text)
                // A number followed by one stray letter, or inside a link host must never travel as a link.
                ?: return if (text.substringBefore('/').count { it in '0'..'9' } >= 7) BadPhone else BadLink
            return Link(url, host = url.substringAfter("://").substringBefore('/'))
        }
    }
}

/** What E10 shows afterwards. There is no "safe" for a phone number anywhere in this type's phone paths. */
sealed interface LookupOutcome {
    /** [subject]: the last 3 digits of a phone, or the host of a link. */
    data class Answer(val kind: LookupKind, val subject: String, val answer: LookupAnswer) : LookupOutcome

    /** No answer from the server: [possiblyListed] only from the on-device bucket list, and only for a phone. */
    data class Offline(val kind: LookupKind, val subject: String, val possiblyListed: Boolean) : LookupOutcome

    /** A VietQR transfer code read on the phone only (Spec 026 FR-012): nothing was sent, nothing is claimed about the account. */
    data class Transfer(val payeeName: String, val amountVnd: Long?) : LookupOutcome

    data class Notice(val reason: NoticeReason) : LookupOutcome
}

enum class NoticeReason { RATE_LIMITED, CONSENT_PENDING, GENERIC, QR_UNREADABLE }

/**
 * Runs one check (Spec 026 FR-011): asks the server, and when the server cannot be reached falls back to the bucket
 * list on the phone ("có thể nằm trong danh sách", never "an toàn"). Blocking: background thread only.
 *
 * @param consent brings the consent ledger up to date; true when it is. Called once when the server says the
 *   `lookups` consent is missing, because the just-in-time acceptance may not have reached the server yet.
 * @param onUnauthorized the device token was refused (E6 will say so).
 */
class LookupChecker(
    private val gateway: LookupGateway,
    private val index: ThreatIndexHolder,
    private val accessToken: () -> String?,
    private val consent: () -> Boolean,
    private val onUnauthorized: () -> Unit,
) {
    fun check(input: LookupInput, incidentId: String? = null, via: LookupVia = LookupVia.TYPED): LookupOutcome {
        val kind: LookupKind
        val subject: String
        when (input) {
            is LookupInput.Phone -> { kind = LookupKind.PHONE; subject = input.phone.last3 }
            is LookupInput.Link -> { kind = LookupKind.URL; subject = input.host }
            else -> return LookupOutcome.Notice(NoticeReason.GENERIC)
        }
        val offline = LookupOutcome.Offline(kind, subject, possiblyListed = input is LookupInput.Phone && index.current.contains(input.phone.h1))
        val token = accessToken() ?: return offline

        fun call(incident: String?): LookupResult = when (input) {
            is LookupInput.Phone -> gateway.lookupPhone(token, input.phone, via, incident)
            is LookupInput.Link -> gateway.lookupUrl(token, input.url, via, incident)
            else -> LookupResult.Rejected
        }

        var result = call(incidentId)
        if (result is LookupResult.ConsentRequired && consent()) result = call(incidentId)
        // The incident ended or is not this family's: the check itself still stands, without the link to it.
        if (result is LookupResult.IncidentNotFound) result = call(null)
        return when (result) {
            is LookupResult.Done -> LookupOutcome.Answer(kind, subject, result.answer)
            is LookupResult.ConsentRequired -> LookupOutcome.Notice(NoticeReason.CONSENT_PENDING)
            is LookupResult.Unauthorized -> offline.also { onUnauthorized() }
            is LookupResult.RateLimited -> LookupOutcome.Notice(NoticeReason.RATE_LIMITED)
            is LookupResult.NetworkError, is LookupResult.ServerError -> offline
            is LookupResult.Rejected, is LookupResult.IncidentNotFound -> LookupOutcome.Notice(NoticeReason.GENERIC)
        }
    }
}
