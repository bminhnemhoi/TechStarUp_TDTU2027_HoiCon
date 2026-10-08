package vn.hoicon.sentinel.sensing

import android.util.Log
import vn.hoicon.sentinel.BuildConfig

/**
 * Latency marks parsed by scripts/emu-scenario.py: `HC_TIMING: <mark> <epochMillis>` at INFO.
 * Epoch (wall clock) on purpose: `app_foreground` is the UsageEvents timestamp, which is wall clock.
 * Debug builds only (SEC-4). Never put personal data in a mark.
 */
object HcTiming {
    private const val TAG = "HC_TIMING"

    fun mark(name: String, epochMs: Long = System.currentTimeMillis()) {
        if (BuildConfig.DEBUG) Log.i(TAG, "$name $epochMs")
    }
}

/** Spike diagnostics, debug builds only (SEC-4). Numbers only ever appear as last3; apps only as their category. */
object HcSpikeLog {
    private const val TAG = "HC_SPIKE"

    fun i(message: String) {
        if (BuildConfig.DEBUG) Log.i(TAG, message)
    }

    fun w(message: String, error: Throwable? = null) {
        if (BuildConfig.DEBUG) Log.w(TAG, message, error)
    }
}
