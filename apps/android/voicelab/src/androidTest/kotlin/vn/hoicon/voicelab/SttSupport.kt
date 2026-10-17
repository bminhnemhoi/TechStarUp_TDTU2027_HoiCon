package vn.hoicon.voicelab

import android.content.Intent
import android.speech.RecognitionSupport
import android.speech.RecognitionSupportCallback
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executor
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/** `checkRecognitionSupport` for vi-VN, shared by the probe and the run test. */
object SttSupport {
    fun viIntent(): Intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
        .putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
        .putExtra(RecognizerIntent.EXTRA_LANGUAGE, "vi-VN")

    fun installedVi(s: RecognitionSupport?): Boolean = s?.installedOnDeviceLanguages?.any { it.startsWith("vi") } == true

    /** True when the on-device recognizer exists AND has a vi-VN model installed (a service alone is not enough: API 34 AVD). */
    fun onDeviceViInstalled(): Boolean {
        val ctx = Lab.context
        if (!SpeechRecognizer.isOnDeviceRecognitionAvailable(ctx)) return false
        var rec: SpeechRecognizer? = null
        Lab.instrumentation.runOnMainSync { rec = runCatching { SpeechRecognizer.createOnDeviceSpeechRecognizer(ctx) }.getOrNull() }
        val recognizer = rec ?: return false
        val executor = Executors.newSingleThreadExecutor()
        val installed = installedVi(query(recognizer, executor).first)
        executor.shutdown()
        Lab.instrumentation.runOnMainSync { recognizer.destroy() }
        return installed
    }

    /** Returns the support result or an error string (e.g. UnsupportedOperation / timeout / error code). */
    fun query(recognizer: SpeechRecognizer, executor: Executor): Pair<RecognitionSupport?, String?> {
        val latch = CountDownLatch(1)
        var result: RecognitionSupport? = null
        var error: String? = null
        Lab.instrumentation.runOnMainSync {
            try {
                recognizer.checkRecognitionSupport(viIntent(), executor, object : RecognitionSupportCallback {
                    override fun onSupportResult(recognitionSupport: RecognitionSupport) { result = recognitionSupport; latch.countDown() }
                    override fun onError(error2: Int) { error = "error_$error2"; latch.countDown() }
                })
            } catch (e: RuntimeException) {
                error = e.javaClass.simpleName
                latch.countDown()
            }
        }
        if (!latch.await(15, TimeUnit.SECONDS) && error == null) error = "timeout"
        return result to error
    }
}
