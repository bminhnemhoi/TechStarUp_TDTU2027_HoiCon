package vn.hoicon.latency

import android.os.Build
import android.os.Bundle
import android.os.ParcelFileDescriptor
import android.os.SystemClock
import android.util.Log
import androidx.test.platform.app.InstrumentationRegistry
import java.io.File
import kotlin.math.ceil
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/**
 * Real-device latency for ADR-007 (P1-S2): `app_foreground → pause_shown` on the production path, minus Telecom.
 * The call is simulated by the debug-only ScenarioReceiver (no SIM in Firebase Test Lab); from there on it is the
 * shipping code: risk window (FGS) → UsageStats tick → RiskEngine → SafePauseActivity first frame.
 *
 * Same marks and nearest-rank percentiles as scripts/emu-scenario.py. "cold" = `am force-stop` before each run
 * (process started by the broadcast, SafePause is its first UI); "warm" = process alive, as after a real call.
 *
 * Needs the debug build of :app (HC_TIMING marks) and :demobank installed. Arguments (`-e`): runs (default 10),
 * compile (default "speed": AOT like a Play install; "none" keeps the APK as installed).
 * Output: logcat tag HC_LATENCY + latency.json in this APK's external files dir (FTL: --directories-to-pull).
 */
class SafePauseLatencyTest {
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val args: Bundle = InstrumentationRegistry.getArguments()
    private val runs = args.getString("runs")?.toIntOrNull() ?: 10

    private fun sh(command: String): String =
        ParcelFileDescriptor.AutoCloseInputStream(instrumentation.uiAutomation.executeShellCommand(command))
            .bufferedReader()
            .use { it.readText() }

    @Before
    fun grantAndWake() {
        assertTrue("install the debug :demobank APK", sh("pm path $DEMOBANK").contains("package:"))
        sh("appops set $SENTINEL SYSTEM_ALERT_WINDOW allow")
        sh("appops set $SENTINEL GET_USAGE_STATS allow")
        if (Build.VERSION.SDK_INT >= 33) sh("pm grant $SENTINEL android.permission.POST_NOTIFICATIONS")
        // Android 15+: the FGS can't start from the screening callback without this (ADR-007).
        sh("dumpsys deviceidle whitelist +$SENTINEL")
        if ((args.getString("compile") ?: "speed") == "speed") sh("cmd package compile -m speed -f $SENTINEL")
        sh("input keyevent KEYCODE_WAKEUP")
        sh("wm dismiss-keyguard")
        sh("svc power stayon true")
    }

    @Test
    fun bankAppToSafePause() {
        val results = mutableMapOf<String, List<Map<String, Long>>>()
        for (mode in listOf("cold", "warm")) {
            sh("am force-stop $SENTINEL") // the first warm run starts from a fresh process too
            results[mode] = (1..runs).mapNotNull { runOnce(cold = mode == "cold") }
        }
        val report = report(results)
        Log.i(TAG, report)
        File(instrumentation.context.getExternalFilesDir(null), "latency.json").writeText(report)
        for ((mode, list) in results) assertEquals("$mode: SafePause shown in every run", runs, list.size)
    }

    /** One run; null (logged) when SafePause never showed — that is a functional failure, not a slow run. */
    private fun runOnce(cold: Boolean): Map<String, Long>? {
        sh("am force-stop $DEMOBANK")
        sh("input keyevent KEYCODE_HOME")
        if (cold) sh("am force-stop $SENTINEL")
        SystemClock.sleep(1_000)
        sh("logcat -c")
        sh("am broadcast -f 0x20 -n $SENTINEL/.debug.ScenarioReceiver -a vn.hoicon.debug.CALL")
        waitFor(10_000) { "window_opened" in marks() || "window_opened_bg" in marks() }
        SystemClock.sleep(1_500) // let the window settle, like the call-then-open gap of the emulator scenario
        sh("am start -n $DEMOBANK/.MainActivity --es screen transfer")
        waitFor(PAUSE_WAIT_MS) { "pause_shown" in marks() }
        SystemClock.sleep(500)
        val marks = marks()

        // Clean up: leaving SafePause finishes it; clearing the call closes the window on its next tick.
        sh("input keyevent KEYCODE_HOME")
        sh("am broadcast -f 0x20 -n $SENTINEL/.debug.ScenarioReceiver -a vn.hoicon.debug.CLEAR")
        waitFor(5_000) { "window_closed" in marks() }

        val foreground = marks["app_foreground"]
        val shown = marks["pause_shown"]
        if (foreground == null || shown == null) {
            Log.w(TAG, "run missed (cold=$cold): marks=${marks.keys.sorted()}")
            return null
        }
        return buildMap {
            put("pause", shown - foreground)
            marks["risk_detected"]?.let { put("detect", it - foreground); put("open", shown - it) }
            marks["tts_started"]?.let { put("speech", it - foreground) }
            if ("pause_fallback" in marks) put("fallback", 1L)
        }.also { Log.i(TAG, "cold=$cold $it") }
    }

    /** `HC_TIMING: <mark> <epochMs>`, last value wins. */
    private fun marks(): Map<String, Long> =
        Regex("""HC_TIMING\s*:\s*(\w+)\s+(\d+)""")
            .findAll(sh("logcat -d -s HC_TIMING:I"))
            .associate { it.groupValues[1] to it.groupValues[2].toLong() }

    private fun waitFor(timeoutMs: Long, condition: () -> Boolean) {
        val deadline = SystemClock.uptimeMillis() + timeoutMs
        while (!condition() && SystemClock.uptimeMillis() < deadline) SystemClock.sleep(300)
    }

    private fun report(results: Map<String, List<Map<String, Long>>>): String {
        val modes = results.entries.joinToString(",\n") { (mode, list) ->
            val metrics = listOf("detect", "open", "pause", "speech").joinToString(", ") { metric ->
                val values = list.mapNotNull { it[metric] }
                if (values.isEmpty()) "\"$metric\": null" else "\"$metric\": {\"p50\": ${percentile(values, 0.5)}, " +
                    "\"p95\": ${percentile(values, 0.95)}, \"max\": ${values.max()}}"
            }
            val within = list.count { (it["pause"] ?: Long.MAX_VALUE) <= TARGET_MS }
            "    \"$mode\": {\"n\": ${list.size}, \"runs\": $runs, \"pause_le_3s\": $within, " +
                "\"fallback\": ${list.count { "fallback" in it }}, $metrics}"
        }
        return "{\n  \"device\": \"${Build.MANUFACTURER} ${Build.MODEL}\", \"sdk\": ${Build.VERSION.SDK_INT}, " +
            "\"compile\": \"${args.getString("compile") ?: "speed"}\",\n  \"modes\": {\n$modes\n  }\n}"
    }

    /** Nearest rank: with n = 10, p95 is the maximum (same as scripts/emu-scenario.py). */
    private fun percentile(values: List<Long>, q: Double): Long {
        val sorted = values.sorted()
        return sorted[maxOf(0, ceil(q * sorted.size).toInt() - 1)]
    }

    private companion object {
        const val TAG = "HC_LATENCY"
        const val SENTINEL = "vn.hoicon.sentinel"
        const val DEMOBANK = "vn.hoicon.demobank"
        const val PAUSE_WAIT_MS = 20_000L
        const val TARGET_MS = 3_000L
    }
}
