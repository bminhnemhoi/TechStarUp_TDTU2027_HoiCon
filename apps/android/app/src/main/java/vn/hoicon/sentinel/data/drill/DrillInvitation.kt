package vn.hoicon.sentinel.data.drill

import vn.hoicon.sentinel.data.remote.DrillGateway
import vn.hoicon.sentinel.data.remote.DrillOffer
import vn.hoicon.sentinel.data.remote.DrillOfferResult

/** What one heartbeat learned about drills. */
sealed interface DrillCheck {
    /** Not asked at all: nothing may be shared with the family yet. */
    data object NotAllowed : DrillCheck

    /** Not asked: a risk window is open. The person is dealing with a real call; the invitation waits for the next beat. */
    data object Deferred : DrillCheck

    /** The server has no drill for this phone, or this one was answered already. */
    data object Nothing : DrillCheck

    /** The server offered a drill. [firstTime] is false when the notification for it was already shown (see [DrillStore.notifiedDrillId]). */
    data class Invite(val offer: DrillOffer, val firstTime: Boolean) : DrillCheck

    data object Unauthorized : DrillCheck

    /** Network or server trouble. Never an error for the heartbeat: the next beat asks again. */
    data object Failed : DrillCheck
}

/**
 * The "may we even ask?" rule of Spec 028 FR-008, apart from Android so it can be tested:
 *
 *  - only when events may go to the family ([mayShare]; the heartbeat itself needs the same);
 *  - never while a risk window is open ([windowOpen]), and never from the safe-pause path;
 *  - the server decides what is on offer, and it only offers a drill to a family whose senior has the `drills` consent
 *    on the ledger and only inside the window the guardians set, so no local copy of that consent is kept.
 *
 * Blocking: background threads only.
 */
class DrillInvitation(
    private val gateway: DrillGateway,
    private val store: DrillStore,
    private val mayShare: () -> Boolean,
    private val windowOpen: suspend () -> Boolean,
) {
    suspend fun check(accessToken: String): DrillCheck {
        if (!mayShare()) return DrillCheck.NotAllowed
        if (windowOpen()) return DrillCheck.Deferred
        return when (val result = gateway.fetchOffer(accessToken)) {
            is DrillOfferResult.Offer -> invite(result.offer)
            DrillOfferResult.NoOffer -> DrillCheck.Nothing
            DrillOfferResult.Unauthorized -> DrillCheck.Unauthorized
            DrillOfferResult.NetworkError, DrillOfferResult.ServerError -> DrillCheck.Failed
        }
    }

    private fun invite(offer: DrillOffer): DrillCheck {
        // The result of a drill answered a minute ago may not have reached the server yet: the offer is still live there.
        if (offer.drillId == store.handledDrillId) return DrillCheck.Nothing
        store.savePending(offer)
        // Not marked as notified here: only the caller knows whether the notification could be shown.
        return DrillCheck.Invite(offer, firstTime = store.notifiedDrillId != offer.drillId)
    }
}
