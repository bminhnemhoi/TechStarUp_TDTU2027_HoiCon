package vn.hoicon.sentinel.pause

import android.content.Context
import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import vn.hoicon.sentinel.data.remote.ElderQuestion
import vn.hoicon.sentinel.ui.ElderQuestionScreen
import vn.hoicon.sentinel.ui.theme.HoiConTheme
import vn.hoicon.sentinel.work.ElderAnswerScheduler

/**
 * Activity hiển thị màn hình E8 câu hỏi nhanh cho người cao tuổi.
 * Mở bằng [createIntent] (nội dung lấy từ `GET /v1/incidents/{id}/pending-question`). CHƯA có nơi mở nó: FCM chờ tài
 * khoản Firebase (P0-08) — xem specs/024-risk-and-intervention/evidence.md.
 * Câu trả lời giao cho WorkManager ([ElderAnswerScheduler]): màn hình đóng ngay, mất mạng thì gửi lại sau, không mất
 * khi Activity bị hủy giữa chừng.
 */
class ElderQuestionActivity : ComponentActivity() {

    private var answered = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        val incidentId = intent.getStringExtra(EXTRA_INCIDENT_ID) ?: ""
        val questionId = intent.getStringExtra(EXTRA_QUESTION_ID) ?: "q_asked_transfer"
        val text = intent.getStringExtra(EXTRA_TEXT) ?: "Đây là trợ lý AI HỏiCon. Bác có đang được yêu cầu chuyển tiền không ạ?"
        val isDrill = intent.getBooleanExtra(EXTRA_IS_DRILL, false)

        val question = ElderQuestion(
            incidentId = incidentId,
            questionId = questionId,
            text = text,
            isDrill = isDrill,
            answers = listOf("yes", "no", "unsure"),
            expiresAt = "",
        )

        setContent {
            HoiConTheme {
                ElderQuestionScreen(
                    question = question,
                    onAnswerSelected = { answer ->
                        submitAnswerAndFinish(incidentId, questionId, answer)
                    },
                    onTimeout = {
                        submitAnswerAndFinish(incidentId, questionId, "timeout")
                    },
                    onSpeakRequested = { speakText ->
                        Speaker.speak(this@ElderQuestionActivity, listOf(speakText))
                    },
                )
            }
        }
    }

    private fun submitAnswerAndFinish(incidentId: String, questionId: String, answer: String) {
        if (answered) return // bấm hai lần, hoặc hết giờ ngay sau khi bấm
        answered = true
        Speaker.stop()
        if (incidentId.isNotBlank()) ElderAnswerScheduler.submit(applicationContext, incidentId, questionId, answer)
        finish()
    }

    override fun onDestroy() {
        super.onDestroy()
        Speaker.stop()
    }

    companion object {
        const val EXTRA_INCIDENT_ID = "vn.hoicon.extra.INCIDENT_ID"
        const val EXTRA_QUESTION_ID = "vn.hoicon.extra.QUESTION_ID"
        const val EXTRA_TEXT = "vn.hoicon.extra.TEXT"
        const val EXTRA_IS_DRILL = "vn.hoicon.extra.IS_DRILL"

        fun createIntent(
            context: Context,
            incidentId: String,
            questionId: String,
            text: String,
            isDrill: Boolean = false,
        ): Intent {
            return Intent(context, ElderQuestionActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
                putExtra(EXTRA_INCIDENT_ID, incidentId)
                putExtra(EXTRA_QUESTION_ID, questionId)
                putExtra(EXTRA_TEXT, text)
                putExtra(EXTRA_IS_DRILL, isDrill)
            }
        }
    }
}
