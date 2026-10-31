package vn.hoicon.sentinel.ui

import org.junit.Test
import kotlin.test.assertEquals

/** Spec 024 T022 (FR-005, CLAUDE.md rule 15): E8 has at most two main actions; "Không rõ" is the quiet text button, and the codes sent to the server do not change. */
class ElderAnswerLayoutTest {
    @Test
    fun yesAndNoAreTheTwoMainButtonsAndUnsureIsTheQuietOne() {
        val layout = elderAnswerLayout(listOf("yes", "no", "unsure"))
        assertEquals(listOf("yes", "no"), layout.main)
        assertEquals("unsure", layout.quiet)
    }

    @Test
    fun theOrderTheServerSendsDoesNotChangeWhichIsWhich() {
        val layout = elderAnswerLayout(listOf("unsure", "no", "yes"))
        assertEquals(listOf("yes", "no"), layout.main)
        assertEquals("unsure", layout.quiet)
    }

    @Test
    fun aQuestionWithoutAnUnsureAnswerHasNoQuietButton() {
        val layout = elderAnswerLayout(listOf("yes", "no"))
        assertEquals(listOf("yes", "no"), layout.main)
        assertEquals(null, layout.quiet)
    }

    @Test
    fun anAnswerTheScreenDoesNotKnowIsNeverShown() {
        assertEquals(listOf("yes"), elderAnswerLayout(listOf("yes", "maybe")).main)
    }
}
