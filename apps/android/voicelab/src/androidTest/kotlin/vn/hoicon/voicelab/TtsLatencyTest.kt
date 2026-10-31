package vn.hoicon.voicelab

import org.junit.Before
import org.junit.Test
import vn.hoicon.voicelab.VoiceLog.putStats

/**
 * FR-003 (SC-002): `speak()` → `onStart` of the first SafePause sentence, network off (the script checks it).
 * cold = a brand-new TextToSpeech per run (≈ the first risk window after boot / process start; `init_ms` recorded too);
 * warm = one engine, one discarded warm-up utterance, then runs 1 s apart. Same mark as 001's `tts_started`, which
 * `onStart` only approximates ("soon before audio is played", javadoc) — noted in the report.
 */
class TtsLatencyTest {
    @Before
    fun guard() = Lab.assumeTestDevice()

    @Test
    fun coldAndWarm() {
        val runs = Lab.runs()
        cold(runs)
        warm(runs)
    }

    private fun cold(runs: Int) {
        val latencies = mutableListOf<Long>()
        val inits = mutableListOf<Long>()
        val errors = mutableListOf<String>()
        val audio = mutableListOf<Long>()
        repeat(runs) { i ->
            val engine = TtsEngine.create(Lab.context)
            if (engine == null || engine.voice == null) {
                errors += if (engine == null) "init_timeout" else "no_offline_voice"
                engine?.shutdown()
                return@repeat
            }
            inits += engine.initMs
            val r = engine.speakAndMeasure("cold-$i", PauseSpeech.FIRST)
            if (r.onStartMs != null) latencies += r.onStartMs else errors += r.error ?: "unknown"
            r.firstAudioMs?.let { audio += it }
            engine.shutdown()
            Lab.sleep(500)
        }
        emit("cold", runs, latencies, inits, errors, audio)
    }

    private fun warm(runs: Int) {
        val engine = TtsEngine.create(Lab.context)
        val latencies = mutableListOf<Long>()
        val errors = mutableListOf<String>()
        val audio = mutableListOf<Long>()
        if (engine == null || engine.voice == null) {
            errors += if (engine == null) "init_timeout" else "no_offline_voice"
            emit("warm", runs, latencies, emptyList(), errors, audio)
            engine?.shutdown()
            return
        }
        engine.speakAndMeasure("warmup", PauseSpeech.FIRST)
        engine.awaitDone("warmup")
        repeat(runs) { i ->
            Lab.sleep(1_000)
            val r = engine.speakAndMeasure("warm-$i", PauseSpeech.FIRST)
            if (r.onStartMs != null) latencies += r.onStartMs else errors += r.error ?: "unknown"
            r.firstAudioMs?.let { audio += it }
            engine.awaitDone("warm-$i")
        }
        emit("warm", runs, latencies, listOf(engine.initMs), errors, audio)
        engine.shutdown()
    }

    private fun emit(mode: String, runs: Int, latencies: List<Long>, inits: List<Long>, errors: List<String>, audio: List<Long> = emptyList()) =
        VoiceLog.emit("tts_latency") {
            put("avd", Lab.avd).put("mode", mode).put("runs_requested", runs).put("network_off", Lab.networkOff ?: org.json.JSONObject.NULL)
            putStats(latencies)
            put("init_ms", org.json.JSONArray(inits)).put("errors", org.json.JSONArray(errors))
            put("first_audio_ms", org.json.JSONArray(audio)).put("first_audio_p50", VoiceLog.percentile(audio, 50) ?: org.json.JSONObject.NULL)
            put("first_audio_p95", VoiceLog.percentile(audio, 95) ?: org.json.JSONObject.NULL)
        }
}
