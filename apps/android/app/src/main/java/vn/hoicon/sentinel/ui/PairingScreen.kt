package vn.hoicon.sentinel.ui

import androidx.annotation.StringRes
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.ime
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.sp
import androidx.compose.runtime.remember
import vn.hoicon.sentinel.R
import vn.hoicon.sentinel.ui.theme.HoiConTheme

enum class PairingError(@StringRes val message: Int) {
    INCOMPLETE(R.string.pairing_error_incomplete),
    INVALID(R.string.pairing_error_invalid),
    RATE_LIMITED(R.string.pairing_error_rate_limited),
    NETWORK(R.string.pairing_error_network),
    SERVER(R.string.pairing_error_server),
}

sealed interface PairingUi {
    data object Idle : PairingUi

    data object Loading : PairingUi

    data class Failed(val error: PairingError) : PairingUi
}

/** Size of the digits in the code box (spec 020: large, centred). */
private const val CODE_SP = 32

/**
 * E2 Ghép đôi. Six big digits on the numeric keypad; the model submits by itself at the sixth digit, the button is
 * the fallback (also the retry after "no network"). Errors are calm sentences with a next step, never a bare code.
 */
@Composable
fun PairingScreen(
    code: String,
    state: PairingUi,
    onCodeChange: (String) -> Unit,
    onSubmit: () -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val focus = remember { FocusRequester() }
    LaunchedEffect(Unit) { focus.requestFocus() }
    val label = stringResource(R.string.pairing_code_label)
    OnboardingScaffold(
        modifier = modifier,
        pinned = {
            Text(text = label, style = MaterialTheme.typography.bodyMedium)
            OutlinedTextField(
                value = code,
                onValueChange = onCodeChange,
                singleLine = true,
                textStyle = MaterialTheme.typography.headlineMedium.copy(
                    fontSize = CODE_SP.sp,
                    lineHeight = (CODE_SP + 8).sp,
                    textAlign = TextAlign.Center,
                    letterSpacing = 4.sp,
                ),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number, imeAction = ImeAction.Done),
                keyboardActions = KeyboardActions(onDone = { onSubmit() }),
                // No contentDescription here: it would replace the digits TalkBack reads back to the user.
                modifier = Modifier.fillMaxWidth().focusRequester(focus),
            )
            if (state is PairingUi.Failed) {
                NoticePanel(text = stringResource(state.error.message))
            }
        },
        actions = {
            val failed = (state as? PairingUi.Failed)?.error
            PrimaryButton(
                text = stringResource(
                    when {
                        state is PairingUi.Loading -> R.string.pairing_connecting
                        failed == PairingError.NETWORK || failed == PairingError.SERVER -> R.string.pairing_retry
                        else -> R.string.pairing_connect
                    },
                ),
                onClick = onSubmit,
            )
            // With the keyboard open there is little room: the system Back gesture still goes back (BackHandler).
            if (WindowInsets.ime.getBottom(LocalDensity.current) == 0) {
                SecondaryButton(text = stringResource(R.string.pairing_back), onClick = onBack)
            }
        },
    ) {
        Text(
            text = stringResource(R.string.pairing_title),
            style = MaterialTheme.typography.headlineMedium,
            modifier = Modifier.semantics { heading() },
        )
        Text(text = stringResource(R.string.pairing_body), style = MaterialTheme.typography.bodyLarge)
    }
}

@Preview(showBackground = true, locale = "vi")
@Preview(showBackground = true, locale = "vi", fontScale = 2f, name = "Cỡ chữ 200%")
@Composable
private fun PairingScreenPreview() {
    HoiConTheme {
        PairingScreen("123456", PairingUi.Failed(PairingError.INVALID), onCodeChange = {}, onSubmit = {}, onBack = {})
    }
}
