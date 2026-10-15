// Voice lab (P1-S5 / spec 004-voice-vi): measurement tool for Vietnamese on-device TTS/STT on emulators and test
// devices. NOT a product module: debug only, never shipped, :app does not depend on it. Instrumentation tests in
// src/androidTest are the probes (run with `am instrument` by scripts/voice-lab.sh). minSdk 33 because feeding a file
// to SpeechRecognizer (EXTRA_AUDIO_SOURCE) and checkRecognitionSupport exist only from API 33.
plugins {
    alias(libs.plugins.android.application)
}

android {
    namespace = "vn.hoicon.voicelab"
    compileSdk = 36

    defaultConfig {
        applicationId = "vn.hoicon.voicelab"
        minSdk = 33
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    sourceSets {
        // The 20 reference sentences live in data/voice/ (single source of truth, also read by scripts/voice-wer.py).
        getByName("main").assets.directories.add(rootProject.projectDir.resolve("../../data/voice").path)
    }
}

// No release variant at all: this module must never reach an AAB/APK for people (constitution IX).
androidComponents {
    beforeVariants { variantBuilder ->
        if (variantBuilder.buildType == "release") variantBuilder.enable = false
    }
}

dependencies {
    androidTestImplementation(libs.androidx.test.runner)
    androidTestImplementation(libs.junit)
    testImplementation(libs.junit)
}
