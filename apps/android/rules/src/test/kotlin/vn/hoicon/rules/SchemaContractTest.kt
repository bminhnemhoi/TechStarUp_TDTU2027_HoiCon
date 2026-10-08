package vn.hoicon.rules

import java.io.File
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull

/** Enums sent in RiskEvent must match `docs/schemas/risk_event.v1.json` exactly (contract first, CLAUDE.md rule 10). */
class SchemaContractTest {
    private val schema: String by lazy {
        val path = assertNotNull(System.getProperty("hoicon.riskEventSchema"), "schema path not set by Gradle")
        File(path).readText()
    }

    private fun schemaEnum(property: String): List<String> {
        val body = Regex(""""$property"\s*:\s*\{\s*"enum"\s*:\s*\[([^\]]*)]""").find(schema)?.groupValues?.get(1)
        assertNotNull(body, "enum for $property not found")
        return Regex(""""([^"]+)"""").findAll(body).map { it.groupValues[1] }.toList()
    }

    @Test
    fun ruleIdMatchesSchema() = assertEquals(schemaEnum("rule_id"), RuleId.entries.map { it.wire })

    @Test
    fun appCategoryMatchesSchema() = assertEquals(schemaEnum("category"), AppCategory.entries.map { it.wire })

    @Test
    fun callDirectionMatchesSchema() = assertEquals(schemaEnum("direction"), CallDirection.entries.map { it.wire })
}
