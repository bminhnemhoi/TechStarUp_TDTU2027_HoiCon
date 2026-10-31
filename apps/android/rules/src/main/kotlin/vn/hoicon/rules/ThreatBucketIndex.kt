package vn.hoicon.rules

/**
 * The on-device "may be on the warning list" answer (Spec 026, ADR-011): a sorted set of k-anonymous buckets, not of
 * `h1`. A bucket is the first 24 bits of `h1` (it is already a SHA-256, so they are uniform) cut down to [bits]; every
 * bucket stands for roughly 3.6e8 / 2^bits real mobile numbers, so the list cannot be walked back to a number.
 * A match only means "possibly listed": the server still checks the exact h1 whenever an event reaches it.
 *
 * Immutable and thread-safe: the app swaps a whole new instance in after each sync. Lookup is a binary search over an
 * `IntArray` (17 comparisons for 100,000 buckets): no I/O, no allocation, fine on the main thread inside
 * `onScreenCall`.
 */
class ThreatBucketIndex private constructor(val bits: Int, private val sorted: IntArray) {
    val count: Int get() = sorted.size

    /** True when [h1]'s bucket is listed. A malformed h1 is simply "not listed" (never throws inside a call). */
    fun contains(h1: String): Boolean {
        if (sorted.isEmpty()) return false
        val bucket = bucketOrNull(h1, bits) ?: return false
        return sorted.binarySearch(bucket) >= 0
    }

    companion object {
        const val MIN_BITS = 16
        const val MAX_BITS = 24
        private const val BYTES_PER_BUCKET = 3
        private const val H1_HEX_PREFIX = 6
        private const val H1_LENGTH = 64

        /** No list yet (never synced, or nothing flagged): matches nothing. */
        val EMPTY = ThreatBucketIndex(MAX_BITS, IntArray(0))

        /** `int(h1[:6], 16) >> (24 - bits)`, the same function as the server's `bucket24` (see ADR-011). */
        fun bucket(h1: String, bits: Int): Int {
            require(bits in MIN_BITS..MAX_BITS) { "bits must be $MIN_BITS..$MAX_BITS" }
            return requireNotNull(bucketOrNull(h1, bits)) { "not a lowercase 64-hex h1" }
        }

        private fun bucketOrNull(h1: String, bits: Int): Int? {
            if (h1.length != H1_LENGTH) return null
            var value = 0
            for (i in 0 until H1_HEX_PREFIX) {
                val digit = Character.digit(h1[i], 16)
                if (digit < 0) return null
                value = (value shl 4) or digit
            }
            return value ushr (MAX_BITS - bits)
        }

        /**
         * Reads the server's packed list: [expectedCount] (when known) × 3 bytes, each bucket a big-endian uint24, strictly
         * ascending (so sorted and without duplicates), every value below 2^[bits]. Anything else is a corrupt download:
         * throws [IllegalArgumentException] and the caller keeps the list it already has.
         */
        fun fromPacked(bytes: ByteArray, bits: Int, expectedCount: Int? = null): ThreatBucketIndex {
            require(bits in MIN_BITS..MAX_BITS) { "bits must be $MIN_BITS..$MAX_BITS" }
            require(bytes.size % BYTES_PER_BUCKET == 0) { "packed length ${bytes.size} is not a multiple of 3" }
            val n = bytes.size / BYTES_PER_BUCKET
            require(expectedCount == null || expectedCount == n) { "count $expectedCount does not match $n buckets" }
            val limit = 1 shl bits
            val buckets = IntArray(n)
            for (i in 0 until n) {
                val at = i * BYTES_PER_BUCKET
                val v = ((bytes[at].toInt() and 0xFF) shl 16) or ((bytes[at + 1].toInt() and 0xFF) shl 8) or (bytes[at + 2].toInt() and 0xFF)
                require(v < limit) { "bucket #$i does not fit in $bits bits" }
                require(i == 0 || v > buckets[i - 1]) { "bucket #$i is not strictly ascending" }
                buckets[i] = v
            }
            return ThreatBucketIndex(bits, buckets)
        }
    }
}
