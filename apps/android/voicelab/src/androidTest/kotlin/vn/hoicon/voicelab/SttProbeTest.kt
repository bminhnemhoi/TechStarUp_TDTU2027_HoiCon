package vn.hoicon.voicelab

import android.content.Intent
import android.os.Build
import android.speech.RecognitionService
import android.speech.RecognitionSupport
import android.speech.RecognitionSupportCallback
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Before
import org.junit.Test

/**
 * FR-006: does this device have recognition for vi-VN, and on the device itself? Which recognition services exist,
 * what `checkRecognitionSupport` says (installed / pending / supported on device / online), and what happens when we
 * ask once for the model (`triggerModelDownload`, waits up to 120 s, never loops). Nothing is recognized here.
 */
class SttProbeTest {
    private val executor = Executors.newSingleThreadExecutor()

    @Before
    fun guard() = Lab.assumeTestDevice()

    private fun viIntent() = SttSupport.viIntent()

    @Test
    fun probeRecognition() {
        val ctx = Lab.context
        val services = ctx.packageManager.queryIntentServices(Intent(RecognitionService.SERVICE_INTERFACE), 0)
            .map { "${it.serviceInfo.packageName}/${it.serviceInfo.name}" }
        val onDevice = SpeechRecognizer.isOnDeviceRecognitionAvailable(ctx)
        VoiceLog.emit("stt") {
            put("kind", "availability").put("avd", Lab.avd).put("network_off", Lab.networkOff ?: JSONObject.NULL)
            put("recognition_available", SpeechRecognizer.isRecognitionAvailable(ctx)).put("on_device_available", onDevice)
            put("services", JSONArray(services)).put("sdk", Build.VERSION.SDK_INT)
        }
        probeSupport("default", create = { SpeechRecognizer.createSpeechRecognizer(ctx) })
        if (onDevice) probeSupport("on_device", create = { SpeechRecognizer.createOnDeviceSpeechRecognizer(ctx) })
        executor.shutdown()
    }

    private fun probeSupport(kind: String, create: () -> SpeechRecognizer) {
        var rec: SpeechRecognizer? = null
        Lab.instrumentation.runOnMainSync { rec = runCatching(create).getOrNull() }
        val recognizer = rec
        if (recognizer == null) {
            VoiceLog.emit("stt") { put("kind", "support").put("recognizer", kind).put("avd", Lab.avd).put("error", "create_failed") }
            return
        }
        var first = SttSupport.query(recognizer, executor)
        emitSupport(kind, "initial", first)
        if (first.second == null && !installed(first.first)) {
            Lab.instrumentation.runOnMainSync {
                runCatching { recognizer.triggerModelDownload(viIntent()) }.onFailure {
                    VoiceLog.emit("stt") { put("kind", "download").put("recognizer", kind).put("error", it.javaClass.simpleName) }
                }
            }
            val deadline = Lab.nowMs() + 120_000
            var waitedMs = 0L
            while (Lab.nowMs() < deadline && !installed(first.first)) {
                Lab.sleep(5_000)
                waitedMs += 5_000
                first = SttSupport.query(recognizer, executor)
            }
            VoiceLog.emit("stt") { put("kind", "download").put("recognizer", kind).put("avd", Lab.avd).put("installed_after", installed(first.first)).put("waited_ms", waitedMs) }
            emitSupport(kind, "after_download", first)
        }
        Lab.instrumentation.runOnMainSync { recognizer.destroy() }
    }

    private fun installed(s: RecognitionSupport?): Boolean = SttSupport.installedVi(s)

    private fun emitSupport(kind: String, stage: String, r: Pair<RecognitionSupport?, String?>) = VoiceLog.emit("stt") {
        val s = r.first
        put("kind", "support").put("recognizer", kind).put("stage", stage).put("avd", Lab.avd)
        put("error", r.second ?: JSONObject.NULL)
        fun vi(l: List<String>?) = JSONArray(l.orEmpty().filter { it.startsWith("vi") })
        put("installed_vi", vi(s?.installedOnDeviceLanguages)).put("pending_vi", vi(s?.pendingOnDeviceLanguages))
        put("supported_on_device_vi", vi(s?.supportedOnDeviceLanguages)).put("online_vi", vi(s?.onlineLanguages))
        put("installed_count", s?.installedOnDeviceLanguages?.size ?: JSONObject.NULL)
        put("supported_on_device_count", s?.supportedOnDeviceLanguages?.size ?: JSONObject.NULL)
        put("online_count", s?.onlineLanguages?.size ?: JSONObject.NULL)
    }
}
