package vn.hoicon.sentinel.data.remote

import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.time.OffsetDateTime
import java.time.format.DateTimeParseException
import org.json.JSONException
import org.json.JSONObject
import vn.hoicon.sentinel.data.local.TokenStorage

/** `POST` / `DELETE /v1/data-requests` (spec 038; bodies follow docs/schemas/data_request.v1.json). Blocking: call from a background thread. */
class DataRequestApiClient(baseUrl: String, private val timeoutMs: Int = 10_000) {
    private val base = baseUrl.trimEnd('/')

    class Receipt(val requestId: String, val status: String, val requestedAtMs: Long, val executeAfterMs: Long?)

    sealed interface Reply {
        data class Ok(val receipt: Receipt) : Reply
        data class Busy(val retryAfterSeconds: Int) : Reply
        data object Unauthorized : Reply
        data object NotFound : Reply
        data object TooLate : Reply
        data object NetworkError : Reply
        data object ServerError : Reply
    }

    fun request(accessToken: String): Reply = call("POST", "/v1/data-requests", accessToken, JSONObject().put("kind", "delete").put("confirmed", true))

    fun cancel(accessToken: String, requestId: String): Reply = call("DELETE", "/v1/data-requests/$requestId", accessToken, null)

    private fun call(method: String, path: String, token: String, body: JSONObject?): Reply {
        val connection = URL(base + path).openConnection() as HttpURLConnection
        try {
            connection.requestMethod = method
            connection.connectTimeout = timeoutMs
            connection.readTimeout = timeoutMs
            connection.useCaches = false
            connection.instanceFollowRedirects = false // a redirect would resend the Authorization header elsewhere
            connection.setRequestProperty("Accept", "application/json")
            connection.setRequestProperty("Authorization", "Bearer $token")
            if (body != null) {
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json; charset=utf-8")
                connection.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
            }
            val status = connection.responseCode
            val text = (if (status in 200..299) connection.inputStream else connection.errorStream)?.use(::readCapped).orEmpty()
            return when (status) {
                200, 202 -> parse(text)?.let(Reply::Ok) ?: Reply.ServerError
                401, 403 -> Reply.Unauthorized
                404, 405 -> Reply.NotFound
                409 -> Reply.TooLate
                429 -> Reply.Busy(connection.getHeaderField("Retry-After")?.toIntOrNull()?.coerceAtLeast(1) ?: DEFAULT_RETRY_S)
                else -> Reply.ServerError
            }
        } catch (_: IOException) {
            return Reply.NetworkError
        } catch (_: RuntimeException) {
            return Reply.ServerError // e.g. a mis-set base URL: never crash the delete screen
        } finally {
            connection.disconnect()
        }
    }

    /** Replies are tiny JSON; never buffer more than [MAX_REPLY] bytes from a misbehaving server. */
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

    private fun parse(text: String): Receipt? = try {
        val json = JSONObject(text)
        Receipt(
            requestId = json.getString("request_id").also { require(UUID_FORMAT.matches(it)) }, // goes into a DELETE path: only a UUID
            status = json.getString("status"),
            requestedAtMs = OffsetDateTime.parse(json.getString("requested_at")).toInstant().toEpochMilli(),
            executeAfterMs = json.optString("execute_after").takeIf { it.isNotBlank() }?.let { OffsetDateTime.parse(it).toInstant().toEpochMilli() },
        )
    } catch (_: JSONException) {
        null
    } catch (_: IllegalArgumentException) {
        null
    } catch (_: DateTimeParseException) {
        null
    }

    private companion object {
        const val MAX_REPLY = 16 * 1024
        val UUID_FORMAT = Regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
        const val DEFAULT_RETRY_S = 3600
    }
}

/**
 * E12 "Xóa dữ liệu của gia đình" (spec 038 FR-003/FR-006). The server waits 24 hours before it purges and the request can be cancelled; the
 * phone removes nothing of its own until the server has purged, which it learns when the device token is refused after the waiting time
 * ([serverHasPurged]). Offline or refused ⇒ nothing is recorded as sent.
 */
class PrivacyDelete(private val storage: TokenStorage, private val api: DataRequestApiClient) {
    sealed interface Outcome {
        data class Sent(val executeAfterMs: Long) : Outcome
        data object Offline : Outcome
        data class Busy(val retryAfterSeconds: Int) : Outcome
        data object Refused : Outcome
        data object Failed : Outcome
        data object Cancelled : Outcome
        data object TooLate : Outcome

        /** The server has no cancel route yet (spec 038 T007): the request stays pending. */
        data object Unavailable : Outcome
    }

    class Pending(val requestId: String, val executeAfterMs: Long)

    fun pending(): Pending? {
        val id = storage.pendingDeleteId ?: return null
        return Pending(id, storage.pendingDeleteAfterMs)
    }

    fun request(): Outcome {
        val session = storage.load() ?: return Outcome.Refused
        return when (val reply = api.request(session.accessToken)) {
            is DataRequestApiClient.Reply.Ok -> {
                val after = reply.receipt.executeAfterMs ?: (reply.receipt.requestedAtMs + DEFAULT_WAIT_MS)
                storage.pendingDeleteId = reply.receipt.requestId
                storage.pendingDeleteAfterMs = after
                Outcome.Sent(after)
            }
            is DataRequestApiClient.Reply.Busy -> Outcome.Busy(reply.retryAfterSeconds)
            DataRequestApiClient.Reply.Unauthorized -> Outcome.Refused
            DataRequestApiClient.Reply.NetworkError -> Outcome.Offline
            else -> Outcome.Failed
        }
    }

    fun cancel(): Outcome {
        val pending = pending() ?: return Outcome.Cancelled
        val session = storage.load() ?: return Outcome.Refused
        return when (api.cancel(session.accessToken, pending.requestId)) {
            is DataRequestApiClient.Reply.Ok -> clear().let { Outcome.Cancelled }
            DataRequestApiClient.Reply.TooLate -> Outcome.TooLate
            DataRequestApiClient.Reply.NotFound -> Outcome.Unavailable
            DataRequestApiClient.Reply.Unauthorized -> Outcome.Refused
            DataRequestApiClient.Reply.NetworkError -> Outcome.Offline
            else -> Outcome.Failed
        }
    }

    /** The token was refused after the waiting time of a request we sent: the server purged the family. Before that, a refused token is a normal repair. */
    fun serverHasPurged(nowMs: Long): Boolean {
        val pending = pending() ?: return false
        return nowMs >= pending.executeAfterMs && storage.needsRepair
    }

    fun clear() {
        storage.pendingDeleteId = null
        storage.pendingDeleteAfterMs = 0L
    }

    private companion object {
        const val DEFAULT_WAIT_MS = 24L * 60 * 60 * 1000
    }
}
