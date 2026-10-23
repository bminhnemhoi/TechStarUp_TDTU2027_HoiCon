-- Tách role ứng dụng khỏi role chủ bảng (spec 034 FR-008, mục #5 của 020, L1 của 021).
--
-- Vấn đề: ứng dụng chạy bằng role CHỦ BẢNG, nên một lỗi SQL injection hoặc thao tác nhầm có thể `ALTER TABLE ... DISABLE
-- TRIGGER` rồi sửa `consents` / `incident_transitions` (bằng chứng đồng ý theo Nghị định 356/2025, nhật ký chuyển trạng
-- thái). Trigger chống sửa chỉ là hàng rào mềm với chủ bảng; quyền mới là hàng rào cứng.
--
-- Giải pháp: role `hoicon_app` KHÔNG sở hữu bảng nào, KHÔNG phải superuser, không có DDL:
--   * `consents`, `incident_transitions`: chỉ SELECT + INSERT (không UPDATE/DELETE/TRUNCATE, không tắt được trigger).
--   * các bảng còn lại: SELECT/INSERT/UPDATE/DELETE (ứng dụng cần để chạy). `alembic_version`: không cấp.
--   * migration vẫn chạy bằng role chủ (`hoicon` ở dev). Xóa dây chuyền (ON DELETE CASCADE) vẫn chạy được vì hành động
--     tham chiếu thi hành với quyền của chủ bảng, và trigger của `incident_transitions` cho phép xóa do cha đã bị xóa.
--
-- Chạy lại được (idempotent), nên chạy lại SAU MỖI migration thêm bảng để bảng mới có quyền:
--   docker exec -i hoicon-db psql -U hoicon -d hoicon -v ON_ERROR_STOP=1 < infra/postgres/roles.sql
-- Mật khẩu KHÔNG nằm trong tệp này. Đặt một lần, tương tác, rồi dán vào HOICON_DATABASE_URL của ứng dụng:
--   docker exec -it hoicon-db psql -U hoicon -d hoicon -c '\password hoicon_app'
--
-- Lưu ý khi áp dụng ở prod (spec 012): `IncidentRuntime.open` gọi `AsyncPostgresSaver.setup()` (DDL `CREATE TABLE IF NOT
-- EXISTS` của LangGraph) nên cần role chủ; với `hoicon_app` hãy chạy `setup()` một lần bằng role chủ trước.
-- Đã thử (spec 012 T017, `scripts/try-roles.sh` trên Postgres tạm): `setup()` dưới `hoicon_app` báo InsufficientPrivilege, mã bỏ qua
-- lỗi này (`open_checkpointer`) nên API/worker chạy bình thường, miễn bảng đã có. Thứ tự áp: migration + `setup()` bằng role chủ
-- → `roles.sql` (cấp quyền cả bảng checkpoint vừa tạo) → đổi `HOICON_DATABASE_URL` sang `hoicon_app`.

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'hoicon_app') THEN
        CREATE ROLE hoicon_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOINHERIT;
    END IF;
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO hoicon_app', current_database());
END
$$;

GRANT USAGE ON SCHEMA public TO hoicon_app;
REVOKE CREATE ON SCHEMA public FROM hoicon_app;

DO $$
DECLARE
    t record;
BEGIN
    FOR t IN
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public' AND tablename NOT IN ('consents', 'incident_transitions', 'alembic_version')
    LOOP
        EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON public.%I TO hoicon_app', t.tablename);
    END LOOP;
END
$$;

-- Vết yêu cầu xóa dữ liệu (pháp lý): app chỉ ghi thêm và cập nhật trạng thái, không xóa được.
REVOKE DELETE, TRUNCATE ON public.data_requests FROM hoicon_app;

-- Sổ chỉ-ghi-thêm: thu hồi sạch mọi quyền sửa, kể cả quyền còn sót từ lần cấp trước.
GRANT SELECT, INSERT ON public.consents, public.incident_transitions TO hoicon_app;
REVOKE UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON public.consents, public.incident_transitions FROM hoicon_app;
REVOKE ALL ON public.alembic_version FROM hoicon_app;
