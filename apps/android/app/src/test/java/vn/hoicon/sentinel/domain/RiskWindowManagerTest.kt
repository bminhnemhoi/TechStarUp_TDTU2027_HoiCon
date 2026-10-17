package vn.hoicon.sentinel.domain

import kotlinx.coroutines.runBlocking
import org.junit.Test
import vn.hoicon.rules.RiskEngine
import vn.hoicon.sentinel.data.local.RiskWindowState
import vn.hoicon.sentinel.domain.events.RiskEvent
import vn.hoicon.sentinel.domain.events.RiskEventType
import vn.hoicon.sentinel.domain.rules.RiskWindowManager
import vn.hoicon.sentinel.outbox.FakeRiskWindowDao
import vn.hoicon.sentinel.outbox.sequentialFactory
import vn.hoicon.sentinel.outbox.stranger
import vn.hoicon.sentinel.outbox.unknownCall
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue

class RiskWindowManagerTest {
    private val dao = FakeRiskWindowDao()
    private val sent = ArrayList<RiskEvent>()
    private val manager = RiskWindowManager(dao, sequentialFactory()) { sent += it }
    private val t0 = 1_760_000_000_000L
    private val minute = 60_000L

    private fun types() = sent.map { it.type }

    @Test
    fun opensOnAnUnknownCallAndKeepsNoCallerInTheTable() = runBlocking {
        manager.onCallScreened(unknownCall(t0), t0)
        val state = checkNotNull(dao.state)
        assertTrue(state.isOpen && state.callActive)
        assertEquals(t0, state.openedAt)
        assertFalse(state.toString().contains(stranger.h1), "h1 of a phone number is reversible: not in this table")
        assertEquals(stranger.h1, sent.single().toJson().getJSONObject("caller").getString("h1"), "it goes to the encrypted outbox")
        assertEquals(listOf(RiskEventType.RISK_WINDOW_OPENED), types())
    }

    @Test
    fun flaggedCallAlsoQueuesFlaggedNumberCall() = runBlocking {
        manager.onCallScreened(unknownCall(t0, flagged = true), t0)
        assertEquals(listOf(RiskEventType.RISK_WINDOW_OPENED, RiskEventType.FLAGGED_NUMBER_CALL), types())
    }

    @Test
    fun aTrustedCallNeverOpensAWindow() = runBlocking {
        manager.onCallScreened(unknownCall(t0).copy(trusted = true), t0)
        assertNull(dao.state)
        assertTrue(sent.isEmpty())
    }

    @Test
    fun windowIsSixHundredSecondsAfterTheCallEnds() = runBlocking {
        val call = unknownCall(t0)
        manager.onCallScreened(call, t0)
        manager.onCallEnded(call, endedAtMs = t0 + 2 * minute)
        val state = checkNotNull(dao.state)
        assertFalse(state.callActive)
        assertEquals(t0 + 2 * minute + 600_000, state.expiresAt)
        assertTrue(RiskWindowManager.isOpen(state, t0 + 12 * minute - 1))
        assertFalse(RiskWindowManager.isOpen(state, t0 + 12 * minute))
        assertEquals(listOf(RiskEventType.RISK_WINDOW_OPENED, RiskEventType.CALL_ENDED), types())
    }

    @Test
    fun aLongCallKeepsTheWindowOpenWhileItLasts() = runBlocking {
        manager.onCallScreened(unknownCall(t0), t0)
        assertTrue(RiskWindowManager.isOpen(dao.state, t0 + 45 * minute), "call still on: open however long")
    }

    @Test
    fun absoluteCapStopsAStuckWindow() {
        val call = unknownCall(t0)
        assertEquals(t0 + RiskEngine.MAX_WINDOW_MS, RiskWindowManager.expiryAfterCall(call, endedAtMs = t0 + RiskEngine.MAX_WINDOW_MS + minute))
        assertEquals(t0 + 11 * minute, RiskWindowManager.expiryAfterCall(call, endedAtMs = t0 + minute))
    }

    @Test
    fun aSecondCallInsideTheWindowExtendsItWithoutANewOpenedEvent() = runBlocking {
        val first = unknownCall(t0)
        manager.onCallScreened(first, t0)
        manager.onCallEnded(first, t0 + minute)
        manager.onCallScreened(unknownCall(t0 + 5 * minute), t0 + 5 * minute)
        assertEquals(t0, checkNotNull(dao.state).openedAt, "same window")
        assertTrue(checkNotNull(dao.state).callActive)
        assertEquals(1, types().count { it == RiskEventType.RISK_WINDOW_OPENED })
    }

    @Test
    fun aCallAfterTheWindowRanOutOpensANewOne() = runBlocking {
        val first = unknownCall(t0)
        manager.onCallScreened(first, t0)
        manager.onCallEnded(first, t0 + minute)
        val later = t0 + 20 * minute
        manager.onCallScreened(unknownCall(later), later)
        assertEquals(later, checkNotNull(dao.state).openedAt)
        assertEquals(2, types().count { it == RiskEventType.RISK_WINDOW_OPENED })
    }

    @Test
    fun closeIsIdempotentAndQueuesOneClosedEvent() = runBlocking {
        val call = unknownCall(t0, endedAt = t0 + minute)
        manager.onCallScreened(call, t0)
        manager.close(call, t0 + 11 * minute)
        manager.close(call, t0 + 11 * minute + 1)
        assertEquals(RiskWindowState.CLOSED, dao.state)
        assertEquals(1, types().count { it == RiskEventType.RISK_WINDOW_CLOSED })
        assertFalse(RiskWindowManager.isOpen(dao.state, t0 + 11 * minute))
    }

    @Test
    fun callFlickerReopensTheActiveFlagWithoutEvents() = runBlocking {
        val call = unknownCall(t0)
        manager.onCallScreened(call, t0)
        manager.onCallEnded(call, t0 + minute)
        sent.clear()
        manager.onCallActive()
        assertTrue(checkNotNull(dao.state).callActive)
        assertTrue(sent.isEmpty())
    }

    @Test
    fun aRowLeftOpenByAKilledProcessClosesAtTheAbsoluteCap() = runBlocking {
        manager.onCallScreened(unknownCall(t0), t0)
        assertTrue(RiskWindowManager.isOpen(dao.state, t0 + RiskEngine.MAX_WINDOW_MS))
        assertFalse(RiskWindowManager.isOpen(dao.state, t0 + RiskEngine.MAX_WINDOW_MS + 1), "call flag stuck on")
    }

    @Test
    fun aCallAfterAnOrphanedWindowOpensANewOneAndReportsItsFlag() = runBlocking {
        manager.onCallScreened(unknownCall(t0), t0)
        sent.clear()
        val later = t0 + RiskEngine.MAX_WINDOW_MS + 5 * minute
        manager.onCallScreened(unknownCall(later, flagged = true), later)
        assertEquals(listOf(RiskEventType.RISK_WINDOW_OPENED, RiskEventType.FLAGGED_NUMBER_CALL), types())
    }

    @Test
    fun aFlaggedSecondCallInsideAnOpenWindowIsStillReported() = runBlocking {
        manager.onCallScreened(unknownCall(t0), t0)
        sent.clear()
        manager.onCallScreened(unknownCall(t0 + minute, flagged = true), t0 + minute)
        assertEquals(listOf(RiskEventType.FLAGGED_NUMBER_CALL), types())
    }
}
