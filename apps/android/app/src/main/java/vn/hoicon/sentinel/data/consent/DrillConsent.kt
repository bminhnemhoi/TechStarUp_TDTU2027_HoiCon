package vn.hoicon.sentinel.data.consent

import vn.hoicon.sentinel.data.local.TokenStorage

/**
 * The practice-call consent (Spec 028, purpose `drills`): only an adult who says so herself/himself agrees (Spec 028 FR / CLAUDE.md
 * rule 8, pilot is 18+), and "Để lúc khác" records nothing. What was agreed to is the `drills` text in
 * docs/legal/consent/ (hashed by [ConsentSync] into the ledger); this class only keeps the local half.
 */
class DrillConsent(private val storage: TokenStorage) {
    enum class Result { AGREED, NEEDS_ADULT_CONFIRMATION }

    val agreed: Boolean get() = storage.acceptedDrillsVersion == ConsentLedger.VERSION

    fun accept(adultConfirmed: Boolean): Result {
        if (!adultConfirmed) return Result.NEEDS_ADULT_CONFIRMATION
        storage.acceptedDrillsVersion = ConsentLedger.VERSION
        return Result.AGREED
    }
}
