package vn.hoicon.sentinel.domain.rules

import vn.hoicon.rules.AppCategory
import vn.hoicon.rules.AppForeground
import vn.hoicon.rules.BankAppCatalog
import vn.hoicon.rules.CallSignal
import vn.hoicon.rules.Decision
import vn.hoicon.rules.RemoteControlCatalog
import vn.hoicon.rules.RiskEngine
import vn.hoicon.rules.RiskLevel
import vn.hoicon.rules.RuleId
import vn.hoicon.sentinel.domain.events.EventFactory
import vn.hoicon.sentinel.domain.events.EventTiming
import vn.hoicon.sentinel.domain.events.RiskEvent
import vn.hoicon.sentinel.domain.events.RiskEventType

/**
 * The on-device rules as the sensing chain uses them (ADR-001, Spec 022 FR-004): which foreground apps matter, what
 * [RiskEngine] decides about them (R1 banking app, R5 remote-control app), and the event to queue for the server.
 * Deterministic, no network, no LLM; the verdict never waits for the event to be stored ([sink] is fire-and-forget).
 */
class LocalRulesEvaluator(
    private val events: EventFactory,
    private val sink: (RiskEvent) -> Unit,
) {
    /**
     * The app as the rules see it: a bank/wallet/securities app with its category, a remote-control app as `other`
     * (R5 matches by package), anything else null. Keeps UsageStats noise out of the engine.
     */
    fun watched(packageName: String, atMs: Long): AppForeground? =
        BankAppCatalog.categoryOf(packageName)?.let { AppForeground(packageName, it, atMs) }
            ?: if (RemoteControlCatalog.isRemoteControl(packageName)) {
                AppForeground(packageName, AppCategory.OTHER, atMs)
            } else {
                null
            }

    /**
     * Decides for [app] in front during [call]. A decision that pauses the user queues `banking_app_foreground`
     * (R1) with detection timing. R5 queues nothing here: the schema has no event type for a remote-control app, so
     * the server learns of it from the `safe_pause_shown` event of the pause itself (critical, category `other`).
     */
    fun evaluate(
        call: CallSignal?,
        app: AppForeground,
        nowMs: Long,
        callActive: Boolean,
        floor: RiskLevel = RiskLevel.NONE,
    ): Decision {
        val decision = RiskEngine.evaluate(call, app, floor)
        record(decision, call, app, nowMs, callActive)
        return decision
    }

    /** Same, for an app that was already in front when the call connected (the GAP case of [RiskEngine]). */
    fun evaluateAlreadyInFront(
        call: CallSignal?,
        app: AppForeground,
        callConnected: Boolean,
        nowMs: Long,
        callActive: Boolean,
        floor: RiskLevel = RiskLevel.NONE,
    ): Decision {
        val decision = RiskEngine.evaluateForegroundDuringCall(call, app, callConnected, nowMs, floor)
        record(decision, call, app, nowMs, callActive)
        return decision
    }

    private fun record(decision: Decision, call: CallSignal?, app: AppForeground, nowMs: Long, callActive: Boolean) {
        if (!decision.pausesUser || decision.ruleId == RuleId.R5) return
        // The verdict is already made and the pause is about to open: nothing about the event may stop it.
        try {
            sink(
                events.build(
                    type = RiskEventType.BANKING_APP_FOREGROUND,
                    nowMs = nowMs,
                    floor = decision.level,
                    rule = decision.ruleId,
                    call = call,
                    callActive = callActive,
                    app = app,
                    timing = EventTiming(detectMs = (nowMs - app.atMs).coerceAtLeast(0)),
                ),
            )
        } catch (_: Exception) {
            // Losing a telemetry event is acceptable; losing the safe pause is not.
        }
    }
}
