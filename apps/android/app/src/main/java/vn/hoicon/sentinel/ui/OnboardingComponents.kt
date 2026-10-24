package vn.hoicon.sentinel.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import vn.hoicon.sentinel.R
import vn.hoicon.sentinel.ui.theme.BrandNavy
import vn.hoicon.sentinel.ui.theme.HoiConTokens
import vn.hoicon.sentinel.ui.theme.RiskMediumAccent
import vn.hoicon.sentinel.ui.theme.RiskMediumBg
import vn.hoicon.sentinel.ui.theme.RiskMediumFg
import vn.hoicon.sentinel.ui.theme.SurfaceMuted
import vn.hoicon.sentinel.ui.theme.SurfaceWhite

private val TouchMin = HoiConTokens.Size.TouchMinDp.dp
private val ButtonHeight = (HoiConTokens.Size.TouchMinDp + 8).dp
private val Gutter = HoiConTokens.Size.SpaceXlDp.dp
private val Radius = HoiConTokens.Size.RadiusCardDp.dp

/**
 * Shared frame of the onboarding screens (same idea as E7, UX-1): only the text scrolls, the action bar is pinned
 * to the bottom so the buttons stay visible at any font scale and above the keyboard.
 */
@Composable
internal fun OnboardingScaffold(
    modifier: Modifier = Modifier,
    pinned: (@Composable ColumnScope.() -> Unit)? = null,
    /** Long consent texts: say "Kéo xuống để đọc tiếp" while more is below (the fade alone looked like a cut-off screen). */
    scrollHint: Boolean = false,
    actions: @Composable ColumnScope.() -> Unit,
    body: @Composable ColumnScope.() -> Unit,
) {
    Surface(modifier = modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(modifier = Modifier.fillMaxSize().safeDrawingPadding()) {
            val scroll = rememberScrollState()
            Box(modifier = Modifier.weight(1f).fillMaxWidth()) {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .verticalScroll(scroll)
                        .padding(start = Gutter, top = HoiConTokens.Size.SpaceLgDp.dp, end = Gutter, bottom = HoiConTokens.Size.SpaceLgDp.dp),
                    verticalArrangement = Arrangement.spacedBy(HoiConTokens.Size.SpaceLgDp.dp),
                    content = body,
                )
                if (scroll.canScrollForward) {
                    // Fading edge: tells the reader there is more text below the pinned buttons.
                    Column(modifier = Modifier.align(Alignment.BottomCenter).fillMaxWidth()) {
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(32.dp)
                                .background(Brush.verticalGradient(listOf(Color.Transparent, SurfaceWhite))),
                        )
                        if (scrollHint) {
                            // On a solid strip so it never prints over the faded words.
                            Text(
                                text = stringResource(R.string.onboarding_scroll_hint),
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = FontWeight.Bold,
                                color = BrandNavy,
                                textAlign = TextAlign.Center,
                                modifier = Modifier.fillMaxWidth().background(SurfaceWhite).padding(horizontal = 12.dp, vertical = 4.dp),
                            )
                        }
                    }
                }
            }
            if (pinned != null) {
                // Input and its answer stay on screen however big the font or the keyboard: only the intro scrolls.
                Column(
                    modifier = Modifier.padding(horizontal = Gutter, vertical = HoiConTokens.Size.SpaceSmDp.dp),
                    verticalArrangement = Arrangement.spacedBy(HoiConTokens.Size.SpaceMdDp.dp),
                    content = pinned,
                )
            }
            HorizontalDivider()
            Column(
                modifier = Modifier.padding(start = Gutter, top = HoiConTokens.Size.SpaceMdDp.dp, end = Gutter, bottom = HoiConTokens.Size.SpaceLgDp.dp),
                verticalArrangement = Arrangement.spacedBy(HoiConTokens.Size.SpaceSmDp.dp),
                content = actions,
            )
        }
    }
}

/** The one main action of a screen: navy, 24sp bold label, >= 72dp tall. */
@Composable
internal fun PrimaryButton(text: String, onClick: () -> Unit, modifier: Modifier = Modifier) {
    Button(
        onClick = onClick,
        shape = RoundedCornerShape(HoiConTokens.Size.RadiusButtonDp.dp),
        colors = ButtonDefaults.buttonColors(containerColor = BrandNavy, contentColor = SurfaceWhite),
        modifier = modifier.fillMaxWidth().heightIn(min = ButtonHeight),
    ) {
        Text(text = text, style = MaterialTheme.typography.labelLarge, textAlign = TextAlign.Center)
    }
}

@Composable
internal fun SecondaryButton(text: String, onClick: () -> Unit, modifier: Modifier = Modifier) {
    OutlinedButton(
        onClick = onClick,
        shape = RoundedCornerShape(HoiConTokens.Size.RadiusButtonDp.dp),
        border = BorderStroke(2.dp, BrandNavy),
        modifier = modifier.fillMaxWidth().heightIn(min = TouchMin),
    ) {
        Text(text = text, style = MaterialTheme.typography.labelLarge, color = BrandNavy, textAlign = TextAlign.Center)
    }
}

/** Calm amber notice (never the red "critical" palette): says what happened and what to do next. Icon + words. */
@Composable
internal fun NoticePanel(text: String, modifier: Modifier = Modifier) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(Radius))
            .background(RiskMediumBg)
            .border(2.dp, RiskMediumAccent, RoundedCornerShape(Radius))
            .padding(HoiConTokens.Size.SpaceLgDp.dp)
            .semantics { liveRegion = LiveRegionMode.Polite },
    ) {
        Image(
            painter = painterResource(R.drawable.ic_stat_shield),
            contentDescription = null,
            colorFilter = ColorFilter.tint(RiskMediumAccent),
            modifier = Modifier.size(40.dp),
        )
        Text(
            text = text,
            style = MaterialTheme.typography.bodyMedium,
            color = RiskMediumFg,
            modifier = Modifier.padding(start = HoiConTokens.Size.SpaceMdDp.dp),
        )
    }
}

/** One numbered-free "card" of a list (E3 commitments, E4 summary): title + words on the muted surface. */
@Composable
internal fun InfoCard(title: String, body: String, modifier: Modifier = Modifier, bodyBold: Boolean = false) {
    Column(
        verticalArrangement = Arrangement.spacedBy(HoiConTokens.Size.SpaceSmDp.dp),
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(Radius))
            .background(SurfaceMuted)
            .padding(HoiConTokens.Size.SpaceLgDp.dp)
            .semantics(mergeDescendants = true) {},
    ) {
        Text(text = title, style = MaterialTheme.typography.titleLarge, modifier = Modifier.semantics { heading() })
        Text(text = body, style = MaterialTheme.typography.bodyMedium, fontWeight = if (bodyBold) FontWeight.Bold else null)
    }
}

/** "Nghe lại" as a small control inside the text (not in the action bar, which keeps its two main actions). */
@Composable
internal fun ListenButton(text: String, onClick: () -> Unit, modifier: Modifier = Modifier) {
    OutlinedButton(
        onClick = onClick,
        shape = RoundedCornerShape(HoiConTokens.Size.RadiusButtonDp.dp),
        border = BorderStroke(2.dp, BrandNavy),
        modifier = modifier.heightIn(min = TouchMin),
    ) {
        Text(text = text, style = MaterialTheme.typography.labelLarge, color = BrandNavy)
    }
}
