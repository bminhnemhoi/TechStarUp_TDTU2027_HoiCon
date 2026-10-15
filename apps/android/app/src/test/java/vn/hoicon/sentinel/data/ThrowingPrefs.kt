package vn.hoicon.sentinel.data

import android.content.SharedPreferences
import java.security.GeneralSecurityException
import java.lang.reflect.Proxy

/** SharedPreferences whose every call fails, like EncryptedSharedPreferences after the Keystore key was invalidated. */
fun throwingPrefs(): SharedPreferences = Proxy.newProxyInstance(
    SharedPreferences::class.java.classLoader,
    arrayOf(SharedPreferences::class.java),
) { _, _, _ -> throw GeneralSecurityException("keystore key invalidated") } as SharedPreferences
