package vn.hoicon.sentinel.data

import kotlinx.coroutines.runBlocking
import org.junit.Test
import vn.hoicon.sentinel.data.drill.DrillCheck
import vn.hoicon.sentinel.data.drill.DrillInvitation
import vn.hoicon.sentinel.data.drill.DrillStore
import vn.hoicon.sentinel.data.remote.DrillGateway
import vn.hoicon.sentinel.data.remote.DrillOffer
import vn.hoicon.sentinel.data.remote.DrillOfferResult
import vn.hoicon.sentinel.data.remote.DrillOffers
import vn.hoicon.sentinel.data.remote.DrillResultOutcome
import vn.hoicon.sentinel.data.remote.DrillStatus
import vn.hoicon.sentinel.domain.drill.DrillAnswer
import kotlin.test.assertEquals
import kotlin.test.assertIs
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

/** Spec 028 T015: when the phone asks for a drill, and what it remembers so it does not nag. */
class DrillInvitationTest {
    private val json = """{"drill_id":"drl-0001","is_drill":true,"window_end":"2026-10-16T10:30:00+07:00","script":{
        "id":"drill_mau","scenario_ref":"scn_mau","title":"Mẫu","agency_fictional":"Phòng Điều tra Mẫu","steps":[
        {"line_vi":"Một","choices":[{"id":"a","label_vi":"A","correct":true,"feedback_vi":"f"},{"id":"b","label_vi":"B","correct":false,"feedback_vi":"f"}]},
        {"line_vi":"Hai","choices":[{"id":"a","label_vi":"A","correct":false,"feedback_vi":"f"},{"id":"b","label_vi":"B","correct":true,"feedback_vi":"f"}]}],
        "debrief":{"red_flags_vi":["x"],"praise_vi":"y"}}}"""
    private val offer: DrillOffer = assertNotNull(DrillOffers.parse(json))

    private class FakeGateway(var reply: DrillOfferResult) : DrillGateway {
        var asked = 0
        override fun fetchOffer(accessToken: String): DrillOfferResult { asked++; return reply }
        override fun sendResult(accessToken: String, drillId: String, status: DrillStatus, answers: List<DrillAnswer>, startedAt: String?, completedAt: String?) =
            DrillResultOutcome.Accepted
    }

    private class MemoryStore : DrillStore {
        var saved: DrillOffer? = null
        override var notifiedDrillId: String? = null
        override var handledDrillId: String? = null
        override fun pending() = saved
        override fun savePending(offer: DrillOffer) { saved = offer }
        override fun markHandled(drillId: String) { saved = null; handledDrillId = drillId }
        override fun clearAll() { saved = null; notifiedDrillId = null; handledDrillId = null }
    }

    private fun invitation(
        gateway: FakeGateway,
        store: MemoryStore = MemoryStore(),
        mayShare: Boolean = true,
        windowOpen: Boolean = false,
    ) = DrillInvitation(gateway, store, { mayShare }, { windowOpen })

    private fun check(invitation: DrillInvitation) = runBlocking { invitation.check("tok") }

    @Test
    fun withoutPermissionToShareNothingIsAsked() {
        val gateway = FakeGateway(DrillOfferResult.Offer(offer))
        assertEquals(DrillCheck.NotAllowed, check(invitation(gateway, mayShare = false)))
        assertEquals(0, gateway.asked)
    }

    @Test
    fun anOpenRiskWindowPostponesTheInvitation() {
        val gateway = FakeGateway(DrillOfferResult.Offer(offer))
        val store = MemoryStore()
        assertEquals(DrillCheck.Deferred, check(invitation(gateway, store, windowOpen = true)))
        assertEquals(0, gateway.asked)
        assertNull(store.saved); assertNull(store.notifiedDrillId)
    }

    @Test
    fun clearingTheStoreForgetsTheOldFamily() {
        val store = MemoryStore().also { it.savePending(offer); it.notifiedDrillId = "drl-0001"; it.markHandled("drl-0001") }
        store.clearAll()
        assertNull(store.saved); assertNull(store.notifiedDrillId); assertNull(store.handledDrillId)
    }

    @Test
    fun theFirstOfferIsSavedAndNotifiedOnce() {
        val gateway = FakeGateway(DrillOfferResult.Offer(offer))
        val store = MemoryStore()
        val first = assertIs<DrillCheck.Invite>(check(invitation(gateway, store)))
        assertTrue(first.firstTime)
        assertEquals("drl-0001", store.saved?.drillId)
        // The worker marks a drill as notified only once the notification was really shown: until then the next beat tries again.
        assertTrue(assertIs<DrillCheck.Invite>(check(invitation(gateway, store))).firstTime)
        store.notifiedDrillId = "drl-0001"
        // 15 minutes later the server still offers it: the notification is not shown a second time.
        assertEquals(false, assertIs<DrillCheck.Invite>(check(invitation(gateway, store))).firstTime)
    }

    @Test
    fun aDrillTheServerHasNotHeardAnswerToYetIsNotOfferedAgain() {
        val gateway = FakeGateway(DrillOfferResult.Offer(offer))
        val store = MemoryStore().also { it.markHandled("drl-0001") }
        assertEquals(DrillCheck.Nothing, check(invitation(gateway, store)))
        assertNull(store.saved)
    }

    @Test
    fun aNewDrillAfterAnAnsweredOneIsOffered() {
        val gateway = FakeGateway(DrillOfferResult.Offer(offer))
        val store = MemoryStore().also { it.markHandled("drl-0000"); it.notifiedDrillId = "drl-0000" }
        assertTrue(assertIs<DrillCheck.Invite>(check(invitation(gateway, store))).firstTime)
    }

    @Test
    fun noOfferMeansNothing() {
        assertEquals(DrillCheck.Nothing, check(invitation(FakeGateway(DrillOfferResult.NoOffer))))
    }

    @Test
    fun troubleNeverBecomesAnException() {
        assertEquals(DrillCheck.Failed, check(invitation(FakeGateway(DrillOfferResult.NetworkError))))
        assertEquals(DrillCheck.Failed, check(invitation(FakeGateway(DrillOfferResult.ServerError))))
        assertEquals(DrillCheck.Unauthorized, check(invitation(FakeGateway(DrillOfferResult.Unauthorized))))
    }
}
