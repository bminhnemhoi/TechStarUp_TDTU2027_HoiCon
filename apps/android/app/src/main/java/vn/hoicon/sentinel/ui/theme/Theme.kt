package vn.hoicon.sentinel.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

// Light only for now; navy on white is ~11.5:1 (>= 7:1 required for the elder app).
private val HoiConColors = lightColorScheme(
    primary = BrandNavy,
    onPrimary = SurfaceWhite,
    secondary = BrandOrange,
    onSecondary = SurfaceWhite,
    tertiary = BrandGreen,
    onTertiary = SurfaceWhite,
    background = SurfaceWhite,
    onBackground = BrandNavy,
    surface = SurfaceWhite,
    onSurface = BrandNavy,
)

@Composable
fun HoiConTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = HoiConColors, typography = HoiConTypography, content = content)
}
