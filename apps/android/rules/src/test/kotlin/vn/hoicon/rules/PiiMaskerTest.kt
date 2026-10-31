package vn.hoicon.rules

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

class PiiMaskerTest {
    @Test
    fun masksNationalAndInternationalPhones() {
        assertEquals("gọi …678 nhé", PiiMasker.mask("gọi 0912345678 nhé"))
        assertEquals("từ …678", PiiMasker.mask("từ +84 912 345 678"))
        assertEquals("từ …678", PiiMasker.mask("từ +84-912-345-678"))
        assertEquals("bàn …234", PiiMasker.mask("bàn (028) 3822 1234"))
        assertEquals("…678", PiiMasker.mask("0084912345678"))
    }

    @Test
    fun masksAccountAndIdNumbers() {
        assertEquals("stk …789", PiiMasker.mask("stk 1234567890123456789"))
        assertEquals("cccd …901", PiiMasker.mask("cccd 079123456901"))
    }

    @Test
    fun keepsShortNumbersAndPlainText() {
        val text = "seeded 12 events in 345 ms, OTP flow, last3=678, api=36"
        assertEquals(text, PiiMasker.mask(text))
        assertFalse(PiiMasker.containsNumber(text))
    }

    @Test
    fun maskedTextNeverContainsMoreThanLastThree() {
        val masked = PiiMasker.mask("a 0912345678 b +84 988 777 666 c 1234567890123")
        assertFalse(PiiMasker.containsNumber(masked), masked)
        assertFalse("0912345678" in masked || "988777666" in masked)
    }

    @Test
    fun containsNumberFlagsRawNumbers() {
        assertTrue(PiiMasker.containsNumber("số 0912 345 678"))
        assertTrue(PiiMasker.containsNumber("+84912345678"))
    }

    @Test
    fun callerKeepsOnlyHashAndLast3() {
        val phone = assertNotNull(PiiMasker.caller("0912 345 678"))
        assertEquals("678", phone.last3)
        assertEquals(64, phone.h1.length)
        assertFalse("912345678" in phone.h1 + phone.toString())
        assertEquals("…678", phone.toString())
    }

    @Test
    fun callerIsNullWhenNotADialableNumber() {
        assertNull(PiiMasker.caller(null))
        assertNull(PiiMasker.caller("Private"))
        assertNull(PiiMasker.caller("113"))
    }
}
