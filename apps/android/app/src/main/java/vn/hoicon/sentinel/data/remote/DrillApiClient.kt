package vn.hoicon.sentinel.data.remote

import java.io.IOException
import org.json.JSONArray
import org.json.JSONException
import org.json.JSONObject
import vn.hoicon.sentinel.domain.drill.DrillAnswer
import vn.hoicon.sentinel.domain.drill.DrillChoice
import vn.hoicon.sentinel.domain.drill.DrillDebrief
import vn.hoicon.sentinel.domain.drill.DrillScript
import vn.hoicon.sentinel.domain.drill.DrillStep
import vn.hoicon.sentinel.domain.drill.DrillTiming

/**
 * One drill the server wants this phone to offer (`drill_offer.v1`, Spec 028 D3). The script travels inside the offer, so
 * the drill can be played with no network. [json] is the `drill` object exactly as received: it is what the phone keeps
 * until the person answers, and [DrillOffers.parse] turns it back into this.
 */
class DrillOffer(val drillId: String, val windowEnd: String, val script: DrillScript, val json: String)

/** How a drill ended on the phone; [wire] is the `status` of `drill_result.v1`. The server alone decides passed/failed. */
enum class DrillStatus(val wire: String) { DECLINED("declined"), ABORTED("aborted"), COMPLETED("completed") }

sealed interface DrillOfferResult {
    data class Offer(val offer: DrillOffer) : DrillOfferResult

    /** `{"drill": null}`: nothing to offer right now. */
    data object NoOffer : DrillOfferResult

    data object Unauthorized : DrillOfferResult

    data object NetworkError : DrillOfferResult

    /** 5xx, or an answer that does not follow the contract (including a script that is not a well-formed drill). */
    data object ServerError : DrillOfferResult
}

sealed interface DrillResultOutcome {
    /** `2xx`, or `409`: the server already holds a result for this drill (the same one sent twice, or an earlier one). */
    data object Accepted : DrillResultOutcome

    data object Unauthorized : DrillResultOutcome

    /** `404`: not this family's drill, or gone. Nothing to retry. */
    data object NotFound : DrillResultOutcome

    /** `400`/`422`: the server will never accept this body. */
    data object Rejected : DrillResultOutcome

    data object NetworkError : DrillResultOutcome

    data object ServerError : DrillResultOutcome
}

/** The part of the API the drill code needs; tests use a fake. */
interface DrillGateway {
    fun fetchOffer(accessToken: String): DrillOfferResult

    fun sendResult(
        accessToken: String,
        drillId: String,
        status: DrillStatus,
        answers: List<DrillAnswer>,
        startedAt: String? = null,
        completedAt: String? = null,
    ): DrillResultOutcome
}

/**
 * `GET /v1/drills/offer` and `POST /v1/drills/{id}/result` (Spec 028 FR-005). Only letters of choices and ids travel:
 * no free text, no recording, nothing about the person (SC-006). Blocking: background threads only, and never on the
 * safe-pause path.
 */
class DrillApiClient(baseUrl: String, timeoutMs: Int = TIMEOUT_MS) : DrillGateway {
    private val http = JsonHttp(baseUrl, timeoutMs)

    override fun fetchOffer(accessToken: String): DrillOfferResult {
        val reply = try {
            http.send("GET", "/v1/drills/offer", accessToken, body = null, maxReply = MAX_REPLY)
        } catch (_: IOException) {
            return DrillOfferResult.NetworkError
        }
        return when (reply.status) {
            200 -> parseOffer(reply.body)
            401 -> DrillOfferResult.Unauthorized
            // Not allowed for this family (no `drills` consent, feature off): nothing to offer. NOT a refused token: a side
            // feature saying no must never make E6 ask the person to reconnect.
            403 -> DrillOfferResult.NoOffer
            else -> DrillOfferResult.ServerError
        }
    }

    override fun sendResult(
        accessToken: String,
        drillId: String,
        status: DrillStatus,
        answers: List<DrillAnswer>,
        startedAt: String?,
        completedAt: String?,
    ): DrillResultOutcome {
        // The id goes into the URL path: only an id that looks like one is ever sent.
        if (!DrillOffers.ID.matches(drillId)) return DrillResultOutcome.Rejected
        val body = JSONObject()
            .put("drill_id", drillId)
            .put("status", status.wire)
            .put("answers", JSONArray().apply { answers.forEach { put(JSONObject().put("step", it.step).put("choice_id", it.choiceId)) } })
        startedAt?.let { body.put("started_at", it) }
        completedAt?.let { body.put("completed_at", it) }
        val reply = try {
            http.send("POST", "/v1/drills/$drillId/result", accessToken, body, MAX_REPLY)
        } catch (_: IOException) {
            return DrillResultOutcome.NetworkError
        }
        return when (reply.status) {
            in 200..299, 409 -> DrillResultOutcome.Accepted
            401 -> DrillResultOutcome.Unauthorized
            404 -> DrillResultOutcome.NotFound
            400, 403, 422 -> DrillResultOutcome.Rejected
            else -> DrillResultOutcome.ServerError
        }
    }

    private fun parseOffer(text: String): DrillOfferResult = try {
        val drill = JSONObject(text).opt("drill")
        when {
            drill == null || drill == JSONObject.NULL -> DrillOfferResult.NoOffer
            drill is JSONObject -> DrillOffers.parse(drill.toString())?.let { DrillOfferResult.Offer(it) } ?: DrillOfferResult.ServerError
            else -> DrillOfferResult.ServerError
        }
    } catch (_: JSONException) {
        DrillOfferResult.ServerError
    }

    private companion object {
        const val TIMEOUT_MS = 10_000
        const val MAX_REPLY = 64 * 1024
    }
}

/** Reads the `drill` object of `drill_offer.v1`. Anything that does not follow the contract gives null: never half a drill. */
object DrillOffers {
    /** A drill id ends up in a URL path: letters, digits, `_` and `-` only. */
    internal val ID = Regex("^[A-Za-z0-9_-]{1,64}$")

    // The caps of `drill_script.v1` (plan §4): a longer text is not a drill this phone made room for.
    private const val MAX_LINE = 400
    private const val MAX_LABEL = 40
    private val LAST3 = Regex("^[0-9]{3}$")

    fun parse(json: String): DrillOffer? = try {
        val drill = JSONObject(json)
        val drillId = drill.getString("drill_id")
        // `is_drill` is a constant `true` in the contract: an offer that does not say so is not played as a drill.
        if (!ID.matches(drillId) || !drill.has("is_drill") || !drill.getBoolean("is_drill")) {
            null
        } else {
            val windowEnd = drill.getString("window_end")
            // Fail closed: a window that cannot be read is a drill that is not played.
            if (DrillTiming.parseEnd(windowEnd) == null) null else DrillOffer(drillId, windowEnd, script(drill.getJSONObject("script")), json)
        }
    } catch (_: JSONException) {
        null
    } catch (_: IllegalArgumentException) {
        null
    }

    private fun script(s: JSONObject): DrillScript {
        val steps = s.getJSONArray("steps").objects().map { step ->
            DrillStep(
                lineVi = step.getString("line_vi").also { require(it.length <= MAX_LINE) },
                choices = step.getJSONArray("choices").objects().map { c ->
                    DrillChoice(
                        c.getString("id"),
                        c.getString("label_vi").also { require(it.length <= MAX_LABEL) },
                        c.getBoolean("correct"),
                        c.getString("feedback_vi").also { require(it.length <= MAX_LINE) },
                    )
                },
            )
        }
        val debrief = s.getJSONObject("debrief")
        return DrillScript(
            id = s.getString("id"),
            scenarioRef = s.getString("scenario_ref"),
            title = s.getString("title"),
            agencyFictional = s.getString("agency_fictional"),
            callerLast3Fictional = s.optString("caller_last3_fictional").takeIf { it.isNotEmpty() }?.also { require(LAST3.matches(it)) },
            steps = steps,
            debrief = DrillDebrief(
                redFlagsVi = debrief.getJSONArray("red_flags_vi").let { a -> List(a.length()) { a.getString(it) } },
                praiseVi = debrief.getString("praise_vi"),
            ),
        )
    }

    private fun JSONArray.objects(): List<JSONObject> = List(length()) { getJSONObject(it) }
}
