package vn.hoicon.sentinel

import android.Manifest
import android.app.role.RoleManager
import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import vn.hoicon.sentinel.sensing.HcSpikeLog
import vn.hoicon.sentinel.sensing.SensorPermission

/**
 * Opens the system page (or dialog) for one sensing permission. Shared by the home screen and the onboarding E4 so both
 * behave the same. Create it while the activity is being constructed (it registers result launchers); [onChanged] runs
 * when the user comes back from a role / permission dialog.
 */
class PermissionOpener(private val activity: ComponentActivity, private val onChanged: () -> Unit) {
    private val roleRequest = activity.registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { onChanged() }

    private val runtimeRequest = activity.registerForActivityResult(ActivityResultContracts.RequestPermission()) { ok ->
        // Permanently denied: the dialog no longer shows, so send the user to the app's settings page instead.
        if (!ok) openSettings(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, withPackage = true)
        onChanged()
    }

    fun open(permission: SensorPermission) {
        when (permission) {
            SensorPermission.CALL_SCREENING_ROLE -> roleRequest.launch(
                activity.getSystemService(RoleManager::class.java).createRequestRoleIntent(RoleManager.ROLE_CALL_SCREENING),
            )
            SensorPermission.DISPLAY_OVER_APPS -> openSettings(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, withPackage = true)
            SensorPermission.USAGE_ACCESS -> openSettings(Settings.ACTION_USAGE_ACCESS_SETTINGS)
            SensorPermission.NOTIFICATIONS -> if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                runtimeRequest.launch(Manifest.permission.POST_NOTIFICATIONS)
            } else {
                startSafely(
                    Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).putExtra(Settings.EXTRA_APP_PACKAGE, activity.packageName),
                )
            }
            // List screen only: the direct "allow" dialog needs REQUEST_IGNORE_BATTERY_OPTIMIZATIONS (Play-restricted).
            SensorPermission.BATTERY_UNRESTRICTED -> openSettings(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS)
        }
    }

    private fun openSettings(action: String, withPackage: Boolean = false) {
        val intent = Intent(action)
        if (withPackage) intent.data = Uri.fromParts("package", activity.packageName, null)
        startSafely(intent)
    }

    private fun startSafely(intent: Intent) {
        try {
            activity.startActivity(intent)
        } catch (e: ActivityNotFoundException) {
            HcSpikeLog.w("settings page missing: ${intent.action}", e)
            activity.startActivity(Intent(Settings.ACTION_SETTINGS))
        }
    }
}
