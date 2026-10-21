package vn.hoicon.sentinel.data

import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue
import vn.hoicon.sentinel.data.consent.ConsentLedger
import vn.hoicon.sentinel.data.consent.DrillConsent
import vn.hoicon.sentinel.data.local.TokenStorage

/** Spec 028 Medium #1: practice calls need a deliberate, adult, just-in-time yes; "Để lúc khác" leaves no trace. */
class DrillConsentTest {
    private val storage = TokenStorage(FakePrefs())
    private val consent = DrillConsent(storage)

    @Test
    fun withoutTheAdultTickNothingIsAgreed() {
        assertEquals(DrillConsent.Result.NEEDS_ADULT_CONFIRMATION, consent.accept(adultConfirmed = false))
        assertFalse(consent.agreed)
        assertNull(storage.acceptedDrillsVersion)
    }

    @Test
    fun anAdultYesIsRememberedForTheCurrentWords() {
        assertEquals(DrillConsent.Result.AGREED, consent.accept(adultConfirmed = true))
        assertTrue(consent.agreed)
        assertEquals(ConsentLedger.VERSION, storage.acceptedDrillsVersion)
    }

    @Test
    fun anOlderVersionOfTheYesDoesNotCount() {
        storage.acceptedDrillsVersion = "2026.10-v2"
        assertFalse(consent.agreed)
    }
}
