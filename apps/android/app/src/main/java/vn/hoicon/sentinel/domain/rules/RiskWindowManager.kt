package vn.hoicon.sentinel.domain.rules

import vn.hoicon.rules.CallSignal
import vn.hoicon.rules.RiskEngine
import vn.hoicon.sentinel.data.local.RiskWindowDao
import vn.hoicon.sentinel.data.local.RiskWindowState
import vn.hoicon.sentinel.domain.events.EventFactory
import vn.hoicon.sentinel.domain.events.RiskEvent
import vn.hoicon.sentinel.domain.events.RiskEventType

/**
 * Lifecycle of the risk window (Spec 022 FR-003): opens when a call from a number outside the contacts is
 * screened, stays open while the call lasts and [RiskEngine.WINDOW_MS] (600 s) after it ends, capped at
 * [RiskEngine.MAX_WINDOW_MS] from the latest call's start. Each open/close queues one event and updates the
 * observable [RiskWindowState] row that E6 and the heartbeat read.
 *
 * Whether a given moment is inside the window is decided by [RiskEngine.inWindow] on the live signal; this class
 * only records the transitions. Call it from one serial context: opens and closes must reach the row in order.
 */
class RiskWindowManager(
    private val dao: RiskWindowDao,
    private val events: EventFactory,
    private val sink: (RiskEvent) -> Unit,
) {
    /** A call from an unknown number was screened (or merged into the open window). */
    suspend fun onCallScreened(call: CallSignal, nowMs: Long) {
        if (call.trusted) return
        val current = dao.get()
        val wasOpen = isOpen(current, nowMs)
        dao.put(
            RiskWindowState(
                isOpen = true,
                openedAt = if (wasOpen && current != null) current.openedAt else nowMs,
                callActive = true,
                expiresAt = expiryAfterCall(call, endedAtMs = nowMs),
            ),
        )
        if (!wasOpen) sink(events.build(RiskEventType.RISK_WINDOW_OPENED, nowMs, call = call, callActive = true))
        // Every screened call that matches the local threat list is reported, also inside a window already open.
        if (call.flagged) sink(events.build(RiskEventType.FLAGGED_NUMBER_CALL, nowMs, call = call, callActive = true))
    }

    /** A call is on again inside the open window (the call-state signal flickered, or a second call connected). */
    suspend fun onCallActive() {
        val current = dao.get() ?: return
        if (current.isOpen && !current.callActive) dao.put(current.copy(callActive = true))
    }

    /** The call is over; the window now runs out [RiskEngine.WINDOW_MS] later. */
    suspend fun onCallEnded(call: CallSignal, endedAtMs: Long) {
        val current = dao.get() ?: return
        if (!current.isOpen) return
        dao.put(current.copy(callActive = false, expiresAt = expiryAfterCall(call, endedAtMs)))
        sink(events.build(RiskEventType.CALL_ENDED, endedAtMs, call = call.copy(endedAtMs = endedAtMs), callActive = false))
    }

    /** The window is over (time ran out, or no call is left). Idempotent: closing a closed window does nothing. */
    suspend fun close(call: CallSignal?, nowMs: Long) {
        val current = dao.get() ?: return
        if (!current.isOpen) return
        dao.put(RiskWindowState.CLOSED)
        sink(events.build(RiskEventType.RISK_WINDOW_CLOSED, nowMs, call = call, callActive = false))
    }

    companion object {
        /** True while the window should show as open: a call is on, or the 600 s after it have not run out. */
        fun isOpen(state: RiskWindowState?, nowMs: Long): Boolean {
            if (state == null || !state.isOpen) return false
            // A row left open by a killed process must not stay open for ever: same absolute cap as the engine.
            if (nowMs - state.openedAt > RiskEngine.MAX_WINDOW_MS) return false
            return state.callActive || nowMs < state.expiresAt
        }

        /** End of the window: [endedAtMs] + 600 s, never later than the absolute cap from the latest call's start. */
        fun expiryAfterCall(call: CallSignal, endedAtMs: Long): Long =
            minOf(endedAtMs + RiskEngine.WINDOW_MS, call.latestStartAtMs + RiskEngine.MAX_WINDOW_MS)
    }
}
