package vn.hoicon.sentinel.data.remote

import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID
import org.json.JSONArray
import org.json.JSONException
import org.json.JSONObject
import vn.hoicon.sentinel.data.consent.ConsentItem
import vn.hoicon.sentinel.data.local.DeviceSession

sealed interface PairResult {
    data class Paired(val session: DeviceSession) : PairResult

    /** Wrong, expired or already-used code (also anything that is not 6 digits; never sent to the server). */
    data object InvalidCode : PairResult

    data object RateLimited : PairResult

    /** No connection, timeout or TLS failure. */
    data object NetworkError : PairResult

    /** The server answered, but not with something this app understands. */
    data object ServerError : PairResult
}

sealed interface ConsentResult {
    data class Recorded(val count: Int) : ConsentResult

    /** The device token was refused: pair again. */
    data object Unauthorized : ConsentResult

    data object NetworkError : ConsentResult

    data object ServerError : ConsentResult
}

/**
 * `POST /v1/pair` and `POST /v1/consents` (docs/API.md; bodies follow docs/schemas/pair_*.v1.json and
 * consent_record.v1.json). Blocking: call from a background thread. Never used on the safe-pause path.
 * Nothing here is logged: codes and tokens are secrets, error bodies are server text.
 */
class PairingApiClient(
    baseUrl: String,
    private val timeoutMs: Int = TIMEOUT_MS,
) {
    private val base = baseUrl.trimEnd('/')

    fun pair(code: String, appVersion: String, rulesVersion: String, deviceLabel: String?): PairResult {
        if (!CODE_FORMAT.matches(code)) return PairResult.InvalidCode
        val body = JSONObject()
            .put("code", code)
            .put("app_version", appVersion.take(MAX_VERSION))
            .put("rules_version", rulesVersion.take(MAX_VERSION))
            .put("platform", "android")
        deviceLabel?.takeIf { it.isNotBlank() }?.let { body.put("device_label", it.take(MAX_LABEL)) }
        val reply = try {
            post("/v1/pair", body, bearer = null)
        } catch (_: IOException) {
            return PairResult.NetworkError
        }
        return when (reply.status) {
            200, 201 -> parseSession(reply.body)?.let(PairResult::Paired) ?: PairResult.ServerError
            400, 404, 409, 410, 422 -> PairResult.InvalidCode
            429 -> PairResult.RateLimited
            else -> PairResult.ServerError
        }
    }

    fun recordConsents(accessToken: String, items: List<ConsentItem>): ConsentResult {
        if (items.isEmpty()) return ConsentResult.Recorded(0)
        val array = JSONArray()
        for (item in items) {
            array.put(
                JSONObject()
                    .put("purpose", item.purpose)
                    .put("granted", item.granted)
                    .put("consent_version", item.consentVersion)
                    .put("text_sha256", item.textSha256)
                    .put("channel", item.channel),
            )
        }
        val reply = try {
            post("/v1/consents", JSONObject().put("items", array), bearer = accessToken)
        } catch (_: IOException) {
            return ConsentResult.NetworkError
        }
        return when (reply.status) {
            200, 201 -> ConsentResult.Recorded(items.size)
            401, 403 -> ConsentResult.Unauthorized
            else -> ConsentResult.ServerError
        }
    }

    private class Reply(val status: Int, val body: String)

    private fun post(path: String, body: JSONObject, bearer: String?): Reply {
        val connection = URL(base + path).openConnection() as HttpURLConnection
        try {
            connection.requestMethod = "POST"
            connection.connectTimeout = timeoutMs
            connection.readTimeout = timeoutMs
            connection.useCaches = false
            // A redirect would resend the Authorization header to wherever it points.
            connection.instanceFollowRedirects = false
            connection.doOutput = true
            connection.setRequestProperty("Content-Type", "application/json; charset=utf-8")
            connection.setRequestProperty("Accept", "application/json")
            bearer?.let { connection.setRequestProperty("Authorization", "Bearer $it") }
            connection.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
            val status = connection.responseCode
            val stream = if (status in 200..299) connection.inputStream else connection.errorStream
            val text = stream?.use { readCapped(it) }.orEmpty()
            return Reply(status, text)
        } finally {
            connection.disconnect()
        }
    }

    /** Replies are tiny JSON; refuse to buffer more than [MAX_REPLY] bytes from a misbehaving server. */
    private fun readCapped(stream: java.io.InputStream): String {
        val buffer = ByteArray(MAX_REPLY)
        var size = 0
        while (size < MAX_REPLY) {
            val n = stream.read(buffer, size, MAX_REPLY - size)
            if (n < 0) break
            size += n
        }
        return String(buffer, 0, size, Charsets.UTF_8)
    }

    private fun parseSession(text: String): DeviceSession? {
        val json = try {
            JSONObject(text)
        } catch (_: JSONException) {
            return null
        }
        fun str(key: String) = if (json.isNull(key)) null else json.optString(key).takeIf { it.isNotBlank() }
        fun uuid(key: String) = str(key)?.takeIf { runCatching { UUID.fromString(it) }.isSuccess }
        if (str("token_type") != "bearer" || json.optInt("expires_in", 0) < 1) return null
        return DeviceSession(
            deviceId = uuid("device_id") ?: return null,
            familyId = uuid("family_id") ?: return null,
            memberId = uuid("member_id") ?: return null,
            familyName = str("family_name") ?: return null,
            accessToken = str("access_token") ?: return null,
            refreshToken = str("refresh_token") ?: return null,
        )
    }

    private companion object {
        const val TIMEOUT_MS = 10_000
        const val MAX_REPLY = 64 * 1024
        const val MAX_VERSION = 32
        const val MAX_LABEL = 64
        val CODE_FORMAT = Regex("^[0-9]{6}$")
    }
}
