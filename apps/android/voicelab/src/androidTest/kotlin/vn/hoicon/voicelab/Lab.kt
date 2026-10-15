package vn.hoicon.voicelab

import android.content.Context
import android.os.Build
import android.os.Bundle
import android.os.SystemClock
import android.provider.Settings
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.speech.tts.Voice
import androidx.test.platform.app.InstrumentationRegistry
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import org.junit.Assume.assumeTrue

/** Shared plumbing of the probes (instrumentation arguments, device guard, TTS helpers). */
object Lab {
    val instrumentation get() = InstrumentationRegistry.getInstrumentation()
    val args: Bundle get() = InstrumentationRegistry.getArguments()
    val context: Context get() = instrumentation.targetContext
    val avd: String get() = args.getString("avd") ?: "?"
    val networkOff: Boolean? get() = args.getString("network_off")?.toBooleanStrictOrNull()

    fun runs(default: Int = 20): Int = args.getString("runs")?.toIntOrNull() ?: default

    /** The lab plays audio, changes nothing else, but only ever runs on emulators / test devices (never a stray phone). */
    fun assumeTestDevice() {
        val emulator = Build.HARDWARE in setOf("ranchu", "goldfish")
        val testLab = Settings.System.getString(context.contentResolver, "firebase.test.lab") == "true"
        val explicit = args.getString("testDevice") == "true"
        assumeTrue("only on an emulator, Firebase Test Lab or an explicit -e testDevice true", emulator || testLab || explicit)
    }

    fun nowMs(): Long = SystemClock.elapsedRealtimeNanos() / 1_000_000

    fun sleep(ms: Long) = Thread.sleep(ms)
}

/** A started [TextToSpeech] engine plus how long `onInit` took. */
class TtsEngine private constructor(val tts: TextToSpeech, val initMs: Long, val status: Int) {
    val voice: Voice? = if (status == TextToSpeech.SUCCESS) {
        runCatching { PauseSpeech.pickOfflineVietnamese(tts.voices.orEmpty()) }.getOrNull()
    } else {
        null
    }
    private val marks = ConcurrentHashMap<String, Mark>()

    class Mark {
        val started = CountDownLatch(1)
        val done = CountDownLatch(1)

        @Volatile var startNs = 0L

        @Volatile var beginSynthNs = 0L

        @Volatile var firstAudioNs = 0L

        @Volatile var error: String? = null
    }

    init {
        if (status == TextToSpeech.SUCCESS) {
            voice?.let { tts.voice = it }
            tts.setSpeechRate(PauseSpeech.SPEECH_RATE)
            tts.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                override fun onStart(utteranceId: String?) {
                    marks[utteranceId]?.let { it.startNs = SystemClock.elapsedRealtimeNanos(); it.started.countDown() }
                }

                override fun onBeginSynthesis(utteranceId: String?, sampleRateInHz: Int, audioFormat: Int, channelCount: Int) {
                    marks[utteranceId]?.let { if (it.beginSynthNs == 0L) it.beginSynthNs = SystemClock.elapsedRealtimeNanos() }
                }

                override fun onAudioAvailable(utteranceId: String?, audio: ByteArray?) {
                    marks[utteranceId]?.let { if (it.firstAudioNs == 0L) it.firstAudioNs = SystemClock.elapsedRealtimeNanos() }
                }

                override fun onDone(utteranceId: String?) {
                    marks[utteranceId]?.done?.countDown()
                }

                @Deprecated("Deprecated in Java")
                override fun onError(utteranceId: String?) = onError(utteranceId, -1)

                override fun onError(utteranceId: String?, errorCode: Int) {
                    marks[utteranceId]?.let { it.error = "tts_error_$errorCode"; it.started.countDown(); it.done.countDown() }
                }
            })
        }
    }

    /** Milliseconds from the `speak()` call to each callback; [onStartMs] is the pre-registered decision metric. */
    class SpeakResult(val onStartMs: Long?, val beginSynthMs: Long?, val firstAudioMs: Long?, val error: String?)

    /**
     * Speaks [text] and measures `speak()` → `onStart` (decision metric, same mark as 001's `tts_started`). Also reports
     * `onBeginSynthesis` / first `onAudioAvailable` (null when the engine does not call them) as supplementary numbers:
     * `onStart` can fire when the request is queued, long before sound, so it is only a lower bound (R5).
     * Call [awaitDone] before reading the supplementary numbers of a finished utterance.
     */
    fun speakAndMeasure(id: String, text: String, timeoutMs: Long = 5_000): SpeakResult {
        val mark = Mark().also { marks[id] = it }
        val t0 = SystemClock.elapsedRealtimeNanos()
        val rc = tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, id)
        if (rc != TextToSpeech.SUCCESS) return SpeakResult(null, null, null, "speak_rejected")
        if (!mark.started.await(timeoutMs, TimeUnit.MILLISECONDS)) return SpeakResult(null, null, null, "no_onstart_${timeoutMs}ms")
        mark.error?.let { return SpeakResult(null, null, null, it) }
        fun ms(ns: Long) = if (ns == 0L) null else (ns - t0) / 1_000_000
        // Give the first audio chunk a moment (it normally arrives right after onStart).
        if (mark.firstAudioNs == 0L) Lab.sleep(300)
        return SpeakResult((mark.startNs - t0) / 1_000_000, ms(mark.beginSynthNs), ms(mark.firstAudioNs), null)
    }

    fun awaitDone(id: String, timeoutMs: Long = 15_000): Boolean = marks[id]?.done?.await(timeoutMs, TimeUnit.MILLISECONDS) ?: false

    /** Synthesizes to [file] and waits for completion. Returns null when done, else the error. */
    fun synthesize(id: String, text: String, file: java.io.File, timeoutMs: Long = 20_000): String? {
        val mark = Mark().also { marks[id] = it }
        val rc = tts.synthesizeToFile(text, null, file, id)
        if (rc != TextToSpeech.SUCCESS) return "synth_rejected"
        if (!mark.done.await(timeoutMs, TimeUnit.MILLISECONDS)) return "synth_timeout_${timeoutMs}ms"
        return mark.error
    }

    fun shutdown() {
        tts.stop()
        tts.shutdown()
    }

    companion object {
        /** Creates the engine (Google's, like `Speaker`) and waits for `onInit`; returns null on timeout. */
        fun create(context: Context, engine: String = PauseSpeech.ENGINE, timeoutMs: Long = 15_000): TtsEngine? {
            val ready = CountDownLatch(1)
            var status = TextToSpeech.ERROR
            var initAt = 0L
            val t0 = SystemClock.elapsedRealtimeNanos()
            val tts = TextToSpeech(context, { s -> status = s; initAt = SystemClock.elapsedRealtimeNanos(); ready.countDown() }, engine)
            if (!ready.await(timeoutMs, TimeUnit.MILLISECONDS)) {
                tts.shutdown()
                return null
            }
            return TtsEngine(tts, (initAt - t0) / 1_000_000, status)
        }
    }
}
