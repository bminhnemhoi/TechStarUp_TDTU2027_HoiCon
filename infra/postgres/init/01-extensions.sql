-- Chạy một lần khi volume Postgres mới được tạo. Test dùng DB riêng hoicon_test.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE DATABASE hoicon_test OWNER hoicon;
\connect hoicon_test
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
