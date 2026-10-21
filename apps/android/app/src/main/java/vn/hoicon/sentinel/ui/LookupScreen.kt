package vn.hoicon.sentinel.ui

import androidx.annotation.StringRes
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.ime
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.tooling.preview.Preview
import vn.hoicon.sentinel.R
import vn.hoicon.sentinel.data.consent.ConsentLedger
import vn.hoicon.sentinel.ui.theme.HoiConTheme

/** Why the typed text was not checked; shown under the field as a calm sentence with the next step. */
enum class LookupError(@StringRes val message: Int) {
    EMPTY(R.string.lookup_error_empty),
    PHONE(R.string.lookup_error_phone),
    LINK(R.string.lookup_error_link),
    PASTE(R.string.lookup_error_paste),
    SCAN(R.string.lookup_error_scan),
}

/**
 * E10 consent, asked just in time before the FIRST check (Spec 026 FR-011). Same shape as E3: the words are exactly what
 * the consent ledger hashes for the `lookups` purpose (data/consent/ConsentTexts.kt); change them only together with
 * ConsentLedger.VERSION. "Để sau" is a real answer: nothing is recorded and nothing is checked.
 */
@Composable
fun LookupConsentScreen(
    onAccept: () -> Unit,
    onDecline: () -> Unit,
    onListen: () -> Unit,
    modifier: Modifier = Modifier,
) {
    OnboardingScaffold(
        modifier = modifier,
        actions = {
            PrimaryButton(text = stringResource(R.string.lookups_consent_accept), onClick = onAccept)
            SecondaryButton(text = stringResource(R.string.lookups_consent_decline), onClick = onDecline)
        },
    ) {
        // Every line of docs/legal/consent/lookups.vi.md, as the ledger hashes it (the family sentence included).
        ConsentTextBlock(rememberConsentParts(ConsentLedger.LOOKUPS))
        ListenButton(text = stringResource(R.string.onboarding_listen_again), onClick = onListen)
    }
}

/**
 * E10 "Kiểm tra số hay đường link": one box for a phone number or a pasted link, one main button. The box and its
 * message stay pinned above the keyboard (only the intro scrolls), so nothing is lost at 200% text. The raw text lives
 * only in [text]; the model hashes or cuts it on "Kiểm tra" and clears it.
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
fun LookupScreen(
    text: String,
    error: LookupError?,
    checking: Boolean,
    onTextChange: (String) -> Unit,
    onCheck: () -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    canScan: Boolean = false,
    onScan: () -> Unit = {},
    onPaste: () -> Unit = {},
) {
    OnboardingScaffold(
        modifier = modifier,
        pinned = {
            // Only the box and its message stay above the keyboard. The keyboard opens when the person touches the box, so the
            // title, the hint and "Quay lại" are all in view on arrival (at 200% text an open keyboard hid them).
            OutlinedTextField(
                value = text,
                onValueChange = onTextChange,
                singleLine = true,
                label = { Text(text = stringResource(R.string.lookup_field_label), style = MaterialTheme.typography.bodyMedium) },
                textStyle = MaterialTheme.typography.bodyLarge,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone, imeAction = ImeAction.Done),
                keyboardActions = KeyboardActions(onDone = { onCheck() }),
                modifier = Modifier.fillMaxWidth().heightIn(min = 64.dp),
            )
            if (error != null) NoticePanel(text = stringResource(error.message))
        },
        actions = {
            PrimaryButton(
                text = stringResource(if (checking) R.string.lookup_checking else R.string.lookup_check),
                onClick = onCheck,
            )
            if (WindowInsets.ime.getBottom(LocalDensity.current) == 0) {
                SecondaryButton(text = stringResource(R.string.lookup_back), onClick = onBack)
            }
        },
    ) {
        Text(text = stringResource(R.string.lookup_ai), style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Bold)
        Text(
            text = stringResource(R.string.lookup_title),
            style = MaterialTheme.typography.headlineMedium,
            modifier = Modifier.semantics { heading() },
        )
        Text(text = stringResource(R.string.lookup_hint), style = MaterialTheme.typography.bodyLarge)
        // Small inline controls, not action-bar buttons: the screen keeps its one main action. No scanner without Play services.
        FlowRow(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            ListenButton(text = stringResource(R.string.lookup_paste), onClick = onPaste)
            if (canScan) ListenButton(text = stringResource(R.string.lookup_scan), onClick = onScan)
        }
    }
}

@Preview(showBackground = true, locale = "vi")
@Preview(showBackground = true, locale = "vi", fontScale = 2f, name = "Cỡ chữ 200%")
@Composable
private fun LookupScreenPreview() {
    HoiConTheme {
        LookupScreen("bit.ly/abc", LookupError.LINK, checking = false, onTextChange = {}, onCheck = {}, onBack = {}, canScan = true)
    }
}

@Preview(showBackground = true, locale = "vi", fontScale = 2f, name = "Đồng ý, cỡ chữ 200%")
@Composable
private fun LookupConsentPreview() {
    HoiConTheme { LookupConsentScreen(onAccept = {}, onDecline = {}, onListen = {}) }
}
