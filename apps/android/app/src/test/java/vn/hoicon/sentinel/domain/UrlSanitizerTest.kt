package vn.hoicon.sentinel.domain

import org.junit.Test
import vn.hoicon.sentinel.domain.lookup.UrlSanitizer
import kotlin.test.assertEquals
import kotlin.test.assertNull

/** Spec 026 FR-012: only scheme://host[:port]/path may leave the phone. */
class UrlSanitizerTest {
    private fun s(raw: String) = UrlSanitizer.sanitize(raw)

    @Test
    fun dropsUserInfoQueryAndFragment() {
        assertEquals("https://example.org/a/b", s("https://me:pw@example.org/a/b?x=1&y=2#top"))
        assertEquals("http://example.org/", s("http://example.org/?q=1"))
        assertEquals("https://example.org", s("https://example.org#frag"))
        assertEquals("https://example.org", s("https://example.org?x=1"))
    }

    @Test
    fun lowercasesTheHostAndKeepsThePath() {
        assertEquals("https://example.org/Pay/File.APK", s("HTTPS://Example.ORG/Pay/File.APK"))
    }

    @Test
    fun aLinkWithoutASchemeIsHttps() {
        assertEquals("https://bit.ly/abc", s("bit.ly/abc"))
        assertEquals("https://example.org:8080/x", s("example.org:8080/x?a=b"))
    }

    @Test
    fun aLookAlikeDomainIsPunycoded() {
        assertEquals("https://xn--vietcombnk-z4a.com/", s("https://vietcombánk.com/"))
    }

    @Test
    fun keepsAnIpHost() {
        assertEquals("http://192.0.2.7/x.apk", s("http://192.0.2.7/x.apk"))
    }

    @Test
    fun rejectsEverythingThatIsNotAPlainWebLink() {
        for (bad in listOf("", "   ", "javascript:alert(1)", "file:///etc/passwd", "tel:+84900000002", "mailto:a@b.vn", "ftp://example.org",
            "https://", "https:///x", "https://exa mple.org", "https://example.org:99999/", "https://-bad-.org", "https://exa_mple.org", "https://a..b")) {
            assertNull(s(bad), "should reject: $bad")
        }
    }

    @Test
    fun rejectsOverlongLinks() {
        assertNull(s("https://example.org/" + "a".repeat(2100)))
    }

    @Test
    fun aPhoneNumberHiddenInALinkNeverTravels() {
        assertEquals("https://zalo.me/*", s("zalo.me/0912345678"))
        assertEquals("https://zalo.me/u/*", s("https://zalo.me/u/0912.345.678?x=1"))
        assertNull(s("0912345678.example.vn"))
        assertNull(s("sdt0912345678a.vn"))
        assertEquals("https://mau.vn/don/12345", s("mau.vn/don/12345"))
    }
}
