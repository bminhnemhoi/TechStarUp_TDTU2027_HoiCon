package vn.hoicon.sentinel.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
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
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.CustomAccessibilityAction
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.customActions
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.onClick
import androidx.compose.ui.semantics.onLongClick
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import vn.hoicon.rules.RiskLevel
import vn.hoicon.sentinel.R
import vn.hoicon.sentinel.pause.HoldToContinue
import vn.hoicon.sentinel.pause.PauseKind
import vn.hoicon.sentinel.ui.theme.BrandNavy
import vn.hoicon.sentinel.ui.theme.BrandOrange
import vn.hoicon.sentinel.ui.theme.HoiConTheme
import vn.hoicon.sentinel.ui.theme.SurfaceMuted
import vn.hoicon.sentinel.ui.theme.SurfaceWhite

/** Callbacks of E7; the hold-to-continue ones go through [HoldToContinue] in the activity. */
class SafePauseActions(
    val onReplay: () -> Unit,
    val onAskChild: () -> Unit,
    val onCancel: () -> Unit,
    val onHoldPress: () -> Unit,
    val onHoldRelease: () -> Unit,
    val onHoldTap: () -> Unit,
    val onAccessibleContinue: () -> Unit,
    val onConfirm: () -> Unit,
)

/** The calm minute of E7 (docs/DESIGN-SYSTEM.md: no countdown that scares). Advisory: "Vẫn tiếp tục" is never locked. */
const val PAUSE_COUNTDOWN_SECONDS = 60

/**
 * E7 "Khoan chuyển tiền đã" (Spec 022 FR-006). The shipping UI; the View layout `activity_safe_pause.xml` stays only
 * as the debug A/B variant of spec 001.
 * UX-1: only the text scrolls; the action bar is pinned to the bottom so every button shows at any font scale.
 * At most two main actions ("Hỏi con", "Hủy giao dịch"); "Vẫn tiếp tục" is the quiet third, held 3 s (CLAUDE.md rule 4).
 */
@Composable
fun SafePauseScreen(
    level: RiskLevel,
    kind: PauseKind,
    reason: String,
    secondsLeft: Int,
    status: HoldToContinue.Status,
    statusText: String,
    progress: Float,
    actions: SafePauseActions,
    modifier: Modifier = Modifier,
) {
    Surface(modifier = modifier.fillMaxSize(), color = SurfaceWhite) {
      BoxWithConstraints(modifier = Modifier.fillMaxSize().safeDrawingPadding()) {
        // The action bar never takes more than 55% of the screen (it scrolls if it must, e.g. 200% font plus status
        // lines): the text above keeps room, and on a small screen no button is cut off.
        val barMax = maxHeight * 0.55f
        Column(modifier = Modifier.fillMaxSize()) {
            val scroll = rememberScrollState()
            Box(modifier = Modifier.weight(1f).fillMaxWidth()) {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .verticalScroll(scroll)
                        .padding(start = 24.dp, top = 16.dp, end = 24.dp, bottom = 16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp),
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            text = stringResource(R.string.pause_disclosure),
                            style = MaterialTheme.typography.bodyMedium,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.weight(1f).padding(end = 12.dp),
                        )
                        OutlinedButton(onClick = actions.onReplay, modifier = Modifier.heightIn(min = 64.dp)) {
                            Text(text = stringResource(R.string.pause_replay), fontSize = 20.sp, color = BrandNavy)
                        }
                    }
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Image(
                            painter = painterResource(R.drawable.ic_stat_shield),
                            contentDescription = null,
                            colorFilter = ColorFilter.tint(BrandOrange),
                            modifier = Modifier.size(48.dp),
                        )
                        Text(
                            text = stringResource(
                                if (level == RiskLevel.CRITICAL) R.string.pause_level_critical else R.string.pause_level_high,
                            ),
                            style = MaterialTheme.typography.titleLarge,
                            modifier = Modifier.padding(start = 12.dp),
                        )
                    }
                    Text(
                        text = stringResource(if (kind == PauseKind.REMOTE_CONTROL) R.string.pause_title_remote else R.string.pause_title),
                        style = MaterialTheme.typography.headlineSmall.copy(fontSize = 32.sp, lineHeight = 40.sp),
                        modifier = Modifier.semantics { heading() },
                    )
                    Text(
                        text = stringResource(if (kind == PauseKind.REMOTE_CONTROL) R.string.pause_body_remote else R.string.pause_body),
                        style = MaterialTheme.typography.bodyLarge,
                    )
                    Text(text = reason, style = MaterialTheme.typography.bodyMedium)
                    // I2: ask for the family password. The app never stores or asks for it: the person on the phone does.
                    InfoCard(
                        title = stringResource(R.string.pause_family_password_title),
                        body = stringResource(R.string.pause_family_password_body),
                    )
                    CalmMinute(secondsLeft = secondsLeft)
                }
                if (scroll.canScrollForward) {
                    // Fading edge: tells the reader there is more text below the pinned buttons.
                    Box(
                        modifier = Modifier
                            .align(Alignment.BottomCenter)
                            .fillMaxWidth()
                            .height(48.dp)
                            .background(Brush.verticalGradient(listOf(Color.Transparent, SurfaceWhite))),
                    )
                }
            }
            HorizontalDivider()
            Column(
                modifier = Modifier
                    .heightIn(max = barMax)
                    .verticalScroll(rememberScrollState())
                    .padding(start = 24.dp, top = 12.dp, end = 24.dp, bottom = 16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                // Status + confirm ABOVE the buttons: growing text never moves the buttons under the finger (UX-2).
                if (statusText.isNotEmpty()) {
                    Text(
                        text = statusText,
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.Bold,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.fillMaxWidth().semantics { liveRegion = LiveRegionMode.Polite },
                    )
                }
                if (status == HoldToContinue.Status.ConfirmReady) {
                    OutlinedButton(onClick = actions.onConfirm, modifier = Modifier.fillMaxWidth().heightIn(min = 72.dp)) {
                        Text(
                            text = stringResource(R.string.pause_confirm_button),
                            style = MaterialTheme.typography.labelLarge,
                            color = BrandNavy,
                        )
                    }
                }
                PrimaryButton(text = stringResource(R.string.pause_ask_child), onClick = actions.onAskChild)
                CancelButton(kind = kind, onClick = actions.onCancel)
                HoldButton(progress = progress, actions = actions, modifier = Modifier.padding(top = 4.dp))
            }
        }
      }
    }
}

/** "Hủy giao dịch" (bank) / "Về màn hình chính" (remote control): it only goes home, and the second line says so. */
@Composable
private fun CancelButton(kind: PauseKind, onClick: () -> Unit) {
    OutlinedButton(
        onClick = onClick,
        shape = RoundedCornerShape(36.dp),
        border = BorderStroke(2.dp, BrandNavy),
        modifier = Modifier.fillMaxWidth().heightIn(min = 72.dp),
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                text = stringResource(if (kind == PauseKind.REMOTE_CONTROL) R.string.pause_cancel_remote else R.string.pause_cancel_bank),
                style = MaterialTheme.typography.labelLarge,
                color = BrandNavy,
            )
            if (kind == PauseKind.FINANCIAL) {
                Text(text = stringResource(R.string.pause_cancel_sub), style = MaterialTheme.typography.bodyMedium, color = BrandNavy)
            }
        }
    }
}

/**
 * One calm minute to think (Spec 022 FR-006): a bar that fills, never red, no per-second announcement. It only
 * advises; leaving early is always possible. Reaching the end is announced once.
 */
@Composable
private fun CalmMinute(secondsLeft: Int) {
    val done = secondsLeft <= 0
    val spoken = stringResource(R.string.pause_countdown_a11y)
    Column(
        verticalArrangement = Arrangement.spacedBy(8.dp),
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(SurfaceMuted)
            .padding(16.dp)
            .semantics(mergeDescendants = true) {
                if (!done) contentDescription = spoken else liveRegion = LiveRegionMode.Polite
            },
    ) {
        Text(
            text = stringResource(R.string.pause_countdown_title),
            style = MaterialTheme.typography.titleLarge,
            modifier = Modifier.semantics { heading() },
        )
        Text(
            text = stringResource(if (done) R.string.pause_countdown_done else R.string.pause_countdown_left),
            style = MaterialTheme.typography.bodyMedium,
        )
        val elapsed = ((PAUSE_COUNTDOWN_SECONDS - secondsLeft.coerceIn(0, PAUSE_COUNTDOWN_SECONDS)).toFloat() / PAUSE_COUNTDOWN_SECONDS)
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(14.dp)
                .clip(RoundedCornerShape(7.dp))
                .background(SurfaceWhite)
                .border(1.dp, BrandNavy, RoundedCornerShape(7.dp)),
        ) {
            Box(modifier = Modifier.fillMaxWidth(elapsed).height(12.dp).background(BrandNavy))
        }
    }
}

/** "Vẫn tiếp tục": hold 3 s (touch) or the accessible countdown path (TalkBack / Switch Access). */
@Composable
private fun HoldButton(progress: Float, actions: SafePauseActions, modifier: Modifier = Modifier) {
    val shape = RoundedCornerShape(36.dp)
    val label = stringResource(R.string.pause_continue)
    val spokenLabel = stringResource(R.string.pause_continue_a11y_desc)
    val longClickLabel = stringResource(R.string.pause_continue_long_click_label)
    val a11yAction = stringResource(R.string.pause_continue_a11y_action)
    Box(
        contentAlignment = Alignment.Center,
        modifier = modifier
            .fillMaxWidth()
            .heightIn(min = 72.dp)
            .clip(shape)
            .background(SurfaceWhite)
            .border(width = 2.dp, color = BrandNavy, shape = shape)
            .pointerInput(Unit) {
                // Leaving the button's bounds cancels the gesture (tryAwaitRelease = false) ⇒ treated as too short.
                detectTapGestures(onPress = {
                    actions.onHoldPress()
                    tryAwaitRelease()
                    actions.onHoldRelease()
                })
            }
            .semantics(mergeDescendants = true) {
                role = Role.Button
                contentDescription = spokenLabel
                onClick { actions.onHoldTap(); true }
                onLongClick(label = longClickLabel) { actions.onAccessibleContinue(); true }
                customActions = listOf(CustomAccessibilityAction(a11yAction) { actions.onAccessibleContinue(); true })
            },
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.padding(start = 16.dp, top = 10.dp, end = 16.dp, bottom = 20.dp),
        ) {
            Text(text = label, style = MaterialTheme.typography.labelLarge, color = BrandNavy, textAlign = TextAlign.Center)
            Text(
                text = stringResource(R.string.pause_continue_hint),
                style = MaterialTheme.typography.bodyMedium,
                color = BrandNavy,
                textAlign = TextAlign.Center,
            )
        }
        Box(
            modifier = Modifier
                .align(Alignment.BottomStart)
                .fillMaxWidth(progress)
                .height(10.dp)
                .background(BrandNavy),
        )
    }
}

@Preview(showBackground = true, locale = "vi")
@Preview(showBackground = true, locale = "vi", fontScale = 2f, name = "Cỡ chữ 200%")
@Composable
private fun SafePauseScreenPreview() {
    HoiConTheme {
        SafePauseScreen(
            level = RiskLevel.HIGH,
            kind = PauseKind.FINANCIAL,
            reason = "HỏiCon nhắc vì bác đang nghe một số lạ và vừa mở ứng dụng ngân hàng.",
            secondsLeft = 42,
            status = HoldToContinue.Status.Idle,
            statusText = "",
            progress = 0.4f,
            actions = SafePauseActions({}, {}, {}, {}, {}, {}, {}, {}),
        )
    }
}
