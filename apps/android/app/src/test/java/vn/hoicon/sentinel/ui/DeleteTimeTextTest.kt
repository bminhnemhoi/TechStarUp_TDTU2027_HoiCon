package vn.hoicon.sentinel.ui

import java.time.OffsetDateTime
import java.time.ZoneId
import org.junit.Test
import kotlin.test.assertEquals

/** E12 says when the deletion starts in words an older person reads at once: hour, then day and month, in the phone's own zone. */
class DeleteTimeTextTest {
    private fun ms(iso: String) = OffsetDateTime.parse(iso).toInstant().toEpochMilli()

    @Test
    fun hourThenDayAndMonthInTheGivenZone() {
        val vn = ZoneId.of("Asia/Ho_Chi_Minh")
        assertEquals("9:00 ngày 26 tháng 10", deleteTimeText(ms("2026-10-26T09:00:00+07:00"), vn))
        assertEquals("21:05 ngày 3 tháng 1", deleteTimeText(ms("2027-01-03T14:05:00Z"), vn))
        assertEquals("2:00 ngày 26 tháng 10", deleteTimeText(ms("2026-10-26T09:00:00+07:00"), ZoneId.of("UTC")))
    }
}
