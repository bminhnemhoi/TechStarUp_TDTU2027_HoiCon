package vn.hoicon.voicelab

import android.media.AudioAttributes
import android.media.MediaPlayer
import android.os.SystemClock
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Before
import org.junit.Test
import vn.hoicon.voicelab.VoiceLog.putStats

/**
 * FR-004 (SC-003): latency of playing a ready-made clip with `MediaPlayer`, to compare with TTS (FR-003).
 * cold = new player per run (setDataSource + prepare + start); warm = one prepared player, rewound, `start()` only.
 * Time is taken from the call that begins playing (cold: the constructor; warm: `start()`) to the first sign that audio
 * moves: `ts` = `getTimestamp()` returns a running media clock, `pos` = `currentPosition > 0` (1 ms resolution; R4).
 */
class ClipLatencyTest {
    @Before
    fun guard() = Lab.assumeTestDevice()

    @Test
    fun coldAndWarm() {
        val runs = Lab.runs()
        emit("cold", runs, measure(runs, warm = false))
        emit("warm", runs, measure(runs, warm = true))
    }

    private class Run(val tsMs: Long?, val posMs: Long?, val prepareMs: Long?)

    private fun newPlayer(): MediaPlayer = MediaPlayer().apply {
        setAudioAttributes(AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA).setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build())
        Lab.context.resources.openRawResourceFd(R.raw.clip_pause_0).use { setDataSource(it.fileDescriptor, it.startOffset, it.length) }
    }

    /** Polls for the first audio movement after `start()`; returns (tsMs, posMs) relative to [t0] or nulls on timeout. */
    private fun awaitFirstFrame(mp: MediaPlayer, t0: Long): Pair<Long?, Long?> {
        var ts: Long? = null
        var pos: Long? = null
        val deadline = SystemClock.elapsedRealtimeNanos() + 3_000_000_000L
        while (SystemClock.elapsedRealtimeNanos() < deadline && (ts == null || pos == null)) {
            val now = SystemClock.elapsedRealtimeNanos()
            if (ts == null && runCatching { mp.timestamp }.getOrNull()?.let { it.mediaClockRate > 0f } == true) ts = (now - t0) / 1_000_000
            if (pos == null && runCatching { mp.currentPosition }.getOrDefault(0) > 0) pos = (now - t0) / 1_000_000
            Thread.sleep(2)
        }
        return ts to pos
    }

    private fun measure(runs: Int, warm: Boolean): List<Run> {
        val results = mutableListOf<Run>()
        var shared: MediaPlayer? = null
        if (warm) {
            shared = newPlayer().apply { prepare() }
            // One discarded pass so decoder and audio track are really warm.
            shared.start(); awaitFirstFrame(shared, SystemClock.elapsedRealtimeNanos()); shared.pause(); shared.seekTo(0); Thread.sleep(500)
        }
        repeat(runs) {
            Thread.sleep(1_000)
            if (warm) {
                val mp = shared!!
                val t0 = SystemClock.elapsedRealtimeNanos()
                mp.start()
                val (ts, pos) = awaitFirstFrame(mp, t0)
                results += Run(ts, pos, null)
                mp.pause(); mp.seekTo(0); Thread.sleep(300)
            } else {
                val t0 = SystemClock.elapsedRealtimeNanos()
                val mp = newPlayer()
                mp.prepare()
                val prepared = (SystemClock.elapsedRealtimeNanos() - t0) / 1_000_000
                mp.start()
                val (ts, pos) = awaitFirstFrame(mp, t0)
                results += Run(ts, pos, prepared)
                mp.release()
            }
        }
        shared?.release()
        return results
    }

    private fun emit(mode: String, runs: Int, results: List<Run>) = VoiceLog.emit("clip_latency") {
        put("avd", Lab.avd).put("mode", mode).put("runs_requested", runs).put("network_off", Lab.networkOff ?: JSONObject.NULL)
        val ts = results.mapNotNull { it.tsMs }
        val pos = results.mapNotNull { it.posMs }
        put("ts", JSONObject().putStats(ts))
        put("pos", JSONObject().putStats(pos))
        put("prepare_ms", JSONArray(results.mapNotNull { it.prepareMs }))
        put("timeouts", results.count { it.tsMs == null && it.posMs == null })
    }
}
