package vn.hoicon.sentinel

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import vn.hoicon.sentinel.ui.HelloScreen
import vn.hoicon.sentinel.ui.theme.HoiConTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            HoiConTheme {
                HelloScreen()
            }
        }
    }
}
