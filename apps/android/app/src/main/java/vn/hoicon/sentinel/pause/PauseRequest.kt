package vn.hoicon.sentinel.pause

import android.content.Intent
import vn.hoicon.rules.AppCategory
import vn.hoicon.rules.RiskLevel
import vn.hoicon.rules.RuleId

/** What the safe pause is about; picks the words and the "leave" button. */
enum class PauseKind {
    /** R1: a bank, wallet or securities app opened after a call from a stranger. */
    FINANCIAL,

    /** R5: a remote-control app opened after a call from a stranger. */
    REMOTE_CONTROL,
}

/**
 * Everything E7 needs, carried in the intent from the risk window (or from the fallback notification). No number,
 * no name: the caller is read from the window state only when an event is built.
 *
 * @property appAtMs when the app came to the front (UsageStats clock), to time `app_foreground → pause_shown`.
 */
data class PauseRequest(
    val level: RiskLevel,
    val category: AppCategory,
    val ruleId: RuleId?,
    val packageName: String,
    val appAtMs: Long,
    val callActive: Boolean,
) {
    val kind: PauseKind get() = if (ruleId == RuleId.R5) PauseKind.REMOTE_CONTROL else PauseKind.FINANCIAL

    fun putInto(intent: Intent): Intent = intent
        .putExtra(EXTRA_LEVEL, level.wire)
        .putExtra(EXTRA_CATEGORY, category.wire)
        .putExtra(EXTRA_RULE, ruleId?.name)
        .putExtra(EXTRA_PACKAGE, packageName)
        .putExtra(EXTRA_APP_AT, appAtMs)
        .putExtra(EXTRA_CALL_ACTIVE, callActive)

    companion object {
        private const val EXTRA_LEVEL = "level"
        private const val EXTRA_CATEGORY = "category"
        private const val EXTRA_RULE = "rule"
        private const val EXTRA_PACKAGE = "package"
        private const val EXTRA_APP_AT = "app_at"
        private const val EXTRA_CALL_ACTIVE = "call_active"

        /** Tolerant: a missing or unknown extra falls back to the safe default (a HIGH pause about a bank app). */
        fun from(intent: Intent?) = PauseRequest(
            level = RiskLevel.entries.firstOrNull { it.wire == intent?.getStringExtra(EXTRA_LEVEL) } ?: RiskLevel.HIGH,
            category = AppCategory.entries.firstOrNull { it.wire == intent?.getStringExtra(EXTRA_CATEGORY) } ?: AppCategory.BANK,
            ruleId = RuleId.entries.firstOrNull { it.name == intent?.getStringExtra(EXTRA_RULE) },
            packageName = intent?.getStringExtra(EXTRA_PACKAGE).orEmpty(),
            appAtMs = intent?.getLongExtra(EXTRA_APP_AT, 0L) ?: 0L,
            callActive = intent?.getBooleanExtra(EXTRA_CALL_ACTIVE, true) ?: true,
        )
    }
}
