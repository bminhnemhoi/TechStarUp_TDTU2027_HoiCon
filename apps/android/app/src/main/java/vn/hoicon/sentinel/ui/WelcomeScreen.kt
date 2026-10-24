package vn.hoicon.sentinel.ui

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.size
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import vn.hoicon.sentinel.R
import vn.hoicon.sentinel.ui.theme.BrandNavy
import vn.hoicon.sentinel.ui.theme.HoiConTheme

/**
 * E1 Chào mừng. The first words are the AI disclosure (CLAUDE.md rule 6, tested in AiDisclosureCopyTest);
 * one main action + "Nghe lại".
 */
@Composable
fun WelcomeScreen(onStart: () -> Unit, onListen: () -> Unit, modifier: Modifier = Modifier, notice: String? = null) {
    OnboardingScaffold(
        modifier = modifier,
        actions = {
            PrimaryButton(text = stringResource(R.string.welcome_start), onClick = onStart)
            SecondaryButton(text = stringResource(R.string.onboarding_listen_again), onClick = onListen)
        },
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(16.dp),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Image(
                painter = painterResource(R.drawable.ic_shield_check),
                contentDescription = null,
                colorFilter = ColorFilter.tint(BrandNavy),
                modifier = Modifier.size(96.dp),
            )
        }
        notice?.let { NoticePanel(text = it) }
        Text(
            text = stringResource(R.string.hello_ai_disclosure),
            style = MaterialTheme.typography.bodyLarge,
            fontWeight = FontWeight.SemiBold,
        )
        Text(
            text = stringResource(R.string.welcome_title),
            style = MaterialTheme.typography.headlineMedium,
            modifier = Modifier.semantics { heading() },
        )
        Text(text = stringResource(R.string.welcome_body), style = MaterialTheme.typography.bodyLarge)
    }
}

@Preview(showBackground = true, locale = "vi")
@Preview(showBackground = true, locale = "vi", fontScale = 2f, name = "Cỡ chữ 200%")
@Composable
private fun WelcomeScreenPreview() {
    HoiConTheme { WelcomeScreen(onStart = {}, onListen = {}) }
}
