plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.ksp)
}

android {
    namespace = "vn.hoicon.sentinel"
    compileSdk = 36

    defaultConfig {
        applicationId = "vn.hoicon.sentinel"
        minSdk = 29
        targetSdk = 36
        versionCode = 3
        versionName = "0.3.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    // MigrationTestHelper reads the exported Room schemas (app/schemas) as test assets.
    sourceSets.getByName("androidTest").assets.directories.add(layout.projectDirectory.dir("schemas").asFile.absolutePath)

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    // Ký bản phát hành bằng biến môi trường (tệp khóa và mật khẩu KHÔNG nằm trong repo). Không đặt đủ bốn biến ⇒ bản release
    // không ký (APK `-unsigned`, AAB không chữ ký): đủ để chạy release-gate, nhưng không tải lên Play được.
    val signingFile = providers.environmentVariable("HOICON_KEYSTORE_FILE").orNull
    val signingStorePass = providers.environmentVariable("HOICON_KEYSTORE_PASSWORD").orNull
    val signingAlias = providers.environmentVariable("HOICON_KEY_ALIAS").orNull
    val signingKeyPass = providers.environmentVariable("HOICON_KEY_PASSWORD").orNull
    val releaseSigning = if (signingFile != null && signingStorePass != null && signingAlias != null && signingKeyPass != null) {
        signingConfigs.create("release") {
            storeFile = file(signingFile)
            storePassword = signingStorePass
            keyAlias = signingAlias
            keyPassword = signingKeyPass
        }
    } else {
        null
    }

    buildTypes {
        // Địa chỉ máy chủ ghép đôi (spec 020). Debug: máy chủ dev trên máy chủ của AVD (10.0.2.2); ghi đè bằng
        // -PhoiconApiBaseUrl=... (http:// chỉ áp dụng cho debug). Release: HTTPS (cleartext bị chặn từ API 28); yêu cầu
        // dựng release kèm địa chỉ http:// thì build dừng ngay, không lặng lẽ đổi địa chỉ. Đường dừng an toàn KHÔNG dùng mạng.
        val apiBaseUrl = providers.gradleProperty("hoiconApiBaseUrl")
        val releaseRequested = gradle.startParameter.taskNames.any { it.contains("Release", ignoreCase = true) || it.contains("Demo") }
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
            val override = apiBaseUrl.orNull
            val url = if (override != null && !releaseRequested && !override.startsWith("https://")) {
                "https://api.hoicon.vn" // chỉ để cấu hình debug xong; không bao giờ đóng gói
            } else {
                checked(override ?: "https://api.hoicon.vn", listOf("https://"))
            }
            buildConfigField("String", "API_BASE_URL", "\"$url\"")
            // R8 rút gọn + che tên lớp, bỏ tài nguyên thừa; BuildConfig.DEBUG = false ⇒ nhật ký chẩn đoán (HC_TIMING/HC_SPIKE)
            // bị loại khỏi dex. Cổng release-gate.sh kiểm các điều này trên chính tệp phát hành.
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            releaseSigning?.let { signingConfig = it }
        }
        // Bản dựng cho video và gian trưng bày (spec 012 T016): giống release (R8, BuildConfig.DEBUG = false) nhưng cài song song
        // được (".demo"), nhãn "HỏiCon (demo)" (src/demo/res) và địa chỉ máy chủ demo qua -PhoiconApiBaseUrl (https).
        create("demo") {
            initWith(getByName("release"))
            applicationIdSuffix = ".demo"
            matchingFallbacks += "release"
            // Không có khóa phát hành ⇒ ký bằng khóa debug của SDK để cài thẳng lên máy ảo/máy gian trưng bày (không tải lên Play được).
            signingConfig = releaseSigning ?: signingConfigs.getByName("debug")
            val url = if (apiBaseUrl.orNull?.startsWith("https://") == true) checked(apiBaseUrl.get(), listOf("https://")) else "https://api.hoicon.vn"
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
    implementation(libs.androidx.room.runtime)
    implementation(libs.androidx.room.ktx)
    ksp(libs.androidx.room.compiler)
    implementation(libs.androidx.work.runtime.ktx)
    implementation(libs.tink.android)
    implementation(libs.play.services.code.scanner)
    implementation(libs.androidx.fragment)
    // Cài baseline profile (src/main/baseline-prof.txt) ngay khi cài app, không đợi dịch nền: khởi động nguội nhanh hơn (O3 MASTER-PLAN).
    implementation(libs.androidx.profileinstaller)
    debugImplementation(libs.androidx.compose.ui.tooling)

    testImplementation(libs.junit)
    testImplementation(libs.kotlin.test)
    testImplementation(libs.org.json)

    // Spec 026: the Room v1→v2 migration is checked against the exported schemas on an emulator (no Robolectric here).
    androidTestImplementation(libs.androidx.room.testing)
    androidTestImplementation(libs.androidx.test.ext.junit)
    androidTestImplementation(libs.androidx.test.runner)
}

// room-testing (androidTest) needs kotlinx-serialization 1.8.x, but AGP's own classpath pins 1.7.3, which fails at run time
// with AbstractMethodError in MigrationTestHelper. Only the instrumentation classpath is raised; the app is untouched.
configurations.matching { it.name.contains("AndroidTest", ignoreCase = true) }.configureEach {
    resolutionStrategy.eachDependency {
        if (requested.group == "org.jetbrains.kotlinx" && requested.name.startsWith("kotlinx-serialization-")) {
            useVersion("1.8.1")
            because("room-testing's MigrationTestHelper needs serialization >= 1.8")
        }
    }
}

// Room xuất lược đồ ra app/schemas để mọi thay đổi CSDL sau này có migration kiểm được (Spec 022).
ksp {
    arg("room.schemaLocation", layout.projectDirectory.dir("schemas").asFile.absolutePath)
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
    // Spec 011: the consent texts and manifest the app must match line for line (ConsentManifestPinTest).
    val consentXml = layout.projectDirectory.file("src/main/res/values/consent_texts.xml")
    val consentDocs = layout.projectDirectory.dir("../../../docs/legal/consent")
    inputs.file(consentXml).withPathSensitivity(PathSensitivity.NONE)
    inputs.dir(consentDocs).withPathSensitivity(PathSensitivity.RELATIVE)
    systemProperty("hoicon.consentXml", consentXml.asFile.absolutePath)
    systemProperty("hoicon.consentDocs", consentDocs.asFile.absolutePath)
}

// Release is HTTPS only: the check lives in the release buildType above (at configuration time, so it also works with the
// configuration cache). Debug builds accept http:// too; the debug-only network config lets them reach 10.0.2.2 only.
