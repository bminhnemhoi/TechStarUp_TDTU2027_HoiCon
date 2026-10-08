package vn.hoicon.sentinel.sensing

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.media.AudioManager
import android.os.Build
import android.telephony.PhoneStateListener
import android.telephony.TelephonyCallback
import android.telephony.TelephonyManager

/**
 * Is a call ringing / connected right now? (H2, ADR-007: AudioManager.mode, no permission.)
 *  - `audio_mode_<n>` marks: AudioManager.mode. Event-driven on API 31+ (OnModeChangedListener), else sampled each tick.
 *  - `tel_state_<n>` marks: PhoneStateListener LISTEN_CALL_STATE on API 29–30 (no permission). On API 31+ the
 *    TelephonyCallback needs READ_PHONE_STATE, which is NOT declared since ADR-007 ⇒ skipped.
 * SEC-9: only MODE_RINGTONE / MODE_IN_CALL count as a phone call (not MODE_IN_COMMUNICATION, i.e. VoIP/other apps),
 * so another app's audio session can't keep the risk window open. Main thread only.
 */
@Suppress("DEPRECATION", "OVERRIDE_DEPRECATION") // PhoneStateListener is the only call-state API on API 29–30.
class CallStateMonitor(private val context: Context) {
    private val audio = context.getSystemService(AudioManager::class.java)
    private val telephony = context.getSystemService(TelephonyManager::class.java)
    private var lastAudioMode = Int.MIN_VALUE
    private var telephonyState: Int? = null
    private var telephonyCallback: TelephonyCallback? = null
    private var phoneStateListener: PhoneStateListener? = null
    private var modeListener: AudioManager.OnModeChangedListener? = null

    fun start() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val listener = AudioManager.OnModeChangedListener { mode -> onAudioMode(mode) }
            audio.addOnModeChangedListener(context.mainExecutor, listener)
            modeListener = listener
            startTelephonyCallback()
        } else {
            startPhoneStateListener()
        }
        HcSpikeLog.i("call state sources: audio=on telephony=${telephonyCallback != null || phoneStateListener != null}")
    }

    fun stop() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            modeListener?.let { audio.removeOnModeChangedListener(it) }
            telephonyCallback?.let { telephony.unregisterTelephonyCallback(it) }
        }
        phoneStateListener?.let { telephony.listen(it, PhoneStateListener.LISTEN_NONE) }
        modeListener = null
        telephonyCallback = null
        phoneStateListener = null
    }

    /** Ringing or connected. Called on every tick (also samples the audio mode). */
    fun inCall(): Boolean {
        onAudioMode(audio.mode)
        telephonyState?.let { return it != TelephonyManager.CALL_STATE_IDLE }
        return lastAudioMode == AudioManager.MODE_RINGTONE || lastAudioMode == AudioManager.MODE_IN_CALL
    }

    /** Answered (or dialling out): the user is talking to the caller. Call after [inCall] in the same tick. */
    fun connected(): Boolean {
        telephonyState?.let { return it == TelephonyManager.CALL_STATE_OFFHOOK }
        return lastAudioMode == AudioManager.MODE_IN_CALL
    }

    private fun onAudioMode(mode: Int) {
        if (mode == lastAudioMode) return
        lastAudioMode = mode
        HcTiming.mark("audio_mode_$mode")
    }

    private fun onTelephonyState(state: Int) {
        if (state == telephonyState) return
        telephonyState = state
        HcTiming.mark("tel_state_$state")
    }

    private fun startTelephonyCallback() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return
        if (context.checkSelfPermission(Manifest.permission.READ_PHONE_STATE) != PackageManager.PERMISSION_GRANTED) {
            HcSpikeLog.i("TelephonyCallback skipped: READ_PHONE_STATE not granted (audio mode only)")
            return
        }
        val callback = object : TelephonyCallback(), TelephonyCallback.CallStateListener {
            override fun onCallStateChanged(state: Int) = onTelephonyState(state)
        }
        try {
            telephony.registerTelephonyCallback(context.mainExecutor, callback)
            telephonyCallback = callback
        } catch (e: SecurityException) {
            HcSpikeLog.w("TelephonyCallback refused", e)
        }
    }

    private fun startPhoneStateListener() {
        // API 29–30: LISTEN_CALL_STATE needs no permission; the number argument stays empty (no READ_CALL_LOG).
        val listener = object : PhoneStateListener() {
            override fun onCallStateChanged(state: Int, ignoredNumber: String?) = onTelephonyState(state)
        }
        telephony.listen(listener, PhoneStateListener.LISTEN_CALL_STATE)
        phoneStateListener = listener
    }
}
