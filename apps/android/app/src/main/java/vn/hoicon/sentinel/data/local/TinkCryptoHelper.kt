package vn.hoicon.sentinel.data.local

import android.content.Context
import androidx.core.content.edit
import com.google.crypto.tink.Aead
import com.google.crypto.tink.RegistryConfiguration
import com.google.crypto.tink.aead.AeadConfig
import com.google.crypto.tink.KeyTemplates
import com.google.crypto.tink.integration.android.AndroidKeysetManager
import java.security.KeyStore
import java.util.Base64

/**
 * AEAD (AES-256-GCM, Tink) for the outbox payloads. The keyset sits in app-private prefs, wrapped by a master key
 * held by the Android system key store, so `sentinel.db` read off the disk (backup, root, forensic copy) shows only
 * ciphertext.
 *
 * Never throws: a key store that lost its key (new screen lock, restore, OS update) makes [encrypt]/[decrypt] return
 * null and the caller drops the event instead of crashing the app that also hosts the safe pause.
 * Takes an [Aead] so the logic is testable on the JVM; production uses [create].
 */
class TinkCryptoHelper(private val aead: Aead?) {
    /** `base64(ciphertext)` bound to [associatedData] (the event id), or null when no key is available. */
    fun encrypt(plain: String, associatedData: String): String? = try {
        aead?.encrypt(plain.toByteArray(Charsets.UTF_8), associatedData.toByteArray(Charsets.UTF_8))
            ?.let { ENCODER.encodeToString(it) }
    } catch (_: Exception) {
        null
    }

    /** The plain text, or null when the key is gone, the text was altered, or [associatedData] does not match. */
    fun decrypt(encoded: String, associatedData: String): String? = try {
        aead?.decrypt(DECODER.decode(encoded), associatedData.toByteArray(Charsets.UTF_8))
            ?.toString(Charsets.UTF_8)
    } catch (_: Exception) {
        null
    }

    val isAvailable: Boolean get() = aead != null

    companion object {
        private val ENCODER = Base64.getUrlEncoder().withoutPadding()
        private val DECODER = Base64.getUrlDecoder()
        private const val KEYSET_NAME = "hoicon_outbox_keyset"
        private const val KEYSET_PREFS = "hoicon_outbox_keyset_prefs"
        private const val MASTER_KEY_URI = "android-keystore://hoicon_outbox_master"
        private const val MASTER_KEY_ALIAS = "hoicon_outbox_master"

        /** Opens (or creates) the keyset; if the system key store or the file is broken, wipes both once and retries. */
        fun create(context: Context): TinkCryptoHelper {
            val app = context.applicationContext
            return TinkCryptoHelper(open(app) ?: run { reset(app); open(app) })
        }

        private fun open(context: Context): Aead? = try {
            AeadConfig.register()
            val keyset = AndroidKeysetManager.Builder()
                .withSharedPref(context, KEYSET_NAME, KEYSET_PREFS)
                .withKeyTemplate(KeyTemplates.get("AES256_GCM"))
                .withMasterKeyUri(MASTER_KEY_URI)
                .build()
            // Tink silently carries on WITHOUT a master key when the system key store cannot make one (it logs and
            // keeps the keyset in the clear). Refuse that: no wrapping key means no encrypted outbox.
            if (!hasMasterKey()) null else keyset.keysetHandle.getPrimitive(RegistryConfiguration.get(), Aead::class.java)
        } catch (_: Exception) {
            null
        }

        private fun hasMasterKey(): Boolean = try {
            KeyStore.getInstance("AndroidKeyStore").apply { load(null) }.containsAlias(MASTER_KEY_ALIAS)
        } catch (_: Exception) {
            false
        }

        /** Old outbox rows become unreadable after this; they are dropped as FAILED, new events work again. */
        private fun reset(context: Context) {
            runCatching { context.getSharedPreferences(KEYSET_PREFS, Context.MODE_PRIVATE).edit { clear() } }
            runCatching {
                KeyStore.getInstance("AndroidKeyStore").apply { load(null) }.deleteEntry(MASTER_KEY_ALIAS)
            }
        }
    }
}
