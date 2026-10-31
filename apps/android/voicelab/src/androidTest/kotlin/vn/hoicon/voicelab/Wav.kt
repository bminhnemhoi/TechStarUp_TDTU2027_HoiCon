package vn.hoicon.voicelab

import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder

/** Minimal RIFF/WAVE reader: finds `fmt ` and `data` chunks (the header is not always 44 bytes). */
class Wav(val sampleRate: Int, val channels: Int, val bitsPerSample: Int, val pcm: ByteArray) {
    val durationMs: Long get() = pcm.size * 1000L / (sampleRate * channels * (bitsPerSample / 8))

    companion object {
        fun read(file: File): Wav {
            val bytes = file.readBytes()
            require(bytes.size > 44 && String(bytes, 0, 4) == "RIFF" && String(bytes, 8, 4) == "WAVE") { "not a WAV file" }
            val buf = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
            var pos = 12
            var rate = 0
            var channels = 0
            var bits = 0
            var pcmFormat = false
            while (pos + 8 <= bytes.size) {
                val id = String(bytes, pos, 4)
                val size = buf.getInt(pos + 4)
                val body = pos + 8
                when (id) {
                    "fmt " -> {
                        pcmFormat = buf.getShort(body).toInt() == 1
                        channels = buf.getShort(body + 2).toInt()
                        rate = buf.getInt(body + 4)
                        bits = buf.getShort(body + 14).toInt()
                    }
                    "data" -> {
                        require(pcmFormat) { "not PCM" }
                        val len = if (size < 0 || body + size > bytes.size) bytes.size - body else size
                        return Wav(rate, channels, bits, bytes.copyOfRange(body, body + len))
                    }
                }
                pos = body + size + (size and 1)
            }
            error("no data chunk")
        }
    }
}
