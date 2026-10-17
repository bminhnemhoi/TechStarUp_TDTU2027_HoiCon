package vn.hoicon.sentinel.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import vn.hoicon.sentinel.R
import vn.hoicon.sentinel.ui.theme.HoiConTheme

/**
 * E3 Công bố nổi bật (Google Play "prominent disclosure"): shown in full BEFORE the system opens any permission page
 * (E4), says what is collected, why, and what is never done, and needs a deliberate tap on "Tôi hiểu và tiếp tục".
 * "Chưa đồng ý" (and Back) is a real answer: it leads to [DisclosureDeclinedScreen], nothing is recorded. The words here are exactly what the consent ledger hashes
 * (data/consent/ConsentTexts.kt); change them only together with ConsentLedger.VERSION.
 */
@Composable
fun ProminentDisclosureScreen(
    familyName: String,
    onAccept: () -> Unit,
    onDecline: () -> Unit,
    onListen: () -> Unit,
    modifier: Modifier = Modifier,
) {
    OnboardingScaffold(
        modifier = modifier,
        actions = {
            PrimaryButton(text = stringResource(R.string.disclosure_accept), onClick = onAccept)
            SecondaryButton(text = stringResource(R.string.disclosure_decline), onClick = onDecline)
        },
    ) {
        if (familyName.isNotBlank()) {
            Text(
                text = stringResource(R.string.disclosure_connected, familyName),
                style = MaterialTheme.typography.bodyLarge,
                fontWeight = FontWeight.SemiBold,
            )
        }
        Text(
            text = stringResource(R.string.disclosure_title),
            style = MaterialTheme.typography.headlineMedium,
            modifier = Modifier.semantics { heading() },
        )
        ListenButton(text = stringResource(R.string.onboarding_listen_again), onClick = onListen)
        InfoCard(stringResource(R.string.disclosure_1_title), stringResource(R.string.disclosure_1_body))
        InfoCard(stringResource(R.string.disclosure_2_title), stringResource(R.string.disclosure_2_body))
        InfoCard(stringResource(R.string.disclosure_3_title), stringResource(R.string.disclosure_3_body))
        InfoCard(stringResource(R.string.disclosure_4_title), stringResource(R.string.disclosure_4_body))
        Text(text = stringResource(R.string.disclosure_next), style = MaterialTheme.typography.bodyMedium)
    }
}

/** After "Chưa đồng ý": calm, no pressure, one way back and one way out. */
@Composable
fun DisclosureDeclinedScreen(onReview: () -> Unit, onClose: () -> Unit, modifier: Modifier = Modifier) {
    OnboardingScaffold(
        modifier = modifier,
        actions = {
            PrimaryButton(text = stringResource(R.string.decline_review), onClick = onReview)
            SecondaryButton(text = stringResource(R.string.decline_close), onClick = onClose)
        },
    ) {
        Text(
            text = stringResource(R.string.decline_title),
            style = MaterialTheme.typography.headlineMedium,
            modifier = Modifier.semantics { heading() },
        )
        Text(text = stringResource(R.string.decline_body), style = MaterialTheme.typography.bodyLarge)
    }
}

@Preview(showBackground = true, locale = "vi")
@Preview(showBackground = true, locale = "vi", fontScale = 2f, name = "Cỡ chữ 200%")
@Composable
private fun ProminentDisclosureScreenPreview() {
    HoiConTheme {
        ProminentDisclosureScreen(familyName = "Gia đình Bác Ba", onAccept = {}, onDecline = {}, onListen = {})
    }
}
