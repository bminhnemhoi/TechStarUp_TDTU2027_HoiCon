package vn.hoicon.sentinel.data.local

import android.content.Context
import android.content.SharedPreferences
import androidx.core.content.edit
import java.security.KeyStore
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/** What `POST /v1/pair` returns (docs/schemas/pair_response.v1.json), minus the token type and expiry. */
data class DeviceSession(
    val deviceId: String,
    val familyId: String,
    val memberId: String,
    val familyName: String,
    val accessToken: String,
    val refreshToken: String,
) {
    // Tokens must never reach a log line (toString is what a stray `$session` would print).
    override fun toString() = "DeviceSession(deviceId=$deviceId)"
}

/**
 * Pairing state on the phone. The file is AES-256 encrypted with a key in the Android Keystore
 * (EncryptedSharedPreferences). Replaced by DataStore + Tink in P2-05.
 *
 * Never throws: a Keystore that was invalidated (new screen lock, restore, OS update) or a corrupted file reads as
 * "not paired" instead of crashing the app that also hosts the safe pause. [prefs] is null when even a fresh
 * file cannot be created; the device then simply stays unpaired.
 *
 * Takes plain [SharedPreferences] so the logic is testable on the JVM; production uses [create].
 */
class TokenStorage(private val prefs: SharedPreferences?) {
    /** @return false when the session could not be written (the caller must not treat the device as paired). */
    fun save(session: DeviceSession): Boolean = write {
        putString(DEVICE_ID, session.deviceId)
        putString(FAMILY_ID, session.familyId)
        putString(MEMBER_ID, session.memberId)
        putString(FAMILY_NAME, session.familyName)
        putString(ACCESS_TOKEN, session.accessToken)
        putString(REFRESH_TOKEN, session.refreshToken)
        putBoolean(NEEDS_REPAIR, false)
    }

    /** The saved session, or null when the device was never paired (or any field is missing or unreadable). */
    fun load(): DeviceSession? = read {
        fun field(key: String) = getString(key, null)?.takeIf { it.isNotBlank() }
        DeviceSession(
            deviceId = field(DEVICE_ID) ?: return@read null,
            familyId = field(FAMILY_ID) ?: return@read null,
            memberId = field(MEMBER_ID) ?: return@read null,
            familyName = field(FAMILY_NAME) ?: return@read null,
            accessToken = field(ACCESS_TOKEN) ?: return@read null,
            refreshToken = field(REFRESH_TOKEN) ?: return@read null,
        )
    }

    fun hasValidToken(): Boolean = load() != null

    /**
     * The server refused the device token (expired after 30 days, or the family revoked the device) and there is no
     * refresh endpoint yet: events and heartbeats cannot reach the family. E6 says so instead of "Đang bảo vệ".
     * Cleared by [save] (a new pairing) and [clear].
     */
    var needsRepair: Boolean
        get() = read { getBoolean(NEEDS_REPAIR, false) } ?: false
        set(value) {
            write { putBoolean(NEEDS_REPAIR, value) }
        }

    /** Version of the prominent-disclosure text (E3) the user accepted, or null. */
    var acceptedDisclosureVersion: String?
        get() = read { getString(DISCLOSURE_VERSION, null) }
        set(value) {
            write { putString(DISCLOSURE_VERSION, value) }
        }

    /**
     * What the server's ledger already holds as granted, one `purpose|version|textHash` key per purpose, so a new
     * consent version or new wording is recorded again (see ConsentLedger.key).
     */
    var recordedConsents: Set<String>
        get() = read { getStringSet(RECORDED_CONSENTS, emptySet()).orEmpty().toSet() } ?: emptySet()
        set(value) {
            write { putStringSet(RECORDED_CONSENTS, value.toSet()) }
        }

    fun clear() {
        write { clear() }
    }

    private fun <T> read(block: SharedPreferences.() -> T?): T? = try {
        prefs?.block()
    } catch (_: Exception) {
        null
    }

    private fun write(block: SharedPreferences.Editor.() -> Unit): Boolean = try {
        prefs?.edit(action = block) != null
    } catch (_: Exception) {
        false
    }

    companion object {
        private const val FILE = "hoicon_device"
        private const val DEVICE_ID = "device_id"
        private const val FAMILY_ID = "family_id"
        private const val MEMBER_ID = "member_id"
        private const val FAMILY_NAME = "family_name"
        private const val ACCESS_TOKEN = "access_token"
        private const val REFRESH_TOKEN = "refresh_token"
        private const val NEEDS_REPAIR = "needs_repair"
        private const val DISCLOSURE_VERSION = "disclosure_version"
        private const val RECORDED_CONSENTS = "recorded_consents"
        private const val MASTER_KEY_ALIAS = "_androidx_security_master_key_"

        /** Opens the encrypted file; if the Keystore or the file is broken, wipes both once and starts empty. */
        fun create(context: Context): TokenStorage {
            val app = context.applicationContext
            return TokenStorage(open(app) ?: run { reset(app); open(app) })
        }

        private fun open(context: Context): SharedPreferences? = try {
            val key = MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build()
            EncryptedSharedPreferences.create(
                context,
                FILE,
                key,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
            ).also { it.all } // reading every entry forces decryption: a bad file fails here, not later
        } catch (_: Exception) {
            null
        }

        private fun reset(context: Context) {
            runCatching { context.deleteSharedPreferences(FILE) }
            runCatching { KeyStore.getInstance("AndroidKeyStore").apply { load(null) }.deleteEntry(MASTER_KEY_ALIAS) }
        }
    }
}
