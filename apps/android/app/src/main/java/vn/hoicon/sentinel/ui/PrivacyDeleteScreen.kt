package vn.hoicon.sentinel.ui

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.disabled
import androidx.compose.ui.semantics.onLongClick
import androidx.compose.ui.semantics.role
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import java.time.Instant
import java.time.ZoneId
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch
import vn.hoicon.sentinel.R
import vn.hoicon.sentinel.ui.theme.BrandNavy
import vn.hoicon.sentinel.ui.theme.SurfaceWhite

/** "9:00 ngày 26 tháng 10": hour, then day and month, in the phone's own zone (E12 says when the deletion starts). */
fun deleteTimeText(epochMs: Long, zone: ZoneId = ZoneId.systemDefault()): String {
    val t = Instant.ofEpochMilli(epochMs).atZone(zone)
    return "${t.hour}:${"%02d".format(t.minute)} ngày ${t.dayOfMonth} tháng ${t.monthValue}"
}

const val HOLD_MS = 3000

/**
 * E12 "Xóa dữ liệu của gia đình" (Spec 038 FR-003): what goes, what stays, the 24-hour wait that can be cancelled, then ONE deliberate
 * act: hold the button for 3 seconds (same pattern as E7's "Vẫn tiếp tục"). [messageRes] is the last answer (offline, busy, ...); nothing
 * is removed from the phone here.
 */
@Composable
fun PrivacyDeleteScreen(
    guardianNotified: Boolean,
    sending: Boolean,
    messageRes: Int?,
    onHeld: () -> Unit,
    onTooShort: () -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    OnboardingScaffold(
        modifier = modifier,
        scrollHint = true,
        pinned = {
            messageRes?.let { Text(text = stringResource(it), style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.Bold, modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite }) }
        },
        actions = {
            HoldToConfirm(text = stringResource(if (sending) R.string.delete_sending else R.string.delete_hold), enabled = !sending, onHeld = onHeld, onTooShort = onTooShort)
            Spacer(Modifier.height(8.dp)) // the deliberate act and the way out are not neighbours
            SecondaryButton(text = stringResource(R.string.delete_back), onClick = onBack)
        },
    ) {
        Text(text = stringResource(R.string.delete_title), style = MaterialTheme.typography.headlineMedium, modifier = Modifier.semantics { heading() })
        Text(text = stringResource(R.string.delete_what), style = MaterialTheme.typography.bodyLarge)
        Text(text = stringResource(R.string.delete_keep), style = MaterialTheme.typography.bodyLarge)
        Text(text = stringResource(R.string.delete_wait), style = MaterialTheme.typography.bodyLarge)
        Text(text = stringResource(R.string.delete_deadline), style = MaterialTheme.typography.bodyLarge)
        if (guardianNotified) Text(text = stringResource(R.string.delete_guardian), style = MaterialTheme.typography.bodyLarge)
    }
}

/** A neutral button filled while the finger stays down; letting go early cancels (nothing is sent). */
@Composable
private fun HoldToConfirm(text: String, enabled: Boolean, onHeld: () -> Unit, onTooShort: () -> Unit) {
    val progress = remember { Animatable(0f) }
    var pressed by remember { mutableStateOf(false) }
    val currentOnHeld by rememberUpdatedState(onHeld)
    val scope = rememberCoroutineScope()
    val shape = RoundedCornerShape(36.dp)
    val hint = stringResource(R.string.delete_hold_a11y)
    Box(
        contentAlignment = Alignment.Center,
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 72.dp)
            .clip(shape)
            .background(SurfaceWhite)
            .border(2.dp, BrandNavy, shape)
            .semantics(mergeDescendants = true) {
                role = Role.Button
                if (!enabled) disabled()
                // TalkBack: double-tap and hold runs the same 3-second act as the finger does (the gesture itself cannot be heard).
                onLongClick(label = hint) {
                    currentOnHeld()
                    true
                }
            }
            .pointerInput(enabled) {
                if (!enabled) return@pointerInput
                detectTapGestures(onPress = {
                    pressed = true
                    var completed = false
                    val job = scope.launch {
                        try {
                            progress.animateTo(1f, tween(HOLD_MS, easing = LinearEasing))
                            completed = true
                            currentOnHeld()
                        } catch (_: CancellationException) {
                            // let go early: nothing is sent
                        }
                    }
                    tryAwaitRelease()
                    job.cancel()
                    pressed = false
                    scope.launch { progress.snapTo(0f) }
                    if (!completed) onTooShort()
                })
            },
    ) {
        // matchParentSize: the fill follows the button's own height instead of growing to the whole action bar.
        Box(modifier = Modifier.matchParentSize()) {
            Box(modifier = Modifier.fillMaxHeight().fillMaxWidth(progress.value).background(BrandNavy.copy(alpha = 0.2f)))
        }
        Text(
            text = if (pressed && enabled) stringResource(R.string.delete_holding) else text,
            style = MaterialTheme.typography.labelLarge,
            color = BrandNavy,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 14.dp), // room for the Vietnamese marks when the label wraps at 200%
        )
    }
}
