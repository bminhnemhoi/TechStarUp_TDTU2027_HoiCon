package vn.hoicon.sentinel.pause

import android.content.Context
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.speech.tts.Voice
import vn.hoicon.sentinel.sensing.HcSpikeLog
import vn.hoicon.sentinel.sensing.HcTiming

/**
 * On-device Vietnamese TTS for the safe pause (no network on the critical path). Process-wide so the risk window
 * can warm the engine up before SafePause needs it. Main thread only.
 *
 * SEC-8: prefers Google's engine and only ever uses a vi-VN voice that works offline; without one it stays silent
 * and marks `tts_unavailable` (garbled or network speech is worse than none; pre-recorded audio comes in P2-05).
 * UX-4: one utterance per sentence, rate 0.9, 350 ms of silence between sentences.
 */
object Speaker {
    private const val PREFERRED_ENGINE = "com.google.android.tts"
    private const val SPEECH_RATE = 0.9f
    private const val PAUSE_BETWEEN_SENTENCES_MS = 350L
    private const val FIRST_UTTERANCE = "say-0"

    private var tts: TextToSpeech? = null
    private var ready = false
    private var offlineVoice: Voice? = null
    private var pending: List<String>? = null

    fun warmUp(context: Context) {
        if (tts != null) return
        val startedAt = System.currentTimeMillis()
        tts = TextToSpeech(context.applicationContext, { status -> onInit(status, startedAt) }, PREFERRED_ENGINE)
    }

    fun speak(context: Context, sentences: List<String>) {
        warmUp(context)
        if (ready) speakNow(sentences) else pending = sentences
    }

    fun stop() {
        pending = null
        tts?.stop()
    }

    fun shutdown() {
        tts?.shutdown()
        tts = null
        ready = false
        offlineVoice = null
        pending = null
    }

    private fun onInit(status: Int, startedAt: Long) {
        val engine = tts ?: return
        if (status != TextToSpeech.SUCCESS) {
            HcSpikeLog.w("tts init failed status=$status")
            return
        }
        offlineVoice = runCatching { pickOfflineVietnamese(engine.voices.orEmpty()) }.getOrNull()
        offlineVoice?.let { engine.voice = it }
        engine.setSpeechRate(SPEECH_RATE)
        HcSpikeLog.i(
            "tts ready in ${System.currentTimeMillis() - startedAt} ms engine=${engine.defaultEngine} " +
                "vi-VN offline voice=${offlineVoice?.name ?: "MISSING"}",
        )
        engine.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
            override fun onStart(utteranceId: String?) {
                if (utteranceId == FIRST_UTTERANCE) HcTiming.mark("tts_started")
            }

            override fun onDone(utteranceId: String?) = Unit

            @Deprecated("Deprecated in Java")
            override fun onError(utteranceId: String?) = HcSpikeLog.w("tts error")
        })
        ready = true
        pending?.let {
            pending = null
            speakNow(it)
        }
    }

    private fun pickOfflineVietnamese(voices: Set<Voice>): Voice? = voices
        .filter { voice ->
            voice.locale.language == "vi" &&
                !voice.isNetworkConnectionRequired &&
                TextToSpeech.Engine.KEY_FEATURE_NOT_INSTALLED !in voice.features.orEmpty()
        }
        .maxWithOrNull(compareBy<Voice>({ it.quality }, { -it.latency }))

    private fun speakNow(sentences: List<String>) {
        val engine = tts ?: return
        if (offlineVoice == null) {
            HcTiming.mark("tts_unavailable")
            return
        }
        sentences.forEachIndexed { index, sentence ->
            if (index > 0) engine.playSilentUtterance(PAUSE_BETWEEN_SENTENCES_MS, TextToSpeech.QUEUE_ADD, "gap-$index")
            val mode = if (index == 0) TextToSpeech.QUEUE_FLUSH else TextToSpeech.QUEUE_ADD
            engine.speak(sentence, mode, null, "say-$index")
        }
    }
}
