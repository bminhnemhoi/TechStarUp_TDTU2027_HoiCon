package vn.hoicon.sentinel.ui

import java.io.File
import vn.hoicon.sentinel.pause.PauseKind
import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue

/** E7 wording and order decided in Spec 010 T030 (turn 9): the button says what it does, the scroll hint names no direction, large text leads with the steps. */
class PauseLayoutStringsTest {
    private val xml = File(checkNotNull(System.getProperty("hoicon.appStrings"))).readText(Charsets.UTF_8)

    private fun string(name: String) = Regex("""<string name="$name">(.*?)</string>""", RegexOption.DOT_MATCHES_ALL).find(xml)?.groupValues?.get(1)

    @Test
    fun theCancelButtonOfBothVariantsSaysItGoesHome() {
        assertEquals("Về màn hình chính", string("pause_cancel"))
        assertNull(string("pause_cancel_bank"), "\"Hủy giao dịch\" promised more than the button does")
        assertNull(string("pause_cancel_sub"))
        assertFalse("Hủy giao dịch" in xml)
    }

    @Test
    fun theScrollHintNamesNoDirectionOfTheFinger() {
        assertEquals("Còn nữa ở dưới ↓", string("onboarding_scroll_hint"))
    }

    @Test
    fun onlyTheRemoteControlVariantAtLargeTextPutsTheStepsFirst() {
        assertTrue(pauseStepsFirst(PauseKind.REMOTE_CONTROL, large = true))
        assertFalse(pauseStepsFirst(PauseKind.REMOTE_CONTROL, large = false))
        assertFalse(pauseStepsFirst(PauseKind.FINANCIAL, large = true))
    }
}
