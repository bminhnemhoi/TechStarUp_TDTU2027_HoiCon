package vn.hoicon.rules

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotEquals
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * Numbers are FICTIONAL (data/fixtures/phones.json uses the 0900000xxx range) and assembled at runtime so no
 * raw phone literal sits in source (guard-privacy, CLAUDE.md rule 2).
 */
class PhoneHasherTest {
    private val mobileNsn = "9" + "0000" + "0001" // national significant number of unknown_caller
    private val landlineNsn = "24" + "3999" + "0000" // fictional Hà Nội landline (10-digit NSN)
    private val vnMobile = "+84$mobileNsn"

    @Test
    fun vietnameseMobileFormsNormaliseToSameE164() {
        val forms = listOf(
            "0$mobileNsn",
            "+84$mobileNsn",
            "84$mobileNsn",
            "0084$mobileNsn",
            "+84 0$mobileNsn",
            " 0${mobileNsn.chunked(3).joinToString(" ")} ",
            "0${mobileNsn.chunked(3).joinToString(".")}",
            "(+84) ${mobileNsn.chunked(3).joinToString("-")}",
        )
        for (form in forms) assertEquals(vnMobile, PhoneHasher.toE164(form), "form: ${form.length} chars")
    }

    @Test
    fun invisibleUnicodeSeparatorsAreIgnored() {
        val nbsp = " "
        val narrowNbsp = " "
        val forms = listOf(
            "0${mobileNsn.chunked(3).joinToString(nbsp)}",
            "+84$narrowNbsp$mobileNsn",
            "‪+84 $mobileNsn‬", // LRE … PDF (bidi embedding from copy-paste)
            "‎0$mobileNsn", // LRM
            "﻿0$mobileNsn​", // BOM + zero-width space
        )
        for (form in forms) assertEquals(vnMobile, PhoneHasher.toE164(form), "form with ${form.length} code units")
    }

    @Test
    fun vietnameseLandlineWithTenDigitNationalNumber() {
        assertEquals("+84$landlineNsn", PhoneHasher.toE164("0$landlineNsn"))
        assertEquals("+84$landlineNsn", PhoneHasher.toE164("84$landlineNsn"))
    }

    @Test
    fun foreignInternationalNumbersAreKept() {
        val us = "1" + "555" + "0100" + "123"
        assertEquals("+$us", PhoneHasher.toE164("+$us"))
        assertEquals("+$us", PhoneHasher.toE164("00$us"))
        // "00" is the international prefix in VN, so 00 + 90… is a Turkish number, not a malformed VN one.
        assertEquals("+$mobileNsn", PhoneHasher.toE164("00$mobileNsn"))
    }

    @Test
    fun nonNumbersAndWrongLengthsAreRejected() {
        val rejected = listOf(
            "",
            "   ",
            "anonymous",
            "113", // emergency short code
            "1900" + "1234", // service number, national only
            "0" + "9" + "0000", // too short
            "0" + mobileNsn + "12", // NSN 11 digits
            "+84" + "9" + "000000", // NSN 7 digits
            "+0" + mobileNsn,
            "+" + "1" + "234567", // 7 digits
            "+" + "1".repeat(16), // > 15 digits
            "+84" + "00" + mobileNsn, // NSN starting with 0 after the trunk prefix is dropped
            "09x" + "0000001",
            "84" + "9" + "0000", // bare 84 with wrong length is not a country code
        )
        for (raw in rejected) assertNull(PhoneHasher.toE164(raw), "should reject a ${raw.length}-char input")
    }

    @Test
    fun h1KnownAnswer() {
        // python: hashlib.sha256(b"hoicon:v1:" + e164).hexdigest() — keep in sync with backend hoicon.domain.pii.
        assertEquals("3f0f23b3e724e869e1b0552e6c64ea562a022c311476be6dadb58b6011936956", PhoneHasher.h1(vnMobile))
    }

    @Test
    fun h1IsLowercaseHexAndStableAcrossForms() {
        val a = assertNotNull(PhoneHasher.hash("0$mobileNsn"))
        val b = assertNotNull(PhoneHasher.hash("+84 $mobileNsn"))
        assertEquals(a, b)
        assertTrue(Regex("^[0-9a-f]{64}$").matches(a.h1))
        assertEquals("001", a.last3)
        val other = assertNotNull(PhoneHasher.hash("0" + "9" + "0000" + "0002"))
        assertNotEquals(a.h1, other.h1)
        assertEquals("aa1b1fcd5c51853e998738c59cffa5a4d95bd39ef7ef3b6d905c9c6c3af987e4", other.h1)
    }

    @Test
    fun hashReturnsNullForNonNumbersAndToStringNeverLeaksTheNumber() {
        assertNull(PhoneHasher.hash("anonymous"))
        val hashed = assertNotNull(PhoneHasher.hash("0$mobileNsn"))
        assertEquals("…001", hashed.toString())
        assertTrue(mobileNsn !in hashed.toString())
    }

    @Test
    fun h1RejectsNonE164Input() {
        val result = runCatching { PhoneHasher.h1("0$mobileNsn") }
        assertTrue(result.isFailure)
    }
}
