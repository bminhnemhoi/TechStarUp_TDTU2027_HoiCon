package vn.hoicon.sentinel.domain

import org.junit.Test
import vn.hoicon.sentinel.domain.qr.VietQr
import vn.hoicon.sentinel.domain.qr.VietQrParser
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue

/** Spec 026 T027: payloads are FICTIONAL (made up payee, bank code and account); nothing here is a real account. */
class VietQrParserTest {
    // With amount 150000, payee NGUYEN VAN MAU.
    private val withAmount = "00020101021238540010A00000072701240006970403011001234567890208QRIBFTTA530370454061500005802VN5914NGUYEN VAN MAU6006HA NOI630420C9"

    // No amount (the sender types it), payee TRAN THI MAU.
    private val noAmount = "00020101021138540010A00000072701240006970403011001234567890208QRIBFTTA53037045802VN5912TRAN THI MAU63043E2E"

    // A well-formed EMV code of another scheme (GUID A000000999).
    private val otherScheme = "00020101021138190010A0000009990101x5904KHAC6304B5C4"

    @Test
    fun crcMatchesTheStandardCheckValue() {
        assertEquals("29B1", VietQrParser.crc16("123456789"))
    }

    @Test
    fun readsThePayeeAndTheAmount() {
        assertEquals(VietQr("NGUYEN VAN MAU", 150_000L), VietQrParser.parse(withAmount))
        assertEquals(VietQr("TRAN THI MAU", null), VietQrParser.parse(noAmount))
        assertEquals(VietQr("TRAN THI MAU", null), VietQrParser.parse("  $noAmount\n"))
    }

    @Test
    fun theAccountNumberIsNotKeptAnywhere() {
        val parsed = VietQrParser.parse(withAmount)!!
        assertFalse("0123456789" in parsed.toString())
    }

    @Test
    fun aTamperedCodeIsRefused() {
        assertNull(VietQrParser.parse(withAmount.replace("150000", "950000")), "amount changed, CRC no longer matches")
        assertNull(VietQrParser.parse(withAmount.replace("NGUYEN", "NGUYEM")))
        assertNull(VietQrParser.parse(withAmount.dropLast(1) + "0"))
        assertNull(VietQrParser.parse(withAmount.dropLast(4)), "no CRC")
        assertNull(VietQrParser.parse(withAmount.take(40)), "cut short")
    }

    @Test
    fun anotherSchemeOrNonQrTextIsRefused() {
        assertNull(VietQrParser.parse(otherScheme))
        assertTrue(VietQrParser.looksLikeEmv(otherScheme))
        for (text in listOf("", "hello", "https://example.org", "000201", "0002010102126304ABCD")) {
            assertNull(VietQrParser.parse(text), text)
        }
        assertFalse(VietQrParser.looksLikeEmv("https://example.org"))
    }

    @Test
    fun malformedFieldsNeverThrow() {
        val junk = listOf("00020101021238540010A0000007270124", "0002010102129999", "00020101021238ZZ", "000201" + "1".repeat(300))
        for (text in junk) assertNull(VietQrParser.parse(text), text)
    }
}
