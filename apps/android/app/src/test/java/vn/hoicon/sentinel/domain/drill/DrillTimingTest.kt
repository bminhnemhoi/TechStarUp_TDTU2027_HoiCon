package vn.hoicon.sentinel.domain.drill

import java.time.Instant
import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue

/** Spec 028: the window of a drill. An unreadable date is never "still open" (fail closed). */
class DrillTimingTest {
    private val now = Instant.parse("2026-10-16T03:00:00Z")

    @Test
    fun readsOffsetsAndZ() {
        assertEquals(Instant.parse("2026-10-16T03:30:00Z"), DrillTiming.parseEnd("2026-10-16T10:30:00+07:00"))
        assertEquals(Instant.parse("2026-10-16T03:30:00Z"), DrillTiming.parseEnd("2026-10-16T03:30:00Z"))
    }

    @Test
    fun aWindowIsOverOnlyAfterItsEnd() {
        assertFalse(DrillTiming.isOver("2026-10-16T10:30:00+07:00", now))
        assertTrue(DrillTiming.isOver("2026-10-16T09:59:59+07:00", now))
    }

    @Test
    fun anUnreadableDateCountsAsOver() {
        for (bad in listOf("", "mai", "2026-10-16", "2026-10-16T10:30:00")) {
            assertNull(DrillTiming.parseEnd(bad), bad)
            assertTrue(DrillTiming.isOver(bad, now), bad)
            assertNull(DrillTiming.millisUntil(bad, now), bad)
        }
    }

    @Test
    fun millisUntilCountsDownAndStopsAtZero() {
        assertEquals(30 * 60_000L, DrillTiming.millisUntil("2026-10-16T03:30:00Z", now))
        assertNull(DrillTiming.millisUntil("2026-10-16T02:00:00Z", now))
    }
}
