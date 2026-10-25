package vn.hoicon.sentinel.ui

import java.io.File
import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/** Spec 038 T008 (reviewer's Medium items on E12): the words of the title, the 24-hour wait, the cancelled notice and the per-card TalkBack labels. */
class SettingsCopyTest {
    private val xml = File(checkNotNull(System.getProperty("hoicon.appStrings"))).readText(Charsets.UTF_8)

    private fun string(name: String) = Regex("""<string name="$name">(.*?)</string>""", RegexOption.DOT_MATCHES_ALL).find(xml)?.groupValues?.get(1)

    @Test
    fun theTitleSaysWhereThePersonIs() {
        assertEquals("Cài đặt và quyền riêng tư", string("settings_title"))
    }

    @Test
    fun changingYourMindIsPromisedOnlyForTheWaitingTime() {
        val wait = checkNotNull(string("delete_wait"))
        assertTrue("Trong 24 giờ chờ, nếu bác đổi ý" in wait)
        assertTrue("ở đầu màn" in wait) // where the cancel button really is
        assertFalse("lúc nào cũng được" in wait)
    }

    @Test
    fun cancellingSaysThePersonIsStillProtected() {
        assertEquals("Đã hủy yêu cầu xóa. HỏiCon vẫn bảo vệ bác.", string("delete_cancelled"))
    }

    @Test
    fun eachSwitchButtonNamesTheThingItSwitches() {
        // the argument is the noun ("việc báo cho con cháu"), so TalkBack hears "Tắt việc báo cho con cháu", not just "Tắt"
        assertEquals("Tắt %1\$s", string("switch_turn_off_for"))
        assertEquals("Bật %1\$s", string("switch_turn_on_for"))
        assertNotNull(string("switch_noun_guardian_alerts"))
    }
}
