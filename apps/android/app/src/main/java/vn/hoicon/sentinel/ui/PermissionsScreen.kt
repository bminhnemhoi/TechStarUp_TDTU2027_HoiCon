package vn.hoicon.sentinel.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import vn.hoicon.sentinel.R
import vn.hoicon.sentinel.data.consent.ConsentLedger
import vn.hoicon.sentinel.sensing.SensorPermission
import vn.hoicon.sentinel.ui.theme.BrandNavy
import vn.hoicon.sentinel.ui.theme.HoiConTheme

/** First paragraph and the remaining ones (still joined by a blank line); the rest is "" for a one-paragraph text. */
internal fun splitLead(text: String): Pair<String, String> = text.substringBefore("\n\n") to text.substringAfter("\n\n", "")

private class PermissionRow(val title: String, val why: String, val how: String)

/**
 * The three sensing-chain permissions show the very words their consent purpose hashes (docs/legal/consent/, first line =
 * title, the rest = why); notification and battery settings have no purpose and keep their own short strings.
 */
@Composable
private fun permissionRows(): Map<SensorPermission, PermissionRow> {
    @Composable
    fun consent(permission: SensorPermission, how: Int): PermissionRow {
        val parts = consentParts(LocalContext.current.resources, checkNotNull(ConsentLedger.purposeOf(permission)))
        return PermissionRow(parts.title, parts.body, stringResource(how))
    }
    return mapOf(
        SensorPermission.CALL_SCREENING_ROLE to consent(SensorPermission.CALL_SCREENING_ROLE, R.string.perm_how_role),
        SensorPermission.DISPLAY_OVER_APPS to consent(SensorPermission.DISPLAY_OVER_APPS, R.string.perm_how_settings),
        SensorPermission.USAGE_ACCESS to consent(SensorPermission.USAGE_ACCESS, R.string.perm_how_settings),
        SensorPermission.NOTIFICATIONS to PermissionRow(
            stringResource(R.string.perm_notif_title), stringResource(R.string.perm_notif_why), stringResource(R.string.perm_how_notif),
        ),
        SensorPermission.BATTERY_UNRESTRICTED to PermissionRow(
            stringResource(R.string.perm_battery_title), stringResource(R.string.perm_battery_why), stringResource(R.string.perm_how_battery),
        ),
    )
}

/**
 * Dev screen for spike P1-S1: shows what the sensing chain has and opens the exact settings page for each item.
 * Not the elder onboarding (E3, one permission per screen) — that is P2.
 */
@Composable
fun PermissionsScreen(
    granted: Set<SensorPermission>,
    onOpen: (SensorPermission) -> Unit,
    modifier: Modifier = Modifier,
    onBack: (() -> Unit)? = null,
    onSwitchOff: (SensorPermission) -> Unit = {},
) {
    Surface(modifier = modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(
            modifier = Modifier
                .safeDrawingPadding()
                .verticalScroll(rememberScrollState())
                .padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Text(
                text = stringResource(R.string.hello_title),
                style = MaterialTheme.typography.displaySmall,
                modifier = Modifier.semantics { heading() },
            )
            Text(text = stringResource(R.string.hello_ai_disclosure), style = MaterialTheme.typography.bodyLarge)
            Text(text = stringResource(R.string.perm_screen_intro), style = MaterialTheme.typography.bodyMedium)
            for ((permission, row) in permissionRows()) {
                HorizontalDivider()
                PermissionItem(row = row, isGranted = permission in granted, onOpen = { onOpen(permission) }, onSwitchOff = { onSwitchOff(permission) })
            }
            if (onBack != null) {
                HorizontalDivider()
                SecondaryButton(text = stringResource(R.string.e6_back), onClick = onBack)
            }
        }
    }
}

@Composable
private fun PermissionItem(row: PermissionRow, isGranted: Boolean, onOpen: () -> Unit, onSwitchOff: () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(
            text = row.title,
            style = MaterialTheme.typography.titleLarge,
            modifier = Modifier.semantics { heading() },
        )
        val (lead, rest) = splitLead(row.why)
        Text(text = lead, style = MaterialTheme.typography.bodyMedium)
        // Status is words with a symbol, same navy colour (brand green is only ~5:1 on white, below 7:1).
        val stateWords = stringResource(if (isGranted) R.string.perm_state_on else R.string.perm_state_off)
        Text(
            text = stringResource(if (isGranted) R.string.perm_status_on else R.string.perm_status_off),
            style = MaterialTheme.typography.bodyLarge,
            fontWeight = FontWeight.Bold,
            // The mark is a character: TalkBack gets the state in words (stateDescription), not "dấu kiểm"/"hình tròn".
            modifier = Modifier.semantics { stateDescription = stateWords },
        )
        // UX-9: an item already on needs no action — only its status remains. The button comes right after the first
        // paragraph so a reader at 200% reaches it before the three explanatory ones (reviewer, 22/10).
        if (!isGranted) {
            val a11yLabel = stringResource(R.string.perm_open_settings_for, row.title)
            OutlinedButton(
                onClick = onOpen,
                shape = RoundedCornerShape(32.dp),
                border = BorderStroke(2.dp, BrandNavy), // same navy edge as the other secondary buttons (reviewer: pale edge read as disabled)
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 64.dp)
                    .semantics { contentDescription = a11yLabel },
            ) {
                Text(text = stringResource(R.string.perm_open_settings), style = MaterialTheme.typography.labelLarge)
            }
        }
        if (isGranted) {
            // Withdrawing consent is as easy as giving it: a quiet secondary button to the page that switches the item off.
            val offLabel = stringResource(R.string.perm_switch_off_for, row.title)
            OutlinedButton(
                onClick = onSwitchOff,
                shape = RoundedCornerShape(32.dp),
                border = BorderStroke(2.dp, BrandNavy),
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 64.dp)
                    .semantics { contentDescription = offLabel },
            ) {
                Text(text = stringResource(R.string.perm_switch_off), style = MaterialTheme.typography.labelLarge)
            }
        }
        if (rest.isNotEmpty()) Text(text = rest, style = MaterialTheme.typography.bodyMedium)
    }
}

/**
 * E4 Cấp quyền: one system permission per step (docs/DESIGN-SYSTEM.md), already-granted ones are skipped, "Để sau"
 * never traps the user. The disclosure (E3) has been accepted before this screen is ever reached (SC-003).
 * Granting is detected by the activity on resume; this screen only reflects [granted].
 */
@Composable
fun PermissionStepScreen(
    granted: Set<SensorPermission>,
    consentPending: Boolean,
    onOpen: (SensorPermission) -> Unit,
    onFinish: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val all = SensorPermission.entries
    var passed by rememberSaveable { mutableIntStateOf(0) }
    val index = (passed until all.size).firstOrNull { all[it] !in granted }
    if (index == null) {
        // Without the three sensing-chain permissions HỏiCon cannot protect: never say "ready" then (UX review).
        val missing = all.filter { ConsentLedger.purposeOf(it) != null && it !in granted }
        OnboardingScaffold(modifier = modifier, scrollHint = true, actions = {
            if (missing.isEmpty()) {
                PrimaryButton(text = stringResource(R.string.perm_done_button), onClick = onFinish)
            } else {
                PrimaryButton(text = stringResource(R.string.perm_missing_enable), onClick = { passed = all.indexOf(missing.first()) })
                SecondaryButton(text = stringResource(R.string.perm_step_later), onClick = onFinish)
            }
        }) {
            Text(
                text = stringResource(if (missing.isEmpty()) R.string.perm_done_title else R.string.perm_missing_title),
                style = MaterialTheme.typography.headlineMedium,
                modifier = Modifier.semantics { heading() },
            )
            Text(
                text = stringResource(if (missing.isEmpty()) R.string.perm_done_body else R.string.perm_missing_body),
                style = MaterialTheme.typography.bodyLarge,
            )
            for (permission in all) {
                val row = permissionRows().getValue(permission)
                InfoCard(
                    title = row.title,
                    body = stringResource(if (permission in granted) R.string.perm_status_on else R.string.perm_status_off),
                    bodyBold = true, // status = symbol + words, bold (rule 15)
                )
            }
            if (consentPending) NoticePanel(text = stringResource(R.string.perm_consent_pending))
        }
        return
    }
    val permission = all[index]
    val row = permissionRows().getValue(permission)
    OnboardingScaffold(
        modifier = modifier,
        actions = {
            PrimaryButton(text = stringResource(R.string.perm_step_enable), onClick = { onOpen(permission) })
            SecondaryButton(text = stringResource(R.string.perm_step_later), onClick = { passed = index + 1 })
        },
    ) {
        Text(text = stringResource(R.string.perm_step_counter, index + 1, all.size), style = MaterialTheme.typography.bodyMedium)
        Text(
            text = row.title,
            style = MaterialTheme.typography.headlineMedium,
            modifier = Modifier.semantics { heading() },
        )
        Text(text = row.why, style = MaterialTheme.typography.bodyLarge)
        Text(text = row.how, style = MaterialTheme.typography.bodyMedium)
        if (consentPending) NoticePanel(text = stringResource(R.string.perm_consent_pending))
    }
}

@Preview(showBackground = true, locale = "vi")
@Preview(showBackground = true, locale = "vi", fontScale = 2f, name = "Cỡ chữ 200%")
@Composable
private fun PermissionStepScreenPreview() {
    HoiConTheme {
        PermissionStepScreen(
            granted = setOf(SensorPermission.CALL_SCREENING_ROLE),
            consentPending = false,
            onOpen = {},
            onFinish = {},
        )
    }
}

@Preview(showBackground = true, locale = "vi")
@Preview(showBackground = true, locale = "vi", fontScale = 2f, name = "Cỡ chữ 200%")
@Composable
private fun PermissionsScreenPreview() {
    HoiConTheme {
        PermissionsScreen(granted = setOf(SensorPermission.CALL_SCREENING_ROLE), onOpen = {})
    }
}
