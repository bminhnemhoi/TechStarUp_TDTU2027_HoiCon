// PreToolUse (Edit|Write|MultiEdit): enforce HoiCon privacy & Play-policy rules on the NEW content being written.
//  1. AndroidManifest.xml must not request forbidden permissions / bind forbidden services (Google Play + our privacy promise).
//  2. Source code (not tests/fixtures/eval/data/docs) must not contain raw Vietnamese phone numbers.
//  3. Source code must not log/print phone, account or OTP variables unless wrapped in mask()/hash.
// Exit 2 = blocked (message goes back to Claude). See CLAUDE.md "Luật quyền riêng tư".
import { block, readInput, relPath } from "./lib.mjs";

const input = readInput();
const ti = input?.tool_input ?? {};
const file = relPath(ti.file_path ?? "");
if (!file || file.startsWith("..")) process.exit(0);

// Collect only the text being introduced by this edit.
const pieces = [];
if (typeof ti.content === "string") pieces.push(ti.content);
if (typeof ti.new_string === "string") pieces.push(ti.new_string);
if (Array.isArray(ti.edits)) for (const e of ti.edits) if (typeof e?.new_string === "string") pieces.push(e.new_string);
const text = pieces.join("\n");
if (!text) process.exit(0);

// 1) Android manifest -------------------------------------------------------
if (/AndroidManifest\.xml$/.test(file)) {
  const FORBIDDEN = [
    "android.permission.READ_SMS",
    "android.permission.RECEIVE_SMS",
    "android.permission.SEND_SMS",
    "android.permission.RECEIVE_MMS",
    "android.permission.READ_CALL_LOG",
    "android.permission.WRITE_CALL_LOG",
    "android.permission.PROCESS_OUTGOING_CALLS",
    "android.permission.READ_CONTACTS",
    "android.permission.QUERY_ALL_PACKAGES",
    "android.permission.REQUEST_INSTALL_PACKAGES",
    "android.permission.RECORD_AUDIO_CALL", // placeholder guard for any call-audio capture attempt
    "android.permission.BIND_ACCESSIBILITY_SERVICE",
    "android.permission.BIND_NOTIFICATION_LISTENER_SERVICE",
    "android.permission.CAPTURE_AUDIO_OUTPUT",
  ];
  const hits = FORBIDDEN.filter((p) => text.includes(p));
  if (/android\.accessibilityservice/.test(text)) hits.push("accessibility-service meta-data");
  if (hits.length) {
    block(
      `[guard-privacy] ${file} khai báo quyền/dịch vụ bị cấm: ${hits.join(", ")}.\n` +
        "HỏiCon cam kết không đọc SMS, nhật ký cuộc gọi, danh bạ, không dùng Accessibility/Notification Listener và không ghi âm (CLAUDE.md, ADR-001, docs/PLAY-POLICY.md).\n" +
        "Nếu thật sự cần, viết ADR mới và được Minh duyệt trước.",
    );
  }
  process.exit(0);
}

// 2) & 3) Source code only --------------------------------------------------
const isSource = /\.(kt|kts|java|py|ts|tsx|js|jsx|mjs|cjs)$/.test(file);
const exempt =
  /(^|\/)(tests?|__tests__|androidTest|test|fixtures?|eval|data|docs|scripts\/fixtures)(\/|$)/.test(file) ||
  /\.(test|spec)\.[jt]sx?$/.test(file) ||
  /(^|\/)test_[^/]+\.py$/.test(file) ||
  /(^|\/)\.claude\//.test(file);
if (!isSource || exempt) process.exit(0);

// Vietnamese mobile numbers: 0/+84/84 followed by 3,5,7,8,9 and 8 more digits (allow separators).
const PHONE = /(?<![\w.])(?:\+?84|0)[\s.-]?(?:3|5|7|8|9)(?:[\s.-]?\d){8}(?![\w])/g;
const phones = [...text.matchAll(PHONE)].map((m) => m[0]);
if (phones.length) {
  block(
    `[guard-privacy] Phát hiện số điện thoại dạng thô trong ${file}: ${phones.slice(0, 3).join(", ")}.\n` +
      "Không hardcode số điện thoại trong mã nguồn. Dùng fixture hư cấu trong tests/ hoặc data/, hoặc giá trị hash (h1).",
  );
}

const LOG_CALL = /(\blog(ger)?\.(debug|info|warning|warn|error|exception|critical)|\bLog\.[dviwe]\b|\bTimber\.[dviwe]\b|\bprint(ln)?\s*\(|\bconsole\.(log|info|warn|error|debug)\b|\bprintStackTrace\b)/;
const PII_VAR = /\b(phone(_?number)?|phoneNumber|msisdn|caller(_?number)?|callerNumber|sdt|so_?dien_?thoai|account(_?number|_?no)|accountNumber|bank_?account|otp|cccd|full_?name|zalo_?(user_?)?id)\b/i;
for (const line of text.split(/\r?\n/)) {
  if (LOG_CALL.test(line) && PII_VAR.test(line) && !/\b(mask|redact|hash|h1|last3|masked)\w*/i.test(line)) {
    block(
      `[guard-privacy] Dòng log/print có thể in dữ liệu cá nhân thô trong ${file}:\n  ${line.trim().slice(0, 200)}\n` +
        "Bọc giá trị bằng mask()/PiiMasker (chỉ để lại 3 số cuối) hoặc log hash. Xem hoicon.domain.pii.",
    );
  }
}
process.exit(0);
