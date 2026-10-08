// AGP 9 compiles Kotlin itself (built-in Kotlin); the Kotlin plugins here pin the Kotlin version for every module.
plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.kotlin.jvm) apply false
    alias(libs.plugins.kotlin.compose) apply false
}
