package vn.hoicon.rules

/**
 * Risk levels in ascending order. [wire] values mirror `rule_floor` in `docs/schemas/risk_event.v1.json`.
 */
enum class RiskLevel(val wire: String) {
    NONE("none"),
    LOW("low"),
    MEDIUM("medium"),
    HIGH("high"),
    CRITICAL("critical"),
    ;

    /** The higher of this level and [floor]: a risk may be raised, never lowered below the on-device floor. */
    fun atLeast(floor: RiskLevel): RiskLevel = maxOf(this, floor)
}
