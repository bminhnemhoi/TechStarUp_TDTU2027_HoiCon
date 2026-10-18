# Luật R8 tối thiểu cho bản phát hành (Spec 012 lite). Thư viện (Room, WorkManager, Lifecycle, Tink, ML Kit, Compose) đã
# kèm luật giữ riêng qua consumer rules; ở đây chỉ thêm những gì mã của HỏiCon cần.

# Báo cáo sự cố đọc được sau khi dịch ngược bằng mapping.txt (BUNDLE-METADATA của AAB), mà không lộ tên tệp nguồn.
-keepattributes SourceFile,LineNumberTable
-renamesourcefileattribute SourceFile
