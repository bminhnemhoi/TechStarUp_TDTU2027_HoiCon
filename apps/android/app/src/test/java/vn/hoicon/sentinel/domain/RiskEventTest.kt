package vn.hoicon.sentinel.domain

import java.io.File
import org.json.JSONObject
import org.junit.Test
import vn.hoicon.rules.AppCategory
import vn.hoicon.rules.AppForeground
import vn.hoicon.rules.CallDirection
import vn.hoicon.rules.CallSignal
import vn.hoicon.rules.PiiMasker
import vn.hoicon.rules.RiskLevel
import vn.hoicon.rules.RuleId
import vn.hoicon.sentinel.domain.events.EventTiming
import vn.hoicon.sentinel.domain.events.RiskEventType
import vn.hoicon.sentinel.domain.events.Uuid7
import vn.hoicon.sentinel.outbox.sequentialFactory
import vn.hoicon.sentinel.outbox.stranger
import vn.hoicon.sentinel.outbox.unknownCall
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue

/** Every event the app can build must satisfy docs/schemas/risk_event.v1.json (contract first, CLAUDE.md rule 10). */
class RiskEventTest {
    private val schema = JSONObject(File(System.getProperty("hoicon.schemasDir"), "risk_event.v1.json").readText())
    private val factory = sequentialFactory()
    private val t0 = 1_760_000_000_000L

    private fun assertValid(json: JSONObject) {
        val errors = JsonSchemaLite.validate(schema, json)
        assertTrue(errors.isEmpty(), "$errors in $json")
    }

    @Test
    fun everyEventTypeProducesAValidDocument() {
        for (type in RiskEventType.entries) {
            assertValid(factory.build(type, t0, call = unknownCall(t0 - 90_000, endedAt = t0 - 30_000)).toJson())
            assertValid(factory.build(type, t0).toJson()) // no call, no app: only the required fields
        }
    }

    @Test
    fun bankingEventCarriesRuleCallerAppAndTiming() {
        val event = factory.build(
            RiskEventType.BANKING_APP_FOREGROUND, t0, floor = RiskLevel.CRITICAL, rule = RuleId.R1,
            call = unknownCall(t0 - 400_000, flagged = true), callActive = true,
            app = AppForeground("vn.hoicon.demobank", AppCategory.BANK, t0 - 80),
            timing = EventTiming(detectMs = 80),
        )
        val json = event.toJson()
        assertValid(json)
        assertEquals("R1", json.getString("rule_id"))
        assertEquals("critical", json.getString("rule_floor"))
        assertEquals(stranger.h1, json.getJSONObject("caller").getString("h1"))
        assertEquals("678", json.getJSONObject("caller").getString("last3"))
        assertTrue(json.getJSONObject("caller").getBoolean("flagged"))
        assertEquals("vn.hoicon.demobank", json.getJSONObject("app").getString("package"))
        assertEquals(400, json.getJSONObject("call").getInt("duration_s"))
        assertTrue(json.getJSONObject("call").getBoolean("active"))
        assertEquals(80, json.getJSONObject("timing").getInt("detect_ms"))
    }

    @Test
    fun r5LeavesRuleIdOutBecauseTheSchemaDoesNotListItYet() {
        val json = factory.build(
            RiskEventType.SAFE_PAUSE_SHOWN, t0, floor = RiskLevel.CRITICAL, rule = RuleId.R5,
            call = unknownCall(t0 - 60_000), app = AppForeground("com.anydesk.anydeskandroid", AppCategory.OTHER, t0),
        ).toJson()
        assertValid(json)
        assertFalse(json.has("rule_id"))
        assertEquals("critical", json.getString("rule_floor"))
    }

    @Test
    fun packageIdIsSentOnlyForListedFinancialApps() {
        fun appBlock(pkg: String, category: AppCategory) = factory.build(
            RiskEventType.SAFE_PAUSE_SHOWN, t0, app = AppForeground(pkg, category, t0),
        ).toJson().getJSONObject("app")
        assertEquals("vn.hoicon.demobank", appBlock("vn.hoicon.demobank", AppCategory.BANK).getString("package"))
        assertFalse(appBlock("com.anydesk.anydeskandroid", AppCategory.OTHER).has("package"), "not in bank_apps.vn.json")
        assertFalse(appBlock("com.example.privatehobby", AppCategory.OTHER).has("package"))
    }

    @Test
    fun noRawNumberAnywhereInTheWireJson() {
        val json = factory.build(
            RiskEventType.RISK_WINDOW_OPENED, t0, call = unknownCall(t0), callActive = true,
        ).toJson().toString()
        // Strip what is not a number on purpose (h1: 64 hex, the event id, the timestamp); no run of 8+ digits may remain.
        val rest = json.replace(stranger.h1, "")
            .replace(Regex("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"), "")
            .replace(Regex("\\d{4}-\\d{2}-\\d{2}T[\\d:.]+Z"), "")
        assertFalse(PiiMasker.containsNumber(rest), json)
    }

    @Test
    fun hiddenNumberMeansNoCallerBlock() {
        val hidden = CallSignal(null, CallDirection.INCOMING, false, false, t0, null)
        val json = factory.build(RiskEventType.RISK_WINDOW_OPENED, t0, call = hidden).toJson()
        assertValid(json)
        assertFalse(json.has("caller"))
    }

    @Test
    fun sinceEndIsSetOnlyAfterTheCallEnded() {
        val ended = factory.build(RiskEventType.RISK_WINDOW_CLOSED, t0, call = unknownCall(t0 - 700_000, endedAt = t0 - 600_000))
            .toJson().getJSONObject("call")
        assertEquals(600, ended.getInt("since_end_s"))
        assertFalse(ended.getBoolean("active"))
        val ongoing = factory.build(RiskEventType.RISK_WINDOW_OPENED, t0, call = unknownCall(t0 - 5_000)).toJson().getJSONObject("call")
        assertFalse(ongoing.has("since_end_s"))
        assertEquals(5, ongoing.getInt("duration_s"))
    }

    @Test
    fun idsAreTimeOrderedUuidV7() {
        val a = Uuid7.generate(t0)
        val b = Uuid7.generate(t0 + 1)
        assertTrue(Regex("^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$").matches(a), a)
        assertTrue(a < b)
        assertEquals(t0, a.replace("-", "").substring(0, 12).toLong(16))
        assertTrue(a != Uuid7.generate(t0), "random part differs")
        assertNull(JSONObject(factory.build(RiskEventType.CALL_STARTED, t0).toJson().toString()).optJSONObject("caller"))
    }
}
