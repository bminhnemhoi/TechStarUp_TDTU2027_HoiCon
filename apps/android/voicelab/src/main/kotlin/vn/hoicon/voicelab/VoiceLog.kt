package vn.hoicon.voicelab

import android.os.Build
import android.util.Log
import kotlin.math.ceil
import org.json.JSONArray
import org.json.JSONObject

/** One JSON object per logcat line, tag [TAG]; scripts/voice-lab.sh collects them into the evidence folder. */
object VoiceLog {
    const val TAG = "HC_VOICE"

    fun emit(probe: String, fill: JSONObject.() -> Unit = {}) {
        val line = JSONObject()
            .put("probe", probe)
            .put("api", Build.VERSION.SDK_INT)
            .put("hardware", Build.HARDWARE)
            .apply(fill)
        Log.i(TAG, line.toString())
    }

    /** Nearest-rank percentile (same definition as scripts/emu-scenario.py and scripts/voice-wer.py). */
    fun percentile(values: List<Long>, pct: Int): Long? {
        if (values.isEmpty()) return null
        val sorted = values.sorted()
        return sorted[maxOf(ceil(pct / 100.0 * sorted.size).toInt() - 1, 0)]
    }

    fun JSONObject.putStats(values: List<Long>): JSONObject = this
        .put("n", values.size)
        .put("values_ms", JSONArray(values))
        .put("p50", percentile(values, 50) ?: JSONObject.NULL)
        .put("p95", percentile(values, 95) ?: JSONObject.NULL)
}
