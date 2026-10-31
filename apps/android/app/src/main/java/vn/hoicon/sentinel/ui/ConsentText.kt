package vn.hoicon.sentinel.ui

import android.content.res.Resources
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import vn.hoicon.sentinel.data.consent.consentLines

/**
 * One consent text (docs/legal/consent/<purpose>.vi.md) cut for drawing: the AI sentence when the file opens with it,
 * the title, and the paragraphs. Nothing is dropped, so a screen built from the parts shows every line the ledger hashes
 * ([lines] is the whole list again). The 10 files all follow this shape (Spec 011 README).
 */
internal class ConsentParts(val ai: String?, val title: String, val paragraphs: List<String>) {
    val lines: List<String> get() = listOfNotNull(ai, title) + paragraphs
    val body: String get() = paragraphs.joinToString("\n\n")
}

internal fun consentParts(lines: List<String>): ConsentParts {
    require(lines.isNotEmpty()) { "empty consent text" }
    val hasAi = lines.size > 1 && lines.first().startsWith(AI_LINE_PREFIX)
    val rest = if (hasAi) lines.drop(1) else lines
    return ConsentParts(ai = if (hasAi) lines.first() else null, title = rest.first(), paragraphs = rest.drop(1))
}

internal fun consentParts(res: Resources, purpose: String) = consentParts(consentLines(res, purpose))

private const val AI_LINE_PREFIX = "Đây là trợ lý AI HỏiCon"

@Composable
internal fun rememberConsentParts(purpose: String): ConsentParts {
    val res = LocalContext.current.resources
    val configuration = LocalConfiguration.current
    return remember(purpose, configuration) { consentParts(res, purpose) }
}

/** The AI sentence (bold, first), the title as the heading and every paragraph at reading size. */
@Composable
internal fun ConsentTextBlock(parts: ConsentParts, modifier: Modifier = Modifier) {
    parts.ai?.let {
        Text(text = it, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Bold, modifier = modifier)
    }
    Text(
        text = parts.title,
        style = MaterialTheme.typography.headlineMedium,
        modifier = modifier.semantics { heading() },
    )
    for (paragraph in parts.paragraphs) {
        Text(text = paragraph, style = MaterialTheme.typography.bodyLarge, modifier = modifier)
    }
}
