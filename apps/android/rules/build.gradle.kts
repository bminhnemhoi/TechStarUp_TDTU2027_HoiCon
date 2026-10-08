import org.jetbrains.kotlin.gradle.dsl.JvmTarget

// Pure Kotlin/JVM: deterministic on-device rules (ADR-001), no Android dependency, tested without an emulator.
plugins {
    alias(libs.plugins.kotlin.jvm)
}

// Bytecode 17 so :app can dex it; no toolchain so any JDK >= 17 running Gradle works (dev machine: JDK 21).
java {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
}

kotlin {
    compilerOptions {
        jvmTarget = JvmTarget.JVM_17
    }
}

dependencies {
    testImplementation(kotlin("test"))
}

tasks.test {
    useJUnitPlatform()
    // Contract test reads the shared JSON Schema; declare it as an input so schema edits re-run the tests.
    val riskEventSchema = layout.projectDirectory.file("../../../docs/schemas/risk_event.v1.json")
    inputs.file(riskEventSchema).withPathSensitivity(PathSensitivity.NONE)
    systemProperty("hoicon.riskEventSchema", riskEventSchema.asFile.absolutePath)
    // Shared E.164/h1 vectors with the backend (ADR-006).
    val h1Vectors = layout.projectDirectory.file("../../../docs/schemas/fixtures/h1_vectors.json")
    inputs.file(h1Vectors).withPathSensitivity(PathSensitivity.NONE)
    systemProperty("hoicon.h1Vectors", h1Vectors.asFile.absolutePath)
    // AI-disclosure copy test (CLAUDE.md rule 6) reads the app's strings and notification builder as plain text.
    val appStrings = layout.projectDirectory.file("../app/src/main/res/values/strings.xml")
    val appNotifications =
        layout.projectDirectory.file("../app/src/main/java/vn/hoicon/sentinel/sensing/Notifications.kt")
    inputs.files(appStrings, appNotifications).withPathSensitivity(PathSensitivity.NONE)
    systemProperty("hoicon.appStrings", appStrings.asFile.absolutePath)
    systemProperty("hoicon.appNotifications", appNotifications.asFile.absolutePath)
}
