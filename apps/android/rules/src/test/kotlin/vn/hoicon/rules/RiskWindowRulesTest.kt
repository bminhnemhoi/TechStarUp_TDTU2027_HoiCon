package vn.hoicon.rules

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertSame
import kotlin.test.assertTrue

/** SEC-6 (merging calls), SEC-9 (window caps), GAP (financial app already in front) and [ForegroundTracker]. */
class RiskWindowRulesTest {
    private val minute = 60_000L
    private val t0 = 1_760_000_000_000L
    private val first = HashedPhone(h1 = "a".repeat(64), last3 = "001")
    private val second = HashedPhone(h1 = "b".repeat(64), last3 = "002")

    private fun call(
        at: Long = t0,
        flagged: Boolean = false,
        trusted: Boolean = false,
        endedAt: Long? = null,
        phone: HashedPhone? = first,
    ) = CallSignal(phone, CallDirection.INCOMING, trusted, flagged, startedAtMs = at, endedAtMs = endedAt)

    private fun app(atMs: Long, category: AppCategory = AppCategory.BANK) =
        AppForeground("vn.hoicon.demobank", category, atMs)

    // ---- SEC-6: a later call never lowers the risk --------------------------------------------------------------

    @Test
    fun laterCallNeverLowersTheLevelForAnyCombination() {
        val opens = listOf(
            call(),
            call(flagged = true),
            call(endedAt = t0 + 6 * minute), // long call, now ended ⇒ critical
            call(endedAt = t0 + minute),
            call(trusted = true),
            call(phone = null),
        )
        val nextStarts = listOf(t0 + 7 * minute, t0 + 12 * minute)
        for (open in opens) for (start in nextStarts) for (flagged in listOf(false, true)) {
            for (trusted in listOf(false, true)) for (ended in listOf(null, start + minute)) {
                val next = call(at = start, flagged = flagged, trusted = trusted, endedAt = ended, phone = second)
                val merged = RiskEngine.mergeCall(open, next)
                for (offset in listOf(0L, minute, 5 * minute, 9 * minute)) {
                    val at = app(start + offset)
                    val before = RiskEngine.evaluate(open, at).level
                    val after = RiskEngine.evaluate(merged, at).level
                    assertTrue(after >= before, "open=$open next=$next at+$offset: $before → $after")
                }
            }
        }
    }

    @Test
    fun trustedCallDoesNotCloseOrOverrideAnOpenUntrustedWindow() {
        val open = call(flagged = true)
        val trusted = call(at = t0 + 2 * minute, trusted = true, phone = second)
        assertSame(open, RiskEngine.mergeCall(open, trusted))
        assertEquals(RiskLevel.CRITICAL, RiskEngine.evaluate(RiskEngine.mergeCall(open, trusted), app(t0 + 3 * minute)).level)
    }

    @Test
    fun mergeKeepsFlagEarliestStartAndOpenState() {
        val open = call(flagged = true, endedAt = t0 + 4 * minute)
        val next = call(at = t0 + 8 * minute, phone = second)
        val merged = RiskEngine.mergeCall(open, next)
        assertTrue(merged.flagged)
        assertEquals(t0, merged.startedAtMs)
        assertEquals(t0 + 8 * minute, merged.latestStartAtMs)
        assertNull(merged.endedAtMs, "the new call is ringing ⇒ window stays open")
        assertEquals(first, merged.phone, "keep the flagged number's hash for the incident")
    }

    @Test
    fun mergeReplacesClosedOrTrustedWindows() {
        val closed = call(flagged = true, endedAt = t0 + minute)
        val late = call(at = t0 + minute + RiskEngine.WINDOW_MS + 1, phone = second)
        assertSame(late, RiskEngine.mergeCall(closed, late))
        val trustedOpen = call(trusted = true)
        val stranger = call(at = t0 + minute, phone = second)
        assertSame(stranger, RiskEngine.mergeCall(trustedOpen, stranger))
        assertSame(stranger, RiskEngine.mergeCall(null, stranger))
    }

    @Test
    fun mergedCallsCountTheirCombinedLengthTowardsCritical() {
        val open = call(endedAt = t0 + 3 * minute) // 3 min ⇒ high
        val next = call(at = t0 + 4 * minute, phone = second)
        assertEquals(RiskLevel.CRITICAL, RiskEngine.evaluate(RiskEngine.mergeCall(open, next), app(t0 + 6 * minute)).level)
    }

    // ---- SEC-9: window caps -------------------------------------------------------------------------------------

    @Test
    fun windowHasAnAbsoluteCapFromTheLatestCall() {
        val stuck = call() // call state never reported an end
        assertTrue(RiskEngine.inWindow(stuck, t0 + RiskEngine.MAX_WINDOW_MS))
        assertFalse(RiskEngine.inWindow(stuck, t0 + RiskEngine.MAX_WINDOW_MS + 1))
        assertEquals(Decision.NONE, RiskEngine.evaluate(stuck, app(t0 + RiskEngine.MAX_WINDOW_MS + 1)))
        val merged = RiskEngine.mergeCall(call(), call(at = t0 + 90 * minute, phone = second))
        assertTrue(RiskEngine.inWindow(merged, t0 + 90 * minute + RiskEngine.MAX_WINDOW_MS))
    }

    @Test
    fun endedCallWindowIsTenMinutesEvenIfTheCapIsFurther() {
        val ended = call(endedAt = t0 + minute)
        assertFalse(RiskEngine.inWindow(ended, t0 + minute + RiskEngine.WINDOW_MS + 1))
    }

    // ---- GAP: financial app already in front -------------------------------------------------------------------

    @Test
    fun bankAlreadyInFrontWhenCallConnectsIsR1() {
        val bankBeforeCall = app(t0 - 30 * minute)
        val decision = RiskEngine.evaluateForegroundDuringCall(call(), bankBeforeCall, callConnected = true, t0 + minute)
        assertEquals(Decision(RiskLevel.HIGH, RuleId.R1), decision)
        assertEquals(
            RiskLevel.CRITICAL,
            RiskEngine.evaluateForegroundDuringCall(call(flagged = true), bankBeforeCall, true, t0 + minute).level,
        )
        assertEquals(
            RiskLevel.HIGH,
            RiskEngine.evaluateForegroundDuringCall(call(), app(t0 - minute, AppCategory.SECURITIES), true, t0).level,
        )
    }

    @Test
    fun gapNeedsAConnectedCallAndAFinancialApp() {
        val bank = app(t0 - minute)
        assertEquals(Decision.NONE, RiskEngine.evaluateForegroundDuringCall(call(), bank, false, t0 + minute))
        assertEquals(Decision.NONE, RiskEngine.evaluateForegroundDuringCall(call(endedAt = t0), bank, true, t0 + minute))
        assertEquals(Decision.NONE, RiskEngine.evaluateForegroundDuringCall(call(), null, true, t0 + minute))
        assertEquals(Decision.NONE, RiskEngine.evaluateForegroundDuringCall(null, bank, true, t0 + minute))
        assertEquals(
            Decision.NONE,
            RiskEngine.evaluateForegroundDuringCall(call(), app(t0 - minute, AppCategory.OTHER), true, t0 + minute),
        )
        assertEquals(
            Decision(RiskLevel.NONE, RuleId.R0),
            RiskEngine.evaluateForegroundDuringCall(call(trusted = true), bank, true, t0 + minute),
        )
    }

    @Test
    fun gapRespectsTheFloor() {
        for (floor in RiskLevel.entries) {
            for (connected in listOf(false, true)) {
                val d = RiskEngine.evaluateForegroundDuringCall(call(), app(t0 - minute), connected, t0 + minute, floor)
                assertTrue(d.level >= floor)
            }
        }
    }

    // ---- ForegroundTracker -------------------------------------------------------------------------------------

    @Test
    fun trackerReportsTheAppResumedLastAndNotPausedSince() {
        val tracker = ForegroundTracker()
        assertNull(tracker.current())
        tracker.onEvent("bank", resumed = true, atMs = 100)
        assertEquals("bank" to 100L, tracker.current())
        tracker.onEvent("bank", resumed = false, atMs = 200)
        tracker.onEvent("dialer", resumed = true, atMs = 200)
        assertEquals("dialer" to 200L, tracker.current())
        tracker.onEvent("dialer", resumed = false, atMs = 300)
        assertNull(tracker.current())
    }

    @Test
    fun trackerIgnoresReplayedOlderEvents() {
        val tracker = ForegroundTracker()
        val batch = listOf(Triple("bank", true, 100L), Triple("bank", false, 150L), Triple("launcher", true, 150L))
        repeat(2) { batch.forEach { (pkg, resumed, at) -> tracker.onEvent(pkg, resumed, at) } }
        tracker.onEvent("bank", resumed = true, atMs = 120) // late, older than the pause ⇒ ignored
        assertEquals("launcher" to 150L, tracker.current())
    }

    @Test
    fun trackerSameTimestampPauseThenResumeWithinOneAppStaysResumed() {
        val tracker = ForegroundTracker()
        tracker.onEvent("bank", resumed = true, atMs = 100)
        tracker.onEvent("bank", resumed = false, atMs = 300) // activity A paused…
        tracker.onEvent("bank", resumed = true, atMs = 300) // …activity B of the same app resumed
        assertEquals("bank" to 300L, tracker.current())
    }
}
