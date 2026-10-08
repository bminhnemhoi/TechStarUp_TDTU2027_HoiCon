package vn.hoicon.rules

/** Rule ids; [wire] mirrors `rule_id` in `docs/schemas/risk_event.v1.json`. */
enum class RuleId(val wire: String) {
    R0("R0"),
    R1("R1"),
    R2("R2"),
    R4("R4"),
}

/** Category of the app that came to the foreground; [wire] mirrors `app.category` in the risk_event schema. */
enum class AppCategory(val wire: String) {
    BANK("bank"),
    WALLET("wallet"),
    SECURITIES("securities"),
    SIDELOADED("sideloaded"),
    OTHER("other"),
}

enum class CallDirection(val wire: String) {
    INCOMING("incoming"),
    OUTGOING("outgoing"),
}

/**
 * The call(s) with a number that is not in the address book (CallScreeningService only sees those) behind the open
 * risk window. Never carries the raw number: [phone] is null for hidden/unparseable numbers.
 *
 * @property startedAtMs earliest start among merged calls (see [RiskEngine.mergeCall]).
 * @property endedAtMs null while a call is still ringing or active; otherwise the last moment one was seen active.
 * @property latestStartAtMs start of the most recent merged call; the absolute window cap counts from here.
 */
data class CallSignal(
    val phone: HashedPhone?,
    val direction: CallDirection,
    val trusted: Boolean,
    val flagged: Boolean,
    val startedAtMs: Long,
    val endedAtMs: Long?,
    val latestStartAtMs: Long = startedAtMs,
)

/** An app came to the foreground at [atMs] (wall clock, same base as [CallSignal] times). */
data class AppForeground(val packageName: String, val category: AppCategory, val atMs: Long)

data class Decision(val level: RiskLevel, val ruleId: RuleId?) {
    /** HIGH and above open SafePause. */
    val pausesUser: Boolean get() = level >= RiskLevel.HIGH

    companion object {
        val NONE = Decision(RiskLevel.NONE, null)
    }
}

/**
 * Deterministic on-device rules (ADR-001). No network, no clock reads, no randomness: same input, same output.
 *
 * - R0: trusted contact ⇒ none.
 * - R1: unknown or flagged number, call active or ended ≤ [WINDOW_MS] ago, financial app ([FINANCIAL]) in
 *   foreground ⇒ high; critical when the number is flagged or the call lasted > [LONG_CALL_MS].
 *   Also when the financial app was already in front before the call and stays there once it connects
 *   ([evaluateForegroundDuringCall]): answering from the heads-up never produces a new "app opened" event.
 *
 * The returned level is never below the caller-supplied `floor` (a risk can be raised, never lowered).
 */
object RiskEngine {
    const val VERSION = "0.1.0-s1"
    const val WINDOW_MS: Long = 10 * 60 * 1000L
    const val LONG_CALL_MS: Long = 5 * 60 * 1000L

    /**
     * Absolute cap from the most recent call's start, whatever the call-state signal says: bounds a stuck
     * "in call" reading (battery, privacy). 2 h, not 1 h: "công an" scripts keep victims on the line for hours.
     */
    const val MAX_WINDOW_MS: Long = 2 * 60 * 60 * 1000L

    /** Apps that can move money: R1 applies. Securities included — "đầu tư chứng khoán" is a common scam script. */
    val FINANCIAL: Set<AppCategory> = setOf(AppCategory.BANK, AppCategory.WALLET, AppCategory.SECURITIES)

    fun evaluate(call: CallSignal?, app: AppForeground, floor: RiskLevel = RiskLevel.NONE): Decision {
        val decision = decide(call, app)
        return if (decision.level >= floor) decision else decision.copy(level = floor)
    }

    /**
     * True while [atMs] is inside the risk window of [call]: from call start until [WINDOW_MS] after it ended, and
     * never more than [MAX_WINDOW_MS] after the latest call started.
     */
    fun inWindow(call: CallSignal, atMs: Long): Boolean {
        if (atMs < call.startedAtMs || atMs - call.latestStartAtMs > MAX_WINDOW_MS) return false
        val ended = call.endedAtMs ?: return true
        return atMs - ended <= WINDOW_MS
    }

    /**
     * Folds a newly screened call [next] into the window currently [open] (SEC-6). A later call never lowers the
     * risk: flagged is OR-ed, the earliest start is kept (call length only grows), a call still ringing keeps the
     * window open, and a trusted call never closes or overrides an open untrusted window.
     */
    fun mergeCall(open: CallSignal?, next: CallSignal): CallSignal {
        if (open == null || open.trusted || !inWindow(open, next.startedAtMs)) return next
        if (next.trusted) return open
        val keepOpenPhone = open.flagged && !next.flagged
        return CallSignal(
            phone = if (keepOpenPhone) open.phone else next.phone ?: open.phone,
            direction = next.direction,
            trusted = false,
            flagged = open.flagged || next.flagged,
            startedAtMs = minOf(open.startedAtMs, next.startedAtMs),
            endedAtMs = if (open.endedAtMs == null || next.endedAtMs == null) {
                null
            } else {
                maxOf(open.endedAtMs, next.endedAtMs)
            },
            latestStartAtMs = maxOf(open.latestStartAtMs, next.latestStartAtMs),
        )
    }

    /**
     * GAP: [foreground] is the app in front right now (resumed, not paused since — possibly long before the call).
     * Once the call is [callConnected], a financial app in front counts as opened at [nowMs] ⇒ same rules as R1.
     * While it only rings, nothing happens (the user hasn't engaged with the caller yet).
     */
    fun evaluateForegroundDuringCall(
        call: CallSignal?,
        foreground: AppForeground?,
        callConnected: Boolean,
        nowMs: Long,
        floor: RiskLevel = RiskLevel.NONE,
    ): Decision {
        if (call == null || foreground == null || !callConnected || call.endedAtMs != null) {
            return if (floor == RiskLevel.NONE) Decision.NONE else Decision(floor, null)
        }
        return evaluate(call, foreground.copy(atMs = maxOf(foreground.atMs, nowMs)), floor)
    }

    /** Call length as known at [atMs]: up to the end if it ended, else up to [atMs]. */
    fun callDurationMs(call: CallSignal, atMs: Long): Long =
        ((call.endedAtMs ?: atMs) - call.startedAtMs).coerceAtLeast(0)

    private fun decide(call: CallSignal?, app: AppForeground): Decision {
        if (call == null) return Decision.NONE
        if (call.trusted) return Decision(RiskLevel.NONE, RuleId.R0)
        if (app.category !in FINANCIAL) return Decision.NONE
        if (!inWindow(call, app.atMs)) return Decision.NONE
        val critical = call.flagged || callDurationMs(call, app.atMs) > LONG_CALL_MS
        return Decision(if (critical) RiskLevel.CRITICAL else RiskLevel.HIGH, RuleId.R1)
    }
}
