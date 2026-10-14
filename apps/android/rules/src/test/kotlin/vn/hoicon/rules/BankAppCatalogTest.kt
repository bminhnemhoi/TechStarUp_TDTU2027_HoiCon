package vn.hoicon.rules

import java.io.File
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertNull

/**
 * data/bank_apps.vn.json is the single source (P1-S2); BankAppCatalog.kt and the manifest `<queries>` are generated
 * from it by scripts/gen-bank-apps.py. A failure here means: run the script and commit its output.
 */
class BankAppCatalogTest {
    private fun file(property: String): String {
        val path = assertNotNull(System.getProperty(property), "$property not set by Gradle")
        return File(path).readText(Charsets.UTF_8)
    }

    private val json by lazy { file("hoicon.bankApps") }

    /** package → category of every entry in `apps` (`"candidate_package"` of `unverified` never matches). */
    private val jsonApps: Map<String, String> by lazy {
        Regex(""""package"\s*:\s*"([^"]+)"[^}]*?"category"\s*:\s*"([^"]+)"""")
            .findAll(json)
            .associate { it.groupValues[1] to it.groupValues[2] }
    }

    @Test
    fun catalogMatchesJson() {
        val version = Regex(""""version"\s*:\s*"([^"]+)"""").find(json)?.groupValues?.get(1)
        assertEquals(version, BankAppCatalog.VERSION, "run python scripts/gen-bank-apps.py")
        assertEquals(jsonApps, BankAppCatalog.packages.associateWith { BankAppCatalog.categoryOf(it)?.wire })
    }

    @Test
    fun manifestQueriesMatchJson() {
        val block = Regex("""BEGIN bank_apps.*?END bank_apps""", RegexOption.DOT_MATCHES_ALL).find(file("hoicon.appManifest"))
        assertNotNull(block, "bank_apps markers missing in AndroidManifest.xml")
        val queried = Regex("""<package android:name="([^"]+)"""").findAll(block.value).map { it.groupValues[1] }.toSet()
        assertEquals(jsonApps.keys, queried, "run python scripts/gen-bank-apps.py")
    }

    @Test
    fun exactMatchOnly() {
        assertEquals(AppCategory.BANK, BankAppCatalog.categoryOf("com.vnpay.bidv"))
        assertNull(BankAppCatalog.categoryOf("com.vnpay"), "no prefix matching: com.vnpay.* spans banks and a wallet")
        assertNull(BankAppCatalog.categoryOf("com.vcb"), "package names are case-sensitive")
    }
}
