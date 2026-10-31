package vn.hoicon.sentinel.data

import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue
import vn.hoicon.sentinel.data.consent.ConsentLedger
import vn.hoicon.sentinel.sensing.SensorPermission

class ConsentLedgerTest {
    private val texts = mapOf(
        "core_protection" to "core",
        "call_screening" to "call",
        "usage_monitoring" to "usage",
        "overlay_pause" to "overlay",
    )

    @Test
    fun sha256MatchesTheStandardVector() {
        assertEquals("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", ConsentLedger.sha256Hex("abc"))
    }

    @Test
    fun hashCoversVietnameseTextAsUtf8() {
        assertEquals(64, ConsentLedger.sha256Hex("Đây là trợ lý AI HỏiCon").length)
        assertTrue(ConsentLedger.sha256Hex("bác") != ConsentLedger.sha256Hex("bac"))
    }

    @Test
    fun onlyPermissionsWithAConsentPurposeMapToOne() {
        assertEquals("call_screening", ConsentLedger.purposeOf(SensorPermission.CALL_SCREENING_ROLE))
        assertEquals("usage_monitoring", ConsentLedger.purposeOf(SensorPermission.USAGE_ACCESS))
        assertEquals("overlay_pause", ConsentLedger.purposeOf(SensorPermission.DISPLAY_OVER_APPS))
        assertNull(ConsentLedger.purposeOf(SensorPermission.NOTIFICATIONS))
        assertNull(ConsentLedger.purposeOf(SensorPermission.BATTERY_UNRESTRICTED))
    }

    private fun keys(vararg purposes: String) = purposes.mapTo(mutableSetOf()) { ConsentLedger.key(it, texts.getValue(it)) }

    @Test
    fun newlyGrantedPurposesAreAppendedOnce() {
        val first = ConsentLedger.changes(emptySet(), setOf("core_protection", "call_screening"), texts)
        assertEquals(listOf("call_screening", "core_protection"), first.map { it.purpose })
        assertTrue(first.all { it.granted && it.channel == "app" && it.consentVersion == ConsentLedger.versionOf(it.purpose) })
        assertEquals(ConsentLedger.sha256Hex("call"), first.first().textSha256)
        // Nothing changed since the server last heard from us: nothing to send.
        val recorded = keys("core_protection", "call_screening")
        assertTrue(ConsentLedger.changes(recorded, setOf("core_protection", "call_screening"), texts).isEmpty())
    }

    @Test
    fun addingTheLookupsPurposeAppendsOneRowAndLeavesFamilySharingAlone() {
        val all = texts + ("lookups" to "lookups") + ("guardian_alerts" to "guardian")
        val recorded = ConsentLedger.changes(emptySet(), setOf("core_protection", "guardian_alerts"), all)
            .mapTo(mutableSetOf()) { ConsentLedger.key(it.purpose, all.getValue(it.purpose)) }
        val rows = ConsentLedger.changes(recorded, setOf("core_protection", "guardian_alerts", "lookups"), all)
        assertEquals(listOf("lookups"), rows.map { it.purpose })
        assertEquals(ConsentLedger.versionOf(rows.single().purpose), rows.single().consentVersion)
        // The new purpose never touches the gate that lets events leave the phone for the family.
        assertTrue(ConsentLedger.mayShareWithFamily(ConsentLedger.DISCLOSURE_VERSION, recorded, all))
    }

    @Test
    fun aRevokedPermissionBecomesANewGrantedFalseRow() {
        val rows = ConsentLedger.changes(keys("core_protection", "usage_monitoring"), setOf("core_protection"), texts)
        assertEquals(1, rows.size)
        assertEquals("usage_monitoring", rows[0].purpose)
        assertEquals(false, rows[0].granted)
    }

    @Test
    fun newWordingOfAStillGrantedPurposeIsRecordedAgain() {
        // The user accepted the old text; the screen now says something else (version bump): a fresh granted=true row,
        // and no granted=false row for the purpose that is still on.
        val oldRecorded = setOf("core_protection|2025.01-v0|" + ConsentLedger.sha256Hex("old wording"))
        val rows = ConsentLedger.changes(oldRecorded, setOf("core_protection"), texts)
        assertEquals(1, rows.size)
        assertEquals("core_protection", rows[0].purpose)
        assertTrue(rows[0].granted)
        assertEquals(ConsentLedger.sha256Hex("core"), rows[0].textSha256)
    }

    @Test
    fun nothingIsSharedUntilTheCurrentDisclosureIsAcceptedAndItsGrantIsOnTheLedger() {
        val words = mapOf("guardian_alerts" to "guardian words")
        val recorded = setOf(ConsentLedger.key("guardian_alerts", "guardian words"))
        assertTrue(ConsentLedger.mayShareWithFamily(ConsentLedger.DISCLOSURE_VERSION, recorded, words))
        // accepted but the server has not confirmed yet (offline / 5xx): still closed
        assertFalse(ConsentLedger.mayShareWithFamily(ConsentLedger.DISCLOSURE_VERSION, emptySet(), words))
        // an older version accepted (device upgraded, "Chưa đồng ý" on the new E3): closed
        assertFalse(ConsentLedger.mayShareWithFamily("2026.10-v1", recorded, words))
        assertFalse(ConsentLedger.mayShareWithFamily(null, recorded, words))
        // the words changed since the grant was recorded: closed until it is agreed again
        assertFalse(ConsentLedger.mayShareWithFamily(ConsentLedger.DISCLOSURE_VERSION, recorded, mapOf("guardian_alerts" to "new words")))
        assertFalse(ConsentLedger.mayShareWithFamily(ConsentLedger.DISCLOSURE_VERSION, recorded, emptyMap()))
    }

    @Test
    fun guardianAlertsCarriesItsOwnNewerVersionSoE3IsAskedAgain() {
        // Spec 031 + 032 reworded guardian_alerts (2026.10-v4); the other texts stay on v3 and nobody agrees to them twice.
        assertEquals("2026.10-v4", ConsentLedger.versionOf("guardian_alerts"))
        assertEquals(ConsentLedger.VERSION, ConsentLedger.versionOf("lookups"))
        val words = mapOf("guardian_alerts" to "guardian")
        val recorded = setOf(ConsentLedger.key("guardian_alerts", "guardian"))
        assertTrue(ConsentLedger.mayShareWithFamily(ConsentLedger.DISCLOSURE_VERSION, recorded, words))
        // Someone who accepted E3 under the v3 words must see E3 again before anything leaves the phone.
        assertFalse(ConsentLedger.mayShareWithFamily(ConsentLedger.VERSION, recorded, words))
        // A v3 row recorded earlier does not count for the v4 words.
        assertFalse(ConsentLedger.mayShareWithFamily(ConsentLedger.DISCLOSURE_VERSION, setOf("guardian_alerts|2026.10-v3|" + ConsentLedger.sha256Hex("guardian")), words))
    }
}
