package vn.hoicon.rules

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class RiskEngineTest {
    private val minute = 60_000L
    private val t0 = 1_760_000_000_000L // arbitrary wall-clock origin
    private val stranger = HashedPhone(h1 = "a".repeat(64), last3 = "001")

    private fun call(
        flagged: Boolean = false,
        trusted: Boolean = false,
        endedAt: Long? = null,
        direction: CallDirection = CallDirection.INCOMING,
        phone: HashedPhone? = stranger,
    ) = CallSignal(phone, direction, trusted, flagged, startedAtMs = t0, endedAtMs = endedAt)

    private fun bankAt(atMs: Long, category: AppCategory = AppCategory.BANK) =
        AppForeground("vn.hoicon.demobank", category, atMs)

    @Test
    fun unknownCallerActiveCallBankAppIsHighR1() {
        assertEquals(Decision(RiskLevel.HIGH, RuleId.R1), RiskEngine.evaluate(call(), bankAt(t0 + minute)))
    }

    @Test
    fun walletCountsLikeBank() {
        assertEquals(RiskLevel.HIGH, RiskEngine.evaluate(call(), bankAt(t0 + minute, AppCategory.WALLET)).level)
    }

    @Test
    fun securitiesAppCountsLikeBank() {
        assertEquals(RiskLevel.HIGH, RiskEngine.evaluate(call(), bankAt(t0 + minute, AppCategory.SECURITIES)).level)
    }

    @Test
    fun otherAndSideloadedAppsDoNotTriggerR1() {
        for (category in listOf(AppCategory.OTHER, AppCategory.SIDELOADED)) {
            assertEquals(Decision.NONE, RiskEngine.evaluate(call(), bankAt(t0 + minute, category)))
        }
    }

    @Test
    fun trustedContactIsNoneR0() {
        assertEquals(Decision(RiskLevel.NONE, RuleId.R0), RiskEngine.evaluate(call(trusted = true), bankAt(t0 + minute)))
        assertEquals(
            Decision(RiskLevel.NONE, RuleId.R0),
            RiskEngine.evaluate(call(trusted = true, flagged = true), bankAt(t0 + 6 * minute)),
        )
    }

    @Test
    fun noCallIsNone() {
        assertEquals(Decision.NONE, RiskEngine.evaluate(null, bankAt(t0)))
    }

    @Test
    fun flaggedNumberIsCritical() {
        assertEquals(Decision(RiskLevel.CRITICAL, RuleId.R1), RiskEngine.evaluate(call(flagged = true), bankAt(t0)))
    }

    @Test
    fun callLongerThanFiveMinutesIsCriticalBoundaryIsHigh() {
        assertEquals(RiskLevel.HIGH, RiskEngine.evaluate(call(), bankAt(t0 + 5 * minute)).level)
        assertEquals(RiskLevel.CRITICAL, RiskEngine.evaluate(call(), bankAt(t0 + 5 * minute + 1)).level)
    }

    @Test
    fun endedLongCallStaysCriticalInsideWindow() {
        val ended = call(endedAt = t0 + 6 * minute)
        assertEquals(Decision(RiskLevel.CRITICAL, RuleId.R1), RiskEngine.evaluate(ended, bankAt(t0 + 8 * minute)))
    }

    @Test
    fun windowIsTenMinutesAfterCallEndInclusive() {
        val end = t0 + minute
        val ended = call(endedAt = end)
        assertEquals(RiskLevel.HIGH, RiskEngine.evaluate(ended, bankAt(end + 10 * minute - 1)).level)
        assertEquals(RiskLevel.HIGH, RiskEngine.evaluate(ended, bankAt(end + 10 * minute)).level)
        assertEquals(Decision.NONE, RiskEngine.evaluate(ended, bankAt(end + 10 * minute + 1)))
        assertTrue(RiskEngine.inWindow(ended, end + RiskEngine.WINDOW_MS))
        assertFalse(RiskEngine.inWindow(ended, end + RiskEngine.WINDOW_MS + 1))
    }

    @Test
    fun activeCallHasNoWindowEnd() {
        assertTrue(RiskEngine.inWindow(call(), t0 + 60 * minute))
        assertEquals(RiskLevel.CRITICAL, RiskEngine.evaluate(call(), bankAt(t0 + 60 * minute)).level)
    }

    @Test
    fun bankOpenedBeforeTheCallIsOutsideWindow() {
        assertEquals(Decision.NONE, RiskEngine.evaluate(call(), bankAt(t0 - 1)))
    }

    @Test
    fun hiddenNumberAndOutgoingCallsStillCount() {
        assertEquals(RiskLevel.HIGH, RiskEngine.evaluate(call(phone = null), bankAt(t0 + minute)).level)
        assertEquals(
            RiskLevel.HIGH,
            RiskEngine.evaluate(call(direction = CallDirection.OUTGOING), bankAt(t0 + minute)).level,
        )
    }

    @Test
    fun callDurationNeverNegative() {
        assertEquals(0, RiskEngine.callDurationMs(call(), t0 - minute))
        assertEquals(3 * minute, RiskEngine.callDurationMs(call(endedAt = t0 + 3 * minute), t0 + 9 * minute))
    }

    @Test
    fun levelIsNeverBelowFloorForAnyInput() {
        val calls = listOf(
            null,
            call(),
            call(trusted = true),
            call(flagged = true),
            call(endedAt = t0 + minute),
            call(endedAt = t0 + 6 * minute),
            call(phone = null),
        )
        val times = listOf(t0 - 1, t0, t0 + 2 * minute, t0 + 6 * minute, t0 + 20 * minute)
        for (c in calls) for (at in times) for (category in AppCategory.entries) for (floor in RiskLevel.entries) {
            val unfloored = RiskEngine.evaluate(c, bankAt(at, category))
            val floored = RiskEngine.evaluate(c, bankAt(at, category), floor)
            assertTrue(floored.level >= floor, "level ${floored.level} below floor $floor")
            assertEquals(maxOf(unfloored.level, floor), floored.level)
            assertEquals(unfloored.ruleId, floored.ruleId)
        }
    }

    @Test
    fun onlyHighAndCriticalPauseTheUser() {
        assertEquals(
            listOf(false, false, false, true, true),
            RiskLevel.entries.map { Decision(it, null).pausesUser },
        )
    }

    @Test
    fun evaluationIsDeterministic() {
        val c = call(endedAt = t0 + 2 * minute)
        val a = bankAt(t0 + 4 * minute)
        assertEquals(RiskEngine.evaluate(c, a), RiskEngine.evaluate(c.copy(), a.copy()))
    }
}
