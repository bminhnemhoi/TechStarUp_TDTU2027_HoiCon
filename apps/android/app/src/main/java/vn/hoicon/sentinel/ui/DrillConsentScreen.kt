package vn.hoicon.sentinel.ui

import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.selection.toggleable
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import vn.hoicon.sentinel.ui.theme.RiskMediumFg
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import vn.hoicon.sentinel.R
import vn.hoicon.sentinel.data.consent.ConsentLedger
import vn.hoicon.sentinel.ui.theme.HoiConTheme

/**
 * Consent for practice calls (Spec 028), asked from E6. The words are the `drills` text of docs/legal/consent/ line for
 * line (it says plainly that it is only practice). One extra tap is part of the consent: "Tôi từ 18 tuổi trở lên". The accept
 * button always works; without the tick a calm sentence says what is missing. "Để lúc khác" records nothing.
 */
@Composable
fun DrillConsentScreen(
    adultConfirmed: Boolean,
    needsAdultNotice: Boolean,
    onAdultChange: (Boolean) -> Unit,
    onAccept: () -> Unit,
    onDecline: () -> Unit,
    onListen: () -> Unit,
    modifier: Modifier = Modifier,
) {
    // The tick sits at the end of the reading column (the reader meets it after the words, at any text size) and only the calm
    // reminder is pinned: with the tick, the reminder and two buttons all pinned, 200% left the words one line to read.
    val tick: @Composable () -> Unit = {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 64.dp)
                .toggleable(value = adultConfirmed, role = Role.Checkbox, onValueChange = onAdultChange),
        ) {
            Checkbox(checked = adultConfirmed, onCheckedChange = null)
            Text(text = stringResource(R.string.drills_consent_adult), style = MaterialTheme.typography.bodyLarge)
        }
    }
    OnboardingScaffold(
        modifier = modifier,
        scrollHint = true,
        pinned = {
            // A plain bold sentence, not a panel: a panel took the reading area down to one line at 200%.
            if (needsAdultNotice) {
                Text(
                    text = stringResource(R.string.drills_consent_adult_needed),
                    style = MaterialTheme.typography.bodyLarge,
                    fontWeight = FontWeight.Bold,
                    color = RiskMediumFg,
                    modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite },
                )
            }
        },
        actions = {
            PrimaryButton(text = stringResource(R.string.drills_consent_accept), onClick = onAccept)
            SecondaryButton(text = stringResource(R.string.drills_consent_decline), onClick = onDecline)
        },
    ) {
        ConsentTextBlock(rememberConsentParts(ConsentLedger.DRILLS))
        ListenButton(text = stringResource(R.string.onboarding_listen_again), onClick = onListen)
        tick()
    }
}

@Preview(showBackground = true, locale = "vi")
@Preview(showBackground = true, locale = "vi", fontScale = 2f, name = "Cỡ chữ 200%")
@Composable
private fun DrillConsentScreenPreview() {
    HoiConTheme {
        DrillConsentScreen(adultConfirmed = false, needsAdultNotice = true, onAdultChange = {}, onAccept = {}, onDecline = {}, onListen = {})
    }
}
