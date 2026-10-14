package vn.hoicon.demobank

import android.content.Intent
import android.os.Bundle
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

// Own palette, deliberately unlike HỏiCon so demos show two separate apps. Contrast: white/teal ~8.9:1, banner ~10:1.
private val BankTeal = Color(0xFF0B4F6C)
private val CardTint = Color(0xFFE8F1F5)
private val Ink = Color(0xFF1A1A1A)
private val ErrorInk = Color(0xFF8C1D18)
private val BannerAmber = Color(0xFFFFE08A)
private val BannerInk = Color(0xFF3D2E00)

private enum class Screen { LOGIN, HOME, TRANSFER, CONFIRM, OTP, DONE }

/**
 * "Ngân hàng Mẫu": stand-in for a VN banking app (real ones refuse emulators, ADB and test farms — Circular
 * 77/2025/TT-NHNN art. 5). Walks the transfer flow a scam pushes the elder through; never moves money, no network.
 *
 * Extras for scenarios (P1-S2, scripts/emu-scenario.py, :latency):
 *  - `screen=transfer`: open logged in on the transfer form (the call says "mở app, vào chuyển tiền").
 *  - `secure=true`: FLAG_SECURE like real banking apps (screenshots/recordings go black — keep off for videos).
 */
class MainActivity : ComponentActivity() {
    private var startScreen by mutableStateOf(Screen.LOGIN)
    private var deepLinkSeq by mutableStateOf(0)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        applyExtras(intent)
        setContent {
            MaterialTheme {
                DemoBank(startScreen, deepLinkSeq)
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        applyExtras(intent)
    }

    private fun applyExtras(intent: Intent?) {
        if (intent?.getBooleanExtra(EXTRA_SECURE, false) == true) {
            window.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
        } else {
            window.clearFlags(WindowManager.LayoutParams.FLAG_SECURE)
        }
        if (intent?.getStringExtra(EXTRA_SCREEN) == "transfer") {
            startScreen = Screen.TRANSFER
            deepLinkSeq++ // re-applies the deep link when the activity is already open
        }
    }

    private companion object {
        const val EXTRA_SCREEN = "screen"
        const val EXTRA_SECURE = "secure"
    }
}

@Composable
private fun DemoBank(startScreen: Screen, deepLinkSeq: Int) {
    // Keyed on the deep link so `am start --es screen transfer` jumps there even mid-flow; survives rotation/process
    // death otherwise (the SafePause round trip must bring the elder back to the same form).
    var screen by rememberSaveable(deepLinkSeq) { mutableStateOf(startScreen) }
    val prefillAccount = stringResource(R.string.prefill_account)
    val prefillAmount = stringResource(R.string.prefill_amount)
    val prefillMessage = stringResource(R.string.prefill_message)
    var account by rememberSaveable(deepLinkSeq) { mutableStateOf(prefillAccount) }
    var amount by rememberSaveable(deepLinkSeq) { mutableStateOf(prefillAmount) }
    var message by rememberSaveable(deepLinkSeq) { mutableStateOf(prefillMessage) }
    var showError by rememberSaveable { mutableStateOf(false) }

    val previous = when (screen) {
        Screen.TRANSFER -> Screen.HOME
        Screen.CONFIRM -> Screen.TRANSFER
        Screen.OTP -> Screen.CONFIRM
        else -> null
    }
    BackHandler(enabled = previous != null) { previous?.let { screen = it } }

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
            modifier = Modifier.fillMaxWidth().background(BannerAmber).padding(16.dp),
        )
        Column(modifier = Modifier.padding(24.dp), verticalArrangement = Arrangement.spacedBy(20.dp)) {
            when (screen) {
                Screen.LOGIN -> {
                    Title(stringResource(R.string.app_name))
                    Body(stringResource(R.string.greeting))
                    Primary(stringResource(R.string.login)) { screen = Screen.HOME }
                }

                Screen.HOME -> {
                    Title(stringResource(R.string.app_name))
                    Body(stringResource(R.string.greeting))
                    Card {
                        Body(stringResource(R.string.account_label))
                        Body(stringResource(R.string.balance_label))
                        Text(stringResource(R.string.balance_value), color = Ink, fontSize = 36.sp, fontWeight = FontWeight.Bold)
                    }
                    Primary(stringResource(R.string.transfer)) { screen = Screen.TRANSFER }
                    Secondary(stringResource(R.string.logout)) { screen = Screen.LOGIN }
                }

                Screen.TRANSFER -> {
                    Title(stringResource(R.string.transfer_title))
                    Field(stringResource(R.string.field_account), account, KeyboardType.Number) { account = it }
                    Body(stringResource(R.string.recipient_label, stringResource(R.string.prefill_recipient)))
                    Field(stringResource(R.string.field_amount), amount, KeyboardType.Number) { amount = it }
                    Field(stringResource(R.string.field_message), message, KeyboardType.Text) { message = it }
                    if (showError) {
                        Text(
                            stringResource(R.string.error_required),
                            color = ErrorInk,
                            fontSize = 20.sp,
                            modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite },
                        )
                    }
                    Primary(stringResource(R.string.next)) {
                        showError = account.isBlank() || amount.isBlank()
                        if (!showError) screen = Screen.CONFIRM
                    }
                    Secondary(stringResource(R.string.back)) { screen = Screen.HOME }
                }

                Screen.CONFIRM -> {
                    Title(stringResource(R.string.confirm_title))
                    Card {
                        Body("${stringResource(R.string.confirm_account)}: $account")
                        Body(stringResource(R.string.recipient_label, stringResource(R.string.prefill_recipient)))
                        Body("${stringResource(R.string.confirm_amount)}: $amount ₫")
                        Body("${stringResource(R.string.confirm_message)}: $message")
                    }
                    Primary(stringResource(R.string.confirm)) { screen = Screen.OTP }
                    Secondary(stringResource(R.string.back)) { screen = Screen.TRANSFER }
                }

                Screen.OTP -> {
                    Title(stringResource(R.string.otp_title))
                    Body(stringResource(R.string.otp_body))
                    Primary(stringResource(R.string.otp_verify)) { screen = Screen.DONE }
                    Secondary(stringResource(R.string.back)) { screen = Screen.CONFIRM }
                }

                Screen.DONE -> {
                    Title(stringResource(R.string.done_title))
                    Body(stringResource(R.string.done_body))
                    Primary(stringResource(R.string.home)) { screen = Screen.HOME }
                }
            }
        }
    }
}

@Composable
private fun Title(text: String) = Text(
    text = text,
    color = BankTeal,
    fontSize = 30.sp,
    fontWeight = FontWeight.Bold,
    modifier = Modifier.semantics { heading() },
)

@Composable
private fun Body(text: String) = Text(text = text, color = Ink, fontSize = 22.sp)

@Composable
private fun Card(content: @Composable ColumnScope.() -> Unit) = Surface(shape = RoundedCornerShape(16.dp), color = CardTint) {
    Column(Modifier.fillMaxWidth().padding(20.dp), verticalArrangement = Arrangement.spacedBy(8.dp), content = content)
}

@Composable
private fun Field(label: String, value: String, keyboard: KeyboardType, onChange: (String) -> Unit) = OutlinedTextField(
    value = value,
    onValueChange = onChange,
    label = { Text(label, fontSize = 20.sp) },
    textStyle = TextStyle(fontSize = 22.sp, color = Ink),
    singleLine = true,
    keyboardOptions = KeyboardOptions(keyboardType = keyboard),
    modifier = Modifier.fillMaxWidth(),
)

@Composable
private fun Primary(text: String, onClick: () -> Unit) = Button(
    onClick = onClick,
    colors = ButtonDefaults.buttonColors(containerColor = BankTeal, contentColor = Color.White),
    modifier = Modifier.fillMaxWidth().heightIn(min = 64.dp),
) {
    Text(text = text, fontSize = 24.sp, fontWeight = FontWeight.Bold)
}

@Composable
private fun Secondary(text: String, onClick: () -> Unit) = OutlinedButton(
    onClick = onClick,
    modifier = Modifier.fillMaxWidth().heightIn(min = 64.dp),
) {
    Text(text = text, color = BankTeal, fontSize = 22.sp)
}
