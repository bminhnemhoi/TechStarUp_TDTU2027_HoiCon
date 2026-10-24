package vn.hoicon.sentinel.ui

import android.provider.Settings
import java.io.File
import org.junit.Test
import vn.hoicon.sentinel.PermissionOpener
import vn.hoicon.sentinel.sensing.SensorPermission
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/** Spec 011 T023: an item that is on has a way to switch it off (withdrawing consent is as easy as giving it), and the status words say it without a mark that reads as an error. */
class PermissionSwitchOffTest {
    private val xml = File(checkNotNull(System.getProperty("hoicon.appStrings"))).readText(Charsets.UTF_8)

    private fun string(name: String) = Regex("""<string name="$name">(.*?)</string>""", RegexOption.DOT_MATCHES_ALL).find(xml)?.groupValues?.get(1)

    @Test
    fun everyPermissionHasAPageToSwitchItOff() {
        for (p in SensorPermission.entries) assertNotNull(PermissionOpener.disableAction(p), p.name)
        assertEquals(Settings.ACTION_MANAGE_DEFAULT_APPS_SETTINGS, PermissionOpener.disableAction(SensorPermission.CALL_SCREENING_ROLE))
        assertEquals(Settings.ACTION_USAGE_ACCESS_SETTINGS, PermissionOpener.disableAction(SensorPermission.USAGE_ACCESS))
    }

    @Test
    fun theStatusWordsAndTheSwitchOffLabels() {
        assertEquals("○ Chưa bật", string("perm_status_off"))
        assertEquals("✓ Đã bật", string("perm_status_on"))
        assertEquals("Mở cài đặt để tắt", string("perm_switch_off"))
        assertTrue("%1\$s" in checkNotNull(string("perm_switch_off_for")))
        assertEquals("Chưa bật", string("perm_state_off"))
        assertEquals("Đã bật", string("perm_state_on"))
    }
}
