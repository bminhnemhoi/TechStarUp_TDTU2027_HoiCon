package vn.hoicon.sentinel.pause

import android.content.ActivityNotFoundException
import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

/**
 * Spec 010 T032: "Hỏi con" (E7) opens an EMPTY dialer (no number, so no contacts access: CLAUDE.md rule 3), fires exactly one
 * `ask_child_pressed`, and never throws when the phone has no dialer.
 */
class DialerTest {
    @Test
    fun theDialerIsOpenedWithTheDialActionAndNothingElse() {
        val started = mutableListOf<String>()
        assertTrue(Dialer.open { action -> started += action })
        assertEquals(listOf("android.intent.action.DIAL"), started, "ACTION_DIAL only: the starter is given no number and no data")
    }

    @Test
    fun aPhoneWithoutADialerReturnsFalseInsteadOfThrowing() {
        assertFalse(Dialer.open(onMissing = {}) { throw ActivityNotFoundException("no dialer") }) // the default logs through android.util.Log, which a JVM test cannot call
    }

    @Test
    fun pressingAskChildRecordsOneEventAndOpensTheDialerOnce() {
        var events = 0
        var dials = 0
        val ask = AskChild(record = { events++ }, dial = { dials++; true })
        assertTrue(ask.press())
        assertEquals(1, events)
        assertEquals(1, dials)
    }

    @Test
    fun theFamilyIsToldEvenWhenTheDialerDoesNotOpen() {
        var events = 0
        val ask = AskChild(record = { events++ }, dial = { false })
        assertFalse(ask.press())
        assertEquals(1, events, "the event is recorded before the dialer is tried, so a missing dialer never hides the press")
    }
}
