package vn.hoicon.sentinel.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import vn.hoicon.sentinel.R
import vn.hoicon.sentinel.domain.drill.DrillChoice
import vn.hoicon.sentinel.domain.drill.DrillEvaluation
import vn.hoicon.sentinel.domain.drill.DrillFeedback
import vn.hoicon.sentinel.domain.drill.DrillUi
import vn.hoicon.sentinel.domain.drill.StopReason
import vn.hoicon.sentinel.ui.theme.DrillAccent
import vn.hoicon.sentinel.ui.theme.DrillBg
import vn.hoicon.sentinel.ui.theme.DrillFg
import vn.hoicon.sentinel.ui.theme.HoiConTheme
import vn.hoicon.sentinel.ui.theme.HoiConTokens
import vn.hoicon.sentinel.ui.theme.SurfaceWhite

private val TouchMin = HoiConTokens.Size.TouchMinDp.dp
private val ButtonHeight = (HoiConTokens.Size.TouchMinDp + 8).dp
private val Gutter = HoiConTokens.Size.SpaceXlDp.dp
private val Radius = HoiConTokens.Size.RadiusCardDp.dp

/**
 * E11 "Luyện tập nhận biết lừa đảo" (Spec 028 FR-009). Four screens in the `drill.*` colours, and the same banner on every
 * one: the school icon and "[DIỄN TẬP]" stay pinned at the top, so this can never be taken for a real call. Only the
 * text scrolls; the buttons are pinned at the bottom and stay in view at 200% text. At most two main buttons per
 * screen, and "Dừng luyện tập" as a smaller third one during the drill.
 */
@Composable
fun DrillScreen(
    ui: DrillUi,
    onStart: () -> Unit,
    onLater: () -> Unit,
    onChoose: (String) -> Unit,
    onNext: () -> Unit,
    onStop: () -> Unit,
    onDone: () -> Unit,
    onClose: () -> Unit,
    onListen: () -> Unit,
    modifier: Modifier = Modifier,
) {
    DrillScaffold(
        modifier = modifier,
        actions = {
            when (ui) {
                DrillUi.Invite -> {
                    DrillPrimary(stringResource(R.string.drill_start), onStart)
                    DrillSecondary(stringResource(R.string.drill_later), onLater)
                }
                is DrillUi.Step -> {
                    // While choosing, the two choices sit in the text (under the question), so the caller's words are never
                    // hidden behind a tall button bar at 200%; only "Dừng luyện tập" stays pinned.
                    val feedback = ui.feedback
                    if (feedback != null) {
                        DrillPrimary(stringResource(if (feedback.isLastStep) R.string.drill_summary else R.string.drill_next), onNext)
                    }
                    Spacer(Modifier.height(HoiConTokens.Size.SpaceSmDp.dp))
                    DrillSecondary(stringResource(R.string.drill_stop), onStop)
                }
                is DrillUi.Debrief -> DrillPrimary(stringResource(R.string.drill_done), onDone)
                is DrillUi.Stopped -> DrillPrimary(stringResource(R.string.drill_close), onClose)
            }
        },
    ) {
        when (ui) {
            DrillUi.Invite -> InviteBody(onListen)
            is DrillUi.Step -> StepBody(ui, onListen, onChoose)
            is DrillUi.Debrief -> DebriefBody(ui.evaluation, onListen)
            is DrillUi.Stopped -> StoppedBody(ui)
        }
    }
}

@Composable
private fun DrillScaffold(
    modifier: Modifier = Modifier,
    actions: @Composable ColumnScope.() -> Unit,
    body: @Composable ColumnScope.() -> Unit,
) {
    Surface(modifier = modifier.fillMaxSize(), color = DrillBg) {
        Column(modifier = Modifier.fillMaxSize().safeDrawingPadding()) {
            DrillBanner()
            val scroll = rememberScrollState()
            Box(modifier = Modifier.weight(1f).fillMaxWidth()) {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .verticalScroll(scroll)
                        .padding(horizontal = Gutter, vertical = HoiConTokens.Size.SpaceLgDp.dp),
                    verticalArrangement = Arrangement.spacedBy(HoiConTokens.Size.SpaceLgDp.dp),
                    content = body,
                )
                if (scroll.canScrollForward) {
                    // Fading edge: there is more to read (or choose) below.
                    Box(
                        modifier = Modifier
                            .align(Alignment.BottomCenter)
                            .fillMaxWidth()
                            .height(56.dp)
                            .background(Brush.verticalGradient(listOf(Color.Transparent, DrillBg))),
                    )
                }
            }
            HorizontalDivider(color = DrillAccent)
            Column(
                modifier = Modifier.padding(start = Gutter, top = HoiConTokens.Size.SpaceMdDp.dp, end = Gutter, bottom = HoiConTokens.Size.SpaceLgDp.dp),
                verticalArrangement = Arrangement.spacedBy(HoiConTokens.Size.SpaceMdDp.dp),
                content = actions,
            )
        }
    }
}

/** Always first on screen and never scrolled away: icon + words, so it does not rest on colour alone. */
@Composable
private fun DrillBanner() {
    val bannerDescription = stringResource(R.string.drill_banner_desc)
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(HoiConTokens.Size.SpaceMdDp.dp),
        modifier = Modifier
            .fillMaxWidth()
            .background(DrillFg)
            .padding(horizontal = Gutter, vertical = HoiConTokens.Size.SpaceMdDp.dp)
            .semantics(mergeDescendants = true) {
                heading()
                contentDescription = bannerDescription
            },
    ) {
        Image(
            painter = painterResource(R.drawable.ic_drill_school),
            contentDescription = null,
            colorFilter = ColorFilter.tint(SurfaceWhite),
            modifier = Modifier.size(40.dp),
        )
        Text(
            text = stringResource(R.string.drill_badge),
            style = MaterialTheme.typography.titleLarge,
            color = SurfaceWhite,
        )
    }
}

@Composable
private fun InviteBody(onListen: () -> Unit) {
    ListenControl(onListen)
    Text(stringResource(R.string.drill_ai), style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Bold, color = DrillFg)
    Text(stringResource(R.string.drill_invite_title), style = MaterialTheme.typography.headlineMedium, color = DrillFg, modifier = Modifier.semantics { heading() })
    Text(stringResource(R.string.drill_invite_body), style = MaterialTheme.typography.bodyLarge, color = DrillFg)
}

@Composable
private fun StepBody(ui: DrillUi.Step, onListen: () -> Unit, onChoose: (String) -> Unit) {
    ListenControl(onListen)
    Text(stringResource(R.string.drill_step_counter, ui.index + 1, ui.total), style = MaterialTheme.typography.bodyMedium, color = DrillFg)
    DrillCard {
        Text(stringResource(R.string.drill_caller_says), style = MaterialTheme.typography.bodyMedium, color = DrillFg)
        Text(ui.lineVi, style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.Bold, color = DrillFg)
    }
    val feedback = ui.feedback
    if (feedback == null) {
        Text(stringResource(R.string.drill_pick), style = MaterialTheme.typography.titleLarge, color = DrillFg, modifier = Modifier.semantics { heading() })
        ui.choices.forEach { choice -> DrillPrimary(choice.labelVi, { onChoose(choice.id) }) }
    } else {
        FeedbackPanel(feedback)
    }
}

/** "Đúng rồi!" / "Chưa đúng, nhưng không sao.": said in words, so the answer is not carried by colour or position. */
@Composable
private fun FeedbackPanel(feedback: DrillFeedback) {
    DrillCard(modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite }) {
        Text(
            text = stringResource(if (feedback.correct) R.string.drill_right else R.string.drill_wrong),
            style = MaterialTheme.typography.titleLarge,
            color = DrillFg,
            modifier = Modifier.semantics { heading() },
        )
        Text(stringResource(R.string.drill_chose, feedback.chosenLabel), style = MaterialTheme.typography.bodyMedium, color = DrillFg)
        Text(feedback.text, style = MaterialTheme.typography.bodyLarge, color = DrillFg)
        feedback.safeWayLabel?.let {
            Text(stringResource(R.string.drill_safe_way, it), style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.Bold, color = DrillFg)
        }
    }
}

@Composable
private fun DebriefBody(evaluation: DrillEvaluation, onListen: () -> Unit) {
    ListenControl(onListen)
    Text(stringResource(R.string.drill_ai), style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Bold, color = DrillFg)
    Text(stringResource(R.string.drill_debrief_title), style = MaterialTheme.typography.headlineMedium, color = DrillFg, modifier = Modifier.semantics { heading() })
    Text(stringResource(R.string.drill_debrief_end), style = MaterialTheme.typography.titleLarge, color = DrillFg)
    Text(evaluation.praiseVi, style = MaterialTheme.typography.bodyLarge, color = DrillFg)
    Text(
        stringResource(R.string.drill_debrief_score, evaluation.correctCount, evaluation.total),
        style = MaterialTheme.typography.bodyLarge,
        fontWeight = FontWeight.Bold,
        color = DrillFg,
    )
    DrillCard {
        Text(stringResource(R.string.drill_debrief_flags), style = MaterialTheme.typography.titleLarge, color = DrillFg, modifier = Modifier.semantics { heading() })
        evaluation.redFlagsVi.forEach { Text("•  $it", style = MaterialTheme.typography.bodyMedium, color = DrillFg) }
    }
    Text(stringResource(R.string.drill_debrief_family), style = MaterialTheme.typography.bodyMedium, color = DrillFg)
}

@Composable
private fun StoppedBody(ui: DrillUi.Stopped) {
    Text(stringResource(R.string.drill_ai), style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Bold, color = DrillFg)
    Text(stringResource(R.string.drill_stopped_title), style = MaterialTheme.typography.headlineMedium, color = DrillFg, modifier = Modifier.semantics { heading() })
    Text(
        stringResource(if (ui.reason == StopReason.UNAVAILABLE) R.string.drill_expired_body else R.string.drill_stopped_body),
        style = MaterialTheme.typography.bodyLarge,
        color = DrillFg,
    )
}

@Composable
private fun DrillCard(modifier: Modifier = Modifier, content: @Composable ColumnScope.() -> Unit) {
    Column(
        verticalArrangement = Arrangement.spacedBy(HoiConTokens.Size.SpaceSmDp.dp),
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(Radius))
            .background(SurfaceWhite)
            .border(2.dp, DrillAccent, RoundedCornerShape(Radius))
            .padding(HoiConTokens.Size.SpaceLgDp.dp),
        content = content,
    )
}

/** "Nghe lại" as a small control inside the text, like on the other screens. */
@Composable
private fun ListenControl(onClick: () -> Unit) {
    OutlinedButton(
        onClick = onClick,
        shape = RoundedCornerShape(HoiConTokens.Size.RadiusButtonDp.dp),
        border = BorderStroke(2.dp, DrillFg),
        modifier = Modifier.heightIn(min = TouchMin),
    ) {
        Text(stringResource(R.string.drill_listen), style = MaterialTheme.typography.labelLarge, color = DrillFg)
    }
}

/** A main action: `drill.fg` fill, white 24sp bold label (white on drill.fg is about 11:1), at least 72dp tall. */
@Composable
private fun DrillPrimary(text: String, onClick: () -> Unit) {
    Button(
        onClick = onClick,
        shape = RoundedCornerShape(HoiConTokens.Size.RadiusButtonDp.dp),
        colors = ButtonDefaults.buttonColors(containerColor = DrillFg, contentColor = SurfaceWhite),
        modifier = Modifier.fillMaxWidth().heightIn(min = ButtonHeight),
    ) {
        Text(text = text, style = MaterialTheme.typography.labelLarge, textAlign = TextAlign.Center)
    }
}

@Composable
private fun DrillSecondary(text: String, onClick: () -> Unit) {
    OutlinedButton(
        onClick = onClick,
        shape = RoundedCornerShape(HoiConTokens.Size.RadiusButtonDp.dp),
        border = BorderStroke(2.dp, DrillFg),
        modifier = Modifier.fillMaxWidth().heightIn(min = TouchMin),
    ) {
        Text(text = text, style = MaterialTheme.typography.labelLarge, color = DrillFg, textAlign = TextAlign.Center)
    }
}

private val sampleChoices = listOf(
    DrillChoice("a", "Cúp máy, gọi lại cho con", correct = true, feedbackVi = "Cúp máy rồi hỏi người nhà là cách an toàn nhất."),
    DrillChoice("b", "Làm theo lời họ", correct = false, feedbackVi = "Người lạ giục làm gấp là dấu hiệu lừa đảo."),
)

@Preview(showBackground = true, locale = "vi")
@Preview(showBackground = true, locale = "vi", fontScale = 2f, name = "Cỡ chữ 200%")
@Composable
private fun DrillStepPreview() {
    HoiConTheme {
        DrillScreen(
            ui = DrillUi.Step(0, 3, "Chào bác, tôi là cán bộ Phòng Điều tra Mẫu. Tài khoản của bác liên quan đến một vụ án.", sampleChoices, feedback = null),
            onStart = {}, onLater = {}, onChoose = {}, onNext = {}, onStop = {}, onDone = {}, onClose = {}, onListen = {},
        )
    }
}
