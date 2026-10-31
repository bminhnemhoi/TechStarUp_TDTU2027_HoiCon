package vn.hoicon.sentinel.domain

import org.junit.Test
import vn.hoicon.sentinel.domain.qr.QrContent
import kotlin.test.assertEquals
import kotlin.test.assertIs

/** Spec 026 T027: what a scanned code is decided on the phone. Payloads are fictional. */
class QrContentTest {
    private val transfer = "00020101021238540010A00000072701240006970403011001234567890208QRIBFTTA530370454061500005802VN5914NGUYEN VAN MAU6006HA NOI630420C9"

    @Test
    fun aLinkIsCheckedLikeATypedLink() {
        assertEquals(QrContent.Link("https://chinhphu-mau.vn/abc"), QrContent.classify(" https://chinhphu-mau.vn/abc\n"))
        assertIs<QrContent.Link>(QrContent.classify("HTTP://mau.example/x"))
    }

    @Test
    fun aTelCodeBecomesAPhone() {
        assertEquals(QrContent.Phone("0900000002"), QrContent.classify("tel:0900000002"))
        assertEquals(QrContent.Unreadable, QrContent.classify("tel:  "))
    }

    @Test
    fun aVietQrIsReadAndNeverTreatedAsALink() {
        val content = assertIs<QrContent.Transfer>(QrContent.classify(transfer))
        assertEquals("NGUYEN VAN MAU", content.qr.payeeName)
        assertEquals(150_000L, content.qr.amountVnd)
    }

    @Test
    fun aBadChecksumOrOtherTextIsUnreadable() {
        assertEquals(QrContent.Unreadable, QrContent.classify(transfer.dropLast(4) + "0000"))
        assertEquals(QrContent.Unreadable, QrContent.classify("WIFI:S:mau;T:WPA;P:x;;"))
        assertEquals(QrContent.Unreadable, QrContent.classify(null))
        assertEquals(QrContent.Unreadable, QrContent.classify("   "))
    }
}
