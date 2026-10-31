package vn.hoicon.sentinel.data.consent

import android.content.res.Resources
import vn.hoicon.sentinel.R

/**
 * The exact words shown to the user for each consent purpose, hashed into `text_sha256` (DPIA: proof of what was
 * agreed). One string-array per purpose in `res/values/consent_texts.xml`, line for line the `BEGIN-TEXT` block of
 * `docs/legal/consent/<purpose>.vi.md` (Spec 011), and the screens draw these very lines, so the hash can never drift
 * from what the person read. Changing any of them means bumping [ConsentLedger.VERSION] (CLAUDE.md rule 7);
 * `ConsentManifestPinTest` fails until the manifest, the resource and the version agree.
 */
internal val consentTextArrays: Map<String, Int> = mapOf(
    ConsentLedger.CORE_PROTECTION to R.array.consent_core_protection,
    ConsentLedger.CALL_SCREENING to R.array.consent_call_screening,
    ConsentLedger.USAGE_MONITORING to R.array.consent_usage_monitoring,
    ConsentLedger.OVERLAY_PAUSE to R.array.consent_overlay_pause,
    ConsentLedger.GUARDIAN_ALERTS to R.array.consent_guardian_alerts,
    ConsentLedger.LLM_PROCESSING to R.array.consent_llm_processing,
    ConsentLedger.VOICE_INPUT to R.array.consent_voice_input,
    ConsentLedger.DRILLS to R.array.consent_drills,
    ConsentLedger.PILOT_RESEARCH to R.array.consent_pilot_research,
    ConsentLedger.LOOKUPS to R.array.consent_lookups,
)

/** The lines of one purpose, in order: [AI line,] title, then the paragraphs. */
fun consentLines(res: Resources, purpose: String): List<String> =
    res.getStringArray(consentTextArrays.getValue(purpose)).toList()

/** What gets hashed: the non-empty lines joined by `\n` (the rule in docs/legal/consent/README.md). */
fun consentTexts(res: Resources): Map<String, String> =
    consentTextArrays.keys.associateWith { consentLines(res, it).joinToString("\n") }
