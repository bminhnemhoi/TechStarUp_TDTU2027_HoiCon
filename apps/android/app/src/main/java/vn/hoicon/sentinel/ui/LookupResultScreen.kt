package vn.hoicon.sentinel.ui

import androidx.annotation.DrawableRes
import androidx.annotation.StringRes
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import vn.hoicon.sentinel.R
import vn.hoicon.sentinel.data.lookup.LookupOutcome
import vn.hoicon.sentinel.data.lookup.NoticeReason
import vn.hoicon.sentinel.data.remote.LookupAnswer
import vn.hoicon.sentinel.data.remote.LookupKind
import vn.hoicon.sentinel.data.remote.LookupReason
import vn.hoicon.sentinel.data.remote.LookupSource
import vn.hoicon.sentinel.data.remote.LookupVerdict
import vn.hoicon.sentinel.ui.theme.BrandNavy
import vn.hoicon.sentinel.ui.theme.HoiConTheme
import vn.hoicon.sentinel.ui.theme.HoiConTokens
import vn.hoicon.sentinel.ui.theme.RiskCriticalAccent
import vn.hoicon.sentinel.ui.theme.RiskCriticalBg
import vn.hoicon.sentinel.ui.theme.RiskCriticalFg
import vn.hoicon.sentinel.ui.theme.RiskHighAccent
import vn.hoicon.sentinel.ui.theme.RiskHighBg
import vn.hoicon.sentinel.ui.theme.RiskHighFg
import vn.hoicon.sentinel.ui.theme.RiskLowAccent
import vn.hoicon.sentinel.ui.theme.RiskLowBg
import vn.hoicon.sentinel.ui.theme.RiskLowFg
import vn.hoicon.sentinel.ui.theme.SurfaceMuted

/**
 * The five things E10 can say (Spec 026 FR-011), each with its own colour AND icon AND words, never colour alone.
 * A phone number can never be [SAFE]: [LookupOutcome] and the client both rule that out, and [of] has no way to ask for it.
 */
internal enum class LookupLook(
    val bg: Color,
    val fg: Color,
    val accent: Color,
    @DrawableRes val icon: Int,
    @StringRes val iconDescription: Int,
    @StringRes val title: Int,
    @StringRes val action: Int,
) {
    DANGEROUS(RiskCriticalBg, RiskCriticalFg, RiskCriticalAccent, R.drawable.ic_risk_danger, R.string.lookup_icon_danger, R.string.lookup_dangerous_title, R.string.lookup_dangerous_action),
    WARNING(RiskHighBg, RiskHighFg, RiskHighAccent, R.drawable.ic_risk_warning, R.string.lookup_icon_warning, R.string.lookup_warning_title, R.string.lookup_warning_action),
    UNKNOWN(SurfaceMuted, BrandNavy, BrandNavy, R.drawable.ic_risk_unknown, R.string.lookup_icon_unknown, R.string.lookup_unknown_title, R.string.lookup_unknown_action),
    SAFE(RiskLowBg, RiskLowFg, RiskLowAccent, R.drawable.ic_shield_check, R.string.lookup_icon_safe, R.string.lookup_safe_title, R.string.lookup_safe_action),
    OFFLINE_LISTED(RiskHighBg, RiskHighFg, RiskHighAccent, R.drawable.ic_risk_offline, R.string.lookup_icon_offline, R.string.lookup_offline_listed_title, R.string.lookup_offline_listed_action),
    OFFLINE_UNKNOWN(SurfaceMuted, BrandNavy, BrandNavy, R.drawable.ic_risk_offline, R.string.lookup_icon_offline, R.string.lookup_offline_unknown_title, R.string.lookup_offline_unknown_action),
    TRANSFER(RiskHighBg, RiskHighFg, RiskHighAccent, R.drawable.ic_risk_warning, R.string.lookup_icon_transfer, R.string.lookup_transfer_title, R.string.lookup_transfer_action),
    ;

    companion object {
        fun of(outcome: LookupOutcome): LookupLook? = when (outcome) {
            is LookupOutcome.Answer -> when (outcome.answer.verdict) {
                LookupVerdict.DANGEROUS -> DANGEROUS
                LookupVerdict.WARNING -> WARNING
                LookupVerdict.UNKNOWN -> UNKNOWN
                LookupVerdict.SAFE -> if (outcome.kind == LookupKind.URL) SAFE else UNKNOWN
            }
            is LookupOutcome.Offline -> if (outcome.possiblyListed) OFFLINE_LISTED else OFFLINE_UNKNOWN
            is LookupOutcome.Transfer -> TRANSFER
            is LookupOutcome.Notice -> null
        }
    }
}

/** The sentences read aloud for an outcome: the AI disclosure first, then the verdict, then what to do. */
fun lookupSpeech(ai: String, title: String, action: String) = listOf(ai, title, action)

/**
 * E10 result. Two actions only: "Hỏi con" (main) and "Xong". The card, the advice, the reasons and the sources scroll;
 * the two buttons stay pinned at the bottom at any text size. [askChildMessage] is the answer to a tap on "Hỏi con".
 */
@Composable
fun LookupResultScreen(
    outcome: LookupOutcome,
    onAskChild: () -> Unit,
    onDone: () -> Unit,
    onListen: () -> Unit,
    modifier: Modifier = Modifier,
    @StringRes askChildMessage: Int? = null,
) {
    val look = LookupLook.of(outcome)
    OnboardingScaffold(
        modifier = modifier,
        actions = {
            PrimaryButton(text = stringResource(R.string.e6_ask_child), onClick = onAskChild)
            SecondaryButton(text = stringResource(R.string.lookup_done), onClick = onDone)
        },
    ) {
        val disclosure = when (outcome) {
            is LookupOutcome.Answer -> outcome.answer.disclaimer.ifBlank { stringResource(R.string.lookup_offline_ai) }
            else -> stringResource(R.string.lookup_offline_ai)
        }
        // Only the AI sentence is bold and first (it is also read first); the rest of the disclaimer goes after the advice, so at
        // 200% text the verdict and what to do are not pushed below the fold by a long preamble.
        val (aiSentence, disclaimerRest) = splitDisclosure(disclosure)
        Text(text = aiSentence, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Bold)
        if (outcome is LookupOutcome.Answer && outcome.answer.isDemo) DemoLabel()
        when {
            look != null -> VerdictCard(look, subject(outcome))
            outcome is LookupOutcome.Notice -> NoticePanel(text = stringResource(noticeText(outcome.reason)))
        }
        // The answer to "Hỏi con" sits right under the card so it is seen without scrolling at 200% text.
        if (askChildMessage != null) NoticePanel(text = stringResource(askChildMessage))
        if (look != null) {
            Text(text = stringResource(look.action), style = MaterialTheme.typography.bodyLarge)
            ListenButton(text = stringResource(R.string.onboarding_listen_again), onClick = onListen)
        }
        if (disclaimerRest.isNotEmpty()) Text(text = disclaimerRest, style = MaterialTheme.typography.bodyMedium)
        if (outcome is LookupOutcome.Answer) {
            visibleReasons(outcome.answer.kind, outcome.answer.reasons.map { it.text })
                .forEach { Text(text = it, style = MaterialTheme.typography.bodyMedium) }
            Sources(outcome.answer.sources)
        }
    }
}

/** "Đây là trợ lý AI HỏiCon. Kết quả chỉ để tham khảo…" ⇒ the first sentence and the rest ("" if there is only one). */
internal fun splitDisclosure(text: String): Pair<String, String> {
    val cut = text.indexOf(". ")
    return if (cut < 0) text to "" else text.substring(0, cut + 1) to text.substring(cut + 2).trim()
}

/**
 * The server's reasons are shown as written, except a phone reason that calls the number "an toàn": a phone number is never
 * declared safe (Spec 026 FR-003), whatever the server says.
 */
internal fun visibleReasons(kind: LookupKind, reasons: List<String>): List<String> =
    if (kind == LookupKind.PHONE) reasons.filterNot { it.contains("an toàn", ignoreCase = true) } else reasons

@StringRes
private fun noticeText(reason: NoticeReason) = when (reason) {
    NoticeReason.RATE_LIMITED -> R.string.lookup_notice_rate
    NoticeReason.CONSENT_PENDING -> R.string.lookup_notice_consent
    NoticeReason.GENERIC -> R.string.lookup_notice_generic
    NoticeReason.QR_UNREADABLE -> R.string.lookup_notice_qr
}

@Composable
private fun subject(outcome: LookupOutcome): String {
    if (outcome is LookupOutcome.Transfer) {
        val payee = stringResource(R.string.lookup_transfer_payee, outcome.payeeName)
        val amount = outcome.amountVnd?.let { stringResource(R.string.lookup_transfer_amount, "%,d".format(java.util.Locale.GERMANY, it)) }
        return listOfNotNull(payee, amount).joinToString("\n")
    }
    val (kind, label) = when (outcome) {
        is LookupOutcome.Answer -> outcome.kind to outcome.subject
        is LookupOutcome.Offline -> outcome.kind to outcome.subject
        is LookupOutcome.Notice, is LookupOutcome.Transfer -> return ""
    }
    return stringResource(if (kind == LookupKind.PHONE) R.string.lookup_subject_phone else R.string.lookup_subject_link, label)
}

@Composable
private fun VerdictCard(look: LookupLook, subject: String) {
    val shape = RoundedCornerShape(HoiConTokens.Size.RadiusCardDp.dp)
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .fillMaxWidth()
            .clip(shape)
            .background(look.bg)
            .border(2.dp, look.accent, shape)
            .padding(HoiConTokens.Size.SpaceLgDp.dp)
            .semantics(mergeDescendants = true) { liveRegion = LiveRegionMode.Polite },
    ) {
        Image(
            painter = painterResource(look.icon),
            contentDescription = null, // the title beside it already says the same; the icon is for the eye (shape + colour + words)
            colorFilter = ColorFilter.tint(look.accent),
            modifier = Modifier.size(56.dp),
        )
        Column(
            verticalArrangement = Arrangement.spacedBy(HoiConTokens.Size.SpaceSmDp.dp),
            modifier = Modifier.padding(start = HoiConTokens.Size.SpaceMdDp.dp),
        ) {
            Text(
                text = stringResource(look.title),
                style = MaterialTheme.typography.headlineSmall,
                color = look.fg,
                modifier = Modifier.semantics { heading() },
            )
            if (subject.isNotEmpty()) Text(text = subject, style = MaterialTheme.typography.bodyMedium, color = look.fg)
        }
    }
}

@Composable
private fun DemoLabel() {
    val shape = RoundedCornerShape(8.dp)
    Text(
        text = stringResource(R.string.lookup_demo_label),
        style = MaterialTheme.typography.bodyMedium,
        fontWeight = FontWeight.Bold,
        color = BrandNavy,
        modifier = Modifier
            .clip(shape)
            .background(SurfaceMuted)
            .border(1.dp, BrandNavy, shape)
            .padding(horizontal = 14.dp, vertical = 6.dp),
    )
}

@Composable
private fun Sources(sources: List<LookupSource>) {
    if (sources.isEmpty()) return
    val lines = sources.map { source ->
        source.name
    }
    InfoCard(title = stringResource(R.string.lookup_sources_title), body = lines.joinToString("\n"))
}

private fun sampleAnswer(kind: LookupKind, verdict: LookupVerdict) = LookupAnswer(
    verificationId = "01851bd2-0000-7000-8000-0000000000aa",
    kind = kind,
    verdict = verdict,
    confidence = 0.9,
    reasons = listOf(LookupReason("listed_high", "Số này nằm trong danh sách cảnh báo lừa đảo.")),
    sources = listOf(LookupSource("Cục An ninh mạng (mẫu)", "threat_list", "0123456789abcdef", null)),
    disclaimer = "Đây là trợ lý AI HỏiCon. Kết quả chỉ để tham khảo.",
    incidentLevel = null,
    isDemo = true,
)

@Preview(showBackground = true, locale = "vi")
@Preview(showBackground = true, locale = "vi", fontScale = 2f, name = "Cỡ chữ 200%")
@Composable
private fun DangerPreview() {
    HoiConTheme {
        LookupResultScreen(LookupOutcome.Answer(LookupKind.PHONE, "002", sampleAnswer(LookupKind.PHONE, LookupVerdict.DANGEROUS)), {}, {}, {})
    }
}

@Preview(showBackground = true, locale = "vi", name = "An toàn (đường link, xem trước)")
@Composable
private fun SafePreview() {
    HoiConTheme {
        LookupResultScreen(LookupOutcome.Answer(LookupKind.URL, "example.org", sampleAnswer(LookupKind.URL, LookupVerdict.SAFE)), {}, {}, {})
    }
}

@Preview(showBackground = true, locale = "vi", name = "Mất mạng")
@Composable
private fun OfflinePreview() {
    HoiConTheme { LookupResultScreen(LookupOutcome.Offline(LookupKind.PHONE, "002", possiblyListed = true), {}, {}, {}) }
}
