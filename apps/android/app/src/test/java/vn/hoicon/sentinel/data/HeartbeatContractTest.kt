package vn.hoicon.sentinel.data

import java.io.File
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Test
import vn.hoicon.sentinel.data.remote.HeartbeatStatus
import vn.hoicon.sentinel.data.remote.PairingApiClient
import vn.hoicon.sentinel.domain.JsonSchemaLite
import vn.hoicon.sentinel.sensing.SensorPermission
import kotlin.test.assertEquals
import kotlin.test.assertTrue

/**
 * Spec 029 FR-001: the body the app sends to `POST /v1/heartbeat` is exactly `docs/schemas/heartbeat.v1.json`, and the
 * `android_*` entries of `fixtures/heartbeat.v1.valid.json` are that body, so the server's contract test reads what the
 * phone really sends. Change the body or the schema and one of these fails first.
 */
class HeartbeatContractTest {
    private val dir = File(checkNotNull(System.getProperty("hoicon.schemasDir")))
    private val schema = JSONObject(File(dir, "heartbeat.v1.json").readText())

    private fun fixtures(name: String): List<JSONObject> {
        val array = JSONArray(File(dir, "fixtures/$name").readText())
        return List(array.length()) { array.getJSONObject(it) }
    }

    /** The fixture without its `_`-prefixed notes. */
    private fun JSONObject.document() = JSONObject().also { copy -> keys().forEach { if (!it.startsWith("_")) copy.put(it, get(it)) } }

    private fun named(name: String): JSONObject =
        checkNotNull(fixtures("heartbeat.v1.valid.json").firstOrNull { it.optString("_name") == name }) { "fixture $name" }.document()

    /** Same permission map as `HeartbeatWorker`: every [SensorPermission], lower-cased, with only some granted. */
    private fun permissions(granted: Set<SensorPermission>) = SensorPermission.entries.associate { it.name.lowercase() to (it in granted) }

    private fun assertSame(expected: JSONObject, actual: JSONObject) = assertEquals(sorted(expected).toString(), sorted(actual).toString())

    @Test
    fun theBodyOfAFullStatusIsTheAndroidFullFixture() {
        val body = PairingApiClient.heartbeatBody(
            HeartbeatStatus(
                appVersion = "0.3.0", rulesVersion = "0.2.0", threatListVersion = "3f9a1c07d25e8b46",
                permissionState = permissions(setOf(SensorPermission.CALL_SCREENING_ROLE, SensorPermission.DISPLAY_OVER_APPS, SensorPermission.USAGE_ACCESS)),
            ),
        )
        assertSame(named("android_full"), body)
        assertValid(body)
    }

    @Test
    fun theBodyWithoutAThreatListIsTheAndroidMinimalFixture() {
        val body = PairingApiClient.heartbeatBody(
            HeartbeatStatus(appVersion = "0.3.0-debug", rulesVersion = "0.2.0", threatListVersion = null, permissionState = permissions(emptySet())),
        )
        assertTrue(!body.has("threat_list_version"))
        assertSame(named("android_minimal"), body)
        assertValid(body)
    }

    @Test
    fun everyPermissionTheAppReportsHasAContractName() {
        assertTrue(SensorPermission.entries.size <= 16, "heartbeat.v1 allows at most 16 permissions")
        assertValid(PairingApiClient.heartbeatBody(HeartbeatStatus("0.3.0", "0.2.0", null, permissions(SensorPermission.entries.toSet()))))
    }

    @Test
    fun aVersionLongerThanTheContractIsCutToIt() {
        val body = PairingApiClient.heartbeatBody(HeartbeatStatus("0.3.0".padEnd(40, '0'), "0.2.0", "a".repeat(40), emptyMap()))
        assertEquals(32, body.getString("app_version").length)
        assertEquals(32, body.getString("threat_list_version").length)
    }

    @Test
    fun everyValidFixtureSatisfiesTheSchema() {
        val valid = fixtures("heartbeat.v1.valid.json")
        assertTrue(valid.isNotEmpty())
        for (fixture in valid) assertValid(fixture.document(), fixture.optString("_name"))
    }

    @Test
    fun everyInvalidFixtureIsRefused() {
        val invalid = fixtures("heartbeat.v1.invalid.json")
        assertTrue(invalid.isNotEmpty())
        for (fixture in invalid) {
            assertTrue(JsonSchemaLite.validate(schema, fixture.document()).isNotEmpty(), "accepted: ${fixture.optString("_why")}")
        }
    }

    private fun assertValid(body: JSONObject, label: String = "") {
        val errors = JsonSchemaLite.validate(schema, body)
        assertTrue(errors.isEmpty(), "$label $errors in $body")
    }

    /** JSONObject keeps no key order: compare through a sorted copy. */
    private fun sorted(json: JSONObject): JSONObject = JSONObject().also { out ->
        json.keys().asSequence().sorted().forEach { key ->
            val value = json.get(key)
            out.put(key, if (value is JSONObject) sorted(value) else value)
        }
    }
}
