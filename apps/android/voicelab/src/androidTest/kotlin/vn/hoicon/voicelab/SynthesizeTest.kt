package vn.hoicon.voicelab

import java.io.File
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/**
 * FR-005: synthesizes (native rate, via `synthesizeToFile`) the 4 SafePause sentences, the 4 hard phrases and the
 * 20 reference sentences into `files/wav/<id>.wav`. scripts/voice-lab.sh pulls them to the evidence folder (listeners
 * rate them) and converts them to 16 kHz mono for the synthetic STT set. Fictional text only; no personal data.
 */
class SynthesizeTest {
    @Before
    fun guard() = Lab.assumeTestDevice()

    @Test
    fun synthesizeAll() {
        val engine = TtsEngine.create(Lab.context)
        assertNotNull("TextToSpeech did not report onInit within 15 s", engine)
        engine!!
        assertNotNull("no offline vi-VN voice — see docs/EMULATOR.md §1.2", engine.voice)
        val dir = File(Lab.context.filesDir, "wav").apply { mkdirs() }

        val items = PauseSpeech.SENTENCES.mapIndexed { i, t -> "pause_$i" to t } +
            PauseSpeech.HARD_PHRASES.mapIndexed { i, t -> "hard_$i" to t } +
            referenceSentences().map { it.first to it.second }
        var ok = 0
        items.forEach { (id, text) ->
            val file = File(dir, "$id.wav")
            val err = engine.synthesize(id, text, file)
            val size = if (file.exists()) file.length() else 0L
            if (err == null && size > 44) ok++
            VoiceLog.emit("synth") {
                put("id", id).put("avd", Lab.avd).put("bytes", size).put("voice", engine.voice?.name ?: "?")
                put("error", err ?: JSONObject.NULL)
            }
        }
        engine.shutdown()
        VoiceLog.emit("synth") { put("kind", "summary").put("avd", Lab.avd).put("ok", ok).put("total", items.size) }
        assertEquals("some WAV files were not produced", items.size, ok)
        assertTrue(items.size >= 28)
    }

    private fun referenceSentences(): List<Pair<String, String>> {
        val json = JSONObject(Lab.context.assets.open("sentences.v1.json").bufferedReader().use { it.readText() })
        val arr = json.getJSONArray("sentences")
        return (0 until arr.length()).map { arr.getJSONObject(it).let { s -> s.getString("id") to s.getString("text") } }
    }
}
