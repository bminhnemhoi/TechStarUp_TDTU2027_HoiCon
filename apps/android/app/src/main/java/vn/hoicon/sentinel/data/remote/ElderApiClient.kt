package vn.hoicon.sentinel.data.remote

import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import org.json.JSONArray
import org.json.JSONException
import org.json.JSONObject

data class ElderQuestion(
    val incidentId: String,
    val questionId: String,
    val text: String,
    val isDrill: Boolean,
    val answers: List<String>,
    val expiresAt: String,
)

data class ElderAnswer(
    val questionId: String,
    val answer: String,
    val noteFlags: Map<String, Boolean>? = null,
)

sealed interface ElderAnswerResult {
    data class Accepted(val level: String?) : ElderAnswerResult
    data object Expired : ElderAnswerResult
    data object AlreadyResolved : ElderAnswerResult
    data object Unauthorized : ElderAnswerResult
    data object NetworkError : ElderAnswerResult
    data object ServerError : ElderAnswerResult
}

sealed interface PendingQuestionResult {
    data class Question(val question: ElderQuestion) : PendingQuestionResult
    data object NoQuestion : PendingQuestionResult
    data object Unauthorized : PendingQuestionResult
    data object NetworkError : PendingQuestionResult
    data object ServerError : PendingQuestionResult
}

/**
 * Client kết nối API câu hỏi nhanh E8: `POST /v1/incidents/{id}/answers` và `GET /v1/incidents/{id}/pending-question`.
 * Không ghi log nội dung hay token. Chạy trên background thread (blocking HTTP).
 */
class ElderApiClient(
    baseUrl: String,
    private val timeoutMs: Int = 10_000,
) {
    private val base = baseUrl.trimEnd('/')

    fun submitAnswer(accessToken: String, incidentId: String, answer: ElderAnswer): ElderAnswerResult {
        val payload = JSONObject()
            .put("question_id", answer.questionId)
            .put("answer", answer.answer)

        if (answer.noteFlags != null) {
            val flags = JSONObject()
            for ((k, v) in answer.noteFlags) {
                flags.put(k, v)
            }
            payload.put("note_flags", flags)
        }

        val url = "$base/v1/incidents/$incidentId/answers"
        val reply = try {
            post(url, payload, accessToken)
        } catch (_: IOException) {
            return ElderAnswerResult.NetworkError
        }

        return when (reply.status) {
            200 -> {
                val body = reply.body
                val status = body?.optString("status")
                val level = body?.optString("level")
                when (status) {
                    "accepted" -> ElderAnswerResult.Accepted(level)
                    "expired" -> ElderAnswerResult.Expired
                    "already_resolved" -> ElderAnswerResult.AlreadyResolved
                    else -> ElderAnswerResult.ServerError
                }
            }
            401, 403 -> ElderAnswerResult.Unauthorized
            404 -> ElderAnswerResult.Expired
            else -> ElderAnswerResult.ServerError
        }
    }

    fun getPendingQuestion(accessToken: String, incidentId: String): PendingQuestionResult {
        val url = "$base/v1/incidents/$incidentId/pending-question"
        val reply = try {
            get(url, accessToken)
        } catch (_: IOException) {
            return PendingQuestionResult.NetworkError
        }

        return when (reply.status) {
            200 -> {
                val body = reply.body ?: return PendingQuestionResult.ServerError
                try {
                    val answersArray = body.getJSONArray("answers")
                    val answersList = mutableListOf<String>()
                    for (i in 0 until answersArray.length()) {
                        answersList.add(answersArray.getString(i))
                    }
                    val question = ElderQuestion(
                        incidentId = body.getString("incident_id"),
                        questionId = body.getString("question_id"),
                        text = body.getString("text"),
                        isDrill = body.optBoolean("is_drill", false),
                        answers = answersList,
                        expiresAt = body.optString("expires_at", ""),
                    )
                    PendingQuestionResult.Question(question)
                } catch (_: JSONException) {
                    PendingQuestionResult.ServerError
                }
            }
            401, 403 -> PendingQuestionResult.Unauthorized
            404 -> PendingQuestionResult.NoQuestion
            else -> PendingQuestionResult.ServerError
        }
    }

    private fun post(urlString: String, body: JSONObject, bearer: String): HttpResponse {
        val connection = (URL(urlString).openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = timeoutMs
            readTimeout = timeoutMs
            doOutput = true
            setRequestProperty("Content-Type", "application/json; charset=UTF-8")
            setRequestProperty("Accept", "application/json")
            setRequestProperty("Authorization", "Bearer $bearer")
        }
        val bytes = body.toString().toByteArray(Charsets.UTF_8)
        connection.setFixedLengthStreamingMode(bytes.size)
        connection.outputStream.use { it.write(bytes) }
        return readResponse(connection)
    }

    private fun get(urlString: String, bearer: String): HttpResponse {
        val connection = (URL(urlString).openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = timeoutMs
            readTimeout = timeoutMs
            setRequestProperty("Accept", "application/json")
            setRequestProperty("Authorization", "Bearer $bearer")
        }
        return readResponse(connection)
    }

    private fun readResponse(connection: HttpURLConnection): HttpResponse {
        val status = connection.responseCode
        val stream = if (status in 200..299) connection.inputStream else connection.errorStream
        val text = stream?.bufferedReader()?.use { it.readText() }
        val body = text?.takeIf { it.isNotBlank() }?.let {
            try {
                JSONObject(it)
            } catch (_: JSONException) {
                null
            }
        }
        return HttpResponse(status, body)
    }

    private data class HttpResponse(val status: Int, val body: JSONObject?)
}
