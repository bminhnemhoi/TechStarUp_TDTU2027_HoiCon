package vn.hoicon.sentinel.domain.qr

/** What a scanned QR code turned out to hold, decided on the phone (Spec 026 FR-012, plan D5). */
sealed interface QrContent {
    /** A web link: checked like a typed link (`via = qr`). */
    data class Link(val url: String) : QrContent

    /** A `tel:` code: the number is hashed on the phone and checked like a typed number. */
    data class Phone(val number: String) : QrContent

    /** A VietQR transfer code: read here, nothing is sent (no source for accounts; the account number is personal data). */
    data class Transfer(val qr: VietQr) : QrContent

    /** Anything else, including a VietQR with a bad checksum or another scheme. */
    data object Unreadable : QrContent

    companion object {
        private val WEB = Regex("^https?://", RegexOption.IGNORE_CASE)

        fun classify(raw: String?): QrContent {
            val text = raw?.trim().orEmpty()
            if (text.isEmpty()) return Unreadable
            VietQrParser.parse(text)?.let { return Transfer(it) }
            if (text.startsWith("tel:", ignoreCase = true)) return text.substring(4).takeIf { it.isNotBlank() }?.let(::Phone) ?: Unreadable
            if (WEB.containsMatchIn(text)) return Link(text)
            return Unreadable
        }
    }
}
