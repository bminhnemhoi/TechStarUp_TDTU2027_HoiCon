package vn.hoicon.sentinel.ui

import java.io.File
import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

/**
 * E7 remote-control variant (Spec 010 T029): the body says what the app does, the two steps are a numbered list of
 * their own, and the spoken text (unchanged) still names both steps. Words live in strings.xml, so the test reads it.
 */
class PauseRemoteStringsTest {
    private val xml = File(checkNotNull(System.getProperty("hoicon.appStrings"))).readText(Charsets.UTF_8)

    private fun string(name: String) = Regex("""<string name="$name">(.*?)</string>""", RegexOption.DOT_MATCHES_ALL).find(xml)?.groupValues?.get(1)

    private fun items(name: String) = Regex("""<string-array name="$name">(.*?)</string-array>""", RegexOption.DOT_MATCHES_ALL)
        .find(xml)?.groupValues?.get(1)?.let { block -> Regex("""<item>(.*?)</item>""").findAll(block).map { it.groupValues[1] }.toList() }

    @Test
    fun bodyHoldsNoStepsAndTheTwoStepsAreTheirOwnList() {
        val body = checkNotNull(string("pause_body_remote"))
        assertEquals(
            "Ứng dụng này cho người khác nhìn thấy và điều khiển điện thoại của bác, kể cả ứng dụng ngân hàng. " +
                "Công an, ngân hàng không bao giờ bảo bác cài ứng dụng này.",
            body,
        )
        assertFalse("Hỏi con" in body || "Cúp máy" in body, "the steps moved out of the body")
        val steps = checkNotNull(items("pause_steps_remote")) { "pause_steps_remote missing" }
        assertEquals(2, steps.size)
        assertTrue(steps[0].startsWith("Cúp máy"), steps[0])
        assertTrue("AnyDesk" in steps[0] && "TeamViewer" in steps[0], steps[0])
        assertEquals("Bấm Hỏi con.", steps[1])
    }

    @Test
    fun theSpokenTextStillNamesBothSteps() {
        val spoken = checkNotNull(items("pause_speech_remote")).joinToString(" ")
        assertTrue("cúp máy" in spoken && "Hỏi con" in spoken, spoken)
    }
}
