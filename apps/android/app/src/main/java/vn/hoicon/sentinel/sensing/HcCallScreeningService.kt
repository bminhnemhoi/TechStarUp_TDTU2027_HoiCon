package vn.hoicon.sentinel.sensing

import android.os.Build
import android.telecom.Call
import android.telecom.CallScreeningService
import vn.hoicon.rules.CallDirection
import vn.hoicon.rules.CallSignal
import vn.hoicon.rules.PhoneHasher
import vn.hoicon.rules.RiskEngine

/**
 * Bound by Telecom for calls whose number is NOT in the address book (role CALL_SCREENING) — this is the
 * "unknown number" signal, without READ_CONTACTS / READ_CALL_LOG (ADR-001).
 * Observe only: always allows the call, never silences, rejects or hides it.
 */
class HcCallScreeningService : CallScreeningService() {
    override fun onScreenCall(callDetails: Call.Details) {
        val now = System.currentTimeMillis()
        HcTiming.mark("call_screened", now)
        respondToCall(callDetails, CallResponse.Builder().build())

        // The raw number lives only inside this expression; only h1 + last3 are kept.
        val hashed = callDetails.handle?.schemeSpecificPart?.let(PhoneHasher::hash)
        val direction = if (callDetails.callDirection == Call.Details.DIRECTION_OUTGOING) {
            CallDirection.OUTGOING
        } else {
            CallDirection.INCOMING
        }
        val verification = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            callDetails.callerNumberVerificationStatus
        } else {
            -1
        }
        val next = CallSignal(
            phone = hashed,
            direction = direction,
            trusted = hashed != null && LocalLists.isTrusted(hashed.h1),
            flagged = hashed != null && LocalLists.isFlagged(hashed.h1),
            startedAtMs = now,
            endedAtMs = null,
        )
        // SEC-6: fold into the window that may already be open — a later call never lowers the risk.
        val stored = CallSignalStore.load(this)
        val open = stored?.toSignal(inCallNow = false)
        val merged = RiskEngine.mergeCall(open, next)
        val call = if (stored != null && merged === open) stored else ScreenedCall.from(merged, verification, now)
        if (call !== stored) CallSignalStore.save(this, call)
        HcSpikeLog.i(
            "screened dir=${direction.wire} verification=$verification flagged=${next.flagged} " +
                "trusted=${next.trusted} merged=${open != null && merged !== next} window_flagged=${call.flagged} " +
                "last3=${hashed?.last3 ?: "-"} api=${Build.VERSION.SDK_INT}",
        )
        if (!call.trusted) RiskWindowService.open(this)
    }
}
