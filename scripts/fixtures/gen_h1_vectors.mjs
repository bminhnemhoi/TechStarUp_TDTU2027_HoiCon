// Sinh docs/schemas/fixtures/h1_vectors.json — vector kiểm chuẩn hóa E.164 + h1 (ADR-006). Chỉ số HƯ CẤU.
//   node scripts/fixtures/gen_h1_vectors.mjs docs/schemas/fixtures/h1_vectors.json
// Kỳ vọng E.164 viết tay theo đặc tả (không suy từ code) ⇒ PhoneHasher (Kotlin) và backend cùng phải khớp.
import { createHash } from "node:crypto";
import { writeFileSync } from "node:fs";

const h1 = (e164) => createHash("sha256").update("hoicon:v1:" + e164, "utf8").digest("hex");
const cases = [
  // [input, expected e164 | null, note]
  ["0900000001", "+84900000001", "di động, dạng quốc nội"],
  ["090 000 0001", "+84900000001", "có khoảng trắng"],
  ["090.000.0001", "+84900000001", "có dấu chấm"],
  ["+84900000001", "+84900000001", "đã là E.164"],
  ["+84 90 000 0001", "+84900000001", "E.164 có khoảng trắng"],
  ["84900000001", "+84900000001", "thiếu dấu +"],
  ["0084900000001", "+84900000001", "tiền tố quốc tế 00"],
  ["+840900000001", "+84900000001", "+84 kèm số 0 thừa"],
  ["090 000 0001", "+84900000001", "khoảng trắng không ngắt (NBSP U+00A0)"],
  ["‪+84 90 000 0001‬", "+84900000001", "bọc ký tự định hướng LRE/PDF (U+202A/U+202C) khi dán số"],
  ["‎0900000001", "+84900000001", "dấu LRM (U+200E) ở đầu"],
  ["0900000002", "+84900000002", "số gắn cờ hư cấu (data/fixtures/phones.json)"],
  ["02800000000", "+842800000000", "máy bàn TP.HCM hư cấu (NSN 10 chữ số)"],
  ["+12025550123", "+12025550123", "số quốc tế (Mỹ, dải 555 hư cấu)"],
  ["", null, "ẩn số"],
  ["1900000000", null, "đầu số dịch vụ, không phải số cá nhân"],
  ["12345", null, "quá ngắn"],
  ["09000000", null, "di động thiếu chữ số"],
  ["0900abc001", null, "có chữ cái"],
];
const out = {
  description:
    'Vector kiểm chuẩn hóa E.164 + h1 = SHA-256("hoicon:v1:"+E164) (ADR-006). Dùng chung: :rules PhoneHasherVectorsTest (Kotlin) và backend tests/contract. Chỉ số HƯ CẤU — sinh bởi scripts/fixtures/gen_h1_vectors.mjs.',
  prefix: "hoicon:v1:",
  vectors: cases.map(([input, e164, note]) => ({
    input,
    e164,
    h1: e164 ? h1(e164) : null,
    last3: e164 ? e164.slice(-3) : null,
    note,
  })),
};
writeFileSync(process.argv[2], JSON.stringify(out, null, 2) + "\n", "utf8");
console.log(`wrote ${out.vectors.length} vectors`);
