package vn.hoicon.sentinel.sensing

import android.Manifest
import android.app.AppOpsManager
import android.app.role.RoleManager
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.os.PowerManager
import android.os.Process
import android.provider.Settings

/** Everything the sensing chain needs, as currently granted. Read on every resume of the dev screen. */
enum class SensorPermission {
    CALL_SCREENING_ROLE,
    DISPLAY_OVER_APPS,
    USAGE_ACCESS,
    NOTIFICATIONS,
    BATTERY_UNRESTRICTED,
}

object SensorPermissions {
    fun granted(context: Context): Set<SensorPermission> = SensorPermission.entries.filterTo(mutableSetOf()) {
        isGranted(context, it)
    }

    fun isGranted(context: Context, permission: SensorPermission): Boolean = when (permission) {
        SensorPermission.CALL_SCREENING_ROLE ->
            context.getSystemService(RoleManager::class.java).isRoleHeld(RoleManager.ROLE_CALL_SCREENING)
        SensorPermission.DISPLAY_OVER_APPS -> Settings.canDrawOverlays(context)
        SensorPermission.USAGE_ACCESS -> hasUsageAccess(context)
        SensorPermission.NOTIFICATIONS -> if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
        } else {
            context.getSystemService(android.app.NotificationManager::class.java).areNotificationsEnabled()
        }
        SensorPermission.BATTERY_UNRESTRICTED ->
            context.getSystemService(PowerManager::class.java).isIgnoringBatteryOptimizations(context.packageName)
    }

    @Suppress("DEPRECATION") // unsafeCheckOpNoThrow is the API 29+ call; its replacement needs a newer API level.
    private fun hasUsageAccess(context: Context): Boolean {
        val mode = context.getSystemService(AppOpsManager::class.java)
            .unsafeCheckOpNoThrow(AppOpsManager.OPSTR_GET_USAGE_STATS, Process.myUid(), context.packageName)
        return mode == AppOpsManager.MODE_ALLOWED ||
            (
                mode == AppOpsManager.MODE_DEFAULT &&
                    context.checkSelfPermission(Manifest.permission.PACKAGE_USAGE_STATS) == PackageManager.PERMISSION_GRANTED
                )
    }
}
