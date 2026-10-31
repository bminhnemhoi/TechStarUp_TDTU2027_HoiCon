package vn.hoicon.sentinel.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

// Light only (DS5); navy on white is ~11.5:1 (>= 7:1 required for the elder app).
private val HoiConColors = lightColorScheme(
    primary = BrandNavy,
    onPrimary = SurfaceWhite,
    // Text-on-colour roles use the >= 7:1 variants (DS3): white on BrandOrange / BrandGreen is only ~4.5-5.2:1.
    secondary = BrandOrangeText,
    onSecondary = SurfaceWhite,
    tertiary = BrandGreenText,
    onTertiary = SurfaceWhite,
    background = SurfaceWhite,
    onBackground = BrandNavy,
    surface = SurfaceWhite,
    onSurface = BrandNavy,
    // UX-9: Material defaults (grey outlines/secondary text) fall below 7:1 on white; keep everything navy.
    onSurfaceVariant = BrandNavy,
    outline = BrandNavy,
    outlineVariant = BrandNavy.copy(alpha = 0.4f),
)

@Composable
fun HoiConTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = HoiConColors, typography = HoiConTypography, content = content)
}
