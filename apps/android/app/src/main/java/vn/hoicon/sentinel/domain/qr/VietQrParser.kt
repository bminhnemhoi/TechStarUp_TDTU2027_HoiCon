package vn.hoicon.sentinel.domain.qr

/**
 * What a VietQR transfer code says, read ON THE PHONE (Spec 026 FR-012): nothing here is ever sent to the server.
 * The account number is deliberately NOT kept: it is personal data and the person only needs the payee's name.
 */
data class VietQr(val payeeName: String, val amountVnd: Long?)

/**
 * Parser for EMVCo merchant-presented QR (the format behind VietQR): a run of `tag(2) length(2) value` fields, the last
 * being `63 04 <CRC16>`. A code is accepted only when the CRC matches (a tampered or half-scanned code is refused) and
 * its merchant-account block (tag 38) carries the NAPAS GUID `A000000727`.
 */
object VietQrParser {
    private const val GUID = "A000000727"
    private const val CRC_TAG_PREFIX = "6304"

    /** @return null when [payload] is not a well-formed VietQR transfer code. */
    fun parse(payload: String): VietQr? {
        val text = payload.trim()
        if (text.length < 24 || !text.startsWith("000201") || !crcMatches(text)) return null
        val fields = readFields(text) ?: return null
        val account = readFields(fields["38"] ?: return null) ?: return null
        if (account["00"] != GUID) return null
        val name = fields["59"]?.trim()?.takeIf { it.isNotEmpty() } ?: return null
        val amount = fields["54"]?.let { it.toLongOrNull()?.takeIf { v -> v > 0 } ?: return null }
        return VietQr(payeeName = name, amountVnd = amount)
    }

    /** True when the text looks like an EMV payload at all (so the caller can say "not a code I understand"). */
    fun looksLikeEmv(payload: String) = payload.trim().startsWith("000201")

    private fun readFields(text: String): Map<String, String>? {
        val out = LinkedHashMap<String, String>()
        var i = 0
        while (i < text.length) {
            if (i + 4 > text.length) return null
            val tag = text.substring(i, i + 2)
            val length = text.substring(i + 2, i + 4).toIntOrNull()?.takeIf { it >= 0 } ?: return null
            if (!tag.all { it in '0'..'9' } || i + 4 + length > text.length) return null
            if (out.put(tag, text.substring(i + 4, i + 4 + length)) != null) return null // a repeated tag is not valid
            i += 4 + length
        }
        return out
    }

    private fun crcMatches(text: String): Boolean {
        val at = text.length - 8
        if (at < 0 || text.substring(at, at + 4) != CRC_TAG_PREFIX) return false
        val expected = text.substring(at + 4)
        return expected.equals(crc16(text.substring(0, at + 4)), ignoreCase = true)
    }

    /** CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF), as 4 upper-case hex digits. */
    internal fun crc16(data: String): String {
        var crc = 0xFFFF
        for (byte in data.toByteArray(Charsets.UTF_8)) {
            crc = crc xor ((byte.toInt() and 0xFF) shl 8)
            repeat(8) { crc = if (crc and 0x8000 != 0) ((crc shl 1) xor 0x1021) and 0xFFFF else (crc shl 1) and 0xFFFF }
        }
        return "%04X".format(crc)
    }
}
