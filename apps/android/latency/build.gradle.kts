// On-device latency harness (P1-S2): "financial app opens → SafePause first frame" on real phones (Firebase Test Lab)
// and emulators. Self-instrumenting (own process, like Macrobenchmark) so it can force-stop the app under test.
plugins {
    alias(libs.plugins.android.test)
}

android {
    namespace = "vn.hoicon.latency"
    compileSdk = 36
    targetProjectPath = ":app"

    defaultConfig {
        minSdk = 29
        targetSdk = 36
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    experimentalProperties["android.experimental.self-instrumenting"] = true
}

dependencies {
    implementation(libs.androidx.test.runner)
    implementation(libs.junit)
}
