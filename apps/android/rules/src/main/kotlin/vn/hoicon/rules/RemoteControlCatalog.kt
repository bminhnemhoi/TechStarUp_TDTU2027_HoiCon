package vn.hoicon.rules

/**
 * Remote-control apps that arm rule R5 (idea I1): a stranger on the phone asks the victim to install one and "share
 * the screen". EXACT package match, same as [BankAppCatalog]; the same packages are declared in `<queries>`
 * (AndroidManifest.xml) so UsageStats can see them on API 30+ without QUERY_ALL_PACKAGES.
 *
 * Packages are the Google Play ids of the vendors' own apps. UltraViewer (named in the spec) has no Android app, so
 * there is nothing to list for it. A fake or sideloaded copy under another package id is not caught: that is the
 * `sideload_detected` signal, a later spec.
 */
object RemoteControlCatalog {
    const val VERSION = "2026.10.16-v1"

    val packages: Set<String> = setOf(
        "com.anydesk.anydeskandroid", // AnyDesk
        "com.teamviewer.teamviewer.market.mobile", // TeamViewer
        "com.teamviewer.quicksupport.market", // TeamViewer QuickSupport
        "com.teamviewer.host.market", // TeamViewer Host
        "com.carriez.flutter_hbb", // RustDesk
        "com.google.chromeremotedesktop", // Chrome Remote Desktop
    )

    fun isRemoteControl(packageName: String): Boolean = packageName in packages
}
