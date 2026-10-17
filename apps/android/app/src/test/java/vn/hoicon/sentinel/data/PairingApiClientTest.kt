package vn.hoicon.sentinel.data

import com.sun.net.httpserver.HttpServer
import java.io.File
import java.net.InetSocketAddress
import org.junit.After
import org.junit.Test
import kotlin.test.assertContentEquals
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertIs
import kotlin.test.assertNull
import kotlin.test.assertTrue
import org.json.JSONArray
import org.json.JSONObject
import vn.hoicon.sentinel.data.consent.ConsentItem
import vn.hoicon.sentinel.data.remote.ConsentResult
import vn.hoicon.sentinel.data.remote.EventsResult
import vn.hoicon.sentinel.data.remote.HeartbeatResult
import vn.hoicon.sentinel.data.remote.HeartbeatStatus
import vn.hoicon.sentinel.data.remote.PairResult
import vn.hoicon.sentinel.data.remote.PairingApiClient

/** Talks to a real local HTTP server; request/response shapes are checked against docs/schemas (spec 020 FR-012). */
class PairingApiClientTest {
    private class Seen(val method: String, val path: String, val auth: String?, val type: String?, val body: String)

    private var server: HttpServer? = null
    private var seen: Seen? = null

    @After
    fun stop() = server?.stop(0) ?: Unit

    private fun serve(status: Int, reply: String, headers: Map<String, String> = emptyMap()): PairingApiClient {
        val s = HttpServer.create(InetSocketAddress("127.0.0.1", 0), 0)
        s.createContext("/") { ex ->
            seen = Seen(
                ex.requestMethod,
                ex.requestURI.path,
                ex.requestHeaders.getFirst("Authorization"),
                ex.requestHeaders.getFirst("Content-Type"),
                ex.requestBody.readBytes().toString(Charsets.UTF_8),
            )
            headers.forEach { (k, v) -> ex.responseHeaders.add(k, v) }
            val bytes = reply.toByteArray()
            ex.sendResponseHeaders(status, if (bytes.isEmpty()) -1 else bytes.size.toLong())
            if (bytes.isNotEmpty()) ex.responseBody.use { it.write(bytes) }
            ex.close()
        }
        s.start()
        server = s
        return PairingApiClient("http://127.0.0.1:${s.address.port}", timeoutMs = 2_000)
    }

    private fun schema(name: String) = JSONObject(File(System.getProperty("hoicon.schemasDir"), name).readText())

    private fun fixture(name: String): JSONArray = JSONArray(File(System.getProperty("hoicon.schemasDir"), "fixtures/$name").readText())

    private fun validResponse(): String = fixture("pair_response.v1.valid.json").getJSONObject(0).also { it.remove("_name") }.toString()

    private fun pair(client: PairingApiClient, code: String = "123456") =
        client.pair(code, appVersion = "0.1.0-debug", rulesVersion = "0.1.0-s1", deviceLabel = "Pixel 8")

    @Test
    fun pairSendsAContractShapedRequestAndReturnsTheSession() {
        val client = serve(200, validResponse())
        val result = assertIs<PairResult.Paired>(pair(client))
        assertEquals("Gia đình Bác Ba", result.session.familyName)
        assertEquals("01928374-abcd-7123-89ef-0123456789ab", result.session.deviceId)

        val request = checkNotNull(seen)
        assertEquals("POST", request.method)
        assertEquals("/v1/pair", request.path)
        assertNull(request.auth)
        assertTrue(checkNotNull(request.type).startsWith("application/json"))
        val body = JSONObject(request.body)
        val spec = schema("pair_request.v1.json")
        val required = spec.getJSONArray("required").let { a -> List(a.length()) { a.getString(it) } }
        val allowed = spec.getJSONObject("properties").keys().asSequence().toSet()
        assertTrue(body.keys().asSequence().toSet().containsAll(required), "missing required fields")
        assertTrue(allowed.containsAll(body.keys().asSequence().toSet()), "fields outside the schema")
        assertEquals("android", body.getString("platform"))
        assertEquals("123456", body.getString("code"))
    }

    @Test
    fun malformedCodesNeverReachTheServer() {
        val client = serve(200, validResponse())
        for (code in listOf("", "12345", "1234567", "12345a", "١٢٣٤٥٦", " 123456")) {
            assertEquals(PairResult.InvalidCode, pair(client, code), "code '$code'")
        }
        assertNull(seen)
    }

    @Test
    fun wrongOrExpiredCodeIsInvalidCode() {
        for (status in listOf(400, 404, 409, 410, 422)) {
            val client = serve(status, """{"detail":"Mã ghép đôi không tồn tại hoặc đã hết hạn"}""")
            assertEquals(PairResult.InvalidCode, pair(client), "HTTP $status")
            server?.stop(0)
        }
    }

    @Test
    fun tooManyAttemptsIsRateLimited() {
        assertEquals(PairResult.RateLimited, pair(serve(429, "{}")))
    }

    @Test
    fun serverFailureAndGarbageAreServerError() {
        assertEquals(PairResult.ServerError, pair(serve(500, "oops")))
        server?.stop(0)
        assertEquals(PairResult.ServerError, pair(serve(200, "not json")))
        server?.stop(0)
        assertEquals(PairResult.ServerError, pair(serve(200, "")))
    }

    @Test
    fun aResponseBreakingTheContractIsRejected() {
        val invalid = fixture("pair_response.v1.invalid.json")
        for (i in 0 until invalid.length()) {
            val bad = invalid.getJSONObject(i).also { it.remove("_why") }
            server?.stop(0)
            assertEquals(PairResult.ServerError, pair(serve(200, bad.toString())), "fixture #$i")
        }
        server?.stop(0)
        val noBearer = JSONObject(validResponse()).put("token_type", "mac").toString()
        assertEquals(PairResult.ServerError, pair(serve(200, noBearer)))
        server?.stop(0)
        val notUuid = JSONObject(validResponse()).put("device_id", "not-a-uuid").toString()
        assertEquals(PairResult.ServerError, pair(serve(200, notUuid)))
        server?.stop(0)
        val noToken = JSONObject(validResponse()).put("access_token", " ").toString()
        assertEquals(PairResult.ServerError, pair(serve(200, noToken)))
        server?.stop(0)
        val nullName = JSONObject(validResponse()).put("family_name", JSONObject.NULL).toString()
        assertEquals(PairResult.ServerError, pair(serve(200, nullName)))
    }

    @Test
    fun unreachableServerIsNetworkError() {
        val closed = HttpServer.create(InetSocketAddress("127.0.0.1", 0), 0).also { it.start(); it.stop(0) }
        val client = PairingApiClient("http://127.0.0.1:${closed.address.port}", timeoutMs = 1_000)
        assertEquals(PairResult.NetworkError, pair(client))
    }

    @Test
    fun redirectsAreNotFollowed() {
        val client = serve(302, "", mapOf("Location" to "http://127.0.0.1:9/steal"))
        assertEquals(PairResult.ServerError, pair(client))
    }

    private val item = ConsentItem("call_screening", true, "2026.10-v1", "a".repeat(64))

    @Test
    fun consentsAreSentWithTheDeviceTokenAndMatchTheSchema() {
        val client = serve(200, """{"status":"recorded","count":2,"recorded_at":"2026-10-15T10:00:00Z"}""")
        val items = listOf(item, item.copy(purpose = "core_protection", granted = false))
        assertEquals(ConsentResult.Recorded(2), client.recordConsents("device-jwt", items))

        val request = checkNotNull(seen)
        assertEquals("/v1/consents", request.path)
        assertEquals("Bearer device-jwt", request.auth)
        val sent = JSONObject(request.body).getJSONArray("items")
        assertEquals(2, sent.length())
        val spec = schema("consent_record.v1.json").getJSONObject("properties").getJSONObject("items").getJSONObject("items")
        val required = spec.getJSONArray("required").let { a -> List(a.length()) { a.getString(it) } }
        val purposes = spec.getJSONObject("properties").getJSONObject("purpose").getJSONArray("enum")
        for (i in 0 until sent.length()) {
            val row = sent.getJSONObject(i)
            assertContentEquals(required.sorted(), row.keys().asSequence().toList().sorted())
            assertTrue((0 until purposes.length()).any { purposes.getString(it) == row.getString("purpose") })
            assertTrue(Regex("^[0-9a-f]{64}$").matches(row.getString("text_sha256")))
        }
        assertFalse(sent.getJSONObject(1).getBoolean("granted"))
    }

    @Test
    fun emptyConsentBatchSendsNothing() {
        val client = serve(200, "{}")
        assertEquals(ConsentResult.Recorded(0), client.recordConsents("t", emptyList()))
        assertNull(seen)
    }

    @Test
    fun rejectedTokenIsUnauthorized() {
        assertEquals(ConsentResult.Unauthorized, serve(401, "{}").recordConsents("t", listOf(item)))
    }

    @Test
    fun consentServerErrorsAreServerError() {
        assertEquals(ConsentResult.ServerError, serve(500, "{}").recordConsents("t", listOf(item)))
    }

    // Spec 029 FR-001: a 403 `consent_withdrawn` is "consent needed again", never a refused token.

    private val heartbeat = HeartbeatStatus("0.3.0", "0.2.0", null, mapOf("usage_access" to true))
    private val oneEvent = listOf(JSONObject().put("id", "01928f3a-7b2c-7d4e-8f10-2a3b4c5d6e7f"))
    private val withdrawnBodies = listOf(
        """{"detail":"consent_withdrawn"}""",
        """{"detail":{"code":"consent_withdrawn","message":"Cần đồng ý lại"}}""",
        """consent_withdrawn""",
    )

    @Test
    fun aWithdrawnConsentOnHeartbeatIsNotARefusedToken() {
        for (reply in withdrawnBodies) {
            server?.stop(0)
            assertEquals(HeartbeatResult.ConsentWithdrawn, serve(403, reply).sendHeartbeat("t", heartbeat), reply)
        }
    }

    @Test
    fun aWithdrawnConsentOnEventsIsNotARefusedToken() {
        for (reply in withdrawnBodies) {
            server?.stop(0)
            assertEquals(EventsResult.ConsentWithdrawn, serve(403, reply).sendEvents("t", oneEvent), reply)
        }
    }

    @Test
    fun anyOther403StaysARefusedToken() {
        for (reply in listOf("", "{}", """{"detail":"forbidden"}""", """{"detail":"consent_required"}""")) {
            server?.stop(0)
            assertEquals(HeartbeatResult.Unauthorized, serve(403, reply).sendHeartbeat("t", heartbeat), "heartbeat: $reply")
            server?.stop(0)
            assertEquals(EventsResult.Unauthorized, serve(403, reply).sendEvents("t", oneEvent), "events: $reply")
        }
    }

    @Test
    fun theConsentCodeOnlyCountsOnA403() {
        for (status in listOf(401, 422, 500)) {
            server?.stop(0)
            val reply = """{"detail":"consent_withdrawn"}"""
            val beat = serve(status, reply).sendHeartbeat("t", heartbeat)
            assertTrue(beat != HeartbeatResult.ConsentWithdrawn, "heartbeat HTTP $status")
            server?.stop(0)
            val events = serve(status, reply).sendEvents("t", oneEvent)
            assertTrue(events != EventsResult.ConsentWithdrawn, "events HTTP $status")
        }
    }
}
