package vn.hoicon.sentinel.data

import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue
import vn.hoicon.sentinel.data.local.DeviceSession
import vn.hoicon.sentinel.data.local.TokenStorage

class TokenStorageTest {
    private val session = DeviceSession(
        deviceId = "01928374-abcd-7123-89ef-0123456789ab",
        familyId = "01928374-abcd-7123-89ef-0123456789cd",
        memberId = "01928374-abcd-7123-89ef-0123456789ef",
        familyName = "Gia đình Bác Ba",
        accessToken = "sample-device-access-token",
        refreshToken = "sample-device-refresh-token",
    )

    @Test
    fun freshDeviceIsNotPaired() {
        val storage = TokenStorage(FakePrefs())
        assertFalse(storage.hasValidToken())
        assertNull(storage.load())
        assertNull(storage.acceptedDisclosureVersion)
        assertTrue(storage.recordedConsents.isEmpty())
    }

    @Test
    fun savedSessionRoundTrips() {
        val prefs = FakePrefs()
        TokenStorage(prefs).save(session)
        val reopened = TokenStorage(prefs)
        assertTrue(reopened.hasValidToken())
        assertEquals(session, reopened.load())
    }

    @Test
    fun aMissingFieldMeansNotPaired() {
        val prefs = FakePrefs()
        TokenStorage(prefs).save(session)
        prefs.map.remove("refresh_token")
        assertFalse(TokenStorage(prefs).hasValidToken())
        prefs.map["refresh_token"] = "  "
        assertFalse(TokenStorage(prefs).hasValidToken())
    }

    @Test
    fun disclosureVersionAndRecordedPurposesPersistAndClear() {
        val prefs = FakePrefs()
        val storage = TokenStorage(prefs)
        storage.save(session)
        storage.acceptedDisclosureVersion = "v1"
        storage.recordedConsents = setOf("core_protection", "call_screening")
        val reopened = TokenStorage(prefs)
        assertEquals("v1", reopened.acceptedDisclosureVersion)
        assertEquals(setOf("core_protection", "call_screening"), reopened.recordedConsents)
        reopened.clear()
        assertFalse(reopened.hasValidToken())
        assertNull(reopened.acceptedDisclosureVersion)
    }

    @Test
    fun sessionToStringNeverShowsTokens() {
        val text = session.toString()
        assertFalse(text.contains(session.accessToken))
        assertFalse(text.contains(session.refreshToken))
        assertFalse(text.contains(session.familyName))
    }

    @Test
    fun aBrokenKeystoreReadsAsNotPairedInsteadOfCrashing() {
        val storage = TokenStorage(throwingPrefs())
        assertFalse(storage.hasValidToken())
        assertNull(storage.load())
        assertNull(storage.acceptedDisclosureVersion)
        assertTrue(storage.recordedConsents.isEmpty())
        assertFalse(storage.save(session), "a failed write must be reported")
        storage.acceptedDisclosureVersion = "v1"
        storage.recordedConsents = setOf("x")
        storage.clear()
    }

    @Test
    fun storageThatCouldNotBeOpenedStaysUnpaired() {
        val storage = TokenStorage(null)
        assertFalse(storage.save(session))
        assertFalse(storage.hasValidToken())
    }
}
