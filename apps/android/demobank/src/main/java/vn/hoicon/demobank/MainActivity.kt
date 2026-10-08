package vn.hoicon.demobank

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

// Own palette, deliberately unlike HỏiCon so demos show two separate apps. Contrast: white/teal ~8.9:1, banner ~10:1.
private val BankTeal = Color(0xFF0B4F6C)
private val CardTint = Color(0xFFE8F1F5)
private val Ink = Color(0xFF1A1A1A)
private val BannerAmber = Color(0xFFFFE08A)
private val BannerInk = Color(0xFF3D2E00)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            MaterialTheme {
                DemoBankHome()
            }
        }
    }
}

/** Fake bank home screen. Opening it is all the P1-S1 scenarios need; it never moves money. */
@Composable
private fun DemoBankHome() {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.White)
            .safeDrawingPadding()
            .verticalScroll(rememberScrollState()),
    ) {
        Text(
            text = stringResource(R.string.demo_banner),
            color = BannerInk,
            fontSize = 20.sp,
            fontWeight = FontWeight.Bold,
            modifier = Modifier
                .fillMaxWidth()
                .background(BannerAmber)
                .padding(16.dp),
        )
        Column(modifier = Modifier.padding(24.dp), verticalArrangement = Arrangement.spacedBy(20.dp)) {
            Text(
                text = stringResource(R.string.app_name),
                color = BankTeal,
                fontSize = 32.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.semantics { heading() },
            )
            Text(text = stringResource(R.string.greeting), color = Ink, fontSize = 22.sp)
            Surface(shape = RoundedCornerShape(16.dp), color = CardTint) {
                Column(modifier = Modifier.fillMaxWidth().padding(20.dp)) {
                    Text(text = stringResource(R.string.balance_label), color = Ink, fontSize = 20.sp)
                    Text(
                        text = stringResource(R.string.balance_value),
                        color = Ink,
                        fontSize = 36.sp,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
            Button(
                onClick = { /* Intentionally does nothing: demo app, no real transfers. */ },
                colors = ButtonDefaults.buttonColors(containerColor = BankTeal, contentColor = Color.White),
                modifier = Modifier.fillMaxWidth().heightIn(min = 64.dp),
            ) {
                Text(text = stringResource(R.string.transfer), fontSize = 24.sp, fontWeight = FontWeight.Bold)
            }
        }
    }
}
