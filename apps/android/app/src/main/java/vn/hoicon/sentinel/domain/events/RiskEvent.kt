package vn.hoicon.sentinel.domain.events

import java.time.Instant
import org.json.JSONObject
import vn.hoicon.rules.AppCategory
import vn.hoicon.rules.CallDirection
import vn.hoicon.rules.RiskLevel
import vn.hoicon.rules.RuleId

/** `type` of `docs/schemas/risk_event.v1.json`. */
enum class RiskEventType(val wire: String) {
    CALL_STARTED("call_started"),
    CALL_ENDED("call_ended"),
    FLAGGED_NUMBER_CALL("flagged_number_call"),
    RISK_WINDOW_OPENED("risk_window_opened"),
    RISK_WINDOW_CLOSED("risk_window_closed"),
    BANKING_APP_FOREGROUND("banking_app_foreground"),
    SIDELOAD_DETECTED("sideload_detected"),
    SAFE_PAUSE_SHOWN("safe_pause_shown"),
    SAFE_PAUSE_CONTINUED("safe_pause_continued"),
    SAFE_PAUSE_CANCELLED("safe_pause_cancelled"),
    ASK_CHILD_PRESSED("ask_child_pressed"),
}

/** `caller`: the number only as `h1` + last 3 digits (ADR-006). The raw number never reaches this type. */
data class EventCaller(
    val h1: String,
    val last3: String,
    val inContacts: Boolean,
    val trusted: Boolean? = null,
    val flagged: Boolean? = null,
)

data class EventCall(
    val direction: CallDirection? = null,
    val active: Boolean? = null,
    val durationS: Long? = null,
    val sinceEndS: Long? = null,
)

/** [packageName] is sent only for apps in `bank_apps.vn.json` (the schema's rule); never for any other app. */
data class EventApp(val category: AppCategory, val packageName: String? = null)

data class EventTiming(val detectMs: Long? = null, val pauseMs: Long? = null)

/**
 * One `risk_event.v1.json` document: metadata only, no call content, no raw number. [toJson] is the wire form that
 * `POST /v1/events` takes inside a batch.
 */
data class RiskEvent(
    val id: String,
    val type: RiskEventType,
    val occurredAtMs: Long,
    val ruleFloor: RiskLevel,
    val ruleId: RuleId? = null,
    val caller: EventCaller? = null,
    val call: EventCall? = null,
    val app: EventApp? = null,
    val timing: EventTiming? = null,
    val isDrill: Boolean = false,
    val drillId: String? = null,
    val appVersion: String,
    val rulesVersion: String,
) {
    fun toJson(): JSONObject {
        val json = JSONObject()
            .put("id", id)
            .put("schema_version", SCHEMA_VERSION)
            .put("type", type.wire)
            .put("occurred_at", Instant.ofEpochMilli(occurredAtMs).toString())
            .put("rule_floor", ruleFloor.wire)
            .put("is_drill", isDrill)
            .put("app_version", appVersion.take(MAX_VERSION))
            .put("rules_version", rulesVersion.take(MAX_VERSION))
        // A rule the schema does not list yet (R5) is left out: the floor already says "critical".
        ruleId?.takeIf { it.inContract }?.let { json.put("rule_id", it.wire) }
        drillId?.let { json.put("drill_id", it) }
        caller?.let {
            json.put(
                "caller",
                JSONObject().put("h1", it.h1).put("last3", it.last3).put("in_contacts", it.inContacts).apply {
                    it.trusted?.let { v -> put("trusted", v) }
                    it.flagged?.let { v -> put("flagged", v) }
                },
            )
        }
        call?.let {
            json.put(
                "call",
                JSONObject().apply {
                    it.direction?.let { v -> put("direction", v.wire) }
                    it.active?.let { v -> put("active", v) }
                    it.durationS?.let { v -> put("duration_s", v.coerceAtLeast(0)) }
                    it.sinceEndS?.let { v -> put("since_end_s", v.coerceAtLeast(0)) }
                },
            )
        }
        app?.let {
            json.put(
                "app",
                JSONObject().put("category", it.category.wire).apply { it.packageName?.let { v -> put("package", v) } },
            )
        }
        timing?.let {
            json.put(
                "timing",
                JSONObject().apply {
                    it.detectMs?.let { v -> put("detect_ms", v.coerceAtLeast(0)) }
                    it.pauseMs?.let { v -> put("pause_ms", v.coerceAtLeast(0)) }
                },
            )
        }
        return json
    }

    companion object {
        const val SCHEMA_VERSION = 1
        private const val MAX_VERSION = 32
    }
}
