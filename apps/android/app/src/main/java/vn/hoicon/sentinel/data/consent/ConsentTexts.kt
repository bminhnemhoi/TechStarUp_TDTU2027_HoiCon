package vn.hoicon.sentinel.data.consent

import android.content.res.Resources
import vn.hoicon.sentinel.R
import vn.hoicon.sentinel.sensing.SensorPermission

/**
 * The exact words shown to the user for each consent purpose, hashed into `text_sha256` (DPIA: proof of what was
 * agreed). Same string resources as E3/E4, so the hash can never drift from the screen. Changing any of these
 * strings means bumping [ConsentLedger.VERSION] (CLAUDE.md rule 7).
 */
fun consentTexts(res: Resources): Map<String, String> {
    fun join(vararg ids: Int) = ids.joinToString("\n") { res.getString(it) }
    val permissionTexts = mapOf(
        SensorPermission.CALL_SCREENING_ROLE to join(R.string.perm_role_title, R.string.perm_role_why),
        SensorPermission.USAGE_ACCESS to join(R.string.perm_usage_title, R.string.perm_usage_why),
        SensorPermission.DISPLAY_OVER_APPS to join(R.string.perm_overlay_title, R.string.perm_overlay_why),
    )
    return buildMap {
        put(
            ConsentLedger.CORE_PROTECTION,
            join(
                R.string.disclosure_title,
                R.string.disclosure_1_title, R.string.disclosure_1_body,
                R.string.disclosure_2_title, R.string.disclosure_2_body,
                R.string.disclosure_3_title, R.string.disclosure_3_body,
                R.string.disclosure_4_title, R.string.disclosure_4_body,
                R.string.disclosure_next,
            ),
        )
        put(
            ConsentLedger.GUARDIAN_ALERTS,
            join(R.string.disclosure_3_title, R.string.disclosure_3_body, R.string.disclosure_4_title, R.string.disclosure_4_body),
        )
        put(
            ConsentLedger.LOOKUPS,
            join(
                R.string.lookups_consent_ai, R.string.lookups_consent_title, R.string.lookups_consent_summary,
                R.string.lookups_consent_1_title, R.string.lookups_consent_1_body,
                R.string.lookups_consent_2_title, R.string.lookups_consent_2_body,
                R.string.lookups_consent_3_title, R.string.lookups_consent_3_body,
            ),
        )
        for ((permission, text) in permissionTexts) ConsentLedger.purposeOf(permission)?.let { put(it, text) }
    }
}
