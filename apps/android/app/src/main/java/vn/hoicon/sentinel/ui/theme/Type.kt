package vn.hoicon.sentinel.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import vn.hoicon.sentinel.R

// Be Vietnam Pro (OFL 1.1) is bundled in res/font: no network or Play services needed, so the safe-pause screen
// keeps its font offline (CLAUDE.md rule 4). Sizes come from the generated tokens (elder scale, rule 15).
val BeVietnamPro = FontFamily(
    Font(R.font.be_vietnam_pro_regular, FontWeight.Normal),
    Font(R.font.be_vietnam_pro_semibold, FontWeight.SemiBold),
    Font(R.font.be_vietnam_pro_bold, FontWeight.Bold),
)

private fun style(size: Int, lineSize: Int, weight: Int) = TextStyle(
    fontFamily = BeVietnamPro,
    fontWeight = FontWeight(weight),
    fontSize = size.sp,
    lineHeight = lineSize.sp,
)

private val tokens = HoiConTokens.Type
private val display = style(tokens.DisplaySp, tokens.DisplayLineSp, tokens.DisplayWeight)
private val headline = style(tokens.HeadlineSp, tokens.HeadlineLineSp, tokens.HeadlineWeight)
private val title = style(tokens.TitleSp, tokens.TitleLineSp, tokens.TitleWeight)
private val bodyLarge = style(tokens.BodyLargeSp, tokens.BodyLargeLineSp, tokens.BodyLargeWeight)
private val body = style(tokens.BodySp, tokens.BodyLineSp, tokens.BodyWeight)
private val button = style(tokens.ButtonSp, tokens.ButtonLineSp, tokens.ButtonWeight)

// Every Material 3 role is mapped (nothing falls back to Roboto or to M3's 11-16sp defaults: rule 15, text >= 20sp).
val HoiConTypography = Typography(
    displayLarge = display,
    displayMedium = display,
    displaySmall = display,
    headlineLarge = headline,
    headlineMedium = headline,
    headlineSmall = headline,
    titleLarge = title,
    titleMedium = title,
    titleSmall = title,
    bodyLarge = bodyLarge,
    bodyMedium = body,
    bodySmall = body,
    labelLarge = button,
    labelMedium = button,
    labelSmall = button,
)
