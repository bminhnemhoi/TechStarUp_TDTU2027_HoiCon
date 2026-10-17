package vn.hoicon.sentinel.ui

import android.content.Context
import com.google.android.gms.common.ConnectionResult
import com.google.android.gms.common.GoogleApiAvailability
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.codescanner.GmsBarcodeScannerOptions
import com.google.mlkit.vision.codescanner.GmsBarcodeScanning

/**
 * "Quét mã QR" through Google Code Scanner (Spec 026 FR-012): the camera screen belongs to Google Play services, so this
 * app asks for no CAMERA permission and never touches the camera or the picture. Without Play services the button is
 * simply not shown.
 */
object QrScan {
    fun available(context: Context): Boolean =
        GoogleApiAvailability.getInstance().isGooglePlayServicesAvailable(context) == ConnectionResult.SUCCESS

    /** [onResult] gets the text of the code, or null when the scanner failed; a cancelled scan reports nothing. */
    fun scan(context: Context, onResult: (String?) -> Unit) {
        val options = GmsBarcodeScannerOptions.Builder().setBarcodeFormats(Barcode.FORMAT_QR_CODE).build()
        GmsBarcodeScanning.getClient(context, options).startScan()
            .addOnSuccessListener { onResult(it.rawValue) }
            .addOnFailureListener { onResult(null) }
    }
}
