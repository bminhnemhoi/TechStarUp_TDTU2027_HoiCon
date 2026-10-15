package vn.hoicon.sentinel.domain

import org.json.JSONArray
import org.json.JSONObject

/**
 * Just enough JSON Schema (2020-12) for `docs/schemas/risk_event.v1.json`: type, required, properties,
 * additionalProperties=false, enum, const, pattern, minimum, maxLength, format uuid / date-time, and allOf/if/then.
 * Not a general validator; it exists so a contract change breaks a test here instead of a batch on the server.
 */
object JsonSchemaLite {
    private val uuid = Regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
    private val dateTime = Regex("^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?(Z|[+-]\\d{2}:\\d{2})$")

    fun validate(schema: JSONObject, value: Any?, path: String = "$"): List<String> {
        val errors = ArrayList<String>()
        check(schema, value, path, errors)
        return errors
    }

    private fun check(schema: JSONObject, value: Any?, path: String, errors: MutableList<String>) {
        schema.optJSONArray("enum")?.let { options ->
            if (options.toList().none { it == value }) errors += "$path: $value not in enum ${options.toList()}"
        }
        if (schema.has("const") && schema.get("const") != value) errors += "$path: expected const ${schema.get("const")}"
        schema.optString("type").takeIf { it.isNotEmpty() }?.let { type ->
            if (!typeMatches(type, value)) {
                errors += "$path: expected $type but was ${value?.javaClass?.simpleName}"
                return
            }
        }
        if (value is String) {
            schema.optString("pattern").takeIf { it.isNotEmpty() }?.let {
                if (!Regex(it).containsMatchIn(value)) errors += "$path: '$value' does not match $it"
            }
            if (schema.has("maxLength") && value.length > schema.getInt("maxLength")) errors += "$path: longer than maxLength"
            when (schema.optString("format")) {
                "uuid" -> if (!uuid.matches(value)) errors += "$path: not a uuid"
                "date-time" -> if (!dateTime.matches(value)) errors += "$path: not a date-time"
            }
        }
        if (value is Number && schema.has("minimum") && value.toDouble() < schema.getDouble("minimum")) {
            errors += "$path: below minimum"
        }
        if (value is JSONObject) checkObject(schema, value, path, errors)
        schema.optJSONArray("allOf")?.let { all ->
            for (i in 0 until all.length()) {
                val rule = all.getJSONObject(i)
                val condition = rule.optJSONObject("if")
                if (condition == null || validate(condition, value, path).isEmpty()) {
                    rule.optJSONObject("then")?.let { check(it, value, path, errors) }
                }
            }
        }
    }

    private fun checkObject(schema: JSONObject, value: JSONObject, path: String, errors: MutableList<String>) {
        schema.optJSONArray("required")?.toList()?.forEach { key ->
            if (!value.has(key as String)) errors += "$path: missing required '$key'"
        }
        val properties = schema.optJSONObject("properties")
        if (schema.opt("additionalProperties") == false && properties != null) {
            value.keys().forEach { key -> if (!properties.has(key)) errors += "$path: unexpected property '$key'" }
        }
        properties?.keys()?.forEach { key ->
            if (value.has(key)) check(properties.getJSONObject(key), value.get(key), "$path.$key", errors)
        }
    }

    private fun typeMatches(type: String, value: Any?): Boolean = when (type) {
        "object" -> value is JSONObject
        "string" -> value is String
        "boolean" -> value is Boolean
        "integer" -> value is Int || value is Long
        "number" -> value is Number
        "array" -> value is JSONArray
        else -> true
    }

    private fun JSONArray.toList(): List<Any?> = List(length()) { get(it) }
}
