package vn.hoicon.sentinel.domain

import org.junit.Test
import vn.hoicon.rules.AppCategory
import vn.hoicon.rules.Decision
import vn.hoicon.rules.RiskLevel
import vn.hoicon.rules.RuleId
import vn.hoicon.sentinel.domain.events.RiskEvent
import vn.hoicon.sentinel.domain.events.RiskEventType
import vn.hoicon.sentinel.domain.rules.LocalRulesEvaluator
import vn.hoicon.sentinel.outbox.sequentialFactory
import vn.hoicon.sentinel.outbox.unknownCall
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

class LocalRulesEvaluatorTest {
    private val sent = ArrayList<RiskEvent>()
    private val evaluator = LocalRulesEvaluator(sequentialFactory()) { sent += it }
    private val t0 = 1_760_000_000_000L
    private val minute = 60_000L
    private val bank = "vn.hoicon.demobank"
    private val anyDesk = "com.anydesk.anydeskandroid"

    @Test
    fun watchedKnowsBanksAndRemoteControlAppsOnly() {
        assertEquals(AppCategory.BANK, evaluator.watched(bank, t0)?.category)
        assertEquals(AppCategory.WALLET, evaluator.watched("com.mservice.momotransfer", t0)?.category)
        assertEquals(AppCategory.OTHER, evaluator.watched(anyDesk, t0)?.category)
        assertNull(evaluator.watched("com.android.chrome", t0))
        assertNull(evaluator.watched("com.anydesk", t0))
    }

    @Test
    fun r1BankAppInTheWindowIsHighAndQueuesABankingEvent() {
        val app = checkNotNull(evaluator.watched(bank, t0 + minute))
        val decision = evaluator.evaluate(unknownCall(t0), app, nowMs = t0 + minute + 120, callActive = true)
        assertEquals(Decision(RiskLevel.HIGH, RuleId.R1), decision)
        val event = sent.single()
        assertEquals(RiskEventType.BANKING_APP_FOREGROUND, event.type)
        assertEquals(RiskLevel.HIGH, event.ruleFloor)
        assertEquals(RuleId.R1, event.ruleId)
        assertEquals(120, event.timing?.detectMs)
        assertEquals(bank, event.app?.packageName)
    }

    @Test
    fun r5RemoteControlAppIsCriticalAndLeavesTheEventToThePause() {
        val app = checkNotNull(evaluator.watched(anyDesk, t0 + minute))
        val decision = evaluator.evaluate(unknownCall(t0), app, nowMs = t0 + minute, callActive = true)
        assertEquals(Decision(RiskLevel.CRITICAL, RuleId.R5), decision)
        assertTrue(decision.pausesUser)
        assertTrue(sent.isEmpty(), "the schema has no event type for it; safe_pause_shown carries it")
    }

    @Test
    fun noCallNoDecisionNoEvent() {
        val app = checkNotNull(evaluator.watched(bank, t0))
        assertEquals(Decision.NONE, evaluator.evaluate(null, app, t0, callActive = false))
        assertTrue(sent.isEmpty())
    }

    @Test
    fun trustedCallerIsNeverPaused() {
        val app = checkNotNull(evaluator.watched(bank, t0 + minute))
        val decision = evaluator.evaluate(unknownCall(t0).copy(trusted = true), app, t0 + minute, callActive = true)
        assertEquals(RiskLevel.NONE, decision.level)
        assertTrue(sent.isEmpty())
    }

    @Test
    fun bankAppAlreadyInFrontWhenTheCallConnectsPauses() {
        val app = checkNotNull(evaluator.watched(bank, t0 - 5 * minute))
        val decision = evaluator.evaluateAlreadyInFront(unknownCall(t0), app, callConnected = true, nowMs = t0 + 3_000, callActive = true)
        assertEquals(RuleId.R1, decision.ruleId)
        assertNotNull(sent.singleOrNull())
    }

    @Test
    fun alreadyInFrontWhileOnlyRingingDoesNothing() {
        val app = checkNotNull(evaluator.watched(anyDesk, t0 - minute))
        val decision = evaluator.evaluateAlreadyInFront(unknownCall(t0), app, callConnected = false, nowMs = t0 + 1_000, callActive = true)
        assertEquals(Decision.NONE, decision)
    }

    @Test
    fun theLocalFloorIsNeverLowered() {
        val app = checkNotNull(evaluator.watched("com.android.vending".let { bank }, t0 + minute))
        val decision = evaluator.evaluate(unknownCall(t0), app, t0 + minute, callActive = true, floor = RiskLevel.CRITICAL)
        assertEquals(RiskLevel.CRITICAL, decision.level)
    }
}
