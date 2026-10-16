package vn.hoicon.sentinel

import android.app.Application
import android.content.res.Resources
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import vn.hoicon.sentinel.data.consent.ConsentLedger
import vn.hoicon.sentinel.data.consent.ConsentSync
import vn.hoicon.sentinel.data.consent.consentTexts
import vn.hoicon.sentinel.data.local.TokenStorage
import vn.hoicon.sentinel.data.lookup.LookupChecker
import vn.hoicon.sentinel.data.lookup.LookupInput
import vn.hoicon.sentinel.data.lookup.LookupOutcome
import vn.hoicon.sentinel.data.lookup.NoticeReason
import vn.hoicon.sentinel.data.remote.LookupVia
import vn.hoicon.sentinel.domain.qr.QrContent
import vn.hoicon.sentinel.data.remote.LookupApiClient
import vn.hoicon.sentinel.data.remote.PairingApiClient
import vn.hoicon.sentinel.data.threat.ThreatIndexes
import vn.hoicon.sentinel.sensing.HcTiming
import vn.hoicon.sentinel.sensing.SensorPermissions
import vn.hoicon.sentinel.ui.LookupError

enum class LookupStep { CONSENT, INPUT, RESULT }

/**
 * E10 (Spec 026): consent on first use → one box → the answer. The raw text lives only in [text]; "Kiểm tra" turns it
 * into a hash (phone) or a cut link and clears the box, so the number is gone from memory state before the network is
 * touched. Survives rotation and font-scale changes.
 */
class LookupModel(private val app: Application) : AndroidViewModel(app) {
    private val storage = TokenStorage.create(app)
    private val consents = ConsentSync(storage, PairingApiClient(BuildConfig.API_BASE_URL))
    private val checker = LookupChecker(
        gateway = LookupApiClient(BuildConfig.API_BASE_URL),
        index = ThreatIndexes.shared,
        accessToken = { storage.load()?.accessToken },
        consent = { syncConsents() == ConsentSync.Outcome.UP_TO_DATE },
        onUnauthorized = { storage.needsRepair = true },
    )

    var step by mutableStateOf(if (storage.acceptedLookupsVersion == ConsentLedger.VERSION) LookupStep.INPUT else LookupStep.CONSENT)
        private set
    var text by mutableStateOf("")
        private set
    var error by mutableStateOf<LookupError?>(null)
        private set
    var checking by mutableStateOf(false)
        private set
    var outcome by mutableStateOf<LookupOutcome?>(null)
        private set

    /** Set once by the activity from its intent; a malformed id is dropped by the client, never sent. */
    var incidentId: String? = null

    /** What was already read aloud (rotation recreates the activity). */
    var lastSpoken: Any? = null

    fun onTextChange(value: String) {
        if (checking) return
        text = value.take(MAX_INPUT)
        error = null
    }

    /** The just-in-time consent was accepted: remember it for this version and tell the server in the background. */
    fun acceptConsent(res: Resources) {
        storage.acceptedLookupsVersion = ConsentLedger.VERSION
        step = LookupStep.INPUT
        val texts = consentTexts(res)
        viewModelScope.launch(Dispatchers.IO) { consents.run(SensorPermissions.granted(app), texts) }
    }

    fun check() {
        if (checking) return
        val input = LookupInput.parse(text)
        error = when (input) {
            LookupInput.Empty -> LookupError.EMPTY
            LookupInput.BadPhone -> LookupError.PHONE
            LookupInput.BadLink -> LookupError.LINK
            else -> null
        }
        if (error != null) return
        text = ""
        run(input, LookupVia.TYPED)
    }

    /** "Dán đường link": the pasted text goes into the box (the person still presses "Kiểm tra"). */
    fun paste(clip: CharSequence?) {
        val pasted = clip?.toString()?.trim().orEmpty()
        if (pasted.isEmpty()) error = LookupError.PASTE else onTextChange(pasted)
    }

    fun scanFailed() {
        error = LookupError.SCAN
    }

    /** A scanned code is classified HERE: a link or `tel:` is checked (`via = qr`), a VietQR is only read, never sent. */
    fun onScanned(raw: String?) {
        if (checking) return
        when (val content = QrContent.classify(raw)) {
            is QrContent.Transfer -> show(LookupOutcome.Transfer(content.qr.payeeName, content.qr.amountVnd))
            is QrContent.Link -> LookupInput.parse(content.url).let { if (it is LookupInput.Link) run(it, LookupVia.QR) else unreadable() }
            is QrContent.Phone -> LookupInput.parse(content.number).let { if (it is LookupInput.Phone) run(it, LookupVia.QR) else unreadable() }
            QrContent.Unreadable -> unreadable()
        }
    }

    private fun unreadable() = show(LookupOutcome.Notice(NoticeReason.QR_UNREADABLE))

    private fun show(result: LookupOutcome) {
        outcome = result
        step = LookupStep.RESULT
    }

    private fun run(input: LookupInput, via: LookupVia) {
        checking = true
        HcTiming.mark("lookup_tapped")
        viewModelScope.launch {
            outcome = withContext(Dispatchers.IO) { checker.check(input, incidentId, via) }
            checking = false
            step = LookupStep.RESULT
            HcTiming.mark("lookup_result")
        }
    }

    fun backToInput() {
        outcome = null
        step = LookupStep.INPUT
    }

    private fun syncConsents(): ConsentSync.Outcome = consents.run(SensorPermissions.granted(app), consentTexts(app.resources))

    private companion object {
        const val MAX_INPUT = 2048
    }
}
