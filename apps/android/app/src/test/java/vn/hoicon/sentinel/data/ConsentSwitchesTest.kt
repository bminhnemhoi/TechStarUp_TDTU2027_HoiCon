package vn.hoicon.sentinel.data

import com.sun.net.httpserver.HttpServer
import java.net.InetSocketAddress
import org.json.JSONObject
import org.junit.After
import org.junit.Test
import vn.hoicon.sentinel.data.consent.ConsentLedger
import vn.hoicon.sentinel.data.consent.ConsentSwitches
import vn.hoicon.sentinel.data.consent.ConsentSync
import vn.hoicon.sentinel.data.local.DeviceSession
import vn.hoicon.sentinel.data.local.TokenStorage
import vn.hoicon.sentinel.data.remote.PairingApiClient
import vn.hoicon.sentinel.sensing.SensorPermission
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

/** Spec 038 T003 (FR-001/FR-002): the purposes that are not tied to a system permission can be switched off and on from E12; the ledger only grows. */
class ConsentSwitchesTest {
    private val bodies = mutableListOf<JSONObject>()
    private val server = HttpServer.create(InetSocketAddress("127.0.0.1", 0), 0).also { s ->
        s.createContext("/v1/consents") { ex ->
            bodies += JSONObject(ex.requestBody.readBytes().toString(Charsets.UTF_8))
            ex.sendResponseHeaders(200, -1)
            ex.close()
        }
        s.start()
    }
    private val storage = TokenStorage(FakePrefs()).also {
        it.save(DeviceSession("d", "f", "m", "Nhà", "access", "refresh"))
        it.acceptedDisclosureVersion = ConsentLedger.DISCLOSURE_VERSION
        it.acceptedLookupsVersion = ConsentLedger.VERSION
        it.acceptedDrillsVersion = ConsentLedger.VERSION
    }
    private val sync = ConsentSync(storage, PairingApiClient("http://127.0.0.1:${server.address.port}", timeoutMs = 2_000))
    private val switches = ConsentSwitches(storage)
    private val texts = mapOf(
        "core_protection" to "core", "guardian_alerts" to "guardian", "call_screening" to "call", "usage_monitoring" to "usage",
        "overlay_pause" to "overlay", "lookups" to "lookups", "drills" to "drills",
    )
    private val granted = setOf(SensorPermission.CALL_SCREENING_ROLE)

    @After
    fun stop() = server.stop(0)

    private fun sent(call: Int) = bodies[call].getJSONArray("items").let { a -> List(a.length()) { a.getJSONObject(it).getString("purpose") to a.getJSONObject(it).getBoolean("granted") } }

    @Test
    fun onlyThePurposesWithoutASystemPermissionCanBeSwitched() {
        assertEquals(listOf("guardian_alerts", "lookups", "drills"), ConsentSwitches.SWITCHABLE)
        assertFalse(ConsentLedger.CORE_PROTECTION in ConsentSwitches.SWITCHABLE, "core protection has no switch of its own: stopping it is the delete flow")
        assertTrue(ConsentSwitches.SWITCHABLE.all { p -> SensorPermission.entries.none { ConsentLedger.purposeOf(it) == p } })
        assertTrue(ConsentSwitches.SWITCHABLE.all(switches::isOn))
    }

    @Test
    fun switchingOffLookupsOrDrillsAppendsAFalseRowAndNothingElse() {
        sync.run(granted, texts)
        switches.turnOff(ConsentLedger.LOOKUPS)
        switches.turnOff(ConsentLedger.DRILLS)
        assertFalse(switches.isOn(ConsentLedger.LOOKUPS))
        sync.run(granted, texts)
        assertEquals(listOf("drills" to false, "lookups" to false), sent(1))
        assertEquals(setOf("core_protection", "guardian_alerts", "call_screening"), storage.recordedConsents.map { it.substringBefore('|') }.toSet())
    }

    @Test
    fun switchingOffGuardianAlertsKeepsCoreProtectionAndStopsSharingAtOnce() {
        sync.run(granted, texts)
        switches.turnOff(ConsentLedger.GUARDIAN_ALERTS)
        assertFalse(switches.isOn(ConsentLedger.GUARDIAN_ALERTS))
        assertTrue(storage.guardianAlertsOff, "the local flag stops sending before the ledger row reaches the server")
        sync.run(granted, texts)
        assertEquals(listOf("guardian_alerts" to false), sent(1))
        assertEquals(ConsentLedger.DISCLOSURE_VERSION, storage.acceptedDisclosureVersion, "E3 stays accepted")
    }

    @Test
    fun switchingGuardianAlertsBackOnAppendsATrueRow() {
        sync.run(granted, texts)
        switches.turnOff(ConsentLedger.GUARDIAN_ALERTS)
        sync.run(granted, texts)
        switches.turnOn(ConsentLedger.GUARDIAN_ALERTS)
        sync.run(granted, texts)
        assertEquals(listOf("guardian_alerts" to true), sent(2))
        assertTrue(switches.isOn(ConsentLedger.GUARDIAN_ALERTS))
    }

    @Test
    fun withoutTheDisclosureGuardianAlertsAreNotOn() {
        storage.acceptedDisclosureVersion = null
        assertFalse(switches.isOn(ConsentLedger.GUARDIAN_ALERTS))
    }
}
