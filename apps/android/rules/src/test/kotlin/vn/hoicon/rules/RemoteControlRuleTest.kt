package vn.hoicon.rules

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

/** R5 (idea I1): a remote-control app in front inside the window of an untrusted call ⇒ critical, whatever the call. */
class RemoteControlRuleTest {
    private val minute = 60_000L
    private val t0 = 1_760_000_000_000L
    private val anyDesk = "com.anydesk.anydeskandroid"
    private val stranger = HashedPhone(h1 = "a".repeat(64), last3 = "001")

    private fun call(trusted: Boolean = false, flagged: Boolean = false, endedAt: Long? = null) =
        CallSignal(stranger, CallDirection.INCOMING, trusted, flagged, startedAtMs = t0, endedAtMs = endedAt)

    private fun remoteAt(atMs: Long, pkg: String = anyDesk) = AppForeground(pkg, AppCategory.OTHER, atMs)

    @Test
    fun remoteControlAppInWindowIsCriticalR5() {
        assertEquals(Decision(RiskLevel.CRITICAL, RuleId.R5), RiskEngine.evaluate(call(), remoteAt(t0 + minute)))
        assertTrue(RiskEngine.evaluate(call(), remoteAt(t0 + minute)).pausesUser)
    }

    @Test
    fun shortCallStillCriticalUnlikeR1() {
        // R1 is only "high" for a short unflagged call; remote control is critical from the first minute.
        assertEquals(RiskLevel.HIGH, RiskEngine.evaluate(call(), AppForeground("vn.hoicon.demobank", AppCategory.BANK, t0 + minute)).level)
        assertEquals(RiskLevel.CRITICAL, RiskEngine.evaluate(call(), remoteAt(t0 + minute)).level)
    }

    @Test
    fun allListedPackagesTrigger() {
        for (pkg in RemoteControlCatalog.packages) {
            assertEquals(RuleId.R5, RiskEngine.evaluate(call(), remoteAt(t0 + minute, pkg)).ruleId, pkg)
        }
    }

    @Test
    fun windowEndsTenMinutesAfterTheCall() {
        val ended = call(endedAt = t0 + minute)
        assertEquals(RuleId.R5, RiskEngine.evaluate(ended, remoteAt(t0 + 11 * minute)).ruleId) // exactly 10 min
        assertEquals(Decision.NONE, RiskEngine.evaluate(ended, remoteAt(t0 + 11 * minute + 1)))
    }

    @Test
    fun trustedCallerAndNoCallDoNothing() {
        assertEquals(Decision(RiskLevel.NONE, RuleId.R0), RiskEngine.evaluate(call(trusted = true), remoteAt(t0 + minute)))
        assertEquals(Decision.NONE, RiskEngine.evaluate(null, remoteAt(t0 + minute)))
    }

    @Test
    fun beforeTheCallStartsDoesNotCount() {
        assertEquals(Decision.NONE, RiskEngine.evaluate(call(), remoteAt(t0 - 1)))
    }

    @Test
    fun floorStillRaisesNeverLowers() {
        assertEquals(RiskLevel.CRITICAL, RiskEngine.evaluate(call(), remoteAt(t0 + minute), floor = RiskLevel.HIGH).level)
    }

    @Test
    fun alreadyInFrontWhenTheCallConnectsIsCaught() {
        val decision = RiskEngine.evaluateForegroundDuringCall(
            call(), remoteAt(t0 - 5 * minute), callConnected = true, nowMs = t0 + 2_000,
        )
        assertEquals(Decision(RiskLevel.CRITICAL, RuleId.R5), decision)
    }

    @Test
    fun exactPackageMatchOnly() {
        assertTrue(RemoteControlCatalog.isRemoteControl(anyDesk))
        assertFalse(RemoteControlCatalog.isRemoteControl("com.anydesk"), "no prefix matching")
        assertFalse(RemoteControlCatalog.isRemoteControl("com.anydesk.anydeskandroid.fake".uppercase()))
        assertFalse(RemoteControlCatalog.isRemoteControl("vn.hoicon.demobank"))
    }

    @Test
    fun r5IsNotAFinancialApp() {
        // The two catalogs must never overlap: a package is either money or remote control.
        assertTrue(RemoteControlCatalog.packages.none { BankAppCatalog.categoryOf(it) != null })
    }

    @Test
    fun manifestQueriesListEveryRemoteControlPackage() {
        val manifest = java.io.File(checkNotNull(System.getProperty("hoicon.appManifest"))).readText()
        val queried = Regex("""<package android:name="([^"]+)"""").findAll(manifest).map { it.groupValues[1] }.toSet()
        assertTrue(queried.containsAll(RemoteControlCatalog.packages), "add the missing <package> to <queries>")
    }
}
