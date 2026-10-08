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
}
