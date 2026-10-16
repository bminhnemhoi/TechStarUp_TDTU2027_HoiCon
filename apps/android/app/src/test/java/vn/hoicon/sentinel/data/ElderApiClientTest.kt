package vn.hoicon.sentinel.data

import com.sun.net.httpserver.HttpServer
import java.net.InetSocketAddress
import org.junit.After
import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertIs
import org.json.JSONObject
import vn.hoicon.sentinel.data.remote.ElderAnswer
import vn.hoicon.sentinel.data.remote.ElderAnswerResult
import vn.hoicon.sentinel.data.remote.ElderApiClient
import vn.hoicon.sentinel.data.remote.PendingQuestionResult
import vn.hoicon.sentinel.work.elderAnswerNeedsRetry
import kotlin.test.assertFalse
import kotlin.test.assertTrue

/** Test client API E8 với local mock HTTP server (spec 024, FR-009). */
class ElderApiClientTest {
    private class Seen(val method: String, val path: String, val auth: String?, val body: String)

    private var server: HttpServer? = null
    private var seen: Seen? = null

    @After
    fun stop() = server?.stop(0) ?: Unit

    private fun serve(status: Int, reply: String): ElderApiClient {
        val s = HttpServer.create(InetSocketAddress("127.0.0.1", 0), 0)
        s.createContext("/") { ex ->
            seen = Seen(
                ex.requestMethod,
                ex.requestURI.path,
                ex.requestHeaders.getFirst("Authorization"),
                ex.requestBody.readBytes().toString(Charsets.UTF_8),
            )
            val bytes = reply.toByteArray(Charsets.UTF_8)
            ex.responseHeaders.add("Content-Type", "application/json")
            ex.sendResponseHeaders(status, if (bytes.isEmpty()) -1 else bytes.size.toLong())
            if (bytes.isNotEmpty()) ex.responseBody.use { it.write(bytes) }
            ex.close()
        }
        s.start()
        server = s
        return ElderApiClient("http://127.0.0.1:${s.address.port}", timeoutMs = 2_000)
    }

    @Test
    fun submitAnswer_accepted() {
        val client = serve(200, """{"status": "accepted", "incident_id": "01851bd2-0000-7000-8000-000000000001", "level": "critical"}""")
        val result = client.submitAnswer(
            accessToken = "test-token",
            incidentId = "01851bd2-0000-7000-8000-000000000001",
            answer = ElderAnswer(questionId = "q_caller_authority", answer = "yes"),
        )
        assertIs<ElderAnswerResult.Accepted>(result)
        assertEquals("critical", result.level)
        assertEquals("POST", seen?.method)
        assertEquals("/v1/incidents/01851bd2-0000-7000-8000-000000000001/answers", seen?.path)
        assertEquals("Bearer test-token", seen?.auth)

        val sentBody = JSONObject(seen?.body ?: "{}")
        assertEquals("q_caller_authority", sentBody.getString("question_id"))
        assertEquals("yes", sentBody.getString("answer"))
    }

    @Test
    fun submitAnswer_expired() {
        val client = serve(200, """{"status": "expired", "incident_id": "01851bd2-0000-7000-8000-000000000001"}""")
        val result = client.submitAnswer(
            accessToken = "test-token",
            incidentId = "01851bd2-0000-7000-8000-000000000001",
            answer = ElderAnswer(questionId = "q_asked_transfer", answer = "timeout"),
        )
        assertIs<ElderAnswerResult.Expired>(result)
    }

    @Test
    fun submitAnswer_unauthorized() {
        val client = serve(401, """{"detail": "Token không hợp lệ"}""")
        val result = client.submitAnswer(
            accessToken = "bad-token",
            incidentId = "01851bd2-0000-7000-8000-000000000001",
            answer = ElderAnswer(questionId = "q_know_caller", answer = "no"),
        )
        assertIs<ElderAnswerResult.Unauthorized>(result)
    }

    @Test
    fun getPendingQuestion_success() {
        val client = serve(
            200,
            """{
                "incident_id": "01851bd2-0000-7000-8000-000000000001",
                "question_id": "q_caller_authority",
                "text": "Đây là trợ lý AI HỏiCon. Người đang gọi có tự xưng là công an không ạ?",
                "is_drill": false,
                "answers": ["yes", "no", "unsure"],
                "expires_at": "2026-10-16T12:01:00Z"
            }""",
        )
        val result = client.getPendingQuestion("test-token", "01851bd2-0000-7000-8000-000000000001")
        assertIs<PendingQuestionResult.Question>(result)
        val q = result.question
        assertEquals("01851bd2-0000-7000-8000-000000000001", q.incidentId)
        assertEquals("q_caller_authority", q.questionId)
        assertEquals("Đây là trợ lý AI HỏiCon. Người đang gọi có tự xưng là công an không ạ?", q.text)
        assertEquals(false, q.isDrill)
        assertEquals(listOf("yes", "no", "unsure"), q.answers)
    }

    @Test
    fun getPendingQuestion_noQuestion() {
        val client = serve(404, """{"detail": "Không có câu hỏi nào đang chờ"}""")
        val result = client.getPendingQuestion("test-token", "01851bd2-0000-7000-8000-000000000001")
        assertIs<PendingQuestionResult.NoQuestion>(result)
    }

    @Test
    fun submitAnswer_serverAndNetworkErrorsAreRetried() {
        val answer = ElderAnswer(questionId = "q_know_caller", answer = "no")
        val failed = serve(503, """{"detail": "Hệ thống đang bận"}""")
            .submitAnswer("test-token", "01851bd2-0000-7000-8000-000000000001", answer)
        assertIs<ElderAnswerResult.ServerError>(failed)
        val port = requireNotNull(server).address.port
        server?.stop(0)
        server = null // nothing listens on the port any more
        val offline = ElderApiClient("http://127.0.0.1:$port", timeoutMs = 500)
            .submitAnswer("test-token", "01851bd2-0000-7000-8000-000000000001", answer)
        assertIs<ElderAnswerResult.NetworkError>(offline)

        assertTrue(elderAnswerNeedsRetry(failed))
        assertTrue(elderAnswerNeedsRetry(offline))
        // An answer the server understood is final, even a late one.
        assertFalse(elderAnswerNeedsRetry(ElderAnswerResult.Accepted("high")))
        assertFalse(elderAnswerNeedsRetry(ElderAnswerResult.Expired))
        assertFalse(elderAnswerNeedsRetry(ElderAnswerResult.AlreadyResolved))
        assertFalse(elderAnswerNeedsRetry(ElderAnswerResult.Unauthorized))
    }
}
