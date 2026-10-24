package vn.hoicon.sentinel.ui

import org.junit.Test
import kotlin.test.assertEquals

/** E4 list (Spec 011 T022b): the button sits after the first paragraph, so the text is cut there and nothing is dropped. */
class PermissionLeadSplitTest {
    @Test
    fun cutsAfterTheFirstParagraph() {
        assertEquals("Một." to "Hai.\n\nBa.", splitLead("Một.\n\nHai.\n\nBa."))
    }

    @Test
    fun aSingleParagraphHasNoRest() {
        assertEquals("Một." to "", splitLead("Một."))
    }
}
