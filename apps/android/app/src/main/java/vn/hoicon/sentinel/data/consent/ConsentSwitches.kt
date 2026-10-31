package vn.hoicon.sentinel.data.consent

import vn.hoicon.sentinel.data.local.TokenStorage

/**
 * E12 (Spec 038): the consent purposes that are NOT tied to a system permission, and so have no "turn off in Settings" of their own.
 * Switching one off only changes local state; [ConsentSync] then appends the `granted=false` row (the ledger only grows) and the
 * server stops using it (Spec 034/037). `core_protection` has no switch: stopping it altogether is the delete flow (FR-003). The
 * deterministic safe pause never depends on any of these (CLAUDE.md rule 4).
 */
class ConsentSwitches(private val storage: TokenStorage) {
    fun isOn(purpose: String): Boolean = when (purpose) {
        ConsentLedger.GUARDIAN_ALERTS -> storage.acceptedDisclosureVersion == ConsentLedger.DISCLOSURE_VERSION && !storage.guardianAlertsOff
        ConsentLedger.LOOKUPS -> storage.acceptedLookupsVersion == ConsentLedger.VERSION
        ConsentLedger.DRILLS -> storage.acceptedDrillsVersion == ConsentLedger.VERSION
        else -> false
    }

    fun turnOff(purpose: String) {
        require(purpose in SWITCHABLE) { "$purpose has no switch" }
        when (purpose) {
            ConsentLedger.GUARDIAN_ALERTS -> storage.guardianAlertsOff = true
            ConsentLedger.LOOKUPS -> storage.acceptedLookupsVersion = null
            ConsentLedger.DRILLS -> storage.acceptedDrillsVersion = null
        }
    }

    /**
     * Only `guardian_alerts` comes back here, after its own words were shown again. `lookups` and `drills` go back through their
     * just-in-time screens (E10, the drills consent), which record the agreement themselves.
     */
    fun turnOn(purpose: String) {
        require(purpose == ConsentLedger.GUARDIAN_ALERTS) { "$purpose is switched on by its own consent screen" }
        storage.guardianAlertsOff = false
    }

    companion object {
        val SWITCHABLE = listOf(ConsentLedger.GUARDIAN_ALERTS, ConsentLedger.LOOKUPS, ConsentLedger.DRILLS)
    }
}
