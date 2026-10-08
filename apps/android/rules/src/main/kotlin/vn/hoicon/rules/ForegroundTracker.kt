package vn.hoicon.rules

/**
 * Which app is in front, rebuilt from activity resume/pause events (UsageStats on the device). Needed for the GAP
 * case: a banking app opened long before the call produces no new "resumed" event while the call is answered.
 *
 * Deterministic and order-tolerant: per package only the newest event counts, so re-feeding an overlapping batch
 * of events (the device re-reads a few seconds back each tick) changes nothing.
 */
class ForegroundTracker {
    private class Last(val resumed: Boolean, val atMs: Long)

    private val latest = HashMap<String, Last>()

    /** [resumed] = activity resumed; false = paused or stopped. Ties keep the event fed last (Android logs pause first). */
    fun onEvent(packageName: String, resumed: Boolean, atMs: Long) {
        val previous = latest[packageName]
        if (previous == null || atMs >= previous.atMs) latest[packageName] = Last(resumed, atMs)
    }

    /** The most recently resumed package not paused since, with its resume time; null when nothing is in front. */
    fun current(): Pair<String, Long>? =
        latest.entries.filter { it.value.resumed }.maxByOrNull { it.value.atMs }?.let { it.key to it.value.atMs }
}
