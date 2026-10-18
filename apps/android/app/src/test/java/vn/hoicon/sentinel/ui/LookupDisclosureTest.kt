package vn.hoicon.sentinel.ui

import java.io.File
import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

/** E10 (Spec 026 T025): the consent words the ledger hashes must be on the screen, and the AI sentence stays first. */
class LookupDisclosureTest {
    @Test
    fun theAiSentenceComesFirstAndTheRestMovesAfterTheAdvice() {
        val (ai, rest) = splitDisclosure("Đây là trợ lý AI HỏiCon. Kết quả chỉ để tham khảo, không thay cho ý kiến của con cháu.")
        assertEquals("Đây là trợ lý AI HỏiCon.", ai)
        assertEquals("Kết quả chỉ để tham khảo, không thay cho ý kiến của con cháu.", rest)
    }

    @Test
    fun aSingleSentenceStaysWhole() {
        assertEquals("Đây là trợ lý AI HỏiCon." to "", splitDisclosure("Đây là trợ lý AI HỏiCon."))
        assertEquals("Chưa có dấu chấm" to "", splitDisclosure("Chưa có dấu chấm"))
    }

    /** Found on the AVD: `lookups_consent_summary` was hashed into the ledger but never drawn on the consent screen. */
    @Test
    fun everyLookupsConsentSentenceTheLedgerHashesIsOnTheConsentScreen() {
        val main = File(checkNotNull(System.getProperty("hoicon.appStrings"))).parentFile.parentFile.parentFile // src/main
        val texts = File(main, "java/vn/hoicon/sentinel/data/consent/ConsentTexts.kt").readText()
        val screen = File(main, "java/vn/hoicon/sentinel/ui/LookupScreen.kt").readText()
        val consentBody = screen.substringAfter("fun LookupConsentScreen(").substringBefore("fun LookupScreen(")
        val hashed = Regex("""R\.string\.(lookups_consent_\w+)""").findAll(texts).map { it.groupValues[1] }.toSet()
        assertTrue(hashed.isNotEmpty(), "ConsentTexts.kt no longer lists the lookups strings: update this test")
        for (name in hashed) assertTrue("R.string.$name" in consentBody, "$name is hashed into the ledger but not shown on the consent screen")
    }
}
