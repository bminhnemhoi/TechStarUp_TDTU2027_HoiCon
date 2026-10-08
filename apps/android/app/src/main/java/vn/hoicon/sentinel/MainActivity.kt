package vn.hoicon.sentinel

import android.Manifest
import android.app.role.RoleManager
import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import vn.hoicon.sentinel.sensing.HcSpikeLog
import vn.hoicon.sentinel.sensing.SensorPermission
import vn.hoicon.sentinel.sensing.SensorPermissions
import vn.hoicon.sentinel.ui.PermissionsScreen
import vn.hoicon.sentinel.ui.theme.HoiConTheme

class MainActivity : ComponentActivity() {
    private var granted by mutableStateOf(emptySet<SensorPermission>())

    private val roleRequest = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { refresh() }

    private val runtimeRequest = registerForActivityResult(ActivityResultContracts.RequestPermission()) { ok ->
        // Permanently denied: the dialog no longer shows, so send the user to the app's settings page instead.
        if (!ok) openSettings(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, withPackage = true)
        refresh()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            HoiConTheme {
                PermissionsScreen(granted = granted, onOpen = ::open)
            }
        }
    }

    override fun onResume() {
        super.onResume()
        refresh()
    }

    private fun refresh() {
        granted = SensorPermissions.granted(this)
    }

    private fun open(permission: SensorPermission) {
        when (permission) {
            SensorPermission.CALL_SCREENING_ROLE -> roleRequest.launch(
                getSystemService(RoleManager::class.java).createRequestRoleIntent(RoleManager.ROLE_CALL_SCREENING),
            )
            SensorPermission.DISPLAY_OVER_APPS -> openSettings(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, withPackage = true)
            SensorPermission.USAGE_ACCESS -> openSettings(Settings.ACTION_USAGE_ACCESS_SETTINGS)
            SensorPermission.NOTIFICATIONS -> if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                runtimeRequest.launch(Manifest.permission.POST_NOTIFICATIONS)
            } else {
                startSafely(
                    Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).putExtra(Settings.EXTRA_APP_PACKAGE, packageName),
                )
            }
            // List screen only: the direct "allow" dialog needs REQUEST_IGNORE_BATTERY_OPTIMIZATIONS (Play-restricted).
            SensorPermission.BATTERY_UNRESTRICTED -> openSettings(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS)
        }
    }

    private fun openSettings(action: String, withPackage: Boolean = false) {
        val intent = Intent(action)
        if (withPackage) intent.data = Uri.fromParts("package", packageName, null)
        startSafely(intent)
    }

    private fun startSafely(intent: Intent) {
        try {
            startActivity(intent)
        } catch (e: ActivityNotFoundException) {
            HcSpikeLog.w("settings page missing: ${intent.action}", e)
            startActivity(Intent(Settings.ACTION_SETTINGS))
        }
    }
}
