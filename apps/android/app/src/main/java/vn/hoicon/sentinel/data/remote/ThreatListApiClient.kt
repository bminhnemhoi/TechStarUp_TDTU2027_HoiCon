package vn.hoicon.sentinel.data.remote

import java.io.IOException
import org.json.JSONException
import org.json.JSONObject

sealed interface ThreatListResult {
    /** A new snapshot (`threat_list.v1.json`): [packed] is `count` big-endian uint24 buckets, ascending. */
    class Fresh(val version: String, val bucketBits: Int, val count: Int, val packed: ByteArray) : ThreatListResult

    /** `304`: the list is the one the phone already has. */
    data object NotModified : ThreatListResult

    data object Unauthorized : ThreatListResult

    data object RateLimited : ThreatListResult

    data object NetworkError : ThreatListResult

    /** 5xx, or an answer that does not follow the contract. */
    data object ServerError : ThreatListResult
}

/** The part of the API [vn.hoicon.sentinel.data.threat.ThreatSyncer] needs; tests use a fake. */
interface ThreatListFetcher {
    fun fetch(accessToken: String, since: String?): ThreatListResult
}

/**
 * `GET /v1/threat-list?since=<version>` (Spec 026 FR-009). The answer holds k-anonymous buckets, never a number or an
 * `h1` (ADR-011), so it is safe to keep on the phone. Blocking: background threads only; never on the safe-pause path.
 */
class ThreatListApiClient(baseUrl: String, timeoutMs: Int = TIMEOUT_MS) : ThreatListFetcher {
    private val http = JsonHttp(baseUrl, timeoutMs)

    override fun fetch(accessToken: String, since: String?): ThreatListResult {
        val query = since?.takeIf { VERSION.matches(it) }?.let { "?since=$it" }.orEmpty()
        val reply = try {
            http.send("GET", "/v1/threat-list$query", accessToken, body = null, maxReply = MAX_REPLY)
        } catch (_: IOException) {
            return ThreatListResult.NetworkError
        }
        return when (reply.status) {
            200 -> parse(reply.body) ?: ThreatListResult.ServerError
            304 -> ThreatListResult.NotModified
            401, 403 -> ThreatListResult.Unauthorized
            429 -> ThreatListResult.RateLimited
            else -> ThreatListResult.ServerError
        }
    }

    private fun parse(text: String): ThreatListResult.Fresh? = try {
        val json = JSONObject(text)
        val version = json.getString("version")
        val bits = json.getInt("bucket_bits")
        val count = json.getInt("count")
        val packed = java.util.Base64.getDecoder().decode(json.getString("buckets_b64"))
        if (!VERSION.matches(version) || count < 0) null else ThreatListResult.Fresh(version, bits, count, packed)
    } catch (_: JSONException) {
        null
    } catch (_: IllegalArgumentException) {
        null
    }

    private companion object {
        const val TIMEOUT_MS = 15_000
        // 100,000 buckets ≈ 400 KB of base64: the plan's ceiling for a full snapshot.
        const val MAX_REPLY = 1_024 * 1_024
        val VERSION = Regex("^[0-9a-f]{16}$")
    }
}
