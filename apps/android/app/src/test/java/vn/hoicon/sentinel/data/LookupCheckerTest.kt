package vn.hoicon.sentinel.data

import org.junit.Test
import vn.hoicon.rules.HashedPhone
import vn.hoicon.rules.PhoneHasher
import vn.hoicon.rules.ThreatBucketIndex
import vn.hoicon.sentinel.data.lookup.LookupChecker
import vn.hoicon.sentinel.data.lookup.LookupInput
import vn.hoicon.sentinel.data.lookup.LookupOutcome
import vn.hoicon.sentinel.data.lookup.NoticeReason
import vn.hoicon.sentinel.data.remote.LookupAnswer
import vn.hoicon.sentinel.data.remote.LookupGateway
import vn.hoicon.sentinel.data.remote.LookupKind
import vn.hoicon.sentinel.data.remote.LookupReason
import vn.hoicon.sentinel.data.remote.LookupResult
import vn.hoicon.sentinel.data.remote.LookupVerdict
import vn.hoicon.sentinel.data.remote.LookupVia
import vn.hoicon.sentinel.data.threat.ThreatIndexHolder
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertIs
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/** Spec 026 T025: input parsing, and the outcome for every way a lookup can end (never "safe" for a phone). */
class LookupCheckerTest {
    // Fictional numbers of data/fixtures/phones.json.
    private val flagged = assertNotNull(PhoneHasher.hash("0900000002"))
    private val stranger = assertNotNull(PhoneHasher.hash("0900000001"))

    private fun answer(kind: LookupKind = LookupKind.PHONE, verdict: LookupVerdict = LookupVerdict.DANGEROUS) = LookupAnswer(
        verificationId = "01851bd2-0000-7000-8000-0000000000aa", kind = kind, verdict = verdict, confidence = 0.9,
        reasons = listOf(LookupReason("listed_high", "…")), sources = emptyList(),
        disclaimer = "Đây là trợ lý AI HỏiCon.", incidentLevel = null, isDemo = false,
    )

    private class FakeGateway(var results: MutableList<LookupResult>) : LookupGateway {
        val incidents = mutableListOf<String?>()
        val vias = mutableListOf<LookupVia>()
        override fun lookupPhone(accessToken: String, phone: HashedPhone, via: LookupVia, incidentId: String?): LookupResult {
            incidents += incidentId; vias += via; return results.removeAt(0)
        }
        override fun lookupUrl(accessToken: String, rawUrl: String, via: LookupVia, incidentId: String?): LookupResult {
            incidents += incidentId; vias += via; return results.removeAt(0)
        }
    }

    private fun holderWith(h1: String): ThreatIndexHolder {
        val bucket = ThreatBucketIndex.bucket(h1, 22)
        val bytes = byteArrayOf((bucket ushr 16).toByte(), (bucket ushr 8).toByte(), bucket.toByte())
        return ThreatIndexHolder().also { it.swap(ThreatBucketIndex.fromPacked(bytes, 22)) }
    }

    private fun checker(
        gateway: LookupGateway,
        holder: ThreatIndexHolder = ThreatIndexHolder(),
        token: String? = "tok",
        consent: () -> Boolean = { false },
        unauthorized: () -> Unit = {},
    ) = LookupChecker(gateway, holder, { token }, consent, unauthorized)

    // ---- input ----

    @Test
    fun aTypedPhoneIsHashedAndTheRawTextIsGone() {
        for (typed in listOf("0900000002", "0900 000 002", "+84 900.000.002", "tel:0900000002", " (090) 0000-002 ")) {
            val parsed = LookupInput.parse(typed)
            assertIs<LookupInput.Phone>(parsed, typed)
            assertEquals(flagged.h1, parsed.phone.h1, typed)
            assertEquals("002", parsed.phone.last3)
            assertFalse("0900000002" in parsed.toString(), "the input must not print the number")
        }
    }

    @Test
    fun aLinkIsCutAndItsHostIsKept() {
        val parsed = LookupInput.parse("https://Bit.ly/abc?token=SECRET")
        assertIs<LookupInput.Link>(parsed)
        assertEquals("https://bit.ly/abc", parsed.url)
        assertEquals("bit.ly", parsed.host)
        assertEquals("example.org", assertIs<LookupInput.Link>(LookupInput.parse("example.org:8080/x")).host.substringBefore(':'))
    }

    @Test
    fun aScannedCodeIsSentWithViaQr() {
        val gateway = FakeGateway(mutableListOf(LookupResult.Done(answer(LookupKind.URL, LookupVerdict.UNKNOWN))))
        checker(gateway).check(LookupInput.parse("https://chinhphu-mau.vn/x"), via = LookupVia.QR)
        assertEquals(listOf(LookupVia.QR), gateway.vias)
    }

    @Test
    fun aNumberWithAStrayLetterIsNotSentAsALink() {
        for (typed in listOf("0900000002a", "SDT0900000002", "0900 000 002 abc")) {
            assertEquals(LookupInput.BadPhone, LookupInput.parse(typed), typed)
        }
        assertIs<LookupInput.Link>(LookupInput.parse("zalo.me/0900000002")).also { assertEquals("https://zalo.me/*", it.url) }
    }

    @Test
    fun badInputIsNamedNotGuessed() {
        assertEquals(LookupInput.Empty, LookupInput.parse("   "))
        assertEquals(LookupInput.BadPhone, LookupInput.parse("12345"))
        assertEquals(LookupInput.BadPhone, LookupInput.parse("+000 111"))
        assertEquals(LookupInput.BadLink, LookupInput.parse("javascript:alert(1)"))
        assertEquals(LookupInput.BadLink, LookupInput.parse("khong phai link"))
    }

    // ---- outcomes ----

    @Test
    fun anAnswerIsPassedOnWithTheSubject() {
        val gw = FakeGateway(mutableListOf(LookupResult.Done(answer())))
        val out = checker(gw).check(LookupInput.parse("0900000002"))
        assertIs<LookupOutcome.Answer>(out)
        assertEquals("002", out.subject); assertEquals(LookupKind.PHONE, out.kind)
    }

    @Test
    fun noConnectionFallsBackToTheBucketListAndNeverSaysSafe() {
        val matched = checker(FakeGateway(mutableListOf(LookupResult.NetworkError)), holderWith(flagged.h1)).check(LookupInput.Phone(flagged))
        assertEquals(LookupOutcome.Offline(LookupKind.PHONE, "002", possiblyListed = true), matched)
        val other = checker(FakeGateway(mutableListOf(LookupResult.NetworkError)), holderWith(flagged.h1)).check(LookupInput.Phone(stranger))
        assertEquals(LookupOutcome.Offline(LookupKind.PHONE, "001", possiblyListed = false), other)
        // A server error is treated like no connection (plan flow 1).
        val serverDown = checker(FakeGateway(mutableListOf(LookupResult.ServerError)), holderWith(flagged.h1)).check(LookupInput.Phone(flagged))
        assertEquals(true, assertIs<LookupOutcome.Offline>(serverDown).possiblyListed)
    }

    @Test
    fun aLinkOfflineIsNeverMarkedListed() {
        val out = checker(FakeGateway(mutableListOf(LookupResult.NetworkError)), holderWith(flagged.h1)).check(LookupInput.parse("example.org"))
        assertEquals(LookupOutcome.Offline(LookupKind.URL, "example.org", possiblyListed = false), out)
    }

    @Test
    fun notPairedMeansOfflineWithoutCallingTheServer() {
        val gw = FakeGateway(mutableListOf())
        val out = checker(gw, holderWith(flagged.h1), token = null).check(LookupInput.Phone(flagged))
        assertEquals(true, assertIs<LookupOutcome.Offline>(out).possiblyListed)
        assertTrue(gw.incidents.isEmpty())
    }

    @Test
    fun aRefusedTokenFallsBackAndFlagsRepair() {
        var flagged = false
        val out = checker(FakeGateway(mutableListOf(LookupResult.Unauthorized)), unauthorized = { flagged = true }).check(LookupInput.Phone(stranger))
        assertIs<LookupOutcome.Offline>(out); assertTrue(flagged)
    }

    @Test
    fun aMissingConsentIsSyncedOnceAndTheCheckRetried() {
        var synced = 0
        val gw = FakeGateway(mutableListOf(LookupResult.ConsentRequired, LookupResult.Done(answer())))
        val out = checker(gw, consent = { synced++; true }).check(LookupInput.Phone(flagged))
        assertIs<LookupOutcome.Answer>(out); assertEquals(1, synced); assertEquals(2, gw.incidents.size)
    }

    @Test
    fun aConsentThatStillIsNotThereIsAnHonestNotice() {
        val gw = FakeGateway(mutableListOf(LookupResult.ConsentRequired, LookupResult.ConsentRequired))
        assertEquals(LookupOutcome.Notice(NoticeReason.CONSENT_PENDING), checker(gw, consent = { true }).check(LookupInput.Phone(flagged)))
        val gw2 = FakeGateway(mutableListOf(LookupResult.ConsentRequired))
        assertEquals(LookupOutcome.Notice(NoticeReason.CONSENT_PENDING), checker(gw2, consent = { false }).check(LookupInput.Phone(flagged)))
        assertEquals(1, gw2.incidents.size, "no retry when the ledger could not be brought up to date")
    }

    @Test
    fun aLimitAndARejectionAreNoticesNotResults() {
        assertEquals(LookupOutcome.Notice(NoticeReason.RATE_LIMITED), checker(FakeGateway(mutableListOf(LookupResult.RateLimited(30)))).check(LookupInput.Phone(flagged)))
        assertEquals(LookupOutcome.Notice(NoticeReason.GENERIC), checker(FakeGateway(mutableListOf(LookupResult.Rejected))).check(LookupInput.Phone(flagged)))
    }

    @Test
    fun aGoneIncidentIsDroppedAndTheCheckStands() {
        val gw = FakeGateway(mutableListOf(LookupResult.IncidentNotFound, LookupResult.Done(answer())))
        val out = checker(gw).check(LookupInput.Phone(flagged), incidentId = "01851bd2-0000-7000-8000-000000000001")
        assertIs<LookupOutcome.Answer>(out)
        assertEquals(listOf("01851bd2-0000-7000-8000-000000000001", null), gw.incidents)
    }
}
