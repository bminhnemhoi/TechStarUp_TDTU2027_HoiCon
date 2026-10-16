package vn.hoicon.sentinel.data.remote

import java.io.IOException
import java.io.InputStream
import java.net.HttpURLConnection
import java.net.URL
import org.json.JSONObject

/** One HTTP answer: status, the (size-capped) body text and the `Retry-After` header in seconds when present. */
internal class JsonReply(val status: Int, val body: String, val retryAfterSeconds: Int?)

/**
 * The few lines of `HttpURLConnection` the lookup and threat-list clients share (Spec 026). Blocking: background threads
 * only. No redirects (a redirect would resend the Authorization header elsewhere), no cache, and a hard cap on how
 * much of a reply is buffered. Nothing is logged: URLs, bodies and tokens are never written anywhere.
 */
internal class JsonHttp(baseUrl: String, private val timeoutMs: Int) {
    private val base = baseUrl.trimEnd('/')

    /** @throws IOException on connection, timeout or TLS failure. */
    fun send(method: String, path: String, bearer: String, body: JSONObject?, maxReply: Int): JsonReply {
        val connection = URL(base + path).openConnection() as HttpURLConnection
        try {
            connection.requestMethod = method
            connection.connectTimeout = timeoutMs
            connection.readTimeout = timeoutMs
            connection.useCaches = false
            connection.instanceFollowRedirects = false
            connection.setRequestProperty("Accept", "application/json")
            connection.setRequestProperty("Authorization", "Bearer $bearer")
            if (body != null) {
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json; charset=utf-8")
                connection.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
            }
            val status = connection.responseCode
            val retryAfter = connection.getHeaderField("Retry-After")?.trim()?.toIntOrNull()?.takeIf { it in 0..MAX_RETRY_AFTER }
            val stream = if (status in 200..299) connection.inputStream else connection.errorStream
            val text = if (status == 304) "" else stream?.use { readCapped(it, maxReply) }.orEmpty()
            return JsonReply(status, text, retryAfter)
        } finally {
            connection.disconnect()
        }
    }

    private fun readCapped(stream: InputStream, max: Int): String {
        val out = java.io.ByteArrayOutputStream()
        val chunk = ByteArray(8 * 1024)
        while (out.size() < max) {
            val n = stream.read(chunk, 0, minOf(chunk.size, max - out.size()))
            if (n < 0) break
            out.write(chunk, 0, n)
        }
        return out.toString(Charsets.UTF_8.name())
    }

    private companion object {
        const val MAX_RETRY_AFTER = 86_400
    }
}
