package vn.hoicon.sentinel.ui

import androidx.annotation.StringRes
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
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import vn.hoicon.sentinel.R
import vn.hoicon.sentinel.sensing.SensorPermission
import vn.hoicon.sentinel.ui.theme.HoiConTheme

private class PermissionRow(@StringRes val title: Int, @StringRes val why: Int)

private val rows = mapOf(
    SensorPermission.CALL_SCREENING_ROLE to PermissionRow(R.string.perm_role_title, R.string.perm_role_why),
    SensorPermission.DISPLAY_OVER_APPS to PermissionRow(R.string.perm_overlay_title, R.string.perm_overlay_why),
    SensorPermission.USAGE_ACCESS to PermissionRow(R.string.perm_usage_title, R.string.perm_usage_why),
    SensorPermission.NOTIFICATIONS to PermissionRow(R.string.perm_notif_title, R.string.perm_notif_why),
    SensorPermission.BATTERY_UNRESTRICTED to PermissionRow(R.string.perm_battery_title, R.string.perm_battery_why),
)

/**
 * Dev screen for spike P1-S1: shows what the sensing chain has and opens the exact settings page for each item.
 * Not the elder onboarding (E3, one permission per screen) — that is P2.
 */
@Composable
fun PermissionsScreen(
    granted: Set<SensorPermission>,
    onOpen: (SensorPermission) -> Unit,
    modifier: Modifier = Modifier,
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
            for ((permission, row) in rows) {
                HorizontalDivider()
                PermissionItem(row = row, isGranted = permission in granted, onOpen = { onOpen(permission) })
            }
        }
    }
}

@Composable
private fun PermissionItem(row: PermissionRow, isGranted: Boolean, onOpen: () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(
            text = stringResource(row.title),
            style = MaterialTheme.typography.titleLarge,
            modifier = Modifier.semantics { heading() },
        )
        Text(text = stringResource(row.why), style = MaterialTheme.typography.bodyMedium)
        // Status is words with a symbol, same navy colour (brand green is only ~5:1 on white, below 7:1).
        Text(
            text = stringResource(if (isGranted) R.string.perm_status_on else R.string.perm_status_off),
            style = MaterialTheme.typography.bodyLarge,
        )
        // UX-9: an item already on needs no action — only its status remains.
        if (!isGranted) {
            val a11yLabel = stringResource(R.string.perm_open_settings_for, stringResource(row.title))
            OutlinedButton(
                onClick = onOpen,
                shape = RoundedCornerShape(32.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 64.dp)
                    .semantics { contentDescription = a11yLabel },
            ) {
                Text(text = stringResource(R.string.perm_open_settings), style = MaterialTheme.typography.labelLarge)
            }
        }
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
