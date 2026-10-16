package vn.hoicon.sentinel.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.delay
import vn.hoicon.sentinel.data.remote.ElderQuestion
import vn.hoicon.sentinel.ui.theme.HoiConTokens

/**
 * Màn hình E8: Câu hỏi nhanh cho người cao tuổi (spec 024, US-05, ADR-009).
 * - Chữ ≥ 20sp, tương phản ≥ 7:1 (chữ trắng chỉ trên BrandOrangeText/BrandNavy — trắng trên BrandOrange chỉ ~4,5:1).
 * - 3 nút trả lời + nút nghe lại, mọi vùng chạm ≥ 64dp ("Có", "Không", "Không rõ").
 * - Câu công khai AI nằm ở đầu chính câu hỏi (máy chủ thêm, có test hợp đồng) nên TTS cũng đọc nó; nhãn diễn tập riêng.
 * - Đếm ngược 60 giây rồi tự đóng; nghe lại bằng TTS offline.
 */
@Composable
fun ElderQuestionScreen(
    question: ElderQuestion,
    onAnswerSelected: (String) -> Unit,
    onTimeout: () -> Unit,
    onSpeakRequested: (String) -> Unit,
    modifier: Modifier = Modifier,
    initialRemainingSeconds: Int = 60,
) {
    var remainingSeconds by remember { mutableIntStateOf(initialRemainingSeconds) }

    LaunchedEffect(key1 = question.incidentId) {
        while (remainingSeconds > 0) {
            delay(1000L)
            remainingSeconds--
        }
        onTimeout()
    }

    LaunchedEffect(key1 = question.text) {
        onSpeakRequested(question.text)
    }

    Surface(
        modifier = modifier
            .fillMaxSize()
            .safeDrawingPadding(),
        color = HoiConTokens.Colors.SurfaceBase,
    ) {
        // Câu hỏi cuộn được; 3 nút trả lời luôn ghim ở đáy (cỡ chữ 200% không đẩy nút ra khỏi màn hình).
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(20.dp),
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f)
                    .verticalScroll(rememberScrollState()),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                // Nhãn diễn tập (Luật 8)
                if (question.isDrill) {
                    Box(
                        modifier = Modifier
                            .padding(bottom = 12.dp)
                            .clip(RoundedCornerShape(8.dp))
                            .background(HoiConTokens.Colors.DrillBg)
                            .border(1.dp, HoiConTokens.Colors.DrillAccent, RoundedCornerShape(8.dp))
                            .padding(horizontal = 14.dp, vertical = 6.dp),
                    ) {
                        Text(
                            text = "[DIỄN TẬP]",
                            fontSize = 20.sp,
                            fontWeight = FontWeight.Bold,
                            color = HoiConTokens.Colors.DrillFg,
                        )
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))

                // Nội dung câu hỏi E8
                Text(
                    text = question.text,
                    fontSize = 24.sp,
                    lineHeight = 34.sp,
                    fontWeight = FontWeight.Bold,
                    color = HoiConTokens.Colors.TextPrimary,
                    textAlign = TextAlign.Center,
                    modifier = Modifier
                        .fillMaxWidth()
                        .semantics { heading() },
                )

                Spacer(modifier = Modifier.height(16.dp))

                // Nút nghe lại câu hỏi bằng giọng đọc TTS
                OutlinedButton(
                    onClick = { onSpeakRequested(question.text) },
                    modifier = Modifier.heightIn(min = 64.dp),
                    shape = RoundedCornerShape(12.dp),
                    border = BorderStroke(2.dp, HoiConTokens.Colors.BrandNavy),
                ) {
                    Text(
                        text = "Nghe lại câu hỏi",
                        fontSize = 20.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = HoiConTokens.Colors.BrandNavy,
                    )
                }

                Spacer(modifier = Modifier.height(12.dp))

                Text(
                    text = "Tự động đóng sau $remainingSeconds giây",
                    fontSize = 20.sp,
                    color = HoiConTokens.Colors.TextPrimary,
                )
            }

            // 3 nút bấm kích thước lớn (Có, Không, Không rõ)
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                // Nút CÓ
                Button(
                    onClick = { onAnswerSelected("yes") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(min = 68.dp)
                        .semantics {
                            role = Role.Button
                            contentDescription = "Có, đồng ý với câu hỏi"
                        },
                    shape = RoundedCornerShape(16.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = HoiConTokens.Colors.BrandOrangeText,
                        contentColor = HoiConTokens.Colors.TextOnPrimary,
                    ),
                ) {
                    Text(
                        text = "CÓ",
                        fontSize = 26.sp,
                        fontWeight = FontWeight.Bold,
                    )
                }

                // Nút KHÔNG
                Button(
                    onClick = { onAnswerSelected("no") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(min = 68.dp)
                        .semantics {
                            role = Role.Button
                            contentDescription = "Không, không đồng ý với câu hỏi"
                        },
                    shape = RoundedCornerShape(16.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = HoiConTokens.Colors.BrandNavy,
                        contentColor = HoiConTokens.Colors.TextOnPrimary,
                    ),
                ) {
                    Text(
                        text = "KHÔNG",
                        fontSize = 26.sp,
                        fontWeight = FontWeight.Bold,
                    )
                }

                // Nút KHÔNG RÕ
                OutlinedButton(
                    onClick = { onAnswerSelected("unsure") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(min = 64.dp)
                        .semantics {
                            role = Role.Button
                            contentDescription = "Không rõ, không chắc chắn câu trả lời"
                        },
                    shape = RoundedCornerShape(16.dp),
                    border = BorderStroke(2.dp, HoiConTokens.Colors.BrandNavy),
                    colors = ButtonDefaults.outlinedButtonColors(
                        contentColor = HoiConTokens.Colors.BrandNavy,
                    ),
                ) {
                    Text(
                        text = "KHÔNG RÕ",
                        fontSize = 22.sp,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
        }
    }
}
