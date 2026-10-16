package vn.hoicon.sentinel.data

import com.sun.net.httpserver.HttpServer
import java.net.InetSocketAddress
import org.json.JSONObject
import org.junit.After
import org.junit.Test
import vn.hoicon.rules.PhoneHasher
import vn.hoicon.sentinel.data.remote.LookupApiClient
import vn.hoicon.sentinel.data.remote.LookupKind
import vn.hoicon.sentinel.data.remote.LookupResult
import vn.hoicon.sentinel.data.remote.LookupVerdict
import vn.hoicon.sentinel.data.remote.LookupVia
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertIs
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * Spec 026 T023: `POST /v1/lookups` against a local server. Bodies are checked against the shape of
 * lookup_request.v1 / lookup_result.v1 as written in plan §6 (the schema files themselves are phase 0 on the main
 * checkout and were not merged yet when this was written).
 */
class LookupApiClientTest {
    private class Seen(val method: String, val path: String, val auth: String?, val body: String)

    private var server: HttpServer? = null
    private var seen: Seen? = null
    private var calls = 0

    @After
    fun stop() = server?.stop(0) ?: Unit

    private fun serve(status: Int, reply: String = "", headers: Map<String, String> = emptyMap()): LookupApiClient {
        val s = HttpServer.create(InetSocketAddress("127.0.0.1", 0), 0)
        s.createContext("/") { ex ->
            calls++
            seen = Seen(ex.requestMethod, ex.requestURI.path, ex.requestHeaders.getFirst("Authorization"), ex.requestBody.readBytes().toString(Charsets.UTF_8))
            val bytes = reply.toByteArray()
            headers.forEach { (k, v) -> ex.responseHeaders.add(k, v) }
            ex.sendResponseHeaders(status, if (bytes.isEmpty()) -1 else bytes.size.toLong())
            if (bytes.isNotEmpty()) ex.responseBody.use { it.write(bytes) }
            ex.close()
        }
        s.start(); server = s
        return LookupApiClient("http://127.0.0.1:${s.address.port}", timeoutMs = 2_000)
    }

    // Fictional number of data/fixtures/phones.json; it may only be hashed, never sent.
    private val fictionalNumber = "0900000002"
    private val phone = assertNotNull(PhoneHasher.hash(fictionalNumber))
    private val verificationId = "01851bd2-0000-7000-8000-0000000000aa"
    private val disclaimer = "Đây là trợ lý AI HỏiCon. Kết quả chỉ để tham khảo."

    private fun result(kind: String = "phone", verdict: String = "dangerous", extra: String = "", disclaimer: String = this.disclaimer, confidence: String = "0.9") =
        """{"verification_id":"$verificationId","kind":"$kind","verdict":"$verdict","confidence":$confidence,
            "reasons":[{"code":"listed_high","text":"Số này nằm trong danh sách cảnh báo."}],
            "sources":[{"name":"Cục An ninh mạng","type":"threat_list","list_version":"0123456789abcdef"},{"name":"Quy tắc HỏiCon: no_tls","type":"heuristic"}],
            "disclaimer":"$disclaimer","is_demo":false$extra}"""

    @Test
    fun aPhoneIsSentAsHashAndLast3OnlyNeverTheNumber() {
        val client = serve(200, result(extra = ""","incident_level":"critical""""))
        val out = client.lookupPhone("tok", phone, LookupVia.TYPED, incidentId = "01851bd2-0000-7000-8000-000000000001")
        val body = JSONObject(seen!!.body)
        assertEquals(setOf("kind", "via", "h1", "last3", "incident_id"), body.keys().asSequence().toSet())
        assertEquals("phone", body.getString("kind")); assertEquals("typed", body.getString("via"))
        assertEquals(phone.h1, body.getString("h1")); assertEquals("002", body.getString("last3"))
        assertTrue(Regex("^[0-9a-f]{64}$").matches(body.getString("h1")))
        assertFalse(fictionalNumber in seen!!.body, "raw number in request"); assertFalse("84900000002" in seen!!.body)
        assertEquals("POST", seen!!.method); assertEquals("/v1/lookups", seen!!.path); assertEquals("Bearer tok", seen!!.auth)
        assertIs<LookupResult.Done>(out)
        assertEquals("critical", out.answer.incidentLevel)
        assertEquals(LookupVerdict.DANGEROUS, out.answer.verdict)
        assertEquals(listOf("Cục An ninh mạng", "Quy tắc HỏiCon: no_tls"), out.answer.sources.map { it.name })
        assertEquals("0123456789abcdef", out.answer.sources[0].listVersion)
        assertNull(out.answer.sources[1].listVersion)
        assertEquals("listed_high", out.answer.reasons.single().code)
    }

    @Test
    fun noIncidentMeansNoIncidentField() {
        serve(200, result()).lookupPhone("t", phone, LookupVia.QR)
        val body = JSONObject(seen!!.body)
        assertFalse(body.has("incident_id")); assertEquals("qr", body.getString("via"))
    }

    @Test
    fun aLinkIsCutBeforeItLeavesThePhone() {
        val client = serve(200, result(kind = "url", verdict = "warning"))
        val out = client.lookupUrl("tok", "HTTPS://user:secretpass@Bit.LY/abc?token=SECRET#frag", LookupVia.TYPED)
        val body = JSONObject(seen!!.body)
        assertEquals(setOf("kind", "via", "url"), body.keys().asSequence().toSet())
        assertEquals("https://bit.ly/abc", body.getString("url"))
        for (leak in listOf("secretpass", "SECRET", "frag", "user")) assertFalse(leak in seen!!.body, "$leak leaked")
        assertIs<LookupResult.Done>(out)
        assertEquals(LookupKind.URL, out.answer.kind)
    }

    @Test
    fun aNonWebLinkNeverReachesTheServer() {
        val client = serve(200, result(kind = "url"))
        assertIs<LookupResult.Rejected>(client.lookupUrl("t", "javascript:alert(1)", LookupVia.QR))
        assertIs<LookupResult.Rejected>(client.lookupUrl("t", "   ", LookupVia.TYPED))
        assertEquals(0, calls)
    }

    @Test
    fun aMalformedIncidentIdNeverReachesTheServer() {
        val client = serve(200, result())
        assertIs<LookupResult.Rejected>(client.lookupPhone("t", phone, LookupVia.TYPED, incidentId = "../x"))
        assertEquals(0, calls)
    }

    @Test
    fun aPhoneIsNeverSafeWhateverTheServerSays() {
        val out = serve(200, result(verdict = "safe")).lookupPhone("t", phone, LookupVia.TYPED)
        assertIs<LookupResult.Done>(out)
        assertEquals(LookupVerdict.UNKNOWN, out.answer.verdict)
    }

    @Test
    fun aLinkCanBeSafe() {
        val out = serve(200, result(kind = "url", verdict = "safe")).lookupUrl("t", "https://example.org", LookupVia.TYPED)
        assertIs<LookupResult.Done>(out)
        assertEquals(LookupVerdict.SAFE, out.answer.verdict)
    }

    @Test
    fun statusesMapToResults() {
        fun status(code: Int, body: String = "", headers: Map<String, String> = emptyMap()): LookupResult =
            serve(code, body, headers).lookupPhone("t", phone, LookupVia.TYPED).also { stop() }
        assertIs<LookupResult.Unauthorized>(status(401))
        assertIs<LookupResult.Unauthorized>(status(403, """{"detail":"forbidden"}"""))
        assertIs<LookupResult.ConsentRequired>(status(403, """{"detail":"consent_required"}"""))
        assertIs<LookupResult.ConsentRequired>(status(403, """{"detail":{"code":"consent_required"}}"""))
        assertIs<LookupResult.IncidentNotFound>(status(404))
        assertEquals(30, assertIs<LookupResult.RateLimited>(status(429, headers = mapOf("Retry-After" to "30"))).retryAfterSeconds)
        assertNull(assertIs<LookupResult.RateLimited>(status(429)).retryAfterSeconds)
        assertIs<LookupResult.Rejected>(status(422))
        assertIs<LookupResult.ServerError>(status(500))
        assertIs<LookupResult.ServerError>(status(503))
    }

    @Test
    fun anAnswerThatBreaksTheContractIsAServerError() {
        val bad = listOf(
            "not json",
            result(disclaimer = "Kết quả chỉ để tham khảo."),           // no AI disclosure
            result(kind = "url"),                                         // asked for a phone
            result(verdict = "great"),
            result(confidence = "1.5"),
            result().replace(verificationId, "not-a-uuid"),
            result().replace("\"is_demo\":false", ""),
        )
        for (body in bad) { assertIs<LookupResult.ServerError>(serve(200, body).lookupPhone("t", phone, LookupVia.TYPED), body); stop() }
    }

    @Test
    fun noConnectionIsANetworkError() {
        val client = serve(200, result()); stop()
        assertIs<LookupResult.NetworkError>(client.lookupPhone("t", phone, LookupVia.TYPED))
    }
}
