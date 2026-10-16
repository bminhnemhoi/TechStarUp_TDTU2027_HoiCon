package vn.hoicon.sentinel.data

import com.sun.net.httpserver.HttpServer
import java.net.InetSocketAddress
import java.util.Base64
import org.junit.After
import org.junit.Test
import vn.hoicon.sentinel.data.remote.ThreatListApiClient
import vn.hoicon.sentinel.data.remote.ThreatListResult
import kotlin.test.assertContentEquals
import kotlin.test.assertEquals
import kotlin.test.assertIs

/** Spec 026 T022: the client's side of `GET /v1/threat-list` (threat_list.v1.json). */
class ThreatListApiClientTest {
    private var server: HttpServer? = null
    private var path: String? = null
    private var auth: String? = null
    private var redirectTargetHit = false

    @After
    fun stop() = server?.stop(0) ?: Unit

    private fun serve(status: Int, reply: String = "", extra: Map<String, String> = emptyMap()): ThreatListApiClient {
        val s = HttpServer.create(InetSocketAddress("127.0.0.1", 0), 0)
        s.createContext("/other") { ex -> redirectTargetHit = true; ex.sendResponseHeaders(200, -1); ex.close() }
        s.createContext("/v1") { ex ->
            path = ex.requestURI.toString()
            auth = ex.requestHeaders.getFirst("Authorization")
            val bytes = reply.toByteArray()
            extra.forEach { (k, v) -> ex.responseHeaders.add(k, v) }
            ex.sendResponseHeaders(status, if (bytes.isEmpty()) -1 else bytes.size.toLong())
            if (bytes.isNotEmpty()) ex.responseBody.use { it.write(bytes) }
            ex.close()
        }
        s.start(); server = s
        return ThreatListApiClient("http://127.0.0.1:${s.address.port}", timeoutMs = 2_000)
    }

    private val version = "0123456789abcdef"
    private val packed = byteArrayOf(0, 0, 5, 0, 1, 0)
    private fun okBody(v: String = version, bits: Int = 22, count: Int = 2, b64: String = Base64.getEncoder().encodeToString(packed)) =
        """{"version":"$v","bucket_bits":$bits,"count":$count,"buckets_b64":"$b64","generated_at":"2026-10-16T00:00:00Z"}"""

    @Test
    fun okParsesTheSnapshotAndSendsBearerAndSince() {
        val client = serve(200, okBody())
        val result = client.fetch("tok", since = "fedcba9876543210")
        assertIs<ThreatListResult.Fresh>(result)
        assertEquals(version, result.version); assertEquals(22, result.bucketBits); assertEquals(2, result.count)
        assertContentEquals(packed, result.packed)
        assertEquals("/v1/threat-list?since=fedcba9876543210", path)
        assertEquals("Bearer tok", auth)
    }

    @Test
    fun noSinceMeansNoQueryAndAMalformedSinceIsDropped() {
        val client = serve(200, okBody())
        client.fetch("tok", since = null); assertEquals("/v1/threat-list", path)
        client.fetch("tok", since = "../../x?y=1"); assertEquals("/v1/threat-list", path)
    }

    @Test
    fun statusesMapToResults() {
        assertIs<ThreatListResult.NotModified>(serve(304).fetch("t", version)).also { stop() }
        assertIs<ThreatListResult.Unauthorized>(serve(401).fetch("t", null)).also { stop() }
        assertIs<ThreatListResult.Unauthorized>(serve(403).fetch("t", null)).also { stop() }
        assertIs<ThreatListResult.RateLimited>(serve(429).fetch("t", null)).also { stop() }
        assertIs<ThreatListResult.ServerError>(serve(503).fetch("t", null)).also { stop() }
    }

    @Test
    fun aBodyThatBreaksTheContractIsAServerError() {
        for (bad in listOf("not json", okBody(v = "ABC"), okBody(b64 = "***"), okBody(count = -1), "{}")) {
            assertIs<ThreatListResult.ServerError>(serve(200, bad).fetch("t", null), bad); stop()
        }
    }

    @Test
    fun noConnectionIsANetworkError() {
        val client = serve(200, okBody()); stop()
        assertIs<ThreatListResult.NetworkError>(client.fetch("t", null))
    }

    @Test
    fun redirectsAreNeverFollowed() {
        val client = serve(302, extra = mapOf("Location" to "/other"))
        assertIs<ThreatListResult.ServerError>(client.fetch("tok", null))
        assertEquals(false, redirectTargetHit)
    }
}
