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
        assertEquals("2026.10-v1", ConsentLedger.VERSION, "version changed: re-pin the hashes below")
        assertEquals(
            "caa0b9451d12a0a534db634faaec0e7221718c9bd386f89a740043c425ad6edc",
            hash(
                "disclosure_title",
                "disclosure_1_title", "disclosure_1_body", "disclosure_2_title", "disclosure_2_body",
                "disclosure_3_title", "disclosure_3_body", "disclosure_4_title", "disclosure_4_body",
                "disclosure_next",
            ),
        )
        assertEquals("49c0fca401f2de07993d3015209da49f6aa26f2bf02907cfddf5a4a091f26674", hash("perm_role_title", "perm_role_why"))
        assertEquals("fe1bf2596999014aedaf23acfd9b86a144ef761b2e2a394cc1983702aad0dc40", hash("perm_usage_title", "perm_usage_why"))
        assertEquals("cf2a3ab7c4984c2150e63ef2b7e4736860ec7017827df3299fe94e6513f35a4c", hash("perm_overlay_title", "perm_overlay_why"))
    }
}
