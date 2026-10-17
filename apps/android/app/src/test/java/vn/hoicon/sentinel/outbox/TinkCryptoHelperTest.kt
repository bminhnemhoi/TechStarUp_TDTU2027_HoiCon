package vn.hoicon.sentinel.outbox

import org.junit.Test
import vn.hoicon.sentinel.data.local.TinkCryptoHelper
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNotEquals
import kotlin.test.assertNull
import kotlin.test.assertTrue

class TinkCryptoHelperTest {
    private val crypto = jvmCrypto()

    @Test
    fun roundTripsAndHidesThePlainText() {
        val plain = """{"caller":{"h1":"abc","last3":"678"}}"""
        val encrypted = checkNotNull(crypto.encrypt(plain, "event-1"))
        assertFalse("last3" in encrypted || "678" in encrypted)
        assertEquals(plain, crypto.decrypt(encrypted, "event-1"))
    }

    @Test
    fun sameTextEncryptsDifferentlyEachTime() {
        assertNotEquals(crypto.encrypt("x", "id"), crypto.encrypt("x", "id"))
    }

    @Test
    fun aCiphertextCannotBeMovedToAnotherRow() {
        val encrypted = checkNotNull(crypto.encrypt("secret", "event-1"))
        assertNull(crypto.decrypt(encrypted, "event-2"), "associated data = the row id")
    }

    @Test
    fun anAlteredCiphertextIsRefused() {
        val encrypted = checkNotNull(crypto.encrypt("secret", "event-1"))
        val altered = encrypted.dropLast(2) + if (encrypted.endsWith("AA")) "BB" else "AA"
        assertNull(crypto.decrypt(altered, "event-1"))
        assertNull(crypto.decrypt("not base64 !!", "event-1"))
    }

    @Test
    fun anotherKeyCannotRead() {
        val encrypted = checkNotNull(crypto.encrypt("secret", "event-1"))
        assertNull(jvmCrypto().decrypt(encrypted, "event-1"))
    }

    @Test
    fun withoutAKeyNothingIsEverStoredInThePlain() {
        val none = TinkCryptoHelper(null)
        assertFalse(none.isAvailable)
        assertNull(none.encrypt("secret", "id"))
        assertNull(none.decrypt("anything", "id"))
        assertTrue(crypto.isAvailable)
    }
}
