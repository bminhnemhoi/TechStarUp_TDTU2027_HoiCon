package vn.hoicon.sentinel.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import vn.hoicon.sentinel.R
import vn.hoicon.sentinel.data.consent.ConsentLedger

/**
 * E12 (Spec 038): the confirmation after "Tắt" ("Tắt …? HỏiCon sẽ không … nữa."), and the words again before `guardian_alerts` is
 * switched back on. Two buttons, "Quay lại" never records anything (and is the solid one when turning off). The other purposes switch back on through their own screens.
 */
@Composable
fun ConsentSwitchScreen(purpose: String, turningOff: Boolean, onConfirm: () -> Unit, onBack: () -> Unit, modifier: Modifier = Modifier) {
    val parts = rememberConsentParts(purpose)
    OnboardingScaffold(
        modifier = modifier,
        scrollHint = true,
        actions = {
            // Turning protection off: the safe answer ("Quay lại") is the solid button; turning something on: the confirmation is.
            if (turningOff) {
                PrimaryButton(text = stringResource(R.string.switch_off_back), onClick = onBack)
                SecondaryButton(text = stringResource(R.string.switch_off_confirm), onClick = onConfirm)
            } else {
                PrimaryButton(text = stringResource(R.string.switch_on_confirm), onClick = onConfirm)
                SecondaryButton(text = stringResource(R.string.switch_off_back), onClick = onBack)
            }
        },
    ) {
        if (turningOff) {
            Text(
                text = stringResource(R.string.switch_off_title, stringResource(switchNoun(purpose))),
                style = MaterialTheme.typography.headlineMedium,
                modifier = Modifier.semantics { heading() },
            )
            Text(text = consequence(purpose), style = MaterialTheme.typography.bodyLarge)
        } else {
            Text(
                text = stringResource(R.string.switch_on_title, stringResource(switchNoun(purpose))),
                style = MaterialTheme.typography.headlineMedium,
                modifier = Modifier.semantics { heading() },
            )
            Text(text = stringResource(R.string.switch_on_intro), style = MaterialTheme.typography.bodyLarge)
            ConsentTextBlock(parts)
        }
    }
}

/** The thing being switched, in the words of the screens ("việc báo cho con cháu"): shared by the question, the banner after it and the list. */
fun switchNoun(purpose: String): Int = when (purpose) {
    ConsentLedger.GUARDIAN_ALERTS -> R.string.switch_noun_guardian_alerts
    ConsentLedger.LOOKUPS -> R.string.switch_noun_lookups
    else -> R.string.switch_noun_drills
}

@Composable
private fun consequence(purpose: String): String = stringResource(
    when (purpose) {
        ConsentLedger.GUARDIAN_ALERTS -> R.string.switch_off_consequence_guardian_alerts
        ConsentLedger.LOOKUPS -> R.string.switch_off_consequence_lookups
        else -> R.string.switch_off_consequence_drills
    },
)
