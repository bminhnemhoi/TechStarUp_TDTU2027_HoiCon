package vn.hoicon.sentinel.ui

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import vn.hoicon.sentinel.R
import vn.hoicon.sentinel.ui.theme.BrandGreen
import vn.hoicon.sentinel.ui.theme.BrandGreenText
import vn.hoicon.sentinel.ui.theme.HoiConTheme
import vn.hoicon.sentinel.ui.theme.HoiConTokens
import vn.hoicon.sentinel.ui.theme.RiskLowBg
import vn.hoicon.sentinel.ui.theme.RiskMediumAccent
import vn.hoicon.sentinel.ui.theme.RiskMediumBg
import vn.hoicon.sentinel.ui.theme.RiskMediumFg

/** What E6 shows; computed by the activity from permissions, the paired family and the risk-window row. */
data class ProtectionUiState(
    val familyName: String,
    /** A permission the protection needs is missing: the title says so instead of "Đang bảo vệ". */
    val missingPermissions: Boolean,
    /** A call from a stranger opened the risk window and it has not run out. */
    val windowOpen: Boolean,
    /** "Hỏi con" was pressed on this screen: the answer stays visible when the person comes back from the dialer. */
    val askChildSent: Boolean,
    /** The phone has no dialer that opened: say so instead of pretending the call can be made. */
    val dialerFailed: Boolean = false,
    /** The server refused the device token: the family cannot be reached until the phone is paired again. */
    val needsRepair: Boolean = false,
)

/**
 * E6 "Đang bảo vệ" (Spec 022 FR-005): the home screen after pairing. Says in one word whether the person is protected,
 * which family they are connected to, and offers the two things they can do: "Hỏi con" and the permissions list.
 * Words and an icon always carry the state, never colour alone (docs/DESIGN-SYSTEM.md).
 */
@Composable
fun ProtectionStatusScreen(
    state: ProtectionUiState,
    onAskChild: () -> Unit,
    onPermissions: () -> Unit,
    modifier: Modifier = Modifier,
    onReconnect: () -> Unit = {},
) {
    OnboardingScaffold(
        modifier = modifier,
        actions = {
            PrimaryButton(text = stringResource(R.string.e6_ask_child), onClick = onAskChild)
            if (state.needsRepair) {
                SecondaryButton(text = stringResource(R.string.e6_repair_button), onClick = onReconnect)
            } else {
                SecondaryButton(
                    text = stringResource(if (state.missingPermissions) R.string.e6_permissions_more else R.string.e6_permissions_view),
                    onClick = onPermissions,
                )
            }
        },
    ) {
        Text(text = stringResource(R.string.e6_ai), style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Bold)
        if (state.missingPermissions) {
            NoticePanel(text = stringResource(R.string.e6_title_missing))
        } else {
            ProtectedBadge()
        }
        if (state.needsRepair) {
            NoticePanel(text = stringResource(R.string.e6_repair_notice))
        }
        // What changed or needs an answer comes first: at 200% only the top of the page is on screen.
        if (state.askChildSent) {
            NoticePanel(text = stringResource(if (state.dialerFailed) R.string.e6_dialer_failed else R.string.e6_ask_child_sent))
        }
        if (state.windowOpen) {
            WindowOpenCard()
        }
        Text(
            text = stringResource(if (state.missingPermissions) R.string.e6_body_missing else R.string.e6_body_ok),
            style = MaterialTheme.typography.bodyLarge,
        )
        InfoCard(
            title = stringResource(R.string.e6_family_title),
            body = stringResource(R.string.e6_family_body, state.familyName),
        )
    }
}

/** The shield, the word "Đang bảo vệ bác" and the green card: the "all good" state, icon + words. */
@Composable
private fun ProtectedBadge() {
    val shape = RoundedCornerShape(HoiConTokens.Size.RadiusCardDp.dp)
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .fillMaxWidth()
            .clip(shape)
            .background(RiskLowBg)
            .border(2.dp, BrandGreen, shape)
            .padding(HoiConTokens.Size.SpaceLgDp.dp),
    ) {
        Image(
            painter = painterResource(R.drawable.ic_shield_check),
            contentDescription = null,
            colorFilter = ColorFilter.tint(BrandGreen),
            modifier = Modifier.size(56.dp),
        )
        Text(
            text = stringResource(R.string.e6_title_ok),
            style = MaterialTheme.typography.headlineSmall,
            color = BrandGreenText,
            modifier = Modifier.padding(start = HoiConTokens.Size.SpaceMdDp.dp).semantics { heading() },
        )
    }
}

/** A stranger's call is being watched: calm amber (never the red palette), says what to do. */
@Composable
private fun WindowOpenCard() {
    val shape = RoundedCornerShape(HoiConTokens.Size.RadiusCardDp.dp)
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .fillMaxWidth()
            .clip(shape)
            .background(RiskMediumBg)
            .border(2.dp, RiskMediumAccent, shape)
            .padding(HoiConTokens.Size.SpaceLgDp.dp)
            .semantics(mergeDescendants = true) { liveRegion = LiveRegionMode.Polite },
    ) {
        Image(
            painter = painterResource(R.drawable.ic_stat_shield),
            contentDescription = null,
            colorFilter = ColorFilter.tint(RiskMediumAccent),
            modifier = Modifier.size(40.dp),
        )
        Column(
            verticalArrangement = Arrangement.spacedBy(HoiConTokens.Size.SpaceSmDp.dp),
            modifier = Modifier.padding(start = HoiConTokens.Size.SpaceMdDp.dp),
        ) {
            Text(
                text = stringResource(R.string.e6_window_title),
                style = MaterialTheme.typography.titleLarge,
                color = RiskMediumFg,
                modifier = Modifier.semantics { heading() },
            )
            Text(text = stringResource(R.string.e6_window_body), style = MaterialTheme.typography.bodyMedium, color = RiskMediumFg)
        }
    }
}

@Preview(showBackground = true, locale = "vi")
@Preview(showBackground = true, locale = "vi", fontScale = 2f, name = "Cỡ chữ 200%")
@Composable
private fun ProtectionStatusPreview() {
    HoiConTheme {
        ProtectionStatusScreen(
            state = ProtectionUiState("Gia đình Bác Ba", missingPermissions = false, windowOpen = true, askChildSent = false),
            onAskChild = {},
            onPermissions = {},
        )
    }
}
