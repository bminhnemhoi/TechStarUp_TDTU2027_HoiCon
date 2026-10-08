package vn.hoicon.rules

import java.io.File
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

class RiskLevelTest {
    @Test
    fun atLeastRaisesButNeverLowersBelowFloor() {
        assertEquals(RiskLevel.HIGH, RiskLevel.LOW.atLeast(RiskLevel.HIGH))
        assertEquals(RiskLevel.CRITICAL, RiskLevel.CRITICAL.atLeast(RiskLevel.MEDIUM))
        assertEquals(RiskLevel.NONE, RiskLevel.NONE.atLeast(RiskLevel.NONE))
        for (level in RiskLevel.entries) {
            for (floor in RiskLevel.entries) {
                val result = level.atLeast(floor)
                assertTrue(result >= floor && result >= level, "$level.atLeast($floor) = $result")
                assertTrue(result == level || result == floor, "$level.atLeast($floor) = $result")
            }
        }
    }

    @Test
    fun wireValuesMatchRuleFloorInRiskEventSchema() {
        val path = assertNotNull(System.getProperty("hoicon.riskEventSchema"), "schema path not set by Gradle")
        val schema = File(path).readText()
        val enumBody = Regex(""""rule_floor"\s*:\s*\{\s*"enum"\s*:\s*\[([^\]]*)]""").find(schema)?.groupValues?.get(1)
        assertNotNull(enumBody, "rule_floor enum not found in $path")
        val schemaValues = Regex(""""([^"]+)"""").findAll(enumBody).map { it.groupValues[1] }.toList()
        assertEquals(schemaValues, RiskLevel.entries.map { it.wire })
    }
}
