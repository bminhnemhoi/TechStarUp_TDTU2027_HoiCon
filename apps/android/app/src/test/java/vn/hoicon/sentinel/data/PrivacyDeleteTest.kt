package vn.hoicon.sentinel.data

import com.sun.net.httpserver.HttpServer
import java.net.InetSocketAddress
import java.time.OffsetDateTime
import org.json.JSONObject
import org.junit.After
import org.junit.Test
import vn.hoicon.sentinel.data.local.DeviceSession
import vn.hoicon.sentinel.data.local.TokenStorage
import vn.hoicon.sentinel.data.remote.DataRequestApiClient
import vn.hoicon.sentinel.data.remote.PrivacyDelete
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertIs
import kotlin.test.assertNull
import kotlin.test.assertTrue

/** Spec 038 T004 (FR-003/FR-006): the delete request has a 24-hour window that can be cancelled; nothing local is removed until the server has purged. */
class PrivacyDeleteTest {
    private var postStatus = 202
    private var postBody = """{"request_id":"6f1d3a52-7c1e-4d0a-9d52-0a1b2c3d4e5f","status":"pending","requested_at":"2026-10-25T09:00:00+07:00","execute_after":"2026-10-26T09:00:00+07:00","deadline_hours":72}"""
    private var retryAfter: String? = null
    private var deleteStatus = 200
    private val seen = mutableListOf<String>()
    private val bodies = mutableListOf<JSONObject>()
    private val server = HttpServer.create(InetSocketAddress("127.0.0.1", 0), 0).also { s ->
        s.createContext("/v1/data-requests") { ex ->
            seen += "${ex.requestMethod} ${ex.requestURI.path} auth=${ex.requestHeaders.getFirst("Authorization")}"
            val raw = ex.requestBody.readBytes().toString(Charsets.UTF_8)
            if (ex.requestMethod == "POST") bodies += JSONObject(raw)
            val status = if (ex.requestMethod == "POST") postStatus else deleteStatus
            retryAfter?.let { ex.responseHeaders.add("Retry-After", it) }
            val out = if (status in 200..202) postBody.toByteArray() else ByteArray(0)
            ex.sendResponseHeaders(status, if (out.isEmpty()) -1 else out.size.toLong())
            if (out.isNotEmpty()) ex.responseBody.write(out)
            ex.close()
        }
        s.start()
    }
    private val storage = TokenStorage(FakePrefs()).also { it.save(DeviceSession("d", "f", "m", "Nhà", "access", "refresh")) }
    private fun client(port: Int = server.address.port) = DataRequestApiClient("http://127.0.0.1:$port", timeoutMs = 1_500)
    private val delete = PrivacyDelete(storage, client())

    @After
    fun stop() = server.stop(0)

    private fun ms(iso: String) = OffsetDateTime.parse(iso).toInstant().toEpochMilli()

    @Test
    fun theRequestCarriesTheConfirmationAndKeepsTheLocalDataUntilTheServerPurges() {
        val outcome = delete.request()
        assertIs<PrivacyDelete.Outcome.Sent>(outcome)
        assertEquals(ms("2026-10-26T09:00:00+07:00"), outcome.executeAfterMs)
        assertEquals("POST /v1/data-requests auth=Bearer access", seen.single())
        assertEquals(setOf("kind", "confirmed"), bodies.single().keys().asSequence().toSet())
        assertEquals(true, bodies.single().getBoolean("confirmed"))
        assertTrue(storage.load() != null, "nothing is removed from the phone when the request is sent")
        assertEquals("6f1d3a52-7c1e-4d0a-9d52-0a1b2c3d4e5f", delete.pending()?.requestId)
    }

    @Test
    fun anAlreadyPendingRequestIsTheSameRequest200() {
        postStatus = 200
        assertIs<PrivacyDelete.Outcome.Sent>(delete.request())
        assertEquals(1, storage.let { delete.pending() }?.let { 1 })
    }

    @Test
    fun anOlderServerWithoutExecuteAfterMeansRequestedPlus24Hours() {
        postBody = """{"request_id":"6f1d3a52-7c1e-4d0a-9d52-0a1b2c3d4e5f","status":"pending","requested_at":"2026-10-25T09:00:00+07:00","deadline_hours":72}"""
        val outcome = delete.request()
        assertIs<PrivacyDelete.Outcome.Sent>(outcome)
        assertEquals(ms("2026-10-26T09:00:00+07:00"), outcome.executeAfterMs)
    }

    @Test
    fun offlineSendsNothingAndKeepsNothingPending() {
        val offline = PrivacyDelete(storage, client(port = 1))
        assertEquals(PrivacyDelete.Outcome.Offline, offline.request())
        assertNull(offline.pending())
        assertTrue(storage.load() != null)
    }

    @Test
    fun tooManyRequestsReportsHowLongToWait() {
        postStatus = 429
        retryAfter = "3600"
        assertEquals(PrivacyDelete.Outcome.Busy(3600), delete.request())
        assertNull(delete.pending())
    }

    @Test
    fun aRefusedTokenIsNotTreatedAsSent() {
        postStatus = 401
        assertEquals(PrivacyDelete.Outcome.Refused, delete.request())
        assertNull(delete.pending())
    }

    @Test
    fun cancellingClearsThePendingRequest() {
        delete.request()
        assertEquals(PrivacyDelete.Outcome.Cancelled, delete.cancel())
        assertNull(delete.pending())
        assertEquals("DELETE /v1/data-requests/6f1d3a52-7c1e-4d0a-9d52-0a1b2c3d4e5f auth=Bearer access", seen.last())
    }

    @Test
    fun cancellingAfterThePurgeStartedIsReportedNotHidden() {
        delete.request()
        deleteStatus = 409
        assertEquals(PrivacyDelete.Outcome.TooLate, delete.cancel())
    }

    @Test
    fun aServerWithoutTheCancelRouteKeepsTheRequestPending() {
        delete.request()
        deleteStatus = 404
        assertEquals(PrivacyDelete.Outcome.Unavailable, delete.cancel())
        assertTrue(delete.pending() != null)
    }

    @Test
    fun localDataGoesOnlyWhenTheTokenIsRefusedAfterTheWaitingTime() {
        delete.request()
        val after = ms("2026-10-26T09:00:00+07:00")
        assertFalse(delete.serverHasPurged(nowMs = after + 1), "token still fine: the server has not purged")
        storage.needsRepair = true
        assertFalse(delete.serverHasPurged(nowMs = after - 1), "a refused token before the waiting time is a normal repair, not a deletion")
        assertTrue(delete.serverHasPurged(nowMs = after + 1))
    }

    @Test
    fun withoutAPendingRequestARefusedTokenIsNeverADeletion() {
        storage.needsRepair = true
        assertFalse(delete.serverHasPurged(nowMs = Long.MAX_VALUE))
    }
}
