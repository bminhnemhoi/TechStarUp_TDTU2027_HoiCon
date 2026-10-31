package vn.hoicon.sentinel.data

import java.io.File
import org.json.JSONObject
import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue
import vn.hoicon.sentinel.data.consent.ConsentLedger

/**
 * Spec 011: the words the app shows (res/values/consent_texts.xml) are, line for line, the BEGIN-TEXT block of
 * docs/legal/consent/<purpose>.vi.md, and their SHA-256 is the one in manifest.json. Changing a word anywhere
 * (the .md, the XML, the manifest) without the other two and without bumping its version in ConsentLedger.versionOf turns this red
 * (CLAUDE.md rule 7). The literal pins below make a paired edit of XML + manifest visible too: re-pin them in the same commit.
 */
class ConsentManifestPinTest {
    private val xml = File(assertNotNull(System.getProperty("hoicon.consentXml"))).readText(Charsets.UTF_8)
    private val docs = File(assertNotNull(System.getProperty("hoicon.consentDocs")))
    private val manifest = JSONObject(File(docs, "manifest.json").readText(Charsets.UTF_8)).getJSONArray("purposes")

    private fun unescape(raw: String) = raw.replace("\\\"", "\"").replace("\\'", "'").replace("&amp;", "&")

    private fun appLines(purpose: String): List<String> {
        val block = assertNotNull(
            Regex("""<string-array name="consent_$purpose">(.*?)</string-array>""", RegexOption.DOT_MATCHES_ALL).find(xml),
            "consent_$purpose missing in consent_texts.xml",
        ).groupValues[1]
        return Regex("""<item>(.*?)</item>""").findAll(block).map { unescape(it.groupValues[1]) }.toList()
    }

    private fun docLines(file: String): List<String> {
        val text = File(docs, file).readText(Charsets.UTF_8)
        return text.substringAfter("<!-- BEGIN-TEXT -->").substringBefore("<!-- END-TEXT -->")
            .lines().map { it.trimEnd() }.filter { it.isNotBlank() }
    }

    private val pinned = mapOf(
        "core_protection" to "1576099e185a6208837d7dd2588b8dcc8d332f4f700add3e559cf41e805d666a",
        "call_screening" to "5765f61167f68549fa7de8ab4c7787082924ff7e095a72ac23699d24bde85643",
        "usage_monitoring" to "d69403e4a13874f99d236ab67a8f4f0153c8755e3b45f17a32395736dc4e114f",
        "overlay_pause" to "d98935d94ed0ced77f7f788600489f09cc0e32d472d55dbe9e303f7075300fce",
        "guardian_alerts" to "afd2491512d6ecd7b89ff62cac56a54e8c6429ff741fdd440ca5f86ec6a2b72a",
        "llm_processing" to "00bd60e3e3d6f5ae03e3f55b8862c6babc733a175d839bbc49ce2343a43b2f9b",
        "voice_input" to "4729274fdcf38cb613b1dad6ea7ede7a3e54ab04b8fb044e3f47e3ee5d3bba24",
        "drills" to "6a182f00d88b4ba9121af29937032020de070919e01a5cd527a65a0aafb9bb4d",
        "pilot_research" to "5e41d874539a9e411df7a5854634a94a4395f9a47badb80fce10b317f4bf64d9",
        "lookups" to "b94c6648f8109a4f634fcf8f2c27c7c2d5033f38ac2427cf64b62d4f3b4b8218",
    )

    @Test
    fun everyManifestPurposeHasExactlyOneAppTextWithTheManifestWordsVersionAndHash() {
        assertEquals(pinned.keys, (0 until manifest.length()).map { manifest.getJSONObject(it).getString("purpose") }.toSet())
        for (i in 0 until manifest.length()) {
            val entry = manifest.getJSONObject(i)
            val purpose = entry.getString("purpose")
            val app = appLines(purpose)
            assertEquals(docLines(entry.getString("file")), app, "$purpose: app words differ from docs/legal/consent")
            assertEquals(entry.getString("sha256"), ConsentLedger.sha256Hex(app.joinToString("\n")), "$purpose: hash differs from manifest")
            assertEquals(entry.getString("version"), ConsentLedger.versionOf(purpose), "$purpose: manifest version differs from ConsentLedger.versionOf")
            assertEquals(pinned.getValue(purpose), ConsentLedger.sha256Hex(app.joinToString("\n")), "$purpose: re-pin with the version bump")
        }
    }

    @Test
    fun noConsentTextPromisesWhatTheCodeDoesNotDo() {
        // Spec 011 evidence: nothing tells the family that a permission was switched off (heartbeat only counts coverage).
        val everything = pinned.keys.flatMap { appLines(it) }.joinToString("\n")
        for (promise in listOf("quyền nào đang tắt", "quyền bị tắt", "biết quyền")) {
            assertTrue(promise !in everything, "consent text promises '$promise' but no code does that")
        }
    }
}
