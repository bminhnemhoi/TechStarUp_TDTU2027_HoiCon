package vn.hoicon.sentinel.sensing

import vn.hoicon.rules.AppCategory

/**
 * Spike subset of data/bank_apps.vn.json (full list + loading from file/config in P1-S2).
 * EXACT package match only: `com.vnpay.*` is shared by several banks and a wallet. Keep in sync with `<queries>`
 * in AndroidManifest.xml — without it, UsageStats hides these packages from us (package visibility, API 30+).
 */
object BankApps {
    private val categories: Map<String, AppCategory> = mapOf(
        "vn.hoicon.demobank" to AppCategory.BANK, // demo app, emulator + booth
        "com.VCB" to AppCategory.BANK,
        "com.vnpay.bidv" to AppCategory.BANK,
        "com.vietinbank.ipay" to AppCategory.BANK,
        "com.vnpay.Agribank3g" to AppCategory.BANK,
        "com.mbmobile" to AppCategory.BANK,
        "vn.com.techcombank.bb.app" to AppCategory.BANK,
        "com.mservice.momotransfer" to AppCategory.WALLET,
        "vn.com.vng.zalopay" to AppCategory.WALLET,
    )

    fun categoryOf(packageName: String): AppCategory? = categories[packageName]
}
