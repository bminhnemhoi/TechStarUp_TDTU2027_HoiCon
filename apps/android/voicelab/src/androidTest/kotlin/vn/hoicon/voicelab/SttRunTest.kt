package vn.hoicon.voicelab

import android.content.Intent
import android.media.AudioFormat
import android.os.Bundle
import android.os.ParcelFileDescriptor
import android.os.SystemClock
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import org.json.JSONObject
import org.junit.Assert.fail
import org.junit.Before
import org.junit.Test

/**
 * FR-007: recognizes every `files/stt/<set>/<id>.wav` (16 kHz mono 16-bit, prepared by scripts/voice-lab.sh) with the
 * vi-VN recognizer, the audio coming from a pipe we fill from the file (`EXTRA_AUDIO_SOURCE`, never the microphone). On-device
 * recognizer when available; the default (possibly network) recognizer only with `-e allowNetwork true`, labelled
 * `default_network` ("không dùng cho sản phẩm"). One recognizer per sentence, 15 s timeout.
 *
 * Transcripts go to `files/results/stt-<set>-<avd>.jsonl` (pulled by the script), NOT to logcat: they come from real
 * recordings in the `team` set. Logcat only gets counts and latencies.
 */
class SttRunTest {
    @Before
    fun guard() = Lab.assumeTestDevice()

    @Test
    fun recognizeSet() {
        val ctx = Lab.context
        val set = Lab.args.getString("set") ?: "synthetic"
        val files = File(ctx.filesDir, "stt/$set").listFiles { f -> f.extension == "wav" }?.sortedBy { it.name }.orEmpty()
        if (files.isEmpty()) fail("BLOCKED: no WAV files in files/stt/$set")
        val onDevice = SttSupport.onDeviceViInstalled()
        val allowNetwork = Lab.args.getString("allowNetwork") == "true"
        if (!onDevice && !allowNetwork) {
            fail("BLOCKED: no on-device vi-VN model installed on this device; rerun with --allow-network to measure the default (network) recognizer")
            return
        }
        val label = if (onDevice) "on_device" else "default_network"
        // Real recordings of the team never reach a network recognizer unless the recorders were told (and scripts/voice-lab.sh said so).
        if (label == "default_network" && set == "team" && Lab.args.getString("confirmTeamCloud") != "true") {
            fail("BLOCKED: team recordings would be sent to a network recognizer; needs --confirm-team-audio-to-cloud")
            return
        }
        val out = File(ctx.filesDir, "results").apply { mkdirs() }.resolve("stt-$set-${Lab.avd}.jsonl")
        val lines = mutableListOf<String>()
        var withText = 0
        var errors = 0
        val latencies = mutableListOf<Long>()
        files.forEach { wav ->
            val id = wav.nameWithoutExtension
            val rec = recognizeOne(wav, onDevice)
            if (rec.transcript.isNotBlank()) withText++
            if (rec.error != null) errors++
            if (rec.error == null) latencies += rec.latencyMs
            lines += JSONObject().put("avd", Lab.avd).put("set", set).put("recognizer", label).put("sentence_id", id)
                .put("transcript", rec.transcript).put("confidence", rec.confidence ?: JSONObject.NULL)
                .put("latency_ms", if (rec.error == null) rec.latencyMs else JSONObject.NULL).put("audio_ms", rec.audioMs)
                .put("transcript_source", rec.source).put("error", rec.error ?: JSONObject.NULL).toString()
            Lab.sleep(300)
        }
        out.writeText(lines.joinToString("\n") + "\n")
        VoiceLog.emit("stt_run") {
            put("avd", Lab.avd).put("set", set).put("recognizer", label).put("files", files.size).put("with_text", withText)
            put("errors", errors).put("p50", VoiceLog.percentile(latencies, 50) ?: JSONObject.NULL)
            put("p95", VoiceLog.percentile(latencies, 95) ?: JSONObject.NULL).put("network_off", Lab.networkOff ?: JSONObject.NULL)
        }
    }

    private companion object {
        const val PCM_CHUNK = 3_200 // 100 ms of 16 kHz mono 16-bit
    }

    private class Rec(val transcript: String, val confidence: Float?, val latencyMs: Long, val audioMs: Long, val error: String?, val source: String = "none")

    private fun recognizeOne(wav: File, onDevice: Boolean): Rec {
        val ctx = Lab.context
        val audio = runCatching { Wav.read(wav) }.getOrElse { return Rec("", null, 0, 0, "bad_wav_${it.message}") }
        if (audio.sampleRate != 16_000 || audio.channels != 1 || audio.bitsPerSample != 16) {
            return Rec("", null, 0, audio.durationMs, "bad_format_${audio.sampleRate}hz_${audio.channels}ch_${audio.bitsPerSample}bit")
        }
        // A plain file descriptor is drained in ~1 ms and the on-device recognizer (SODA) then returns an empty lattice,
        // so the audio is fed through a pipe at real-time pace (100 ms chunks), like a microphone would. Headerless PCM
        // + 600 ms of trailing silence so end-pointing can finish; the pipe is closed after that (EOF).
        val (pipeRead, pipeWrite) = ParcelFileDescriptor.createPipe()
        var endWriteNs = 0L
        val writer = Thread {
            runCatching {
                ParcelFileDescriptor.AutoCloseOutputStream(pipeWrite).use { out ->
                    val pcm = audio.pcm + ByteArray(PCM_CHUNK * 6)
                    val begin = SystemClock.elapsedRealtimeNanos()
                    var sent = 0
                    var chunks = 0
                    while (sent < pcm.size) {
                        val n = minOf(PCM_CHUNK, pcm.size - sent)
                        out.write(pcm, sent, n)
                        sent += n
                        chunks++
                        val wait = begin + chunks * 100_000_000L - SystemClock.elapsedRealtimeNanos()
                        if (wait > 0) Thread.sleep(wait / 1_000_000, (wait % 1_000_000).toInt())
                    }
                    endWriteNs = SystemClock.elapsedRealtimeNanos()
                }
            }
        }
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            .putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            .putExtra(RecognizerIntent.EXTRA_LANGUAGE, "vi-VN")
            .putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
            .putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)  // needed: see the empty-final note below
            .putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, onDevice)
            .putExtra(RecognizerIntent.EXTRA_AUDIO_SOURCE, pipeRead)
            .putExtra(RecognizerIntent.EXTRA_AUDIO_SOURCE_CHANNEL_COUNT, 1)
            .putExtra(RecognizerIntent.EXTRA_AUDIO_SOURCE_ENCODING, AudioFormat.ENCODING_PCM_16BIT)
            .putExtra(RecognizerIntent.EXTRA_AUDIO_SOURCE_SAMPLING_RATE, 16_000)

        val done = CountDownLatch(1)
        var transcript = ""
        var lastPartial = ""
        var confidence: Float? = null
        var error: String? = null
        var endNs = 0L
        val listener = object : RecognitionListener {
            override fun onReadyForSpeech(params: Bundle?) = Unit
            override fun onBeginningOfSpeech() = Unit
            override fun onRmsChanged(rmsdB: Float) = Unit
            override fun onBufferReceived(buffer: ByteArray?) = Unit
            override fun onEndOfSpeech() = Unit
            override fun onPartialResults(partialResults: Bundle?) {
                partialResults?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()?.takeIf { it.isNotBlank() }?.let { lastPartial = it }
            }
            override fun onEvent(eventType: Int, params: Bundle?) = Unit
            override fun onError(code: Int) { error = "stt_error_$code"; endNs = SystemClock.elapsedRealtimeNanos(); done.countDown() }
            override fun onResults(results: Bundle?) {
                transcript = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull().orEmpty()
                confidence = results?.getFloatArray(SpeechRecognizer.CONFIDENCE_SCORES)?.firstOrNull()
                endNs = SystemClock.elapsedRealtimeNanos()
                done.countDown()
            }
        }
        var recognizer: SpeechRecognizer? = null
        var t0 = 0L
        Lab.instrumentation.runOnMainSync {
            recognizer = if (onDevice) SpeechRecognizer.createOnDeviceSpeechRecognizer(ctx) else SpeechRecognizer.createSpeechRecognizer(ctx)
            recognizer!!.setRecognitionListener(listener)
            t0 = SystemClock.elapsedRealtimeNanos()
            recognizer!!.startListening(intent)
        }
        writer.start()
        if (!done.await(15, TimeUnit.SECONDS)) {
            error = "timeout"
            endNs = SystemClock.elapsedRealtimeNanos()
        }
        Lab.instrumentation.runOnMainSync { recognizer?.cancel(); recognizer?.destroy() }
        writer.join(5_000)
        pipeRead.close()
        // Observed 15/10/2026 on AVD API 36 (AiAi/SODA on-device vi-VN): the final results bundle is EMPTY while the
        // partial results carry the full text. Use the last non-empty partial then, and label where the text came from.
        var source = "final"
        if (transcript.isBlank() && error == null && lastPartial.isNotBlank()) {
            transcript = lastPartial
            source = "last_partial"
        } else if (transcript.isBlank()) {
            source = "none"
        }
        // latency = end of the audio (last byte written) → final result; negative = the recognizer finished earlier.
        val sinceAudioEnd = if (endWriteNs == 0L) (endNs - t0) / 1_000_000 else (endNs - endWriteNs) / 1_000_000
        return Rec(transcript, confidence, sinceAudioEnd, audio.durationMs, error, source)
    }
}
