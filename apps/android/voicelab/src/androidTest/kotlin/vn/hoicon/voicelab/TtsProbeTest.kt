package vn.hoicon.voicelab

import android.speech.tts.TextToSpeech
import java.util.Locale
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertNotNull
import org.junit.Before
import org.junit.Test

/**
 * FR-002: which Vietnamese TTS voices exist (network off), which one `Speaker.pickOfflineVietnamese` would choose,
 * and whether it really speaks ("no voice" vs "broken voice": 001 saw a listed voice whose pipeline failed to load).
 * One JSON line per fact on logcat tag HC_VOICE (probe=tts).
 */
class TtsProbeTest {
    @Before
    fun guard() = Lab.assumeTestDevice()

    @Test
    fun probeVietnameseVoices() {
        val engine = TtsEngine.create(Lab.context)
        assertNotNull("TextToSpeech did not report onInit within 15 s", engine)
        engine!!
        val tts = engine.tts
        val voices = if (engine.status == TextToSpeech.SUCCESS) tts.voices.orEmpty().filter { it.locale.language == "vi" } else emptyList()

        VoiceLog.emit("tts") {
            put("kind", "engine").put("avd", Lab.avd).put("network_off", Lab.networkOff ?: JSONObject.NULL)
            put("init_status", engine.status).put("init_ms", engine.initMs)
            put("default_engine", tts.defaultEngine)
            put("engines", JSONArray(tts.engines.map { "${it.name}" }))
            put("language_available_vi_VN", tts.isLanguageAvailable(Locale("vi", "VN")))
        }
        voices.sortedBy { it.name }.forEach { v ->
            VoiceLog.emit("tts") {
                put("kind", "voice").put("avd", Lab.avd).put("name", v.name).put("locale", v.locale.toLanguageTag())
                put("network_required", v.isNetworkConnectionRequired).put("quality", v.quality).put("latency", v.latency)
                put("not_installed", TextToSpeech.Engine.KEY_FEATURE_NOT_INSTALLED in v.features.orEmpty())
                put("features", JSONArray(v.features.orEmpty().toList()))
            }
        }

        val picked = engine.voice
        var verdict = "no_voice"
        var onStartMs: Long? = null
        var error: String? = null
        if (picked != null) {
            val r = engine.speakAndMeasure("probe-0", PauseSpeech.FIRST)
            onStartMs = r.onStartMs
            error = r.error
            verdict = if (r.onStartMs != null) "ok" else "broken_voice"
            engine.awaitDone("probe-0")
        }
        VoiceLog.emit("tts") {
            put("kind", "verdict").put("avd", Lab.avd).put("network_off", Lab.networkOff ?: JSONObject.NULL)
            put("vi_voices", voices.size).put("picked", picked?.name ?: JSONObject.NULL)
            put("verdict", verdict).put("first_speak_onstart_ms", onStartMs ?: JSONObject.NULL).put("error", error ?: JSONObject.NULL)
        }
        engine.shutdown()
    }
}
