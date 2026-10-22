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

    /** Found on the AVD: a sentence was hashed into the ledger but never drawn. Now the screen draws the whole text, line for line. */
    @Test
    fun theLookupsConsentScreenDrawsTheWholeHashedText() {
        val main = File(checkNotNull(System.getProperty("hoicon.appStrings"))).parentFile.parentFile.parentFile // src/main
        val screen = File(main, "java/vn/hoicon/sentinel/ui/LookupScreen.kt").readText()
        val consentBody = screen.substringAfter("fun LookupConsentScreen(").substringBefore("fun LookupScreen(")
        assertTrue("rememberConsentParts(ConsentLedger.LOOKUPS)" in consentBody, "the consent screen no longer draws the lookups text")
        assertTrue("ConsentTextBlock(" in consentBody, "paragraphs must be drawn by ConsentTextBlock")
    }
}
