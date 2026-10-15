plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
}

android {
    namespace = "vn.hoicon.sentinel"
    compileSdk = 36

    defaultConfig {
        applicationId = "vn.hoicon.sentinel"
        minSdk = 29
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildTypes {
        // Địa chỉ máy chủ ghép đôi (spec 020). Debug: máy chủ dev trên máy chủ của AVD (10.0.2.2); ghi đè bằng
        // -PhoiconApiBaseUrl=... Release: HTTPS (cleartext bị chặn từ API 28). Đường dừng an toàn KHÔNG dùng mạng.
        val apiBaseUrl = providers.gradleProperty("hoiconApiBaseUrl")
        fun checked(url: String, schemes: List<String>): String {
            require(Regex("^[A-Za-z0-9:/._-]+$").matches(url) && schemes.any(url::startsWith)) {
                "hoiconApiBaseUrl must start with ${schemes.joinToString(" or ")} and contain no quotes/spaces: $url"
            }
            return url
        }
        debug {
            val url = checked(apiBaseUrl.getOrElse("http://10.0.2.2:18000"), listOf("http://", "https://"))
            buildConfigField("String", "API_BASE_URL", "\"$url\"")
        }
        release {
            val url = checked(apiBaseUrl.getOrElse("https://api.hoicon.vn"), listOf("http://", "https://"))
            buildConfigField("String", "API_BASE_URL", "\"$url\"")
        }
    }

    buildFeatures {
        compose = true
        // BuildConfig.DEBUG gates spike diagnostics (HC_TIMING/HC_SPIKE logs, demo h1, UI A/B switch) out of release.
        buildConfig = true
    }
}

dependencies {
    implementation(project(":rules"))

    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.security.crypto)
    debugImplementation(libs.androidx.compose.ui.tooling)

    testImplementation(libs.junit)
    testImplementation(libs.kotlin.test)
    testImplementation(libs.org.json)
}

// Contract tests (spec 020) read the shared JSON Schemas + fixtures; declare them as inputs so schema edits re-run tests.
tasks.withType<Test>().configureEach {
    val schemas = layout.projectDirectory.dir("../../../docs/schemas")
    inputs.dir(schemas).withPathSensitivity(PathSensitivity.RELATIVE)
    systemProperty("hoicon.schemasDir", schemas.asFile.absolutePath)
    // Consent-text pin test reads the strings the user sees (data/consent/ConsentTexts.kt).
    val strings = layout.projectDirectory.file("src/main/res/values/strings.xml")
    inputs.file(strings).withPathSensitivity(PathSensitivity.NONE)
    systemProperty("hoicon.appStrings", strings.asFile.absolutePath)
}

// Release is HTTPS only: packaging refuses anything else, instead of failing at run time on the elder's phone.
// (Debug builds accept http:// too; the debug-only network config lets them reach 10.0.2.2 only.)
val releaseApiBaseUrl = providers.gradleProperty("hoiconApiBaseUrl").getOrElse("https://api.hoicon.vn")
tasks.matching { it.name in setOf("assembleRelease", "bundleRelease", "packageRelease") }.configureEach {
    doFirst { require(releaseApiBaseUrl.startsWith("https://")) { "release needs an https:// hoiconApiBaseUrl, got $releaseApiBaseUrl" } }
}
