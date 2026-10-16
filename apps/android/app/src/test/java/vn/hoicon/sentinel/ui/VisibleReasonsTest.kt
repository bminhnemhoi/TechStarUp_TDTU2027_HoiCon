package vn.hoicon.sentinel.ui

import org.junit.Test
import vn.hoicon.sentinel.data.remote.LookupKind
import kotlin.test.assertEquals

/** Spec 026 FR-003: a phone number is never called "an toàn", even if the server's own reason says so. */
class VisibleReasonsTest {
    private val reasons = listOf("Có trong danh sách cảnh báo.", "Số này an toàn để gọi lại.")

    @Test
    fun aPhoneReasonThatCallsTheNumberSafeIsDropped() {
        assertEquals(listOf("Có trong danh sách cảnh báo."), visibleReasons(LookupKind.PHONE, reasons))
    }

    @Test
    fun aLinkKeepsAllItsReasons() {
        assertEquals(reasons, visibleReasons(LookupKind.URL, reasons))
    }
}
