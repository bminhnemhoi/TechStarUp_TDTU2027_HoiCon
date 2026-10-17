package vn.hoicon.sentinel.data

import java.io.File
import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import vn.hoicon.sentinel.data.consent.ConsentLedger

/**
 * Pins the exact words behind each `text_sha256` (CLAUDE.md rule 7). If this fails you changed text the user agrees
 * to: bump ConsentLedger.VERSION AND update the pins below, in the same commit, so the ledger never holds one
 * version label over two different texts. Mirrors data/consent/ConsentTexts.kt (same string names, same order).
 */
class ConsentTextsPinTest {
    private val strings = File(assertNotNull(System.getProperty("hoicon.appStrings"))).readText(Charsets.UTF_8)

    private fun s(name: String) = assertNotNull(
        Regex("""<string name="$name">([^<]*)</string>""").find(strings),
        "string $name missing",
    ).groupValues[1]

    private fun hash(vararg names: String) = ConsentLedger.sha256Hex(names.joinToString("\n") { s(it) })

    @Test
    fun consentTextsMatchTheirPinnedHashesForThisVersion() {
        assertEquals("2026.10-v2", ConsentLedger.VERSION, "version changed: re-pin the hashes below")
        assertEquals(
            "4236a256e35d62df72d7dc9f41ec8559af1f582f6eb5fa1bc26806f548e2de61",
            hash(
                "disclosure_title",
                "disclosure_1_title", "disclosure_1_body", "disclosure_2_title", "disclosure_2_body",
                "disclosure_3_title", "disclosure_3_body", "disclosure_4_title", "disclosure_4_body",
                "disclosure_next",
            ),
        )
        assertEquals("a2886aef916da7cc1824bde8fceb54a16b3c8ff5abbc93e86cdb7a4dcc9a695d", hash("disclosure_3_title", "disclosure_3_body", "disclosure_4_title", "disclosure_4_body"))
        assertEquals("49c0fca401f2de07993d3015209da49f6aa26f2bf02907cfddf5a4a091f26674", hash("perm_role_title", "perm_role_why"))
        assertEquals("fe1bf2596999014aedaf23acfd9b86a144ef761b2e2a394cc1983702aad0dc40", hash("perm_usage_title", "perm_usage_why"))
        assertEquals("cf2a3ab7c4984c2150e63ef2b7e4736860ec7017827df3299fe94e6513f35a4c", hash("perm_overlay_title", "perm_overlay_why"))
        // Added by Spec 026 without touching the texts above: a new purpose, so VERSION stays and nobody agrees again.
        assertEquals(
            "0f4621ceff8256a4e1f110e1c294c22a955f348544955aa9424df8b0e84392eb",
            hash(
                "lookups_consent_ai", "lookups_consent_title", "lookups_consent_summary",
                "lookups_consent_1_title", "lookups_consent_1_body", "lookups_consent_2_title", "lookups_consent_2_body",
                "lookups_consent_3_title", "lookups_consent_3_body",
            ),
        )
    }
}
