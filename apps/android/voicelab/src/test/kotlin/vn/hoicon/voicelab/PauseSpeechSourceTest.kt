package vn.hoicon.voicelab

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** Guards the copies in [PauseSpeech] against drifting from :app (JVM test; working dir = apps/android/voicelab). */
class PauseSpeechSourceTest {
    private val app = File("../app/src/main")

    @Test
    fun sentencesMatchProductionStrings() {
        val xml = File(app, "res/values/strings.xml").readText()
        val block = Regex("""<string-array name="pause_speech">(.*?)</string-array>""", RegexOption.DOT_MATCHES_ALL)
            .find(xml)?.groupValues?.get(1)
        assertTrue("pause_speech not found in :app strings.xml", block != null)
        val items = Regex("""<item>(.*?)</item>""").findAll(block.orEmpty()).map { it.groupValues[1] }.toList()
        assertEquals(items, PauseSpeech.SENTENCES)
    }

    @Test
    fun voiceCriteriaMatchSpeaker() {
        val speaker = File(app, "java/vn/hoicon/sentinel/pause/Speaker.kt").readText()
        listOf(
            """voice.locale.language == "vi"""",
            "!voice.isNetworkConnectionRequired",
            "TextToSpeech.Engine.KEY_FEATURE_NOT_INSTALLED !in voice.features.orEmpty()",
            "compareBy<Voice>({ it.quality }, { -it.latency })",
            """PREFERRED_ENGINE = "${PauseSpeech.ENGINE}"""",
            "SPEECH_RATE = ${PauseSpeech.SPEECH_RATE}f",
        ).forEach { assertTrue("Speaker.kt no longer contains: $it", speaker.contains(it)) }
    }
}
