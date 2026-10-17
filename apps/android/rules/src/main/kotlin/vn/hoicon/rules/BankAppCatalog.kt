// SINH TỰ ĐỘNG bởi scripts/gen-bank-apps.py từ data/bank_apps.vn.json — không sửa tay.
package vn.hoicon.rules

/**
 * Financial apps that arm rule R1 (50 packages, list version [VERSION]). EXACT package match only:
 * `com.vnpay.*` is shared by several banks and a wallet. The same packages are declared in `<queries>`
 * (AndroidManifest.xml) — without that, UsageStats hides them from us on API 30+.
 */
object BankAppCatalog {
    const val VERSION = "2026.10.14-v1"

    private val categories: Map<String, AppCategory> = mapOf(
        "com.VCB" to AppCategory.BANK,
        "com.bab.retailUAT" to AppCategory.BANK,
        "com.finx.vikki" to AppCategory.BANK,
        "com.hdbank.dihdbank" to AppCategory.BANK,
        "com.mbmobile" to AppCategory.BANK,
        "com.msb.digibank.retail" to AppCategory.BANK,
        "com.ncb.bank" to AppCategory.BANK,
        "com.ocb.liobank" to AppCategory.BANK,
        "com.pvcombank.retail" to AppCategory.BANK,
        "com.sacombank.ewallet" to AppCategory.BANK,
        "com.shinhan.global.vn.bank" to AppCategory.BANK,
        "com.sunshine.ksbank" to AppCategory.BANK,
        "com.tpb.mb.gprsandroid" to AppCategory.BANK,
        "com.vib.myvib2" to AppCategory.BANK,
        "com.vietinbank.ipay" to AppCategory.BANK,
        "com.vnpay.Agribank3g" to AppCategory.BANK,
        "com.vnpay.EximBankOmni" to AppCategory.BANK,
        "com.vnpay.SCB" to AppCategory.BANK,
        "com.vnpay.bidv" to AppCategory.BANK,
        "com.vnpay.coopbank" to AppCategory.BANK,
        "com.vnpay.hdbank" to AppCategory.BANK,
        "com.vnpay.vpbankonline" to AppCategory.BANK,
        "io.lifestyle.plus" to AppCategory.BANK,
        "mobile.acb.com.vn" to AppCategory.BANK,
        "ops.namabank.com.vn" to AppCategory.BANK,
        "src.com.sacombank" to AppCategory.BANK,
        "vn.banvietbank.mobilebanking" to AppCategory.BANK,
        "vn.com.agribank.ebanking.ru" to AppCategory.BANK,
        "vn.com.lpb.lienviet24h" to AppCategory.BANK,
        "vn.com.lpbank.digibank" to AppCategory.BANK,
        "vn.com.msb.smartBanking" to AppCategory.BANK,
        "vn.com.ocb.awe" to AppCategory.BANK,
        "vn.com.seabank.mb1" to AppCategory.BANK,
        "vn.com.techcombank.bb.app" to AppCategory.BANK,
        "vn.hoicon.demobank" to AppCategory.BANK,
        "vn.shb.saha.mbanking" to AppCategory.BANK,
        "vn.tnex.consumer" to AppCategory.BANK,
        "xyz.be.cake" to AppCategory.BANK,
        "com.fss.tcbs.mobiletrading" to AppCategory.SECURITIES,
        "org.ssi.iBoardSSI.Pro" to AppCategory.SECURITIES,
        "vn.com.mbs.m24np" to AppCategory.SECURITIES,
        "vn.com.vndirect.stocks" to AppCategory.SECURITIES,
        "vn.com.vpbs.smartone" to AppCategory.SECURITIES,
        "com.beeasy.toppay" to AppCategory.WALLET,
        "com.bplus.vtpay" to AppCategory.WALLET,
        "com.mobifone.mmdt" to AppCategory.WALLET,
        "com.mservice.momotransfer" to AppCategory.WALLET,
        "vn.com.vng.zalopay" to AppCategory.WALLET,
        "vnpay.smartacccount" to AppCategory.WALLET,
        "vnptpay.vnptmedia.vnpt.com.vnptpay" to AppCategory.WALLET,
    )

    val packages: Set<String> get() = categories.keys

    fun categoryOf(packageName: String): AppCategory? = categories[packageName]
}
