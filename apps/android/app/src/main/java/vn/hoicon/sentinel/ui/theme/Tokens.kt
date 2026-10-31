// SINH TỰ ĐỘNG bởi scripts/gen-design-tokens.py từ design-system/hoicon/tokens.json — không sửa tay.
package vn.hoicon.sentinel.ui.theme

import androidx.compose.ui.graphics.Color

/** Token thiết kế HỏiCon v1.0.0 (docs/DESIGN-SYSTEM.md); bí danh ở Color.kt/Type.kt. */
object HoiConTokens {
    const val Version = "1.0.0"
    const val FontFamilyName = "Be Vietnam Pro"

    object Colors {
        val BrandNavy = Color(0xFF1F3A5F)
        val BrandOrange = Color(0xFFC4561D)
        val BrandOrangeText = Color(0xFF843410)
        val BrandGreen = Color(0xFF1E7B53)
        val BrandGreenText = Color(0xFF115A3B)
        val SurfaceBase = Color(0xFFFFFFFF)
        val SurfaceMuted = Color(0xFFF4F6F9)
        val TextPrimary = Color(0xFF1F3A5F)
        val TextOnPrimary = Color(0xFFFFFFFF)
        val RiskLowFg = Color(0xFF13603F)
        val RiskLowBg = Color(0xFFF0F9F4)
        val RiskLowAccent = Color(0xFF1E7B53)
        val RiskMediumFg = Color(0xFF7A4A00)
        val RiskMediumBg = Color(0xFFFFF8E6)
        val RiskMediumAccent = Color(0xFFA66300)
        val RiskHighFg = Color(0xFF8C2F10)
        val RiskHighBg = Color(0xFFFFF7F2)
        val RiskHighAccent = Color(0xFFC4561D)
        val RiskCriticalFg = Color(0xFF991B1B)
        val RiskCriticalBg = Color(0xFFFEF2F2)
        val RiskCriticalAccent = Color(0xFFDC2626)
        val DrillFg = Color(0xFF4C2A85)
        val DrillBg = Color(0xFFF5F0FC)
        val DrillAccent = Color(0xFF7C4DBA)
        val SimFg = Color(0xFF0A4A78)
        val SimBg = Color(0xFFEEF6FC)
        val SimAccent = Color(0xFF1F76B5)
        val FocusRing = Color(0xFF005FCC)
    }

    object Type {
        const val DisplaySp = 36
        const val DisplayLineSp = 44
        const val DisplayWeight = 700
        const val HeadlineSp = 28
        const val HeadlineLineSp = 36
        const val HeadlineWeight = 700
        const val TitleSp = 24
        const val TitleLineSp = 32
        const val TitleWeight = 700
        const val BodyLargeSp = 22
        const val BodyLargeLineSp = 32
        const val BodyLargeWeight = 400
        const val BodySp = 20
        const val BodyLineSp = 28
        const val BodyWeight = 400
        const val ButtonSp = 24
        const val ButtonLineSp = 30
        const val ButtonWeight = 700
    }

    object Size {
        const val TouchMinDp = 64
        const val SpaceXsDp = 4
        const val SpaceSmDp = 8
        const val SpaceMdDp = 12
        const val SpaceLgDp = 16
        const val SpaceXlDp = 24
        const val SpaceXxlDp = 32
        const val RadiusButtonDp = 16
        const val RadiusCardDp = 20
    }

    object Motion {
        const val ShortMs = 150
        const val MediumMs = 250
        const val ReducedMs = 0
    }
}
