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

sealed interface EventsResult {
    /** The whole batch is stored (a re-sent id counts as stored: the server de-duplicates). */
    data object Accepted : EventsResult

    /**
     * Stored like [Accepted], and the batch linked to an incident (`incident_id` of `events_result.v1.json`). [opened] is true
     * when this batch opened it: the phone then asks the server whether the AI has a question for the person (E8).
     */
    data class AcceptedWithIncident(val incidentId: String, val opened: Boolean) : EventsResult

    /** The server refuses this batch for good (400/413/422): sending it again can never succeed. */
    data object Rejected : EventsResult

    /** The device token was refused: the events stay queued. */
    data object Unauthorized : EventsResult

    /**
     * 403 `consent_withdrawn`: the family withdrew a consent, so the server accepts nothing until it is given again.
     * The pairing is fine: keep the token and the queue, and do not ask the person to connect again.
     */
    data object ConsentWithdrawn : EventsResult

    /** No connection, timeout or TLS failure. */
    data object NetworkError : EventsResult

    /** 5xx, 429, or an endpoint not deployed yet: try again later. */
    data object ServerError : EventsResult
}

/** What the heartbeat says about the phone (`POST /v1/heartbeat`): versions and which permissions are granted. */
data class HeartbeatStatus(
    val appVersion: String,
    val rulesVersion: String,
    val threatListVersion: String?,
    val permissionState: Map<String, Boolean>,
)

sealed interface HeartbeatResult {
    data object Ok : HeartbeatResult
    data object Rejected : HeartbeatResult
    data object Unauthorized : HeartbeatResult

    /** 403 `consent_withdrawn`: consent is needed again; the pairing and the token stay as they are. */
    data object ConsentWithdrawn : HeartbeatResult
    data object NetworkError : HeartbeatResult
    data object ServerError : HeartbeatResult
}

/** The part of the API the outbox needs; [PairingApiClient] implements it, tests use a fake. */
interface EventUploader {
    fun sendEvents(accessToken: String, events: List<JSONObject>): EventsResult
}

/**
 * `POST /v1/pair`, `/v1/consents`, `/v1/events` and `/v1/heartbeat` (docs/API.md; bodies follow
 * docs/schemas/pair_*.v1.json, consent_record.v1.json, risk_event.v1.json and heartbeat.v1.json). Blocking: call from a background
 * thread. Never used on the safe-pause path. Nothing here is logged: codes and tokens are secrets, error bodies
 * are server text.
 */
class PairingApiClient(
    baseUrl: String,
    private val timeoutMs: Int = TIMEOUT_MS,
) : EventUploader {
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

    /** `POST /v1/events`: 1–[MAX_EVENTS_PER_BATCH] `risk_event.v1.json` documents, idempotent on their ids. */
    override fun sendEvents(accessToken: String, events: List<JSONObject>): EventsResult {
        if (events.isEmpty()) return EventsResult.Accepted
        require(events.size <= MAX_EVENTS_PER_BATCH) { "at most $MAX_EVENTS_PER_BATCH events per batch" }
        val body = JSONObject().put("events", JSONArray(events))
        val reply = try {
            post("/v1/events", body, bearer = accessToken)
        } catch (_: IOException) {
            return EventsResult.NetworkError
        }
        if (reply.isConsentWithdrawn()) return EventsResult.ConsentWithdrawn
        return when (reply.status) {
            in 200..299 -> incidentOf(reply.body) ?: EventsResult.Accepted
            400, 413, 422 -> EventsResult.Rejected
            401, 403 -> EventsResult.Unauthorized
            else -> EventsResult.ServerError
        }
    }

    /** `incident_id` / `incident_opened` of the reply; null when absent, null or not a UUID (the batch is stored either way). */
    private fun incidentOf(text: String): EventsResult.AcceptedWithIncident? {
        val json = try {
            JSONObject(text)
        } catch (_: JSONException) {
            return null
        }
        val id = if (json.isNull("incident_id")) null else json.optString("incident_id").takeIf { runCatching { UUID.fromString(it) }.isSuccess }
        return id?.let { EventsResult.AcceptedWithIncident(it, json.optBoolean("incident_opened", false)) }
    }

    /** `POST /v1/heartbeat`: permission state and versions, so the family sees when protection was lost. */
    fun sendHeartbeat(accessToken: String, status: HeartbeatStatus): HeartbeatResult {
        val reply = try {
            post("/v1/heartbeat", heartbeatBody(status), bearer = accessToken)
        } catch (_: IOException) {
            return HeartbeatResult.NetworkError
        }
        if (reply.isConsentWithdrawn()) return HeartbeatResult.ConsentWithdrawn
        return when (reply.status) {
            in 200..299 -> HeartbeatResult.Ok
            400, 413, 422 -> HeartbeatResult.Rejected
            401, 403 -> HeartbeatResult.Unauthorized
            else -> HeartbeatResult.ServerError
        }
    }

    private class Reply(val status: Int, val body: String) {
        /** 403 with the `consent_withdrawn` code (spec 034): not a refused token, so never mapped to Unauthorized. */
        fun isConsentWithdrawn() = status == 403 && body.contains(CONSENT_WITHDRAWN)
    }

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

    companion object {
        /** Batch limit of `POST /v1/events` (spec 021). */
        const val MAX_EVENTS_PER_BATCH = 50
        private const val CONSENT_WITHDRAWN = "consent_withdrawn"

        /** The body of `POST /v1/heartbeat`; follows docs/schemas/heartbeat.v1.json (a test pins its fixtures). */
        internal fun heartbeatBody(status: HeartbeatStatus): JSONObject {
            val permissions = JSONObject()
            status.permissionState.forEach { (name, granted) -> permissions.put(name, granted) }
            val body = JSONObject()
                .put("app_version", status.appVersion.take(MAX_VERSION))
                .put("rules_version", status.rulesVersion.take(MAX_VERSION))
                .put("permission_state", permissions)
            status.threatListVersion?.let { body.put("threat_list_version", it.take(MAX_VERSION)) }
            return body
        }

        private const val TIMEOUT_MS = 10_000
        private const val MAX_REPLY = 64 * 1024
        private const val MAX_VERSION = 32
        private const val MAX_LABEL = 64
        private val CODE_FORMAT = Regex("^[0-9]{6}$")
    }
}
