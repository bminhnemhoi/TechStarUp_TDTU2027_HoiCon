package vn.hoicon.voicelab

import android.speech.tts.TextToSpeech
import android.speech.tts.Voice

/**
 * Copies of production text/criteria so the lab does not depend on :app. PauseSpeechSourceTest (JVM) fails when
 * they drift from :app.
 */
object PauseSpeech {
    /** Verbatim `pause_speech` of apps/android/app/src/main/res/values/strings.xml (copied 15/10/2026). */
    val SENTENCES = listOf(
        "Đây là trợ lý AI HỏiCon.",
        "Bác ơi, khoan chuyển tiền đã.",
        "Công an, ngân hàng không bao giờ bảo chuyển tiền qua điện thoại.",
        "Bác bấm nút Gọi cho con trước nhé.",
    )

    /** First sentence of the safe pause: the latency-critical one (001 `tts_started`). */
    val FIRST = SENTENCES.first()

    /** Hard words for listeners to rate (FR-005). */
    val HARD_PHRASES = listOf("HỏiCon", "3 giây", "con cháu", "ngân hàng")

    const val ENGINE = "com.google.android.tts"
    const val SPEECH_RATE = 0.9f

    /** Same criteria as `Speaker.pickOfflineVietnamese` in :app (offline vi voice, installed, best quality then latency). */
    fun pickOfflineVietnamese(voices: Set<Voice>): Voice? = voices
        .filter { voice ->
            voice.locale.language == "vi" &&
                !voice.isNetworkConnectionRequired &&
                TextToSpeech.Engine.KEY_FEATURE_NOT_INSTALLED !in voice.features.orEmpty()
        }
        .maxWithOrNull(compareBy<Voice>({ it.quality }, { -it.latency }))
}
