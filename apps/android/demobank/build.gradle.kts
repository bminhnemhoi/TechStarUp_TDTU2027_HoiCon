// "Ngân hàng Mẫu": fake banking app for emulator scenarios and booth demos (real VN banking apps refuse emulators).
plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
}

android {
    namespace = "vn.hoicon.demobank"
    compileSdk = 36

    defaultConfig {
        // -PdemobankApplicationId=com.anydesk.anydeskandroid dựng bản "app điều khiển từ xa giả" để thử luật R5 / E7 biến thể
        // điều khiển từ xa trên máy ảo (không bao giờ phát hành; chỉ cài lên máy ảo).
        applicationId = providers.gradleProperty("demobankApplicationId").getOrElse("vn.hoicon.demobank")
        minSdk = 29
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildFeatures {
        compose = true
    }
}

dependencies {
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.compose.material3)
}
