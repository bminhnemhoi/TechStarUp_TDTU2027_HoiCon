package vn.hoicon.sentinel.domain.events

import vn.hoicon.rules.AppCategory
import vn.hoicon.rules.AppForeground
import vn.hoicon.rules.BankAppCatalog
import vn.hoicon.rules.CallSignal
import vn.hoicon.rules.RiskLevel
import vn.hoicon.rules.RuleId

/**
 * Builds `risk_event.v1.json` documents from what the sensing chain knows. The one place that decides what leaves
 * the phone about a call or an app, so the privacy rules are enforced (and tested) here:
 * - the caller is `h1` + last 3 digits only, and only when the number was readable;
 * - an app's package id is sent only when it is in `bank_apps.vn.json` (the schema's rule), never for any other app.
 */
class EventFactory(
    private val appVersion: String,
    private val rulesVersion: String,
    private val newId: (Long) -> String = Uuid7::generate,
) {
    /**
     * @param callActive whether a call is on right now (null = not known); with [call] ended, `since_end_s` is
     *   computed from [nowMs].
     * @param app the app in front, for events about an app.
     */
    fun build(
        type: RiskEventType,
        nowMs: Long,
        floor: RiskLevel = RiskLevel.NONE,
        rule: RuleId? = null,
        call: CallSignal? = null,
        callActive: Boolean? = null,
        app: AppForeground? = null,
        appCategory: AppCategory? = app?.category,
        timing: EventTiming? = null,
    ): RiskEvent = RiskEvent(
        id = newId(nowMs),
        type = type,
        occurredAtMs = nowMs,
        ruleFloor = floor,
        ruleId = rule,
        caller = call?.phone?.let {
            EventCaller(h1 = it.h1, last3 = it.last3, inContacts = false, trusted = call.trusted, flagged = call.flagged)
        },
        call = call?.let { callBlock(it, callActive, nowMs) },
        app = appCategory?.let { EventApp(it, app?.packageName?.takeIf(::isListedPackage)) },
        timing = timing,
        appVersion = appVersion,
        rulesVersion = rulesVersion,
    )

    private fun callBlock(call: CallSignal, active: Boolean?, nowMs: Long): EventCall {
        val ended = call.endedAtMs
        val isActive = active ?: (ended == null)
        return EventCall(
            direction = call.direction,
            active = isActive,
            durationS = ((ended ?: nowMs) - call.startedAtMs).coerceAtLeast(0) / 1000,
            sinceEndS = if (!isActive && ended != null) ((nowMs - ended).coerceAtLeast(0) / 1000) else null,
        )
    }

    private fun isListedPackage(packageName: String) = BankAppCatalog.categoryOf(packageName) != null
}
