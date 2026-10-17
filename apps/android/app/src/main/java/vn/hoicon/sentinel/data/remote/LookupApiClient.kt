package vn.hoicon.sentinel.data.remote

import java.io.IOException
import java.util.UUID
import org.json.JSONArray
import org.json.JSONException
import org.json.JSONObject
import vn.hoicon.rules.HashedPhone
import vn.hoicon.sentinel.domain.lookup.UrlSanitizer

enum class LookupVerdict { SAFE, WARNING, DANGEROUS, UNKNOWN }

enum class LookupKind { PHONE, URL }

/** How the subject was entered; `qr` is for a code the person scanned (Spec 026 FR-012). */
enum class LookupVia(val wire: String) { TYPED("typed"), QR("qr") }

data class LookupReason(val code: String, val text: String)

data class LookupSource(val name: String, val type: String, val listVersion: String?, val url: String?)

/** `lookup_result.v1.json`. [disclaimer] always starts with "Đây là trợ lý AI HỏiCon." (checked on parse). */
data class LookupAnswer(
    val verificationId: String,
    val kind: LookupKind,
    val verdict: LookupVerdict,
    val confidence: Double,
    val reasons: List<LookupReason>,
    val sources: List<LookupSource>,
    val disclaimer: String,
    val incidentLevel: String?,
    val isDemo: Boolean,
)

sealed interface LookupResult {
    data class Done(val answer: LookupAnswer) : LookupResult

    /** 403 `consent_required`: the `lookups` consent is not on the server's ledger (yet). */
    data object ConsentRequired : LookupResult

    /** 401, or 403 for any other reason: the device token was refused. */
    data object Unauthorized : LookupResult

    /** 404: the incident id is not this family's. */
    data object IncidentNotFound : LookupResult

    /** 429: too many lookups; [retryAfterSeconds] when the server said how long. */
    data class RateLimited(val retryAfterSeconds: Int?) : LookupResult

    /** 400/422: the server refused the request itself (a bug on our side, nothing the person can fix by retrying). */
    data object Rejected : LookupResult

    data object NetworkError : LookupResult

    /** 5xx, or an answer that does not follow the contract. */
    data object ServerError : LookupResult
}

/** The part of the API [vn.hoicon.sentinel.data.lookup.LookupChecker] needs; tests use a fake. */
interface LookupGateway {
    fun lookupPhone(accessToken: String, phone: HashedPhone, via: LookupVia, incidentId: String? = null): LookupResult

    fun lookupUrl(accessToken: String, rawUrl: String, via: LookupVia, incidentId: String? = null): LookupResult
}

/**
 * `POST /v1/lookups` (Spec 026 FR-011; bodies follow docs/schemas/lookup_request.v1.json and lookup_result.v1.json).
 * A phone is only ever sent as `h1` + `last3` ([HashedPhone] cannot hold a raw number); a link is cut by
 * [UrlSanitizer] first. Blocking: background threads only. The reply is never logged.
 */
class LookupApiClient(baseUrl: String, timeoutMs: Int = TIMEOUT_MS) : LookupGateway {
    private val http = JsonHttp(baseUrl, timeoutMs)

    override fun lookupPhone(accessToken: String, phone: HashedPhone, via: LookupVia, incidentId: String?): LookupResult =
        post(
            accessToken,
            JSONObject().put("kind", "phone").put("via", via.wire).put("h1", phone.h1).put("last3", phone.last3),
            incidentId,
            LookupKind.PHONE,
        )

    /** @return [LookupResult.Rejected] without calling the server when [rawUrl] is not a plain web link. */
    override fun lookupUrl(accessToken: String, rawUrl: String, via: LookupVia, incidentId: String?): LookupResult {
        val url = UrlSanitizer.sanitize(rawUrl) ?: return LookupResult.Rejected
        return post(accessToken, JSONObject().put("kind", "url").put("via", via.wire).put("url", url), incidentId, LookupKind.URL)
    }

    private fun post(accessToken: String, body: JSONObject, incidentId: String?, kind: LookupKind): LookupResult {
        incidentId?.let { id ->
            if (runCatching { UUID.fromString(id) }.isFailure) return LookupResult.Rejected
            body.put("incident_id", id)
        }
        val reply = try {
            http.send("POST", "/v1/lookups", accessToken, body, MAX_REPLY)
        } catch (_: IOException) {
            return LookupResult.NetworkError
        }
        return when (reply.status) {
            200, 201 -> parse(reply.body, kind)?.let(LookupResult::Done) ?: LookupResult.ServerError
            401 -> LookupResult.Unauthorized
            403 -> if ("consent_required" in reply.body) LookupResult.ConsentRequired else LookupResult.Unauthorized
            404 -> LookupResult.IncidentNotFound
            429 -> LookupResult.RateLimited(reply.retryAfterSeconds)
            400, 422 -> LookupResult.Rejected
            else -> LookupResult.ServerError
        }
    }

    private fun parse(text: String, requested: LookupKind): LookupAnswer? = try {
        val json = JSONObject(text)
        val kind = when (json.getString("kind")) {
            "phone" -> LookupKind.PHONE
            "url" -> LookupKind.URL
            else -> return null
        }
        if (kind != requested) return null
        val parsedVerdict = when (json.getString("verdict")) {
            "safe" -> LookupVerdict.SAFE
            "warning" -> LookupVerdict.WARNING
            "dangerous" -> LookupVerdict.DANGEROUS
            "unknown" -> LookupVerdict.UNKNOWN
            else -> return null
        }
        // A phone number is NEVER "safe" (Spec 026 FR-004): whatever the server says, the phone shows "no information".
        val verdict = if (kind == LookupKind.PHONE && parsedVerdict == LookupVerdict.SAFE) LookupVerdict.UNKNOWN else parsedVerdict
        val confidence = json.getDouble("confidence").takeIf { it in 0.0..1.0 } ?: return null
        val disclaimer = json.getString("disclaimer").takeIf { it.startsWith(AI_DISCLOSURE) } ?: return null
        LookupAnswer(
            verificationId = json.getString("verification_id").also { UUID.fromString(it) },
            kind = kind,
            verdict = verdict,
            confidence = confidence,
            reasons = json.getJSONArray("reasons").objects().map { LookupReason(it.getString("code"), it.getString("text")) },
            sources = json.getJSONArray("sources").objects().map {
                LookupSource(
                    name = it.getString("name"),
                    type = it.getString("type"),
                    listVersion = it.optString("list_version").takeIf { v -> v.isNotBlank() },
                    url = it.optString("url").takeIf { v -> v.isNotBlank() },
                )
            },
            disclaimer = disclaimer,
            incidentLevel = if (json.isNull("incident_level")) null else json.optString("incident_level").takeIf { it in LEVELS },
            isDemo = json.getBoolean("is_demo"),
        )
    } catch (_: JSONException) {
        null
    } catch (_: IllegalArgumentException) {
        null
    }

    private fun JSONArray.objects(): List<JSONObject> = (0 until length()).map { getJSONObject(it) }

    companion object {
        const val AI_DISCLOSURE = "Đây là trợ lý AI HỏiCon."
        private const val TIMEOUT_MS = 10_000
        private const val MAX_REPLY = 64 * 1024
        private val LEVELS = setOf("low", "medium", "high", "critical")
    }
}
