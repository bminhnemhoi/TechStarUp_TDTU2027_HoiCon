package vn.hoicon.sentinel.ui

import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

/** Cutting a consent text for drawing drops nothing: the screen shows every line the ledger hashes. */
class ConsentPartsTest {
    @Test
    fun aTextWithTheAiSentenceKeepsItFirstThenTitleThenParagraphs() {
        val lines = listOf("Đây là trợ lý AI HỏiCon.", "Tiêu đề", "Đoạn một.", "Đoạn hai.")
        val parts = consentParts(lines)
        assertEquals("Đây là trợ lý AI HỏiCon.", parts.ai)
        assertEquals("Tiêu đề", parts.title)
        assertEquals("Đoạn một.\n\nĐoạn hai.", parts.body)
        assertEquals(lines, parts.lines)
    }

    @Test
    fun aTextWithoutItStartsWithTheTitle() {
        val lines = listOf("Hiện lời nhắc", "Đoạn một.")
        val parts = consentParts(lines)
        assertNull(parts.ai)
        assertEquals(lines, parts.lines)
    }
}
