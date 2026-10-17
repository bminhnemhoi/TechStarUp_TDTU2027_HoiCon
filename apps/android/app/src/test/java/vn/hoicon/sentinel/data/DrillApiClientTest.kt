package vn.hoicon.sentinel.data

import com.sun.net.httpserver.HttpServer
import java.net.InetSocketAddress
import org.json.JSONObject
import org.junit.After
import org.junit.Test
import vn.hoicon.sentinel.data.remote.DrillApiClient
import vn.hoicon.sentinel.data.remote.DrillOfferResult
import vn.hoicon.sentinel.data.remote.DrillOffers
import vn.hoicon.sentinel.data.remote.DrillResultOutcome
import vn.hoicon.sentinel.data.remote.DrillStatus
import vn.hoicon.sentinel.domain.drill.DrillAnswer
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertIs
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * Spec 028 T015/T016: the client's side of `GET /v1/drills/offer` and `POST /v1/drills/{id}/result` (drill_offer.v1,
 * drill_result.v1). The script is made up: a fictional agency and a three-digit tail, nothing real.
 */
class DrillApiClientTest {
    private var server: HttpServer? = null
    private var method: String? = null
    private var path: String? = null
    private var auth: String? = null
    private var sentBody: String? = null
    private var requests = 0

    @After
    fun stop() = server?.stop(0) ?: Unit

    private fun serve(status: Int, reply: String = ""): DrillApiClient {
        server?.stop(0)
        val s = HttpServer.create(InetSocketAddress("127.0.0.1", 0), 0)
        s.createContext("/") { ex ->
            requests++
            method = ex.requestMethod
            path = ex.requestURI.toString()
            auth = ex.requestHeaders.getFirst("Authorization")
            sentBody = ex.requestBody.readBytes().toString(Charsets.UTF_8)
            val bytes = reply.toByteArray()
            ex.sendResponseHeaders(status, if (bytes.isEmpty()) -1 else bytes.size.toLong())
            if (bytes.isNotEmpty()) ex.responseBody.use { it.write(bytes) }
            ex.close()
        }
        s.start(); server = s
        return DrillApiClient("http://127.0.0.1:${s.address.port}", timeoutMs = 2_000)
    }

    private fun choice(id: String, correct: Boolean) =
        """{"id":"$id","label_vi":"Lựa chọn $id","correct":$correct,"feedback_vi":"Phản hồi $id"}"""

    private fun step(line: String = "Bác ơi, tôi gọi từ Phòng Điều tra Mẫu.", choices: String = "${choice("a", true)},${choice("b", false)}") =
        """{"line_vi":"$line","choices":[$choices]}"""

    private fun drill(
        id: String = "drl-0001",
        isDrill: Boolean? = true,
        steps: String = "${step()},${step("Bác đọc mã xác thực cho tôi.")}",
    ) = """{"drill_id":"$id",${if (isDrill != null) "\"is_drill\":$isDrill," else ""}"window_end":"2026-10-16T10:30:00+07:00","script":{
        "id":"drill_mau_cong_an","scenario_ref":"scn_mau","title":"Giả danh cơ quan điều tra","agency_fictional":"Phòng Điều tra Mẫu",
        "caller_last3_fictional":"000","steps":[$steps],
        "debrief":{"red_flags_vi":["Dọa bắt giữ","Đòi mã xác thực"],"praise_vi":"Bác đã bình tĩnh."},"approved":false}}"""

    private fun offer(drillJson: String) = """{"drill":$drillJson}"""

    // ---- offer ----

    @Test
    fun anOfferIsParsedAndSentWithTheBearerToken() {
        val result = serve(200, offer(drill())).fetchOffer("tok")
        val offer = assertIs<DrillOfferResult.Offer>(result).offer
        assertEquals("drl-0001", offer.drillId)
        assertEquals("2026-10-16T10:30:00+07:00", offer.windowEnd)
        assertEquals(2, offer.script.steps.size)
        assertEquals("000", offer.script.callerLast3Fictional)
        assertEquals(listOf("Dọa bắt giữ", "Đòi mã xác thực"), offer.script.debrief.redFlagsVi)
        assertEquals("GET", method); assertEquals("/v1/drills/offer", path); assertEquals("Bearer tok", auth)
    }

    @Test
    fun theSavedJsonReadsBackToTheSameDrill() {
        val offer = assertIs<DrillOfferResult.Offer>(serve(200, offer(drill())).fetchOffer("t")).offer
        val again = assertNotNullOffer(DrillOffers.parse(offer.json))
        assertEquals(offer.script, again.script)
        assertEquals(offer.drillId, again.drillId)
    }

    private fun assertNotNullOffer(offer: vn.hoicon.sentinel.data.remote.DrillOffer?) = offer ?: error("saved offer did not parse")

    @Test
    fun noDrillMeansNoOffer() {
        assertIs<DrillOfferResult.NoOffer>(serve(200, """{"drill":null}""").fetchOffer("t"))
    }

    @Test
    fun statusesMapToResults() {
        assertIs<DrillOfferResult.Unauthorized>(serve(401).fetchOffer("t"))
        // 403 = not allowed for this family (no `drills` consent): nothing to offer, and never a "reconnect" for the person.
        assertIs<DrillOfferResult.NoOffer>(serve(403).fetchOffer("t"))
        assertIs<DrillOfferResult.ServerError>(serve(500).fetchOffer("t"))
        assertIs<DrillOfferResult.ServerError>(serve(404).fetchOffer("t"))
    }

    @Test
    fun anOfferThatBreaksTheContractIsNeverPlayed() {
        val broken = listOf(
            offer(drill(isDrill = false)),                                                  // not a drill
            offer(drill(isDrill = null)),                                                   // is_drill missing
            offer(drill(id = "../../x")),                                                   // an id that is not an id
            offer(drill(steps = step())),                                                   // one step
            offer(drill(steps = "${step(choices = "${choice("a", true)},${choice("b", false)},${choice("c", false)}")},${step()}")), // 3 choices
            offer(drill(steps = "${step(choices = "${choice("a", true)},${choice("b", true)}")},${step()}")), // two right
            offer(drill(steps = "${step(choices = "${choice("x1", true)},${choice("b", false)}")},${step()}")), // id "x1"
            offer(drill().replace("2026-10-16T10:30:00+07:00", "mai 10 giờ")),             // window_end that cannot be read
            offer(drill().replace(""""caller_last3_fictional":"000"""", """"caller_last3_fictional":"0900000002"""")), // a real-looking number
            offer(drill(steps = "${step(line = "x".repeat(401))},${step()}")),             // line longer than the contract
            offer(drill(steps = "${step(choices = "${choice("a", true).replace("Lựa chọn a", "L".repeat(41))},${choice("b", false)}")},${step()}")), // label > 40
            "not json", """{"drill":"text"}""", """{}""",
        )
        for (body in broken) {
            val result = serve(200, body).fetchOffer("t")
            assertTrue(result is DrillOfferResult.ServerError || result is DrillOfferResult.NoOffer, body)
            assertFalse(result is DrillOfferResult.Offer, body)
        }
    }

    @Test
    fun noConnectionIsANetworkErrorNotACrash() {
        val dead = DrillApiClient("http://127.0.0.1:1", timeoutMs = 500)
        assertIs<DrillOfferResult.NetworkError>(dead.fetchOffer("t"))
        assertIs<DrillResultOutcome.NetworkError>(dead.sendResult("t", "drl-0001", DrillStatus.DECLINED, emptyList()))
    }

    // ---- result ----

    @Test
    fun aResultCarriesOnlyTheStatusAndTheLettersOfTheChoices() {
        val client = serve(200)
        val outcome = client.sendResult(
            "tok", "drl-0001", DrillStatus.COMPLETED, listOf(DrillAnswer(0, "a"), DrillAnswer(1, "b")),
            startedAt = "2026-10-16T03:00:00Z", completedAt = "2026-10-16T03:02:00Z",
        )
        assertIs<DrillResultOutcome.Accepted>(outcome)
        assertEquals("POST", method); assertEquals("/v1/drills/drl-0001/result", path); assertEquals("Bearer tok", auth)
        val body = JSONObject(sentBody!!)
        assertEquals(setOf("drill_id", "status", "answers", "started_at", "completed_at"), body.keys().asSequence().toSet())
        assertEquals("completed", body.getString("status"))
        val answers = body.getJSONArray("answers")
        assertEquals(2, answers.length())
        assertEquals(setOf("step", "choice_id"), answers.getJSONObject(1).keys().asSequence().toSet())
        assertEquals(1, answers.getJSONObject(1).getInt("step")); assertEquals("b", answers.getJSONObject(1).getString("choice_id"))
    }

    @Test
    fun aDeclinedDrillSendsNoTimesAndNoAnswers() {
        serve(200).sendResult("t", "drl-0001", DrillStatus.DECLINED, emptyList())
        val body = JSONObject(sentBody!!)
        assertEquals("declined", body.getString("status"))
        assertEquals(0, body.getJSONArray("answers").length())
        assertFalse(body.has("started_at")); assertFalse(body.has("completed_at"))
    }

    @Test
    fun statusesOfTheResultMap() {
        fun outcome(status: Int) = serve(status).sendResult("t", "drl-0001", DrillStatus.ABORTED, emptyList())
        assertIs<DrillResultOutcome.Accepted>(outcome(200))
        assertIs<DrillResultOutcome.Accepted>(outcome(201))
        assertIs<DrillResultOutcome.Accepted>(outcome(204))
        assertIs<DrillResultOutcome.Accepted>(outcome(409)) // the server already holds a result for this drill
        assertIs<DrillResultOutcome.Unauthorized>(outcome(401))
        assertIs<DrillResultOutcome.Rejected>(outcome(403))
        assertIs<DrillResultOutcome.NotFound>(outcome(404))
        assertIs<DrillResultOutcome.Rejected>(outcome(400))
        assertIs<DrillResultOutcome.Rejected>(outcome(422))
        assertIs<DrillResultOutcome.ServerError>(outcome(500))
        assertIs<DrillResultOutcome.ServerError>(outcome(503))
    }

    @Test
    fun anIdThatIsNotAnIdNeverReachesTheUrl() {
        val client = serve(200)
        for (bad in listOf("../x", "a/b", "a b", "", "id?x=1", "a".repeat(65))) {
            assertIs<DrillResultOutcome.Rejected>(client.sendResult("t", bad, DrillStatus.DECLINED, emptyList()), bad)
        }
        assertEquals(0, requests)
        assertNull(path)
    }
}
