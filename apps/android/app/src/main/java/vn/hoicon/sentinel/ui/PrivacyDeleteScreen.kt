package vn.hoicon.sentinel.ui

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Box
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
import androidx.compose.ui.semantics.contentDescription
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
import vn.hoicon.sentinel.ui.theme.SurfaceMuted
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
            HoldToConfirm(text = stringResource(if (sending) R.string.delete_sending else R.string.delete_hold), enabled = !sending, onHeld = onHeld)
            SecondaryButton(text = stringResource(R.string.delete_back), onClick = onBack)
        },
    ) {
        Text(text = stringResource(R.string.delete_title), style = MaterialTheme.typography.headlineMedium, modifier = Modifier.semantics { heading() })
        Text(text = stringResource(R.string.delete_what), style = MaterialTheme.typography.bodyLarge)
        Text(text = stringResource(R.string.delete_keep), style = MaterialTheme.typography.bodyLarge)
        Text(text = stringResource(R.string.delete_wait), style = MaterialTheme.typography.bodyLarge)
        if (guardianNotified) Text(text = stringResource(R.string.delete_guardian), style = MaterialTheme.typography.bodyLarge)
    }
}

/** A neutral button filled while the finger stays down; letting go early cancels (nothing is sent). */
@Composable
private fun HoldToConfirm(text: String, enabled: Boolean, onHeld: () -> Unit) {
    val progress = remember { Animatable(0f) }
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
            .semantics { contentDescription = hint }
            .pointerInput(enabled) {
                if (!enabled) return@pointerInput
                detectTapGestures(onPress = {
                    val job = scope.launch {
                        try {
                            progress.animateTo(1f, tween(HOLD_MS, easing = LinearEasing))
                            onHeld()
                        } catch (_: CancellationException) {
                            // let go early: nothing happens
                        }
                    }
                    tryAwaitRelease()
                    job.cancel()
                    scope.launch { progress.snapTo(0f) }
                })
            },
    ) {
        Box(modifier = Modifier.fillMaxHeight().fillMaxWidth(progress.value).background(SurfaceMuted).align(Alignment.CenterStart))
        Text(text = text, style = MaterialTheme.typography.labelLarge, color = BrandNavy, textAlign = TextAlign.Center, modifier = Modifier.padding(horizontal = 16.dp))
    }
}
