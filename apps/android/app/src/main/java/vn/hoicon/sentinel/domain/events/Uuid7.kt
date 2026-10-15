package vn.hoicon.sentinel.domain.events

import java.security.SecureRandom

/**
 * UUIDv7 (RFC 9562): 48-bit Unix milliseconds, version 7, 74 random bits. Event ids are made on the phone, so the
 * server can de-duplicate a re-sent batch (`ON CONFLICT (id) DO NOTHING`); time order keeps the index tidy.
 */
object Uuid7 {
    private val random = SecureRandom()

    fun generate(nowMs: Long = System.currentTimeMillis()): String {
        val bytes = ByteArray(16).also(random::nextBytes)
        for (i in 0 until 6) bytes[i] = (nowMs shr (8 * (5 - i))).toByte()
        bytes[6] = ((bytes[6].toInt() and 0x0F) or 0x70).toByte() // version 7
        bytes[8] = ((bytes[8].toInt() and 0x3F) or 0x80).toByte() // variant 10
        val hex = bytes.joinToString("") { "%02x".format(it) }
        return "${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20)}"
    }
}
