package vn.hoicon.rules

import java.util.Random
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertTrue

/** Spec 026 FR-003/FR-010, SC-004. Only fictional hashes: random hex, and the shared `flagged_caller` fixture h1. */
class ThreatBucketIndexTest {
    // h1 of the fictional `flagged_caller` in data/fixtures/phones.json (same value the debug build hard-codes).
    private val flaggedH1 = "aa1b1fcd5c51853e998738c59cffa5a4d95bd39ef7ef3b6d905c9c6c3af987e4"

    private fun pack(vararg buckets: Int): ByteArray = ByteArray(buckets.size * 3).also { out ->
        buckets.forEachIndexed { i, v ->
            out[i * 3] = (v ushr 16).toByte()
            out[i * 3 + 1] = (v ushr 8).toByte()
            out[i * 3 + 2] = v.toByte()
        }
    }

    private fun randomH1(random: Random): String {
        val sb = StringBuilder(64)
        repeat(64) { sb.append("0123456789abcdef"[random.nextInt(16)]) }
        return sb.toString()
    }

    // Vectors for bucket24 = int(h1[:6], 16), then >> (24 - bits). backend/tests/unit/test_threat_bucket.py (lane B,
    // not merged when this was written) must pin the same numbers.
    @Test
    fun bucketVectors() {
        assertEquals(0xAA1B1F, ThreatBucketIndex.bucket(flaggedH1, 24))
        assertEquals(0xAA1B1F ushr 2, ThreatBucketIndex.bucket(flaggedH1, 22))
        assertEquals(0xAA1B, ThreatBucketIndex.bucket(flaggedH1, 16))
        assertEquals(0, ThreatBucketIndex.bucket("0".repeat(64), 22))
        assertEquals((1 shl 22) - 1, ThreatBucketIndex.bucket("f".repeat(64), 22))
    }

    @Test
    fun bucketRejectsBadInput() {
        assertFailsWith<IllegalArgumentException> { ThreatBucketIndex.bucket(flaggedH1, 15) }
        assertFailsWith<IllegalArgumentException> { ThreatBucketIndex.bucket(flaggedH1, 25) }
        assertFailsWith<IllegalArgumentException> { ThreatBucketIndex.bucket("abc", 22) }
        assertFailsWith<IllegalArgumentException> { ThreatBucketIndex.bucket("g".repeat(64), 22) }
    }

    @Test
    fun containsMatchesListedBucketsOnly() {
        val listed = ThreatBucketIndex.bucket(flaggedH1, 22)
        val index = ThreatBucketIndex.fromPacked(pack(5, listed, (1 shl 22) - 1), 22)
        assertEquals(3, index.count)
        assertTrue(index.contains(flaggedH1))
        // Same first 24 bits ⇒ same bucket, whatever follows: that is what makes the list k-anonymous.
        assertTrue(index.contains(flaggedH1.take(6) + "0".repeat(58)))
        assertFalse(index.contains("bb1b1fcd" + "0".repeat(56)))
    }

    @Test
    fun emptyAndMalformedNeverMatchAndNeverThrow() {
        assertFalse(ThreatBucketIndex.EMPTY.contains(flaggedH1))
        val index = ThreatBucketIndex.fromPacked(pack(0), 22)
        assertTrue(index.contains("0".repeat(64)))
        assertFalse(index.contains(""))
        assertFalse(index.contains("zz".repeat(32)))
        assertFalse(index.contains("0".repeat(63)))
    }

    @Test
    fun emptyPayloadIsAValidEmptyList() {
        val index = ThreatBucketIndex.fromPacked(ByteArray(0), 22, expectedCount = 0)
        assertEquals(0, index.count)
        assertFalse(index.contains(flaggedH1))
    }

    @Test
    fun corruptPayloadsAreRejected() {
        assertFailsWith<IllegalArgumentException> { ThreatBucketIndex.fromPacked(ByteArray(4), 22) }
        assertFailsWith<IllegalArgumentException> { ThreatBucketIndex.fromPacked(pack(1, 2), 22, expectedCount = 3) }
        assertFailsWith<IllegalArgumentException> { ThreatBucketIndex.fromPacked(pack(2, 1), 22) }
        assertFailsWith<IllegalArgumentException> { ThreatBucketIndex.fromPacked(pack(1, 1), 22) }
        assertFailsWith<IllegalArgumentException> { ThreatBucketIndex.fromPacked(pack(1 shl 22), 22) }
        assertFailsWith<IllegalArgumentException> { ThreatBucketIndex.fromPacked(pack(1), 15) }
        assertFailsWith<IllegalArgumentException> { ThreatBucketIndex.fromPacked(pack(1), 25) }
    }

    private fun distinctSorted(random: Random, n: Int, bits: Int): IntArray {
        val set = java.util.TreeSet<Int>()
        while (set.size < n) set.add(random.nextInt(1 shl bits))
        return set.toIntArray()
    }

    @Test
    fun lookupIsFastWith100kBuckets() {
        val random = Random(26)
        val index = ThreatBucketIndex.fromPacked(pack(*distinctSorted(random, 100_000, 22)), 22)
        assertEquals(100_000, index.count)
        val probes = List(20_000) { randomH1(random) }
        repeat(2) { probes.forEach(index::contains) } // warm the JIT: the real service is warm after the first calls
        val nanos = LongArray(probes.size)
        probes.forEachIndexed { i, h1 ->
            val t0 = System.nanoTime()
            index.contains(h1)
            nanos[i] = System.nanoTime() - t0
        }
        nanos.sort()
        val p99Ms = nanos[(nanos.size * 99) / 100] / 1e6
        println("ThreatBucketIndex.contains p99 = $p99Ms ms over ${probes.size} lookups, ${index.count} buckets")
        assertTrue(p99Ms <= 5.0, "p99 $p99Ms ms > 5 ms")
    }

    // SC-004: the false-match rate of a random stranger is N / 2^bits (to within 30%). Counted over 100,000 fictional h1.
    @Test
    fun falseMatchRateIsAboutNOver2PowBits() {
        val random = Random(27)
        val bits = 22
        val listed = 10_000
        val index = ThreatBucketIndex.fromPacked(pack(*distinctSorted(random, listed, bits)), bits)
        val queries = 100_000
        val hits = (0 until queries).count { index.contains(randomH1(random)) }
        val expected = queries.toDouble() * listed / (1 shl bits)
        println("false matches: $hits of $queries (expected ≈ $expected)")
        assertTrue(hits in (expected * 0.7).toInt()..(expected * 1.3).toInt(), "hits=$hits expected≈$expected")
    }
}
