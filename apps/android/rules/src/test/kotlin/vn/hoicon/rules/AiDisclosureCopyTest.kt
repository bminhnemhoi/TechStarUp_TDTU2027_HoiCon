package vn.hoicon.rules

import java.io.File
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * CLAUDE.md rule 6 (AI disclosure), SEC-12: the first thing said/shown to the elder starts with
 * "Đây là trợ lý AI HỏiCon", and every notification carries the "Trợ lý AI HỏiCon" subtext.
 * Reads app sources as text (this module is pure JVM); paths come from Gradle.
 */
class AiDisclosureCopyTest {
    private val disclosure = "Đây là trợ lý AI HỏiCon"

    private fun file(property: String): String {
        val path = assertNotNull(System.getProperty(property), "$property not set by Gradle")
        return File(path).readText(Charsets.UTF_8)
    }

    private val strings by lazy { file("hoicon.appStrings") }

    private fun string(name: String): String {
        val match = Regex("""<string name="$name">([^<]*)</string>""").find(strings)
        return assertNotNull(match, "string $name missing").groupValues[1]
    }

    private fun stringArray(name: String): List<String> {
        val body = Regex("""<string-array name="$name">(.*?)</string-array>""", RegexOption.DOT_MATCHES_ALL)
            .find(strings)
        assertNotNull(body, "string-array $name missing")
        return Regex("""<item>([^<]*)</item>""").findAll(body.groupValues[1]).map { it.groupValues[1] }.toList()
    }

    @Test
    fun spokenPauseStartsWithDisclosure() {
        val speech = stringArray("pause_speech")
        assertTrue(speech.size >= 2, "pause_speech should be one item per sentence")
        assertTrue(speech.first().startsWith(disclosure), "first spoken sentence: ${speech.first()}")
    }

    @Test
    fun shownTextsStartWithDisclosure() {
        for (name in listOf("pause_disclosure", "hello_ai_disclosure")) {
            assertTrue(string(name).startsWith(disclosure), "$name = ${string(name)}")
        }
    }

    @Test
    fun everyNotificationHasTheAiSubtext() {
        assertEquals("Trợ lý AI HỏiCon", string("notif_ai_subtext"))
        val source = file("hoicon.appNotifications")
        val builders = Regex("""Notification\.Builder\(""").findAll(source).count()
        val subtexts = Regex("""\.setSubText\(context\.getString\(R\.string\.notif_ai_subtext\)\)""").findAll(source).count()
        assertTrue(builders > 0, "no Notification.Builder found — did the file move?")
        assertEquals(builders, subtexts, "each Notification.Builder needs .setSubText(notif_ai_subtext)")
    }

    @Test
    fun assistantNeverCallsItselfConOrChau() {
        // HỏiCon always refers to itself as "HỏiCon" (UX-3); "con" only ever means the elder's child.
        val forbidden = Regex("""\b(con|cháu) (sẽ|xin|nhắc|đang để ý)\b""", RegexOption.IGNORE_CASE)
        val hits = forbidden.findAll(strings).map { it.value }.toList()
        assertTrue(hits.isEmpty(), "assistant speaking as con/cháu: $hits")
    }
}
