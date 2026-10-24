package vn.hoicon.sentinel.data

import com.sun.net.httpserver.HttpServer
import java.net.InetSocketAddress
import org.json.JSONObject
import org.junit.After
import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue
import vn.hoicon.sentinel.data.consent.ConsentLedger
import vn.hoicon.sentinel.data.consent.ConsentSync
import vn.hoicon.sentinel.data.consent.DrillConsent
import vn.hoicon.sentinel.data.local.DeviceSession
import vn.hoicon.sentinel.data.local.TokenStorage
import vn.hoicon.sentinel.data.remote.PairingApiClient
import vn.hoicon.sentinel.sensing.SensorPermission

class ConsentSyncTest {
    private val bodies = mutableListOf<JSONObject>()
    private var status = 200
    private val server = HttpServer.create(InetSocketAddress("127.0.0.1", 0), 0).also { s ->
        s.createContext("/v1/consents") { ex ->
            bodies += JSONObject(ex.requestBody.readBytes().toString(Charsets.UTF_8))
            ex.sendResponseHeaders(status, -1)
            ex.close()
        }
        s.start()
    }
    private val storage = TokenStorage(FakePrefs()).also {
        it.save(DeviceSession("d", "f", "m", "Nhà", "access", "refresh"))
        it.acceptedDisclosureVersion = ConsentLedger.DISCLOSURE_VERSION
    }
    private val sync = ConsentSync(storage, PairingApiClient("http://127.0.0.1:${server.address.port}", timeoutMs = 2_000))
    private val texts = mapOf(
        "core_protection" to "core",
        "guardian_alerts" to "guardian",
        "call_screening" to "call",
        "usage_monitoring" to "usage",
        "overlay_pause" to "overlay",
        "lookups" to "lookups",
        "drills" to "drills",
    )

    @After
    fun stop() = server.stop(0)

    private fun purposeNames(keys: Set<String>) = keys.map { it.substringBefore('|') }.toSet()

    private fun purposesSent(call: Int) = bodies[call].getJSONArray("items").let { a -> List(a.length()) { a.getJSONObject(it).getString("purpose") to a.getJSONObject(it).getBoolean("granted") } }

    @Test
    fun firstRunRecordsTheDisclosureAndEachGrantedPermissionOnce() {
        val granted = setOf(SensorPermission.CALL_SCREENING_ROLE, SensorPermission.NOTIFICATIONS, SensorPermission.BATTERY_UNRESTRICTED)
        assertEquals(ConsentSync.Outcome.UP_TO_DATE, sync.run(granted, texts))
        // Notifications and battery have no consent purpose; the disclosure and the call-screening role do.
        assertEquals(listOf("call_screening" to true, "core_protection" to true, "guardian_alerts" to true), purposesSent(0))
        assertEquals(setOf("core_protection", "guardian_alerts", "call_screening"), purposeNames(storage.recordedConsents))

        assertEquals(ConsentSync.Outcome.UP_TO_DATE, sync.run(granted, texts))
        assertEquals(1, bodies.size, "nothing changed, nothing sent")
    }

    @Test
    fun aPermissionTurnedOffLaterAppendsAFalseRow() {
        sync.run(setOf(SensorPermission.USAGE_ACCESS), texts)
        sync.run(emptySet(), texts)
        assertEquals(listOf("usage_monitoring" to false), purposesSent(1))
        assertEquals(setOf("core_protection", "guardian_alerts"), purposeNames(storage.recordedConsents))
    }

    @Test
    fun noDisclosureAcceptedMeansNoCoreRow() {
        storage.acceptedDisclosureVersion = "an-older-version"
        sync.run(setOf(SensorPermission.DISPLAY_OVER_APPS), texts)
        assertEquals(listOf("overlay_pause" to true), purposesSent(0))
    }

    @Test
    fun drillsAreRecordedOnlyAfterTheAdultAgreedToThem() {
        sync.run(emptySet(), texts)
        assertEquals(listOf("core_protection" to true, "guardian_alerts" to true), purposesSent(0))
        assertEquals(DrillConsent.Result.NEEDS_ADULT_CONFIRMATION, DrillConsent(storage).accept(adultConfirmed = false))
        sync.run(emptySet(), texts)
        assertEquals(1, bodies.size, "no 18+ tick, nothing recorded")
        assertEquals(DrillConsent.Result.AGREED, DrillConsent(storage).accept(adultConfirmed = true))
        sync.run(emptySet(), texts)
        assertEquals(listOf("drills" to true), purposesSent(1))
    }

    @Test
    fun twoSyncObjectsRunningTogetherRecordAGrantOnlyOnce() {
        // E6 and the consent screens each make their own ConsentSync: the lock must be shared, or both send the same row.
        val other = ConsentSync(storage, PairingApiClient("http://127.0.0.1:${server.address.port}", timeoutMs = 2_000))
        val threads = listOf(sync, other).map { s -> Thread { s.run(emptySet(), texts) } }
        threads.forEach { it.start() }
        threads.forEach { it.join() }
        assertEquals(1, bodies.size, "the second run must find the grant already recorded")
    }

    @Test
    fun aFailedSendStaysPendingAndIsRetriedNextTime() {
        status = 500
        assertEquals(ConsentSync.Outcome.PENDING, sync.run(emptySet(), texts))
        assertTrue(storage.recordedConsents.isEmpty())
        status = 200
        assertEquals(ConsentSync.Outcome.UP_TO_DATE, sync.run(emptySet(), texts))
        assertEquals(2, bodies.size)
        assertEquals(setOf("core_protection", "guardian_alerts"), purposeNames(storage.recordedConsents))
    }

    @Test
    fun theFamilyAlertsPurposeIsRecordedWithTheDisclosureAndNotWithoutIt() {
        sync.run(emptySet(), texts)
        assertEquals(listOf("core_protection" to true, "guardian_alerts" to true), purposesSent(0))
        storage.clear()
        storage.save(DeviceSession("d", "f", "m", "Nhà", "access", "refresh"))
        sync.run(emptySet(), texts)
        assertEquals(1, bodies.size, "an unaccepted disclosure records nothing, so nothing about the family is agreed")
    }

    @Test
    fun aDeviceUpgradedFromAnOlderVersionRecordsNothingUntilItAcceptsTheNewDisclosure() {
        storage.acceptedDisclosureVersion = "2026.10-v1"
        sync.run(setOf(SensorPermission.CALL_SCREENING_ROLE), texts)
        assertEquals(listOf("call_screening" to true), purposesSent(0), "no core_protection and no guardian_alerts for v2")
    }

    @Test
    fun aNewTextOfTheSamePurposeIsSentAgain() {
        sync.run(emptySet(), texts)
        assertEquals(1, bodies.size)
        sync.run(emptySet(), texts + ("core_protection" to "core, reworded"))
        assertEquals(2, bodies.size)
        assertEquals(listOf("core_protection" to true), purposesSent(1))
    }

    @Test
    fun lookupsIsRecordedOnlyAfterTheJustInTimeAcceptanceAndNeverForcesTheOthersAgain() {
        sync.run(emptySet(), texts)
        assertEquals(listOf("core_protection" to true, "guardian_alerts" to true), purposesSent(0))

        sync.run(emptySet(), texts)
        assertEquals(1, bodies.size, "not accepted yet: nothing about lookups is sent")

        storage.acceptedLookupsVersion = ConsentLedger.VERSION
        assertEquals(ConsentSync.Outcome.UP_TO_DATE, sync.run(emptySet(), texts))
        assertEquals(listOf("lookups" to true), purposesSent(1), "only the new purpose is sent; the earlier grants are not repeated")
        assertEquals(setOf("core_protection", "guardian_alerts", "lookups"), purposeNames(storage.recordedConsents))
        sync.run(emptySet(), texts)
        assertEquals(2, bodies.size, "recorded once")
    }

    @Test
    fun lookupsAcceptedBeforeThePairingDisclosureIsStillRecordedUnderItsOwnWords() {
        storage.acceptedDisclosureVersion = null
        storage.acceptedLookupsVersion = ConsentLedger.VERSION
        sync.run(emptySet(), texts)
        assertEquals(listOf("lookups" to true), purposesSent(0))
    }

    @Test
    fun anUnpairedDeviceSendsNothing() {
        storage.clear()
        assertEquals(ConsentSync.Outcome.SKIPPED, sync.run(emptySet(), texts))
        assertTrue(bodies.isEmpty())
    }
}
