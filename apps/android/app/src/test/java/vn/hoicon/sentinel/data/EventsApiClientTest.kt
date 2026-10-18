package vn.hoicon.sentinel.data

import com.sun.net.httpserver.HttpServer
import java.net.InetSocketAddress
import org.json.JSONObject
import org.junit.After
import org.junit.Test
import vn.hoicon.sentinel.data.remote.EventsResult
import vn.hoicon.sentinel.data.remote.HeartbeatResult
import vn.hoicon.sentinel.data.remote.HeartbeatStatus
import vn.hoicon.sentinel.data.remote.PairingApiClient
import vn.hoicon.sentinel.outbox.sampleEvent
import vn.hoicon.sentinel.outbox.sequentialFactory
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNull
import kotlin.test.assertTrue

/** `POST /v1/events` and `POST /v1/heartbeat` against a real local HTTP server (Spec 022 FR-002, FR-008). */
class EventsApiClientTest {
    private class Seen(val path: String, val auth: String?, val body: String)

    private var server: HttpServer? = null
    private var seen: Seen? = null

    @After
    fun stop() = server?.stop(0) ?: Unit

    private fun serve(status: Int, reply: String = "{}"): PairingApiClient {
        val s = HttpServer.create(InetSocketAddress("127.0.0.1", 0), 0)
        s.createContext("/") { ex ->
            seen = Seen(ex.requestURI.path, ex.requestHeaders.getFirst("Authorization"), ex.requestBody.readBytes().toString(Charsets.UTF_8))
            val bytes = reply.toByteArray()
            ex.sendResponseHeaders(status, if (status == 204) -1 else bytes.size.toLong())
            ex.responseBody.use { it.write(bytes) }
            ex.close()
        }
        s.start()
        server = s
        return PairingApiClient("http://127.0.0.1:${s.address.port}", timeoutMs = 2_000)
    }

    private val factory = sequentialFactory()
    private val events get() = List(3) { sampleEvent(factory).toJson() }

    @Test
    fun eventsGoToTheEventsEndpointWithTheDeviceToken() {
        val batch = events
        assertEquals(EventsResult.Accepted, serve(200, """{"accepted":3,"duplicates":0}""").sendEvents("device-jwt", batch))
        val request = checkNotNull(seen)
        assertEquals("/v1/events", request.path)
        assertEquals("Bearer device-jwt", request.auth)
        val sent = JSONObject(request.body).getJSONArray("events")
        assertEquals(batch.map { it.getString("id") }, List(sent.length()) { sent.getJSONObject(it).getString("id") })
    }

    @Test
    fun anEmptyBatchSendsNothing() {
        assertEquals(EventsResult.Accepted, serve(200).sendEvents("t", emptyList()))
        assertNull(seen)
    }

    @Test
    fun moreThanFiftyEventsIsAProgrammingError() {
        val client = serve(200)
        assertFailsWith<IllegalArgumentException> { client.sendEvents("t", List(51) { events.first() }) }
    }

    @Test
    fun statusCodesMapToOutcomes() {
        val cases = mapOf(
            200 to EventsResult.Accepted, 201 to EventsResult.Accepted, 202 to EventsResult.Accepted,
            400 to EventsResult.Rejected, 413 to EventsResult.Rejected, 422 to EventsResult.Rejected,
            401 to EventsResult.Unauthorized, 403 to EventsResult.Unauthorized,
            404 to EventsResult.ServerError, 429 to EventsResult.ServerError,
            500 to EventsResult.ServerError, 503 to EventsResult.ServerError,
        )
        for ((status, expected) in cases) {
            server?.stop(0)
            assertEquals(expected, serve(status).sendEvents("t", events), "HTTP $status")
        }
    }

    @Test
    fun unreachableServerIsNetworkError() {
        val closed = HttpServer.create(InetSocketAddress("127.0.0.1", 0), 0).also { it.start(); it.stop(0) }
        val client = PairingApiClient("http://127.0.0.1:${closed.address.port}", timeoutMs = 1_000)
        assertEquals(EventsResult.NetworkError, client.sendEvents("t", events))
        assertEquals(HeartbeatResult.NetworkError, client.sendHeartbeat("t", status))
    }

    private val status = HeartbeatStatus(
        appVersion = "0.1.0", rulesVersion = "0.2.0", threatListVersion = null,
        permissionState = mapOf("usage_access" to true, "notifications" to false),
    )

    @Test
    fun heartbeatSendsVersionsAndPermissionState() {
        assertEquals(HeartbeatResult.Ok, serve(200).sendHeartbeat("device-jwt", status.copy(threatListVersion = "2026.10.16")))
        val request = checkNotNull(seen)
        assertEquals("/v1/heartbeat", request.path)
        assertEquals("Bearer device-jwt", request.auth)
        val body = JSONObject(request.body)
        assertEquals("0.1.0", body.getString("app_version"))
        assertEquals("0.2.0", body.getString("rules_version"))
        assertEquals("2026.10.16", body.getString("threat_list_version"))
        assertTrue(body.getJSONObject("permission_state").getBoolean("usage_access"))
        assertEquals(false, body.getJSONObject("permission_state").getBoolean("notifications"))
    }

    @Test
    fun heartbeatOmitsAnUnknownThreatListVersion() {
        serve(200).sendHeartbeat("t", status)
        assertTrue(!JSONObject(checkNotNull(seen).body).has("threat_list_version"))
    }

    @Test
    fun heartbeatStatusCodesMapToOutcomes() {
        val cases = mapOf(
            204 to HeartbeatResult.Ok, 422 to HeartbeatResult.Rejected, 401 to HeartbeatResult.Unauthorized,
            404 to HeartbeatResult.ServerError, 500 to HeartbeatResult.ServerError,
        )
        for ((code, expected) in cases) {
            server?.stop(0)
            assertEquals(expected, serve(code).sendHeartbeat("t", status), "HTTP $code")
        }
    }

    // Spec 024 T013: `incident_id` / `incident_opened` of events_result.v1.json.

    @Test
    fun aReplyWithAnIncidentCarriesItOn() {
        val reply = """{"accepted":3,"duplicates":0,"incident_id":"0192aaaa-0000-7000-8000-000000000001","incident_opened":true}"""
        assertEquals(
            EventsResult.AcceptedWithIncident("0192aaaa-0000-7000-8000-000000000001", opened = true),
            serve(200, reply).sendEvents("t", events),
        )
        server?.stop(0)
        val joined = """{"accepted":1,"duplicates":0,"incident_id":"0192aaaa-0000-7000-8000-000000000001","incident_opened":false}"""
        assertEquals(
            EventsResult.AcceptedWithIncident("0192aaaa-0000-7000-8000-000000000001", opened = false),
            serve(200, joined).sendEvents("t", events),
        )
    }

    @Test
    fun noIncidentOrAnUnreadableOneIsStillJustAccepted() {
        val replies = listOf(
            """{"accepted":3,"duplicates":0,"incident_id":null,"incident_opened":false}""",
            """{"accepted":3,"duplicates":0}""",
            """{"accepted":3,"incident_id":"not-a-uuid","incident_opened":true}""",
            "not json",
            "",
        )
        for (reply in replies) {
            server?.stop(0)
            assertEquals(EventsResult.Accepted, serve(200, reply).sendEvents("t", events), reply)
        }
    }
}
