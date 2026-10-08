/* Tao ban mo ta y tuong HoiCon (Word) - Tech Startup Challenger 2027 */
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, ImageRun, Header, Footer, PageNumber, TableOfContents,
  LevelFormat, PageOrientation, VerticalAlign, TabStopType, Tab, TableLayoutType,
} = require("docx");

const OUT = process.argv[2] || "HoiCon.docx";
const M = JSON.parse(fs.readFileSync(path.join(__dirname, "model.json"), "utf8"));

// ------------------------------------------------------------------ hang so
const FONT = "Times New Roman";
const NAVY = "1F3A5F", ORANGE = "C4561D", GREEN = "1E7B53", GRAYTXT = "595959";
const LIGHT = "EAF1F8", LIGHT_OR = "FDF1E8", LIGHT_GR = "E8F4EE", LINE = "B7C3D3";
const PW = 11906, PH = 16838;                      // A4 (DXA)
const MARGIN = { top: 1134, bottom: 1134, left: 1701, right: 1134, header: 567, footer: 567 };
const CW = PW - MARGIN.left - MARGIN.right;        // 9071 DXA ~ 16 cm
const LCW = PH - 1134 - 1134;                       // vung noi dung trang ngang
const BODY = 28, TSZ = 24, CAP = 24;               // 14pt, 12pt, 12pt

// ------------------------------------------------------------------ trich dan
const REFS = {
  rules: "Ban Tổ chức Tech Startup Challenger 2027, Khoa Công nghệ thông tin, Trường Đại học Tôn Đức Thắng. Thể lệ cuộc thi ý tưởng khởi nghiệp “Tech Startup Challenger 2027”.",
  vov8000: "VOV (24/04/2026). Thiệt hại từ lừa đảo trực tuyến lên tới 8.000 tỷ đồng trong năm 2025. https://vov.vn/phap-luat/thiet-hai-tu-lua-dao-truc-tuyen-len-toi-8000-ty-dong-trong-nam-2025-post1286479.vov",
  nca: "CafeF (01/2026). Năm 2025, thiệt hại do lừa đảo trực tuyến ở Việt Nam ước tính trên 6.000 tỷ đồng (khảo sát 60.300 người dùng của Hiệp hội An ninh mạng quốc gia). https://cafef.vn/nam-2025-thiet-hai-do-lua-dao-truc-tuyen-o-viet-nam-uoc-tinh-tren-6000-ty-dong-18826010807091841.chn",
  tt40000: "Tuổi Trẻ/Người Lao Động (29/12/2025). Bộ Công an: 5 năm, Việt Nam mất gần 40.000 tỷ đồng vì lừa đảo trực tuyến. https://tuoitre.vn/nld/bo-cong-an-5-nam-viet-nam-mat-gan-40000-ti-dong-vi-lua-dao-truc-tuyen-19625122919210539.htm",
  gasa: "Global Anti-Scam Alliance (27/08/2025). State of Scams in Southeast Asia 2025. https://gasa.org/knowledge-base/blog/new-study-reveals-63-of-southeast-asians-experienced-scams-in-past-year",
  tn65: "Thanh Niên (23/10/2025). Lừa đảo tăng mạnh, thiệt hại hàng ngàn tỷ đồng (số liệu Cục An ninh mạng và phòng, chống tội phạm sử dụng công nghệ cao). https://thanhnien.vn/lua-dao-tang-manh-thiet-hai-hang-ngan-ti-dong-185251022190804651.htm",
  hp: "Báo Hải Phòng (2026). Các hình thức lừa đảo trực tuyến phổ biến nhất năm 2025 (báo cáo của Hiệp hội An ninh mạng quốc gia). https://baohaiphong.vn/cac-hinh-thuc-lua-dao-truc-tuyen-nao-pho-bien-nhat-nam-2025-532711.html",
  vnp: "VietnamPlus (27/03/2026). Bảo vệ người cao tuổi trước các chiêu lừa đảo tinh vi trên không gian mạng. https://www.vietnamplus.vn/bao-ve-nguoi-cao-tuoi-truoc-cac-chieu-lua-dao-tinh-vi-tren-khong-gian-mang-post1101437.vnp",
  tt_agri: "Tuổi Trẻ (01/10/2026). Người phụ nữ đi rút tiền tỷ với thái độ bất thường, nhân viên ngân hàng báo công an. https://tuoitre.vn/nguoi-phu-nu-di-rut-tien-ti-voi-thai-do-bat-thuong-nhan-vien-ngan-hang-bao-cong-an-100261001104136065.htm",
  cand: "Công an Nhân dân (02/10/2026). Ma trận lừa đảo trên không gian mạng nhắm vào người già yếu thế. https://cand.vn/ma-tran-lua-dao-tren-khong-gian-mang-nham-vao-nguoi-gia-yeu-the-post823770.html",
  tn_sv: "Thanh Niên (02/01/2026). Từ công văn của Công an TP.HCM, Sở GD-ĐT cảnh báo thủ đoạn lừa đảo mới. https://thanhnien.vn/tu-cong-van-cua-cong-an-tphcm-so-gd-dt-canh-bao-thu-doan-lua-dao-moi-185260102133152052.htm",
  tt_lao: "Tuổi Trẻ (16/09/2026). Công an sang Lào bắt gọn ổ nhóm lừa đảo qua mạng chiếm đoạt 1.500 tỷ đồng của hàng ngàn người Việt. https://tuoitre.vn/cong-an-sang-lao-bat-gon-o-nhom-lua-dao-qua-mang-chiem-doat-1500-ti-dong-cua-hang-ngan-nguoi-viet-100260916204859951.htm",
  tn_acb: "Thanh Niên (08/10/2025). Lừa đảo ngày càng tinh vi, ngân hàng đang làm gì để bảo vệ người dùng. https://thanhnien.vn/lua-dao-ngay-cang-tinh-vi-ngan-hang-dang-lam-gi-de-bao-ve-nguoi-dung-185251008090520098.htm",
  tn_simo: "Thanh Niên (29/05/2025). Gửi tài khoản nghi ngờ lừa đảo sang Ngân hàng Nhà nước; lộ trình cảnh báo khách hàng của các ngân hàng. https://thanhnien.vn/diem-mat-chi-ten-gui-tai-khoan-nghi-ngo-lua-dao-sang-ngan-hang-nha-nuoc-18525052912181878.htm",
  vtv: "VTV (01/01/2026). Từ 1/1/2026, nhiều tài khoản ngân hàng bị ngừng giao dịch do chưa cập nhật CCCD. https://vtv.vn/tu-1-1-2026-nhieu-tai-khoan-ngan-hang-bi-ngung-giao-dich-do-chua-cap-nhat-cccd-100260101130903656.htm",
  frasers: "Frasers Law Company (19/01/2026). Nghị định 356/2025/NĐ-CP hướng dẫn Luật Bảo vệ dữ liệu cá nhân số 91/2025/QH15. https://www.frasersvn.com/vi/legal-updates-and-publications/the-next-chapter-in-data-protection-new-decree-guiding-the-personal-data-protection-law",
  ailaw: "LuatVietnam. Luật Trí tuệ nhân tạo số 134/2025/QH15 ngày 10/12/2025, hiệu lực 01/03/2026. https://english.luatvietnam.vn/law-no-134-2025-qh15-dated-december-10-2025-of-the-national-assembly-on-artificial-intelligence-422299-doc1.html",
  tn_acb30: "Thanh Niên (23/06/2026). ACB cảnh báo 30 kịch bản lừa đảo trực tuyến phổ biến tại Việt Nam. https://thanhnien.vn/acb-canh-bao-30-kich-ban-lua-dao-truc-tuyen-pho-bien-tai-viet-nam-185260623105131392.htm",
  tn_sim: "Thanh Niên (02/07/2026). Cố tình sử dụng SIM không chính chủ sẽ bị phạt tiền lên đến 50 triệu đồng. https://thanhnien.vn/co-tinh-su-dung-sim-khong-chinh-chu-se-bi-phat-tien-len-den-50-trieu-dong-185260702000142323.htm",
  vov_vneid: "VOV (27/02/2026). Tích hợp mạng xã hội với VNeID: xác thực danh tính sẽ hết lừa đảo trực tuyến? https://vov.vn/xa-hoi/tich-hop-mang-xa-hoi-voi-vneid-xac-thuc-danh-tinh-se-het-lua-dao-truc-tuyen-post1271458.vov",
  tn_ios27: "Thanh Niên (03/07/2026). Tính năng mới trên iOS 27 giúp tăng cường chống lừa đảo. https://thanhnien.vn/tinh-nang-moi-tren-ios-27-giup-tang-cuong-chong-lua-dao-185260703104422657.htm",
  tn_pixel: "Thanh Niên (01/02/2026). Galaxy S26 sắp có tính năng phát hiện lừa đảo trong cuộc gọi như trên Pixel. https://thanhnien.vn/galaxy-s26-sap-co-tinh-nang-dang-tien-nhat-tren-pixel-185260201174214127.htm",
  nd330: "Cổng thông tin Xây dựng chính sách, pháp luật – Chính phủ (24/08/2026). Nghị định 330/2026/NĐ-CP về xử phạt vi phạm hành chính trong lĩnh vực an ninh mạng. https://xaydungchinhsach.chinhphu.vn/nghi-dinh-330-2026-nd-cp-ve-xu-phat-vi-pham-hanh-chinh-trong-linh-vuc-an-ninh-mang-119260824172446407.htm",
  tn_google: "Thanh Niên (26/08/2026). Dự án Chống Lừa Đảo nhận hỗ trợ từ Google (chương trình Scam Ready ASEAN). https://thanhnien.vn/du-an-chong-lua-dao-nhan-ho-tro-tu-google-185260826144700166.htm",
  vne_spam: "VnExpress (15/09/2026). Bộ Công an đề xuất nhiều cơ chế mới chống tin nhắn, cuộc gọi rác. https://vnexpress.net/bo-cong-an-de-xuat-nhieu-co-che-moi-chong-tin-nhan-cuoc-goi-rac-5120449.html",
  vov_tet: "VOV. Bộ Công an cảnh báo chiêu lừa đảo trực tuyến dịp Tết và mùa lễ hội. https://vov.vn/phap-luat/bo-cong-an-canh-bao-chieu-lua-dao-truc-tuyen-dip-tet-va-mua-le-hoi-post1265119.vov",
  tn_thue: "Thanh Niên (13/08/2026). Thuế TP.HCM lưu ý nhận diện lừa đảo từ cuộc gọi. https://thanhnien.vn/thue-tphcm-luu-y-nhan-dien-lua-dao-tu-cuoc-goi-185260813120338251.htm",
  kenh14: "Kenh14 (02/10/2026). Công an cảnh báo trang giả mạo “hỗ trợ lấy lại tiền” nhắm vào người đã bị lừa. https://kenh14.vn/cong-an-canh-bao-quan-trong-den-nguoi-dung-facebook-21526100210224978.chn",
  oai_guide: "OpenAI (2025). A practical guide to building agents. https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf",
  anth: "Anthropic. Building effective agents. https://www.anthropic.com/engineering/building-effective-agents",
  lc: "LangChain (2025). State of Agent Engineering (khảo sát 1.340 người xây dựng tác tử AI). https://www.langchain.com/state-of-agent-engineering",
  tn_queue: "Thanh Niên (14/06/2026). Người dân xếp hàng chen kín để học chống lừa đảo qua mạng. https://thanhnien.vn/nguoi-dan-xep-hang-chen-kin-de-hoc-chong-lua-dao-qua-mang-185260614110904479.htm",
  and_csr: "Android Developers. CallScreeningService – API reference. https://developer.android.com/reference/android/telecom/CallScreeningService",
  gp_acc: "Google Play Console Help. Use of the AccessibilityService API. https://support.google.com/googleplay/android-developer/answer/10964491",
  gp_sms: "Google Play Console Help. Use of SMS or Call Log permission groups. https://support.google.com/googleplay/android-developer/answer/10208820",
  apple_cd: "Apple Developer Documentation. CXCallDirectoryProvider (Call Directory Extension). https://developer.apple.com/documentation/callkit/cxcalldirectoryprovider",
  zbot: "Zalo Bot Platform (truy cập 04/10/2026). https://bot.zaloplatforms.com/",
  zalo_oa: "Zalo Solutions. Bảng giá Zalo Official Account (hiệu lực từ 01/06/2026). https://zalo.solutions/oa/pricing",
  zbs: "Zalo Solutions. Bảng giá ZBS Template Message. https://zalo.solutions/business-message/pricing",
  gemini: "Google AI for Developers. Gemini API pricing (truy cập 04/10/2026). https://ai.google.dev/gemini-api/docs/pricing",
  claude: "Anthropic. Claude API pricing (truy cập 04/10/2026). https://platform.claude.com/docs/en/about-claude/pricing",
  dbnd: "Đại biểu Nhân dân (2025). Chi tiết 168 đơn vị hành chính cấp xã của TP.HCM sau hợp nhất. https://daibieunhandan.vn/chi-tiet-168-don-vi-hanh-chinh-cap-xa-cua-tp-ho-chi-minh-sau-hop-nhat-10371821.html",
  vne_ai: "VnExpress (29/09/2026). Trung bình mỗi giờ Việt Nam có thêm 8 doanh nghiệp ứng dụng AI (nghiên cứu của AWS và Strand Partners). https://vnexpress.net/trung-binh-moi-gio-viet-nam-co-them-8-doanh-nghiep-ung-dung-ai-5126323.html",
  vne_ntrust: "VnExpress (2024). Ra mắt phần mềm giúp phát hiện lừa đảo mạng nTrust. https://vnexpress.net/ra-mat-phan-mem-giup-phat-hien-lua-dao-mang-4775737.html",
  appstore: "App Store Việt Nam. nTrust – Phòng chống lừa đảo (truy cập 10/2026). https://apps.apple.com/vn/app/ntrust-ph%C3%B2ng-ch%E1%BB%91ng-l%E1%BB%ABa-%C4%91%E1%BA%A3o/id6504554337",
  tfgi: "Tech for Good Institute (10/09/2025). Building digital resilience: lessons from Vietnam. https://techforgoodinstitute.org/insights/country-spotlights/building-digital-resilience-lessons-from-vietnam-2/",
  tn_ios27b: "Thanh Niên (18/09/2026). Cách kích hoạt tính năng chống lừa đảo mạo danh mới trên iOS 27. https://thanhnien.vn/cach-kich-hoat-tinh-nang-chong-lua-dao-mao-danh-moi-tren-ios-27-185260917081305572.htm",
  aura: "Aura. Pricing (truy cập 10/2026). https://www.aura.com/pricing",
  apate: "Apate.ai (truy cập 10/2026). https://www.apate.ai/",
  sbs: "Saigon Business School (2026). Two SBS teams showcase excellence in both technology and business strategy at Tech Startup Challenger 2026. https://sbsedu.vn/news/two-sbs-teams-showcase-excellence-in-both-technology-and-business-strategy-at-tech-startup-challenger-2026/",
  gdtd: "Giáo dục Thủ đô (2026). Vinh danh 16 sản phẩm công nghệ thông tin sáng tạo tại Hue-ICT Challenge 2026. https://giaoducthudo.giaoducthoidai.vn/vinh-danh-16-san-pham-cong-nghe-thong-tin-sang-tao-tai-hue-ict-challenge-2026-216797.html",
  tt_catlai: "Tuổi Trẻ (06/06/2026). Người dân Cát Lái vui mừng khi phường có điểm hỗ trợ dịch vụ công trực tuyến. https://tuoitre.vn/nguoi-dan-cat-lai-vui-mung-khi-phuong-co-diem-ho-tro-dich-vu-cong-truc-tuyen-20260606102336007.htm",
  gfs: "Google for Startups Cloud Program (truy cập 10/2026). https://startup.google.com/cloud/",
  aws: "AWS Activate – Credits (truy cập 10/2026). https://aws.amazon.com/startups/credits",
  phoasr: "Qualcomm AI Research Vietnam (2026). Vietnamese ASR: A Revisit. Findings of EACL 2026. https://aclanthology.org/2026.findings-eacl.345.pdf",
  bc: "British Council, CIEM, CSIP (2019). State of Social Enterprise in Vietnam. https://www.britishcouncil.org/sites/default/files/state_of_social_enterprise_in_vietnam_british_council_web_final.pdf",
  tn_8: "Thanh Niên (28/07/2026). Cảnh báo 8 chiêu trò lừa đảo nhắm vào người cao tuổi. https://thanhnien.vn/canh-bao-8-chieu-tro-lua-dao-nham-vao-nguoi-cao-tuoi-185260728154001279.htm",
};
const ORDER = [];
function cite(key) {
  if (!REFS[key]) throw new Error("Thieu tai lieu tham khao: " + key);
  let i = ORDER.indexOf(key);
  if (i < 0) { ORDER.push(key); i = ORDER.length - 1; }
  return i + 1;
}

// ------------------------------------------------------------------ chu trong dong
function inline(text, base = {}) {
  const runs = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|(?:\{\{[a-zA-Z0-9_]+\}\})+|\[\[[^\]]+\]\])/g;
  let last = 0, m;
  const mk = (t, extra = {}) => new TextRun({ text: t, font: FONT, ...base, ...extra });
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) runs.push(mk(text.slice(last, m.index)));
    const tok = m[0];
    if (tok.startsWith("**")) runs.push(mk(tok.slice(2, -2), { bold: true }));
    else if (tok.startsWith("{{")) {
      const keys = [...tok.matchAll(/\{\{([a-zA-Z0-9_]+)\}\}/g)].map((x) => x[1]);
      runs.push(mk("[" + keys.map(cite).join(", ") + "]"));
    } else if (tok.startsWith("[[")) runs.push(mk("[" + tok.slice(2, -2) + "]", { highlight: "yellow" }));
    else runs.push(mk(tok.slice(1, -1), { italics: true }));
    last = m.index + tok.length;
  }
  if (last < text.length) runs.push(mk(text.slice(last)));
  return runs;
}

// ------------------------------------------------------------------ khoi noi dung
const P = (text, o = {}) => new Paragraph({
  children: inline(text, o.run || {}),
  alignment: o.align || AlignmentType.JUSTIFIED,
  indent: o.noIndent ? undefined : { firstLine: 567 },
  spacing: { after: o.after ?? 120, before: o.before ?? 0, line: 300 },
  keepNext: o.keepNext || false,
});
let bulletInst = 0, numInst = 0;
function bullets(items, o = {}) {
  return items.map((t) => new Paragraph({
    children: inline(t, o.run || {}),
    numbering: { reference: o.ref || "bullets", level: o.level || 0 },
    alignment: AlignmentType.JUSTIFIED,
    spacing: { after: 80, line: 300 },
  }));
}
function numbered(items) {
  numInst += 1;
  return items.map((t) => new Paragraph({
    children: inline(t),
    numbering: { reference: "numbers", level: 0, instance: numInst },
    alignment: AlignmentType.JUSTIFIED,
    spacing: { after: 80, line: 300 },
  }));
}
const H1 = (text, o = {}) => new Paragraph({ text, heading: HeadingLevel.HEADING_1, pageBreakBefore: !o.noBreak });
const H2 = (text) => new Paragraph({ text, heading: HeadingLevel.HEADING_2 });
const H3 = (text) => new Paragraph({ text, heading: HeadingLevel.HEADING_3 });

let tableNo = 0, figNo = 0;
function tcap(text) {
  tableNo += 1;
  return new Paragraph({
    children: [new TextRun({ text: `Bảng ${tableNo}. `, bold: true, font: FONT, size: CAP }), ...inline(text, { size: CAP, bold: true })],
    alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 80 },
  });
}
function note(text) {
  return new Paragraph({
    children: inline(text, { size: 22, italics: true, color: GRAYTXT }),
    alignment: AlignmentType.LEFT, spacing: { before: 40, after: 160, line: 276 },
  });
}
function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20), data: b };
}
function figure(file, caption, widthPx = 600) {
  figNo += 1;
  const { w, h, data } = pngSize(path.join(__dirname, file));
  const height = Math.round(widthPx * h / w);
  return [
    new Paragraph({
      children: [new ImageRun({ type: "png", data, transformation: { width: widthPx, height },
        altText: { title: caption, description: caption, name: file } })],
      alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60 },
    }),
    new Paragraph({
      children: [new TextRun({ text: `Hình ${figNo}. `, bold: true, font: FONT, size: CAP }), ...inline(caption, { size: CAP, italics: true })],
      alignment: AlignmentType.CENTER, spacing: { after: 200 },
    }),
  ];
}

const border = (c = LINE, s = 4) => ({ style: BorderStyle.SINGLE, size: s, color: c });
const cellBorders = { top: border(), bottom: border(), left: border(), right: border() };
function cellParas(content, o = {}) {
  const kn = !!o.keepNext;
  const arr = Array.isArray(content) ? content : [content];
  const out = [];
  for (const item of arr) {
    if (item && typeof item === "object" && item.bullet) {
      out.push(new Paragraph({
        children: inline(item.bullet, { size: o.size || TSZ, ...(o.run || {}) }),
        numbering: { reference: "tbullets", level: 0 },
        spacing: { after: 30, line: 264 }, alignment: AlignmentType.LEFT, keepNext: kn, keepLines: kn,
      }));
    } else {
      out.push(new Paragraph({
        children: inline(String(item), { size: o.size || TSZ, ...(o.run || {}) }),
        alignment: o.align || AlignmentType.LEFT, spacing: { after: 30, line: 264 }, keepNext: kn, keepLines: kn,
      }));
    }
  }
  return out;
}
function cell(content, width, o = {}) {
  return new TableCell({
    children: cellParas(content, o),
    width: { size: width, type: WidthType.DXA },
    shading: o.fill ? { fill: o.fill, type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 70, bottom: 70, left: 110, right: 110 },
    verticalAlign: o.valign || VerticalAlign.TOP,
    columnSpan: o.span, rowSpan: o.rowSpan,
    borders: o.borders || cellBorders,
  });
}
function table(headers, rows, widths, o = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const hdr = new TableRow({
    tableHeader: true, cantSplit: true,
    children: headers.map((h, i) => cell(h, widths[i], { fill: NAVY, run: { bold: true, color: "FFFFFF" }, align: AlignmentType.CENTER, valign: VerticalAlign.CENTER, keepNext: true })),
  });
  const body = rows.map((r, ri) => new TableRow({
    cantSplit: o.cantSplit !== false,
    children: r.map((c, i) => cell(c, widths[i], {
      fill: (o.firstColFill && i === 0) ? LIGHT : (o.zebra && ri % 2 === 1 ? "F7F9FC" : undefined),
      run: (o.boldFirst && i === 0) ? { bold: true } : {},
      align: (o.rightCols || []).includes(i) ? AlignmentType.RIGHT : ((o.centerCols || []).includes(i) ? AlignmentType.CENTER : AlignmentType.LEFT),
      keepNext: o.keep !== false && ri < rows.length - 1,
    })),
  }));
  return new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: widths, rows: [hdr, ...body], layout: TableLayoutType.FIXED });
}
function callout(title, lines, color = ORANGE, fill = LIGHT_OR) {
  const children = [];
  if (title) children.push(new Paragraph({ children: inline(title, { bold: true, color, size: 26 }), spacing: { after: 60 } }));
  for (const l of lines) {
    if (typeof l === "object" && l.bullet) children.push(new Paragraph({ children: inline(l.bullet, { size: 26 }), numbering: { reference: "tbullets", level: 0 }, spacing: { after: 40, line: 288 } }));
    else children.push(new Paragraph({ children: inline(l, { size: 26 }), alignment: AlignmentType.JUSTIFIED, spacing: { after: 40, line: 288 } }));
  }
  return new Table({
    width: { size: CW, type: WidthType.DXA }, columnWidths: [CW], layout: TableLayoutType.FIXED,
    rows: [new TableRow({ cantSplit: true, children: [new TableCell({
      children, width: { size: CW, type: WidthType.DXA },
      shading: { fill, type: ShadingType.CLEAR, color: "auto" },
      margins: { top: 120, bottom: 120, left: 200, right: 200 },
      borders: { left: { style: BorderStyle.SINGLE, size: 24, color }, top: border(fill), bottom: border(fill), right: border(fill) },
    })] })],
  });
}
function statStrip(items) {
  const w = Math.floor(CW / items.length);
  const widths = items.map((_, i) => (i === items.length - 1 ? CW - w * (items.length - 1) : w));
  return new Table({
    width: { size: CW, type: WidthType.DXA }, columnWidths: widths, layout: TableLayoutType.FIXED,
    rows: [new TableRow({ cantSplit: true, children: items.map(([big, small], i) => new TableCell({
      width: { size: widths[i], type: WidthType.DXA },
      shading: { fill: LIGHT, type: ShadingType.CLEAR, color: "auto" },
      margins: { top: 140, bottom: 140, left: 100, right: 100 },
      borders: { top: border("FFFFFF", 12), bottom: border("FFFFFF", 12), left: border("FFFFFF", 12), right: border("FFFFFF", 12) },
      verticalAlign: VerticalAlign.CENTER,
      children: [
        new Paragraph({ children: [new TextRun({ text: big, bold: true, size: 36, color: i === 0 ? ORANGE : NAVY, font: FONT })], alignment: AlignmentType.CENTER, spacing: { after: 40 } }),
        new Paragraph({ children: inline(small, { size: 22, color: GRAYTXT }), alignment: AlignmentType.CENTER, spacing: { after: 0, line: 252 } }),
      ],
    })) })],
  });
}
const gap = (after = 120) => new Paragraph({ children: [], spacing: { after } });

// so lieu
const fmt = (v, d = 1) => {
  const neg = v < 0; v = Math.abs(v);
  let s = v.toFixed(d);
  let [i, f] = s.split(".");
  i = i.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return (neg ? "−" : "") + (f ? `${i},${f}` : i);
};
const tr = (v) => fmt(v / 1e6, 1);            // trieu dong, 1 chu so thap phan
const ty = (v) => fmt(v / 1e9, 2);            // ty dong
const Y = M.years;

// =================================================================== TRANG BIA
const cover = [];
const coverLine = (text, size, o = {}) => new Paragraph({
  children: [new TextRun({ text, size, bold: o.bold, italics: o.italics, color: o.color, font: FONT })],
  alignment: AlignmentType.CENTER, spacing: { before: o.before || 0, after: o.after ?? 60 },
});
cover.push(coverLine("TRƯỜNG ĐẠI HỌC TÔN ĐỨC THẮNG", 28, { bold: true }));
cover.push(coverLine("KHOA CÔNG NGHỆ THÔNG TIN", 28, { bold: true, after: 40 }));
cover.push(new Paragraph({ children: [], alignment: AlignmentType.CENTER, spacing: { after: 360 },
  indent: { left: 3300, right: 3300 }, border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: NAVY, space: 1 } } }));
cover.push(coverLine("CUỘC THI Ý TƯỞNG KHỞI NGHIỆP", 26, { after: 0 }));
cover.push(coverLine("TRONG LĨNH VỰC CÔNG NGHỆ THÔNG TIN", 26, { after: 40 }));
cover.push(coverLine("TECH STARTUP CHALLENGER 2027", 34, { bold: true, color: NAVY, after: 600 }));
cover.push(coverLine("BẢN MÔ TẢ Ý TƯỞNG DỰ ÁN", 32, { bold: true, after: 40 }));
cover.push(coverLine("(Thuyết minh Vòng loại 1 – Ý tưởng)", 26, { italics: true, after: 520 }));
cover.push(coverLine("HỏiCon", 88, { bold: true, color: NAVY, after: 40 }));
cover.push(coverLine("TRỢ LÝ AI CHỐNG LỪA ĐẢO CHO CẢ NHÀ", 32, { bold: true, color: ORANGE, after: 120 }));
cover.push(coverLine("“Bị dọa chuyển tiền? Hỏi con trước đã.”", 28, { italics: true, color: GRAYTXT, after: 560 }));
const infoRows = [
  ["Lĩnh vực dự thi", "Kinh doanh tạo tác động xã hội (gắn với Tài chính)"],
  ["Công nghệ cốt lõi", "Agentic AI – hệ đa tác tử có con người tham gia quyết định"],
  ["Tên đội thi", "[[Điền tên đội]]"],
  ["Trưởng nhóm", "[[Họ và tên – MSSV – Khoa]]"],
  ["Thành viên", ["[[Họ và tên – MSSV – Khoa]]", "[[Họ và tên – MSSV – Khoa]]", "[[Họ và tên – MSSV – Khoa]]", "[[Họ và tên – MSSV – Khoa]]"]],
  ["Giảng viên hướng dẫn", "[[Họ và tên (nếu có)]]"],
];
const noB = { top: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" }, bottom: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" }, left: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" }, right: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" } };
cover.push(new Table({
  width: { size: 8000, type: WidthType.DXA }, columnWidths: [2700, 5300], layout: TableLayoutType.FIXED,
  alignment: AlignmentType.CENTER,
  rows: infoRows.map(([k, v]) => new TableRow({ children: [
    cell(k + ":", 2700, { run: { bold: true }, size: 26, borders: noB }),
    cell(v, 5300, { size: 26, borders: noB }),
  ] })),
}));
cover.push(coverLine("TP. Hồ Chí Minh, tháng 10 năm 2026", 26, { italics: true, before: 700 }));

// =================================================================== PHAN DAU
const front = [];
front.push(new Paragraph({ children: [new TextRun({ text: "MỤC LỤC", bold: true, size: 32, color: NAVY, font: FONT })], alignment: AlignmentType.CENTER, spacing: { after: 240 } }));
front.push(new TableOfContents("MỤC LỤC", { hyperlink: true, headingStyleRange: "1-2" }));
front.push(H1("DANH MỤC TỪ VIẾT TẮT"));
front.push(tcap("Các từ viết tắt sử dụng trong tài liệu"));
front.push(table(["Từ viết tắt", "Nghĩa đầy đủ"], [
  ["AI / LLM", "Trí tuệ nhân tạo / Mô hình ngôn ngữ lớn (Large Language Model)"],
  ["Agentic AI", "AI dạng tác tử: tự lập kế hoạch, gọi công cụ, thực hiện hành động nhiều bước trong giới hạn an toàn"],
  ["B2C / B2B2C", "Bán trực tiếp cho người dùng / Bán qua đối tác (ngân hàng, bảo hiểm, nhà mạng) tới khách hàng của họ"],
  ["BGK / BTC", "Ban giám khảo / Ban tổ chức"],
  ["CSR", "Trách nhiệm xã hội của doanh nghiệp (Corporate Social Responsibility)"],
  ["EBITDA", "Lợi nhuận trước lãi vay, thuế và khấu hao"],
  ["HITL", "Con người tham gia vòng quyết định (Human-in-the-loop)"],
  ["LOI / MOU", "Thư ý định hợp tác / Biên bản ghi nhớ"],
  ["MCP", "Model Context Protocol – giao thức mở để tác tử AI gọi công cụ"],
  ["MVP", "Sản phẩm khả dụng tối thiểu (Minimum Viable Product)"],
  ["OA / ZBS", "Zalo Official Account / Tin nhắn doanh nghiệp theo mẫu của Zalo (ZBS Template Message)"],
  ["SIMO", "Hệ thống thông tin hỗ trợ quản lý, giám sát và phòng ngừa rủi ro gian lận của Ngân hàng Nhà nước"],
  ["TAM / SAM / SOM", "Tổng thị trường / Thị trường có thể phục vụ / Thị trường có thể đạt được"],
], [2400, CW - 2400], { boldFirst: true, firstColFill: true }));

// ---------------------------------------------------------- TOM TAT
front.push(H1("TÓM TẮT DỰ ÁN"));
front.push(P("**HỏiCon** là hệ thống trợ lý Agentic AI giúp các gia đình Việt Nam chặn lừa đảo đúng lúc nạn nhân đang bị thao túng qua điện thoại. Khi người cao tuổi (hoặc sinh viên) đang nghe một cuộc gọi lạ mà mở ứng dụng ngân hàng, “Lính gác” trên điện thoại lập tức kích hoạt một **khoảng dừng an toàn** bằng giọng nói tiếng Việt. Các tác tử AI trên máy chủ hỏi nhanh vài câu để chấm mức rủi ro, báo cho con cháu qua Zalo kèm tóm tắt và bằng chứng, tự xác minh số điện thoại, tài khoản, đường link, rồi hỗ trợ lập hồ sơ trình báo nếu sự việc đã xảy ra. Quyết định cuối cùng luôn thuộc về con người."));
front.push(tcap("Thông tin tóm tắt dự án HỏiCon"));
front.push(table(["Hạng mục", "Nội dung"], [
  ["Vấn đề", "Lừa đảo trực tuyến gây thiệt hại hơn 8.000 tỷ đồng năm 2025 {{vov8000}}; giả danh công an, cơ quan chức năng là thủ đoạn phổ biến nhất {{nca}}; 50% vụ có nạn nhân cao tuổi xuất phát từ nỗi sợ liên lụy con cháu {{vnp}}."],
  ["Khoảng trống", "Công cụ hiện có chủ yếu là tra cứu (người dùng phải tự nghĩ tới) hoặc cảnh báo ở bước chuyển tiền; chưa có giải pháp can thiệp đúng “khoảng thời gian bị thao túng” và đưa người thân vào quyết định."],
  ["Giải pháp", "“Lính gác” chạy quy tắc tất định trên điện thoại Android và 5 tác tử AI (Chấm rủi ro, Can thiệp, Xác minh, Hồ sơ vụ việc, Huấn luyện) được điều phối bằng LangGraph, gọi công cụ qua MCP, có điểm dừng chờ con người duyệt."],
  ["Khách hàng", "Gia đình có cha mẹ, ông bà cao tuổi (người trả tiền: con cái 25–45 tuổi); sinh viên; ngân hàng, công ty bảo hiểm, nhà mạng (B2B2C)."],
  ["Mô hình doanh thu", "Freemium: gói Gia đình 49.000 đồng/tháng; phí đối tác B2B2C 5.000 đồng/người dùng hoạt động/tháng kèm phí triển khai; tài trợ/CSR cho chương trình cộng đồng."],
  ["Thị trường", "TAM ≈ 6.300 tỷ đồng/năm; SAM (TP.HCM) ≈ 390 tỷ đồng/năm (giả định, xem Mục 4.1)."],
  ["Mục tiêu đến 27/02/2027", "MVP Android và kênh Zalo cho người giám hộ; 50–100 gia đình thí điểm; ≥ 300 phản hồi khảo sát; ≥ 1 thư ý định hợp tác (LOI)."],
  ["Dự báo tài chính", `Doanh thu ${ty(Y[2027].rev)} – ${ty(Y[2028].rev)} – ${ty(Y[2029].rev)} tỷ đồng (2027–2029); EBITDA dương từ năm 2029 (kịch bản cơ sở).`],
  ["Nhu cầu vốn", `${fmt(M.mvp_total / 1e6, 2)} triệu đồng cho giai đoạn cuộc thi (vốn góp thành viên); 2 tỷ đồng vòng tiền hạt giống dự kiến vào quý II/2027.`],
], [2300, CW - 2300], { boldFirst: true, firstColFill: true }));

// =================================================================== CHUONG 1
const c1 = [];
c1.push(H1("CHƯƠNG 1. Ý TƯỞNG DỰ ÁN"));
c1.push(H2("1.1. Bối cảnh: lừa đảo trực tuyến đe dọa mọi gia đình"));
c1.push(P("Theo Bộ Công an, thiệt hại do lừa đảo trực tuyến tại Việt Nam năm 2025 lên tới hơn 8.000 tỷ đồng {{vov8000}}; khảo sát 60.300 người dùng của Hiệp hội An ninh mạng quốc gia ước tính thiệt hại hơn 6.000 tỷ đồng chỉ trong 11 tháng đầu năm 2025 {{nca}}. Cộng dồn giai đoạn 2020–2025, cả nước ghi nhận 24.295 vụ với thiệt hại gần 40.000 tỷ đồng {{tt40000}}. Khảo sát của Liên minh Chống lừa đảo toàn cầu (GASA) cho thấy khoảng 20% người Việt gặp lừa đảo hằng ngày, cao nhất khu vực Đông Nam Á {{gasa}}."));
c1.push(P("Các nguồn số liệu về xu hướng chưa hoàn toàn thống nhất: Cục An ninh mạng và phòng, chống tội phạm sử dụng công nghệ cao ghi nhận số vụ 8 tháng đầu năm 2025 tăng 65% so với cùng kỳ {{tn65}}, trong khi Hiệp hội An ninh mạng quốc gia ghi nhận tỷ lệ người dùng trở thành nạn nhân giảm từ 0,45% (2024) xuống 0,18% (2025). Điểm chung là chỉ 32,12% nạn nhân trình báo cơ quan chức năng {{hp}} – quy mô thực tế còn lớn hơn số liệu chính thức."));
c1.push(statStrip([
  ["8.000+ tỷ", "đồng thiệt hại do lừa đảo trực tuyến năm 2025 {{vov8000}}"],
  ["Số 1", "thủ đoạn: giả danh công an, cơ quan chức năng {{nca}}"],
  ["50%", "vụ có nạn nhân cao tuổi xuất phát từ nỗi sợ liên lụy con cháu {{vnp}}"],
  ["32%", "nạn nhân trình báo cơ quan chức năng {{hp}}"],
]));
c1.push(gap(160));
c1.push(H2("1.2. Vấn đề cốt lõi: khoảng thời gian bị thao túng không có ai bên cạnh"));
c1.push(P("Kịch bản lừa đảo phổ biến nhất hiện nay rất quen thuộc: kẻ gian gọi điện xưng là công an, thông báo nạn nhân “liên quan một vụ án”, yêu cầu giữ bí mật với gia đình, rồi hướng dẫn chuyển tiền “để xác minh” hoặc cài một ứng dụng giả. Công an TP.HCM cho biết 50% vụ có nạn nhân cao tuổi xuất phát từ nỗi sợ liên lụy con cháu và việc thiếu hiểu biết công nghệ; cả nước hiện có khoảng 16,1 triệu người cao tuổi {{vnp}}."));
c1.push(P("Những vụ được ngăn chặn kịp thời gần đây đều nhờ con người. Ngày 30/09/2026, nhân viên Agribank nhận thấy một khách hàng rút hơn 1 tỷ đồng với thái độ bất thường theo kịch bản “công an dặn giữ bí mật” và đã báo công an {{tt_agri}}. Tại Hà Tĩnh tháng 9/2026, cảnh báo của ngân hàng giữ lại được khoản tiết kiệm hơn 1 tỷ đồng, nhưng một cụ bà sinh năm 1958 vẫn mất 4 chỉ vàng {{cand}}. Khi giao dịch diễn ra trên ứng dụng di động, không còn “giao dịch viên tinh ý” nào nhìn thấy nỗi sợ của khách hàng."));
c1.push(P("Sinh viên cũng là nạn nhân. Công an TP.HCM, thông qua Sở Giáo dục và Đào tạo, đã cảnh báo 168 phường, xã và khoảng 3.500 trường học về thủ đoạn giả bạn học để lấy số điện thoại rồi giả danh công an gọi cho học sinh {{tn_sv}}; một đường dây “việc nhẹ lương cao” đặt tại Lào đã chiếm đoạt hơn 1.500 tỷ đồng của hàng nghìn người Việt từ đầu năm 2026 {{tt_lao}}."));
c1.push(callout("Vấn đề cốt lõi", ["Trong khoảng thời gian từ lúc nhận cuộc gọi đến lúc bấm chuyển tiền, nạn nhân bị cô lập: kẻ gian cố tình cắt đứt họ khỏi người thân, còn các lớp bảo vệ hiện có hoặc chưa được kích hoạt (người dùng phải tự tra cứu), hoặc đến quá muộn (chỉ cảnh báo ở bước chuyển tiền với tài khoản đã bị gắn cờ)."]));
c1.push(gap(160));
c1.push(H2("1.3. Thấu hiểu người dùng"));
c1.push(P("Từ việc phân tích các vụ việc được báo chí ghi nhận và trao đổi sơ bộ với gia đình sinh viên, nhóm rút ra bốn nhận định về người dùng:", { keepNext: true }));
c1.push(...bullets([
  "**Người cao tuổi** không thiếu thông tin cảnh báo mà thiếu một “điểm dừng” đúng lúc. Khi bị dọa, họ hoảng sợ và làm theo chỉ dẫn; họ tin con cháu hơn bất kỳ ứng dụng nào.",
  "**Con cái** lo cho cha mẹ nhưng không thể túc trực. Điều họ cần là được báo ngay khi có dấu hiệu bất thường, kèm đủ thông tin để quyết định nhanh, thay vì phát hiện khi tiền đã mất.",
  "**Sinh viên** tự tin về công nghệ nhưng vẫn mắc bẫy việc làm online, giả danh công an, vay qua ứng dụng; đồng thời họ chính là người có thể “lắp lá chắn” cho cha mẹ.",
  "**Ngân hàng** đã đầu tư mạnh vào chống gian lận – ACB chặn hơn 20.000 giao dịch gian lận, bảo vệ khoảng 1.500 tỷ đồng chỉ trong 6 tháng đầu năm 2025 {{tn_acb}} – nhưng chỉ nhìn thấy giao dịch, không nhìn thấy cuộc gọi thao túng diễn ra trước đó.",
]));
c1.push(P("Insight trung tâm của dự án: **kẻ gian thắng khi nạn nhân ở một mình; HỏiCon thắng bằng cách đưa gia đình trở lại cuộc trò chuyện.** Các chuyên gia cũng khuyến nghị mỗi gia đình nên có một “mật khẩu gia đình” và luôn gọi lại cho người thân qua số đã biết {{vnp}} – HỏiCon biến lời khuyên này thành một quy trình tự động.", { before: 80 }));
c1.push(H2("1.4. Ý tưởng HỏiCon"));
c1.push(P("HỏiCon là hệ thống trợ lý Agentic AI chống lừa đảo lấy gia đình làm trung tâm, gồm ba thành phần: (1) **ứng dụng HỏiCon** trên điện thoại Android của người được bảo vệ, chạy “Lính gác” – bộ quy tắc tất định nhận biết chuỗi hành vi rủi ro; (2) **kênh HỏiCon Gia đình** trên Zalo cho người giám hộ (con, cháu); (3) **máy chủ HỏiCon** với 5 tác tử AI phối hợp, có bộ nhớ dài hạn và điểm dừng chờ con người duyệt."));
c1.push(P("Nguyên lý hoạt động là vòng lặp **Dừng – Hỏi – Báo – Xác minh – Xử lý hậu quả**, kèm huấn luyện định kỳ. Hệ thống không ghi âm cuộc gọi, không đọc nội dung giao dịch và không bao giờ tự thao tác thay người dùng trên điện thoại; mọi quyết định có hệ quả đều do con người đưa ra. Hình 1 minh họa cách HỏiCon xử lý một cuộc gọi giả danh công an."));
c1.push(...figure("fig_journey.png", "Hành trình HỏiCon xử lý một cuộc gọi giả danh công an (kịch bản minh họa)"));
c1.push(H2("1.5. Vì sao là bây giờ"));
c1.push(P("Thời điểm triển khai HỏiCon trùng với một loạt thay đổi về pháp lý, công nghệ và hành vi tội phạm trong giai đoạn 2025–2027:", { keepNext: true }));
c1.push(tcap("Các mốc tạo nên “cửa sổ cơ hội” cho HỏiCon"));
c1.push(table(["Thời điểm", "Sự kiện", "Ý nghĩa với HỏiCon"], [
  ["01/04/2025", "BIDV thí điểm cảnh báo khách hàng chuyển tiền tới tài khoản nghi lừa đảo trong cơ sở dữ liệu SIMO, giữ lại hơn 100 tỷ đồng; các ngân hàng lớn triển khai tiếp trong tháng 6–7/2025 {{tn_simo}}", "Ngân hàng chỉ chặn được ở bước chuyển tiền và với tài khoản đã bị gắn cờ"],
  ["01/01/2026", "Tài khoản chưa cập nhật CCCD gắn chip/VNeID hoặc sinh trắc học bị ngừng chuyển tiền, rút tiền, thanh toán {{vtv}}", "Tài khoản “ma” khó dùng hơn, kẻ gian chuyển sang thao túng chính chủ tài khoản"],
  ["01/01/2026", "Luật Bảo vệ dữ liệu cá nhân số 91/2025/QH15 và Nghị định 356/2025/NĐ-CP có hiệu lực {{frasers}}", "Thiết kế bảo vệ quyền riêng tư ngay từ đầu trở thành lợi thế cạnh tranh"],
  ["01/03/2026", "Luật Trí tuệ nhân tạo số 134/2025/QH15 có hiệu lực; người dùng phải nhận biết được khi tương tác với AI {{ailaw}}", "Khung pháp lý rõ ràng cho sản phẩm AI tương tác với người dân"],
  ["23/06/2026", "ACB cảnh báo 30 kịch bản lừa đảo, trong đó có “cuộc gọi im lặng” để thu mẫu giọng làm deepfake người thân {{tn_acb30}}", "Cần lớp xác minh dựa trên quan hệ gia đình (mật khẩu gia đình, gọi lại số đã lưu)"],
  ["01/07/2026", "Quy định xử phạt mới về SIM không chính chủ và Luật An ninh mạng sửa đổi có hiệu lực {{tn_sim}}{{vov_vneid}}", "Danh tính được siết chặt, nhưng chuyên gia nhận định xác thực danh tính “không phải thuốc chữa bách bệnh” {{vov_vneid}}"],
  ["03/07/2026", "iOS 27 bổ sung tín hiệu cảnh báo rủi ro; tính năng phát hiện lừa đảo trong cuộc gọi của Google Pixel chưa có tại Việt Nam {{tn_ios27}}{{tn_pixel}}", "Các hãng bắt đầu vào cuộc nhưng chưa có giải pháp tiếng Việt lấy gia đình làm trung tâm"],
  ["19/08/2026", "Nghị định 330/2026/NĐ-CP: xử lý dữ liệu cá nhân không có sự đồng ý hoặc không lưu nhật ký đồng ý bị phạt 30–50 triệu đồng {{nd330}}", "Nhật ký đồng ý là tính năng bắt buộc của HỏiCon"],
  ["26/08/2026", "Google.org tài trợ 5 triệu USD cho chương trình Scam Ready ASEAN 2025–2027; dự án Chống Lừa Đảo là đối tác triển khai tại Việt Nam {{tn_google}}", "Hệ sinh thái chống lừa đảo có nguồn lực và sẵn sàng hợp tác"],
  ["01/01/2027 (dự kiến)", "Dự thảo nghị định mới về chống tin nhắn, cuộc gọi rác, mở rộng phạm vi sang ứng dụng OTT {{vne_spam}}", "HỏiCon chỉ gửi tin nhắn giao dịch theo sự đồng ý, không tiếp thị tự động"],
  ["27/02/2027", "Vòng chung kết diễn ra ngay sau Tết Nguyên đán – dịp Bộ Công an từng phát cảnh báo lừa đảo {{vov_tet}}", "Sản phẩm ra mắt đúng thời điểm nhu cầu cao"],
], [1650, 4221, 3200], { boldFirst: true, keep: false }));

// =================================================================== CHUONG 2
const c2 = [];
c2.push(H1("CHƯƠNG 2. MỤC TIÊU VÀ GIÁ TRỊ CỦA DỰ ÁN"));
c2.push(H2("2.1. Tầm nhìn và sứ mệnh"));
c2.push(...bullets([
  "**Tầm nhìn:** trở thành “lớp an toàn gia đình” của người Việt trên không gian số – nơi không ai phải một mình đối mặt với kẻ lừa đảo.",
  "**Sứ mệnh:** ứng dụng Agentic AI tiếng Việt để tạo ra khoảng dừng đúng lúc, đưa người thân vào quyết định và giảm thiệt hại do lừa đảo cho người cao tuổi, sinh viên và các gia đình.",
]));
c2.push(H2("2.2. Mục tiêu cụ thể"));
c2.push(tcap("Mục tiêu theo từng giai đoạn"));
c2.push(table(["Giai đoạn", "Mục tiêu", "Chỉ số đo lường"], [
  ["Đến 15/11/2026 (Vòng 1)", "Hoàn thiện thuyết minh và video 3 phút; khảo sát và phỏng vấn người dùng; tuyển gia đình thí điểm", "≥ 300 phản hồi khảo sát; 15 cuộc phỏng vấn sâu; ≥ 100 gia đình đăng ký thí điểm"],
  ["Đến 10/01/2027 (Vòng 2)", "MVP Android, kênh Zalo cho người giám hộ và đủ 5 tác tử; thí điểm thực tế; bộ đánh giá", "50–100 gia đình thí điểm; bộ đánh giá ≥ 100 kịch bản tiếng Việt; ≥ 1 LOI"],
  ["Đến 27/02/2027 (Chung kết)", "Báo cáo kết quả thí điểm; chiến dịch “Tết này, hỏi con trước khi chuyển tiền”", "Số liệu hiệu quả thí điểm; lượt tiếp cận chiến dịch"],
  ["Năm 2027", "Thành lập công ty (quý II); phát hành Android tại TP.HCM; thí điểm B2B2C", "15.000 gia đình sử dụng, 600 gia đình trả phí; 1 đối tác"],
  ["Năm 2028", "Mở rộng Hà Nội, Đà Nẵng, Cần Thơ; phiên bản iOS rút gọn", "60.000 gia đình, 3.000 trả phí; 2 đối tác"],
  ["Năm 2029", "Phủ sóng toàn quốc; tự chủ tài chính", "150.000 gia đình, 7.500 trả phí; 3 đối tác; EBITDA dương"],
], [2300, 3671, 3100], { boldFirst: true }));
c2.push(H2("2.3. Giá trị mang lại cho từng bên"));
c2.push(tcap("Giá trị HỏiCon mang lại"));
c2.push(table(["Đối tượng", "Giá trị"], [
  ["Người cao tuổi", "Được bảo vệ đúng lúc mà không cần thao tác phức tạp: một nút “Hỏi con” và lời nhắc bằng giọng nói tiếng Việt; tự tin hơn khi dùng ngân hàng số."],
  ["Con cái (người giám hộ)", "Biết ngay khi cha mẹ gặp rủi ro, có tóm tắt và bằng chứng để quyết định trong khoảng 30 giây; yên tâm khi ở xa."],
  ["Sinh viên", "“Chế độ sinh viên” chống việc nhẹ lương cao, giả danh công an, vay qua ứng dụng; đồng thời là người kích hoạt lá chắn cho cả nhà."],
  ["Ngân hàng, bảo hiểm, nhà mạng", "Giảm tổn thất và khiếu nại do lừa đảo, tăng niềm tin của khách hàng cao tuổi, bổ sung lớp phòng vệ “trước giao dịch” mà hệ thống của họ không nhìn thấy."],
  ["Xã hội", "Giảm dòng tiền chảy vào tội phạm; nâng năng lực an toàn số cho người cao tuổi; bổ trợ cho nỗ lực của cơ quan chức năng."],
], [2600, CW - 2600], { boldFirst: true, firstColFill: true }));
c2.push(H2("2.4. Chỉ số tác động xã hội"));
c2.push(P("Bên cạnh chỉ số kinh doanh, HỏiCon đo lường và công bố định kỳ các chỉ số tác động sau:", { keepNext: true }));
c2.push(...bullets([
  "Số người được bảo vệ (người cao tuổi, sinh viên) và số gia đình tham gia.",
  "Số lần kích hoạt “khoảng dừng an toàn” và số vụ được gia đình xác nhận đã ngăn chặn.",
  "Ước tính số tiền được bảo vệ (do gia đình khai báo, có kiểm chứng ngẫu nhiên).",
  "Tỷ lệ vượt qua bài diễn tập lừa đảo trước và sau 4 tuần sử dụng.",
  "Số người tham gia các buổi hướng dẫn tại cộng đồng.",
]));
c2.push(P("Dự án đóng góp vào Mục tiêu Phát triển bền vững số 16 (giảm tội phạm có tổ chức và dòng tiền bất hợp pháp) và số 10 (thúc đẩy sự hòa nhập của mọi người, không phân biệt tuổi tác).", { before: 80 }));

// =================================================================== CHUONG 3
const c3 = [];
c3.push(H1("CHƯƠNG 3. MÔ TẢ SẢN PHẨM"));
c3.push(H2("3.1. Tổng quan sản phẩm"));
c3.push(tcap("Ba thành phần của HỏiCon"));
c3.push(table(["Thành phần", "Người dùng", "Nền tảng", "Vai trò"], [
  ["Ứng dụng HỏiCon (Lính gác)", "Người được bảo vệ: cha mẹ, ông bà, sinh viên", "Android; bản iOS rút gọn từ 2028", "Gắn nhãn cuộc gọi, phát hiện chuỗi hành vi rủi ro, khoảng dừng an toàn, nút “Hỏi con”, kiểm tra số/link/QR"],
  ["HỏiCon Gia đình", "Người giám hộ: con, cháu", "Zalo (Bot Platform ở giai đoạn MVP, Official Account khi có pháp nhân) và trang web", "Nhận cảnh báo, xem tóm tắt và bằng chứng, ra quyết định, quản lý thành viên, báo cáo an toàn hằng tháng"],
  ["Máy chủ HỏiCon", "Hệ thống", "Điện toán đám mây", "5 tác tử AI, bộ nhớ dài hạn, công cụ, rào chắn, ghi vết và bộ đánh giá"],
], [2050, 2200, 2200, 2621], { boldFirst: true }));
c3.push(H2("3.2. Tính năng chính"));
c3.push(tcap("Danh sách tính năng và gói dịch vụ"));
c3.push(table(["#", "Tính năng", "Mô tả", "Gói"], [
  ["1", "Gắn nhãn cuộc gọi lạ", "Hiển thị “Số lạ – hãy cẩn trọng” hoặc “Nghi lừa đảo” dựa trên danh bạ tin cậy và dữ liệu cảnh báo", "Cơ bản"],
  ["2", "Nút “Hỏi con”", "Một chạm gửi cảnh báo kèm bối cảnh cho người giám hộ qua Zalo", "Cơ bản"],
  ["3", "Kiểm tra số, link, QR, tài khoản", "Người dùng chia sẻ hoặc chụp để tác tử Xác minh tra cứu", "Cơ bản (giới hạn lượt)"],
  ["4", "Mật khẩu gia đình", "Mã bí mật để xác minh người thân khi nghi bị giả giọng (deepfake)", "Cơ bản"],
  ["5", "Chế độ sinh viên", "Kịch bản riêng cho việc làm online, giả danh công an, vay qua ứng dụng", "Cơ bản"],
  ["6", "Khoảng dừng an toàn tự động", "Tự kích hoạt khi phát hiện chuỗi hành vi rủi ro; lời nhắc bằng giọng nói tiếng Việt, hỏi mật khẩu gia đình", "Gia đình"],
  ["7", "Chấm rủi ro và báo con có tóm tắt", "Hỏi nhanh 2–3 câu, chấm mức rủi ro, gửi tóm tắt, bằng chứng và nút hành động", "Gia đình"],
  ["8", "Xác minh chủ động", "Tra cứu dữ liệu đối tác, gọi lại người thân qua số đã lưu, đối chiếu quy tắc chính thức", "Gia đình"],
  ["9", "Hồ sơ vụ việc", "Soạn đơn trình báo, kịch bản gọi ngân hàng phong tỏa tài khoản, lưu bằng chứng, cảnh báo lừa “lấy lại tiền”", "Gia đình"],
  ["10", "Diễn tập và huấn luyện", "Diễn tập lừa đảo an toàn hằng tuần theo thủ đoạn mới; bài học 1 phút bằng giọng nói", "Gia đình"],
  ["11", "Báo cáo an toàn hằng tháng", "Tổng hợp sự kiện, kết quả diễn tập, khuyến nghị cho từng thành viên", "Gia đình"],
  ["12", "Bảng điều khiển đối tác", "Thống kê ẩn danh, tích hợp kênh ngân hàng/bảo hiểm (đồng thương hiệu)", "Đối tác"],
], [500, 2400, 4471, 1700], { centerCols: [0], keep: false }));
c3.push(H2("3.3. Hành trình sử dụng tiêu biểu"));
c3.push(P("**Thiết lập (khoảng 10 phút).** Anh Minh cài HỏiCon cho mẹ là bà Lan. Ứng dụng xin từng quyền kèm giải thích bằng giọng nói (“HỏiCon không ghi âm cuộc gọi và không đọc giao dịch của bác”), cả nhà thống nhất một mật khẩu gia đình, anh Minh kết nối kênh HỏiCon Gia đình trên Zalo và trở thành người giám hộ."));
c3.push(P("**Khi có cuộc gọi lừa đảo.** Một số lạ gọi cho bà Lan, xưng là công an và yêu cầu chuyển tiền “để xác minh”. Khi bà mở ứng dụng ngân hàng trong lúc vẫn đang nghe máy, Lính gác bật khoảng dừng an toàn: “Đây là trợ lý AI HỏiCon. Công an không yêu cầu chuyển tiền qua điện thoại. Bác hãy hỏi con trước nhé.” Tác tử Chấm rủi ro hỏi bà 2–3 câu ngắn, đánh giá rủi ro CAO; tác tử Can thiệp gửi cho anh Minh tin Zalo kèm tóm tắt và các nút [Gọi mẹ] [Xác minh] [Cho phép tiếp tục]. Tác tử Xác minh phát hiện số gọi đến nằm trong dữ liệu cảnh báo; anh Minh gọi lại cho mẹ và giao dịch dừng lại."));
c3.push(P("**Sau sự việc.** Nếu tiền đã bị chuyển, tác tử Hồ sơ vụ việc lập dòng thời gian, soạn đơn trình báo, hướng dẫn gọi tổng đài ngân hàng để phong tỏa và cảnh báo các trang giả mạo “hỗ trợ lấy lại tiền” {{kenh14}}. Tuần sau, tác tử Huấn luyện tạo một bài diễn tập dựa đúng trên chiêu thức vừa gặp."));
c3.push(H2("3.4. Kiến trúc Agentic AI"));
c3.push(P("HỏiCon tách bạch hai lớp. **Trên điện thoại**, Lính gác chỉ chạy quy tắc tất định, minh bạch, phù hợp chính sách của Google Play (cấm tự động hóa phi tất định thông qua Accessibility {{gp_acc}}). **Trên máy chủ**, 5 tác tử AI được điều phối bằng LangGraph – khung hỗ trợ lưu trạng thái và điểm dừng chờ con người duyệt – gọi công cụ thông qua giao thức MCP, dùng chung bộ nhớ dài hạn và lớp rào chắn, giám sát (Hình 2)."));
c3.push(...figure("fig_arch.png", "Kiến trúc hệ đa tác tử của HỏiCon"));
c3.push(tcap("Nhiệm vụ của từng tác tử"));
c3.push(table(["Tác tử", "Nhiệm vụ tự động", "Công cụ, dữ liệu", "Điểm con người duyệt"], [
  ["Lính gác (trên máy)", "Gắn nhãn cuộc gọi; phát hiện chuỗi rủi ro “đang nghe số lạ → mở ứng dụng ngân hàng” hoặc “cài ứng dụng lạ ngay sau cuộc gọi”; kích hoạt khoảng dừng", "CallScreeningService (không truy cập âm thanh cuộc gọi) {{and_csr}}; quyền truy cập dữ liệu sử dụng ứng dụng do người dùng cấp; danh sách số cảnh báo", "Không cần – quy tắc cố định, có thể giải thích"],
  ["1. Chấm rủi ro", "Hỏi 2–3 câu bằng giọng nói; đối chiếu bộ nhớ; chấm điểm theo các dấu hiệu: xưng cơ quan chức năng, đòi giữ bí mật, thúc ép thời gian, đòi chuyển tiền hoặc cài ứng dụng", "LLM gọi hàm; nhận dạng giọng nói tiếng Việt; bộ nhớ dài hạn", "—"],
  ["2. Can thiệp", "Chọn mức can thiệp (nhắc nhẹ, khoảng dừng, báo khẩn); soạn lời nhắc cá nhân hóa; gửi cảnh báo kèm tóm tắt, mức rủi ro và nút hành động", "Tổng hợp giọng nói tiếng Việt; Zalo, tin mẫu ZBS", "Người giám hộ quyết định bước tiếp theo"],
  ["3. Xác minh", "Tra cứu số điện thoại, đường link, mã QR, số tài khoản; gọi lại người thân qua số đã lưu; đối chiếu quy tắc chính thức (ví dụ: cuộc gọi thật của Thuế TP.HCM hiển thị tên “Thue TP.HCM” {{tn_thue}})", "Dữ liệu cảnh báo của đối tác; kho quy tắc chính thức", "—"],
  ["4. Hồ sơ vụ việc", "Lập dòng thời gian, soạn đơn trình báo, kịch bản gọi tổng đài ngân hàng, nhắc khóa tài khoản; cảnh báo lừa đảo “lấy lại tiền”", "Mẫu văn bản; kho bằng chứng", "Gia đình xác nhận trước khi gửi"],
  ["5. Huấn luyện", "Theo dõi thủ đoạn mới từ cảnh báo chính thức; tạo bài diễn tập cá nhân hóa hằng tuần; ghi kết quả vào bộ nhớ", "Kho kịch bản; lịch", "Gia đình chọn lịch diễn tập"],
], [1650, 3171, 2450, 1800], { boldFirst: true, keep: false }));
c3.push(P("**Điều phối và định tuyến mô hình.** Bộ điều phối lập kế hoạch từng bước, lưu trạng thái (để không mất ngữ cảnh khi mất mạng) và tạm dừng chờ duyệt ở các bước có hệ quả. Mô hình ngôn ngữ nhỏ xử lý các bước thường xuyên để giảm chi phí và độ trễ; mô hình lớn chỉ được dùng cho bước xác minh và soạn hồ sơ phức tạp.", { before: 120 }));
c3.push(P("**Rào chắn và giám sát.** Dữ liệu định danh được ẩn danh hóa trước khi gửi tới mô hình ngôn ngữ; mọi nội dung do kẻ gian cung cấp (tin nhắn, đường link) được coi là dữ liệu không tin cậy để chống tấn công chèn lệnh; mỗi công cụ được phân mức rủi ro; HỏiCon không bao giờ gửi đường link qua SMS. Mỗi lượt chạy đều được ghi vết (trace) và hệ thống được kiểm thử bằng bộ đánh giá ≥ 100 kịch bản lừa đảo tiếng Việt (giả danh công an, thuế, điện lực, deepfake người thân, việc làm online, “lấy lại tiền”, “hỗ trợ cài VNeID”…), đo tỷ lệ phát hiện, tỷ lệ báo nhầm, thời gian người giám hộ phản hồi, độ trễ và chi phí mỗi tác vụ."));
c3.push(H2("3.5. Vì sao HỏiCon là Agentic AI thực thụ"));
c3.push(P(`OpenAI định nghĩa: ứng dụng có LLM nhưng không để LLM điều khiển việc thực thi quy trình – như chatbot hay LLM một lượt – thì không phải tác tử; tác tử thật tự chọn công cụ để thu thập ngữ cảnh và hành động, nhận biết khi nào hoàn thành, tự sửa sai và trả quyền cho con người khi cần, luôn trong giới hạn an toàn rõ ràng {{oai_guide}}. Anthropic khuyến nghị bắt đầu từ thiết kế đơn giản và chỉ tăng độ phức tạp khi chứng minh được hiệu quả {{anth}}. Bảng ${tableNo + 1} đối chiếu HỏiCon với các tiêu chí này.`, { keepNext: true }));
c3.push(tcap("Đối chiếu HỏiCon với tiêu chí của một hệ Agentic AI"));
c3.push(table(["Tiêu chí", "HỏiCon đáp ứng như thế nào"], [
  ["LLM điều khiển quy trình, tự chọn công cụ", "Tác tử Chấm rủi ro tự quyết định hỏi thêm câu nào, tra cứu gì, có cần báo con hay không – không phải luồng kịch bản cố định"],
  ["Công cụ tác động vào hệ thống thật", "Gửi tin Zalo, kích hoạt khoảng dừng trên thiết bị, tạo hồ sơ vụ việc, đặt lịch diễn tập"],
  ["Vòng lập kế hoạch – hành động – kiểm chứng", "Chấm rủi ro → can thiệp → xác minh → cập nhật mức rủi ro → đóng sự kiện hoặc chuyển hồ sơ"],
  ["Bộ nhớ qua nhiều phiên", "Danh bạ tin cậy, mật khẩu gia đình, lịch sử sự kiện, kết quả diễn tập"],
  ["Con người duyệt hành động rủi ro cao", "Mọi quyết định cho phép giao dịch, gửi đơn trình báo đều do người giám hộ hoặc gia đình xác nhận"],
  ["Ghi vết và đánh giá", "Trace từng lượt chạy; bộ đánh giá ≥ 100 kịch bản tiếng Việt; công bố tỷ lệ phát hiện và báo nhầm. Khảo sát của LangChain cho thấy 94% đội đã đưa tác tử vào vận hành có công cụ quan sát {{lc}}"],
  ["Rào chắn và công khai AI", "Ẩn danh hóa, chống chèn lệnh; câu mở đầu “Đây là trợ lý AI HỏiCon” theo yêu cầu minh bạch của Luật Trí tuệ nhân tạo {{ailaw}}"],
], [3000, CW - 3000], { boldFirst: true, firstColFill: true }));
c3.push(H2("3.6. Tính cần thiết"));
c3.push(P("Thiệt hại hàng nghìn tỷ đồng mỗi năm, thủ đoạn nhắm thẳng vào nỗi sợ và sự cô lập của nạn nhân, trong khi các lớp bảo vệ hiện có đều đứng ngoài “khoảng thời gian bị thao túng”. Nhu cầu học cách phòng tránh rất lớn – người dân từng xếp hàng hàng giờ để tham gia một hoạt động học chống lừa đảo {{tn_queue}} – nhưng kiến thức chỉ phát huy tác dụng nếu được nhắc đúng lúc. HỏiCon lấp đúng khoảng trống đó và biến lời khuyên “hãy hỏi người thân trước khi chuyển tiền” thành một quy trình tự động, đo lường được."));
c3.push(H2("3.7. Tính khả thi"));
c3.push(tcap("Căn cứ khả thi của dự án"));
c3.push(table(["Khía cạnh", "Căn cứ"], [
  ["Kỹ thuật", ["Android cung cấp CallScreeningService để gắn nhãn, chặn cuộc gọi mà không cần truy cập âm thanh {{and_csr}}; quyền SMS và nhật ký cuộc gọi chỉ cấp cho ngoại lệ được Google Play duyệt {{gp_sms}} nên MVP không sử dụng.", "iOS hỗ trợ gắn nhãn, chặn số qua Call Directory {{apple_cd}}.", "Khung tác tử (LangGraph), giao thức MCP và mô hình ngôn ngữ hỗ trợ tiếng Việt đều đã sẵn sàng."]],
  ["Tích hợp", "Zalo Bot Platform có gói miễn phí và hỗ trợ kết nối tác tử AI {{zbot}}; Zalo OA gói Growth 2,5 triệu đồng/năm khi có pháp nhân {{zalo_oa}}; tin mẫu ZBS 200–300 đồng/tin {{zbs}}."],
  ["Chi phí vận hành", "Chi phí AI và tin nhắn ước tính khoảng 6.000 đồng/gia đình trả phí/tháng dựa trên bảng giá công khai {{gemini}}{{claude}}{{zbs}}, thấp hơn nhiều so với giá bán 49.000 đồng."],
  ["Nhân lực", "Đội 5 người với 3 thành viên CNTT (Android; backend – tác tử AI; dữ liệu – bảo mật) đủ năng lực xây MVP trong 7 tuần, có cố vấn chuyên môn đồng hành."],
  ["Thí điểm", "50–100 gia đình của sinh viên TDTU, tuyển ngay từ khảo sát Vòng 1; hiệu quả được đo bằng các buổi diễn tập lừa đảo an toàn thay vì chờ kẻ gian gọi thật."],
  ["Pháp lý", "Thiết kế tuân thủ Luật Trí tuệ nhân tạo, Luật Bảo vệ dữ liệu cá nhân và chính sách nền tảng (Mục 3.8)."],
], [2000, CW - 2000], { boldFirst: true, firstColFill: true }));
c3.push(H2("3.8. Bảo mật, quyền riêng tư và tuân thủ pháp luật"));
c3.push(P("Nguyên tắc của HỏiCon: **bảo vệ gia đình không được đánh đổi bằng quyền riêng tư.** Cụ thể:", { keepNext: true }));
c3.push(...bullets([
  "Không ghi âm, không truy cập âm thanh cuộc gọi; không đọc nội dung tin nhắn, giao dịch hay số dư.",
  "Chỉ xử lý siêu dữ liệu tối thiểu (số gọi đến có trong danh bạ hay không, thời lượng, ứng dụng ngân hàng có được mở trong lúc gọi hay không); dữ liệu nhạy cảm được ẩn danh hóa trước khi gửi tới mô hình ngôn ngữ.",
  "Từng quyền được xin riêng, có giải thích rõ ràng; nhật ký đồng ý được lưu đầy đủ; người dùng có thể rút lại đồng ý bất kỳ lúc nào.",
  "Người được bảo vệ chủ động chọn người giám hộ; không có chế độ “theo dõi ngầm”.",
  "Không bao giờ gửi đường link qua SMS; chỉ liên lạc qua kênh Zalo đã xác thực – để kẻ gian không thể mạo danh HỏiCon.",
  "Áp dụng đầy đủ nghĩa vụ của Luật Bảo vệ dữ liệu cá nhân ngay từ đầu (đánh giá tác động, người phụ trách bảo vệ dữ liệu, quy trình thông báo vi phạm) thay vì dựa vào quy định miễn trừ cho doanh nghiệp khởi nghiệp {{frasers}}.",
]));
c3.push(tcap("Đối chiếu yêu cầu pháp lý và thiết kế của HỏiCon"));
c3.push(table(["Quy định", "Yêu cầu chính", "Thiết kế của HỏiCon"], [
  ["Luật Trí tuệ nhân tạo 134/2025/QH15 (hiệu lực 01/03/2026) {{ailaw}}", "Tự phân loại rủi ro; người dùng phải nhận biết khi tương tác với AI; giám sát của con người", "Dự kiến tự phân loại thận trọng ở mức rủi ro trung bình và thực hiện thông báo theo quy định; câu mở đầu “Đây là trợ lý AI HỏiCon”; con người duyệt các quyết định quan trọng; lưu nhật ký hoạt động"],
  ["Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15 và Nghị định 356/2025/NĐ-CP (01/01/2026) {{frasers}}", "Đồng ý rõ ràng, tối thiểu hóa dữ liệu; nghĩa vụ riêng với dữ liệu nhạy cảm và chuyển dữ liệu ra nước ngoài", "Đồng ý theo từng quyền; tối thiểu hóa; lưu dữ liệu định danh trên hạ tầng đặt tại Việt Nam; lập hồ sơ theo quy định khi sử dụng dịch vụ ở nước ngoài"],
  ["Nghị định 330/2026/NĐ-CP (19/08/2026) {{nd330}}", "Phạt 30–50 triệu đồng khi xử lý dữ liệu không có đồng ý hoặc không lưu nhật ký đồng ý", "Nhật ký đồng ý là tính năng bắt buộc, có thể xuất trình khi được yêu cầu"],
  ["Dự thảo nghị định chống tin nhắn, cuộc gọi rác (dự kiến 01/01/2027) {{vne_spam}}", "Kiểm soát tin nhắn, cuộc gọi tiếp thị; mở rộng sang ứng dụng OTT", "Chỉ gửi tin nhắn giao dịch theo sự đồng ý; không tiếp thị qua tin nhắn hay cuộc gọi tự động"],
  ["Chính sách Google Play về SMS, nhật ký cuộc gọi và Accessibility {{gp_sms}}{{gp_acc}}", "Hạn chế quyền nhạy cảm; cấm tự động hóa phi tất định", "Không xin quyền SMS, nhật ký cuộc gọi, Accessibility ở MVP; quy tắc tất định; công bố nổi bật mục đích từng quyền"],
], [2700, 2800, 3571], { boldFirst: true }));

// =================================================================== CHUONG 4
const c4 = [];
c4.push(H1("CHƯƠNG 4. KHẢO SÁT THỊ TRƯỜNG"));
c4.push(H2("4.1. Quy mô thị trường"));
c4.push(tcap("Ước tính quy mô thị trường"));
c4.push(table(["Tầng", "Cách tính", "Kết quả"], [
  ["TAM – cả nước, B2C", "16,1 triệu người cao tuổi {{vnp}} ÷ 1,5 người/hộ ≈ 10,7 triệu hộ × 588.000 đồng/năm (49.000 đồng/tháng)", "≈ 6.300 tỷ đồng/năm"],
  ["SAM – TP.HCM, B2C", "13,7 triệu dân {{dbnd}} × 12% người cao tuổi ≈ 1,64 triệu người ≈ 1,1 triệu hộ × 60% dùng điện thoại thông minh ≈ 0,66 triệu hộ × 588.000 đồng", "≈ 390 tỷ đồng/năm"],
  ["SOM 2029 – B2C", "7.500 gia đình trả phí (≈ 1,1% số hộ thuộc SAM) × 588.000 đồng", "≈ 4,4 tỷ đồng/năm"],
  ["SOM 2029 – B2B2C", "3 đối tác, bình quân 100.000 người dùng hoạt động × 5.000 đồng × 12 tháng", "≈ 6,0 tỷ đồng/năm"],
], [2200, 5071, 1800], { boldFirst: true, rightCols: [2] }));
c4.push(note("Ghi chú: các hệ số 1,5 người/hộ, 12% và 60% là giả định của nhóm và sẽ được kiểm chứng trong khảo sát Vòng 1; dân số TP.HCM sau hợp nhất (13,7 triệu) là số liệu giai đoạn xây dựng đề án."));
c4.push(P("Một cách nhìn khác về quy mô là **giá trị rủi ro được bảo vệ**: 6.000–8.000 tỷ đồng thiệt hại mỗi năm {{nca}}{{vov8000}}. Với đối tác ngân hàng, bài toán đầu tư rất rõ: ACB chặn hơn 20.000 giao dịch gian lận, bảo vệ khoảng 1.500 tỷ đồng trong 6 tháng đầu năm 2025 {{tn_acb}}, tức bình quân khoảng 75 triệu đồng mỗi giao dịch (tính toán của nhóm). Con số này tương đương phí bảo vệ 1.250 khách hàng trong một năm theo mức 5.000 đồng/người/tháng – chỉ cần ngăn được một vụ lừa đảo trên 1.250 khách hàng mỗi năm là đối tác đã hoàn vốn."));
c4.push(H2("4.2. Khách hàng mục tiêu và chân dung người dùng"));
c4.push(tcap("Chân dung các nhóm khách hàng"));
c4.push(table(["Nhóm", "Chân dung", "Nhu cầu và nỗi đau"], [
  ["Người được bảo vệ – “bà Lan”", "68 tuổi, nghỉ hưu, sống tại TP.HCM; dùng điện thoại Android do con mua, dùng Zalo gọi video với cháu và ứng dụng ngân hàng để nhận tiền, thanh toán", "Sợ “dính líu pháp luật”, ngại làm phiền con; cần thao tác cực đơn giản, giọng nói tiếng Việt và một người tin cậy để hỏi"],
  ["Người giám hộ và người trả tiền – “anh Minh”", "38 tuổi, nhân viên văn phòng, sống riêng, bận rộn; dùng Zalo hằng ngày", "Lo cha mẹ bị lừa sau khi đọc tin tức; sẵn sàng trả một khoản nhỏ hằng tháng để được báo ngay khi có rủi ro"],
  ["Sinh viên – “Thảo”", "20 tuổi, sinh viên năm hai, làm thêm online; quê ở tỉnh", "Từng nhận lời mời “việc nhẹ lương cao”; muốn tự bảo vệ và cài lá chắn cho bố mẹ ở quê"],
  ["Đối tác B2B2C", "Ngân hàng, công ty bảo hiểm, nhà mạng: khối quản trị rủi ro, chăm sóc khách hàng, CSR", "Giảm tổn thất và khiếu nại do lừa đảo; tăng niềm tin của khách hàng cao tuổi; có số liệu tác động để báo cáo"],
], [2300, 3571, 3200], { boldFirst: true, firstColFill: true }));
c4.push(H2("4.3. Xu hướng thị trường"));
c4.push(...bullets([
  "Lừa đảo chuyển dịch từ tài khoản “ma” sang thao túng chính chủ tài khoản sau khi xác thực sinh trắc học được áp dụng {{vtv}}; deepfake giọng người thân và lừa “lấy lại tiền” gia tăng {{tn_acb30}}{{kenh14}}.",
  "Người cao tuổi là mục tiêu của nhiều chiêu thức cùng lúc: giả danh cơ quan pháp luật, người thân gặp nạn, tin nhắn ngân hàng giả, tài khoản người thân bị chiếm đoạt… {{tn_8}}",
  "Nhu cầu học kỹ năng chống lừa đảo lớn {{tn_queue}}; Google.org đầu tư 5 triệu USD cho chương trình Scam Ready ASEAN {{tn_google}}.",
  "Agentic AI bùng nổ: 46% doanh nghiệp Việt Nam được khảo sát dự định triển khai Agentic AI {{vne_ai}}.",
  "Các hãng hệ điều hành bắt đầu tích hợp tính năng chống lừa đảo nhưng chưa bản địa hóa cho tiếng Việt và chưa lấy gia đình làm trung tâm {{tn_pixel}}{{tn_ios27}}.",
]));
c4.push(H2("4.4. Kế hoạch khảo sát sơ cấp"));
c4.push(P("Trong Vòng 1, nhóm thực hiện nghiên cứu sơ cấp để kiểm chứng các giả định cốt lõi (bộ câu hỏi dự thảo tại Phụ lục A):", { keepNext: true }));
c4.push(tcap("Kế hoạch nghiên cứu sơ cấp"));
c4.push(table(["Hoạt động", "Đối tượng", "Quy mô", "Mục đích"], [
  ["Khảo sát trực tuyến", "Sinh viên và người đi làm có cha mẹ từ 55 tuổi", "≥ 300 phản hồi", "Đo mức phổ biến của lừa đảo trong gia đình, hệ điều hành và ứng dụng cha mẹ dùng, mức sẵn lòng chi trả (phương pháp Van Westendorp)"],
  ["Phỏng vấn sâu", "Gia đình (cả cha mẹ và con)", "15 gia đình", "Hiểu hành trình bị thao túng, mức chấp nhận quyền truy cập, trải nghiệm mong muốn"],
  ["Kiểm thử khái niệm", "Người cao tuổi", "20 người", "Thử bản mẫu khoảng dừng an toàn bằng giọng nói: mức dễ hiểu, cảm xúc"],
  ["Phỏng vấn chuyên gia", "Ngân hàng, bảo hiểm, dự án Chống Lừa Đảo, công an phường", "5–8 người", "Kiểm chứng nhu cầu B2B2C, nguồn dữ liệu, quy trình hợp tác"],
], [2000, 2600, 1400, 3071], { boldFirst: true }));
c4.push(P("Các giả thuyết cần kiểm chứng:", { before: 120, keepNext: true }));
c4.push(...bullets([
  "**H1:** ≥ 50% gia đình có người thân từng nhận cuộc gọi lừa đảo trong 12 tháng qua.",
  "**H2:** ≥ 60% cha mẹ của người trả lời dùng điện thoại Android.",
  "**H3:** ≥ 30% con cái sẵn lòng trả 39.000–79.000 đồng/tháng cho gói Gia đình.",
  "**H4:** ≥ 70% người cao tuổi đồng ý cấp quyền khi được giải thích rõ “không ghi âm, không đọc giao dịch”.",
  "**H5:** Đối tác ngân hàng/bảo hiểm sẵn sàng thí điểm nếu có số liệu hiệu quả.",
]));
c4.push(note("Kết quả khảo sát sẽ được cập nhật vào bản thuyết minh hoàn thiện trước hạn nộp Vòng 1 (15/11/2026)."));

// =================================================================== CHUONG 5
const c5 = [];
c5.push(H1("CHƯƠNG 5. PHÂN TÍCH CẠNH TRANH VÀ LỢI THẾ CẠNH TRANH"));
c5.push(H2("5.1. Đối thủ và giải pháp thay thế"));
c5.push(tcap("Các giải pháp hiện có và khoảng trống"));
c5.push(table(["Giải pháp", "Cách tiếp cận", "Khoảng trống so với nhu cầu"], [
  ["nTrust (Hiệp hội An ninh mạng quốc gia)", "Ứng dụng miễn phí tra cứu số điện thoại, tài khoản, đường link, mã QR; chặn số đã biết; cơ sở dữ liệu hơn 1 triệu bản ghi {{vne_ntrust}}", "Người dùng phải tự nghĩ tới việc tra cứu; trên iOS đạt 3,4/5 điểm (250 đánh giá), bản cập nhật gần nhất từ 10/2024 {{appstore}}"],
  ["Chống Lừa Đảo (chongluadao.vn)", "Cổng tra cứu, tiện ích trình duyệt, chatbot AI; API dữ liệu cảnh báo hơn 1 triệu lượt gọi/ngày qua hơn 15 đối tác {{tfgi}}", "Không can thiệp trong lúc bị thao túng – phù hợp làm đối tác dữ liệu hơn là đối thủ"],
  ["Cảnh báo của ngân hàng (SIMO, hệ thống chống gian lận)", "Cảnh báo hoặc chặn khi chuyển tiền tới tài khoản đã bị gắn cờ {{tn_simo}}{{tn_acb}}", "Chỉ hoạt động ở bước chuyển tiền; không thấy cuộc gọi thao túng; không có vai trò của gia đình"],
  ["Tính năng của hệ điều hành (Google, Apple)", "Phát hiện lừa đảo trong cuộc gọi trên Pixel; tín hiệu rủi ro trên iOS 27 {{tn_pixel}}{{tn_ios27}}", "Pixel chưa hỗ trợ tại Việt Nam; tính năng chống mạo danh của iOS 27 mặc định tắt và chỉ chia sẻ mức rủi ro với ứng dụng tương thích {{tn_ios27b}}"],
  ["Aura (Mỹ)", "Gói gia đình chống lừa đảo, cảnh báo giao dịch; 32–50 USD/tháng cho 5 người lớn {{aura}}", "Chưa có tại Việt Nam; giá cao so với thu nhập"],
  ["Apate.ai (Úc)", "Bot AI trò chuyện “câu giờ” kẻ gian, bán cho nhà mạng và ngân hàng {{apate}}", "Hướng tới tổ chức; không trực tiếp bảo vệ người dùng cuối"],
  ["Dự án sinh viên cùng chủ đề", "Guardian – nền tảng an toàn cá nhân (giải Ba TSC 2026) {{sbs}}; CallPeace – trợ lý AI cảnh báo lừa đảo trong cuộc gọi (giải Nhì khối THPT, Hue-ICT Challenge 2026) {{gdtd}}", "Định hướng khác: an toàn cá nhân hoặc giám sát cuộc gọi; HỏiCon tập trung vào vòng phối hợp gia đình, xác minh và xử lý hậu quả"],
], [2300, 3571, 3200], { boldFirst: true, keep: false }));
c5.push(...figure("fig_position.png", "Bản đồ định vị cạnh tranh (đánh giá định tính của nhóm dựa trên mô tả công khai của từng giải pháp)"));
c5.push(H2("5.2. Lợi thế cạnh tranh"));
c5.push(...numbered([
  "**Can thiệp đúng lúc:** HỏiCon hoạt động trong “khoảng thời gian bị thao túng” – giữa cuộc gọi và lệnh chuyển tiền – nơi các giải pháp hiện có chưa với tới.",
  "**Gia đình là trung tâm:** đưa người thân tin cậy vào quyết định – điều kẻ gian sợ nhất.",
  "**Agentic AI thực thụ:** vòng lặp dừng – hỏi – báo – xác minh – xử lý hậu quả – huấn luyện, có bộ nhớ, công cụ và con người duyệt.",
  "**Thuần Việt:** giọng nói tiếng Việt, kho kịch bản lừa đảo Việt Nam cập nhật hằng tuần, kênh Zalo quen thuộc với mọi gia đình.",
  "**Quyền riêng tư từ thiết kế:** không ghi âm, không đọc giao dịch – dễ được gia đình và đối tác chấp nhận.",
  "**Phân phối B2B2C:** đồng hành cùng ngân hàng, bảo hiểm, nhà mạng – những bên chịu thiệt hại trực tiếp từ lừa đảo và có sẵn hàng triệu khách hàng.",
]));
c5.push(H2("5.3. Hào phòng thủ dài hạn"));
c5.push(...bullets([
  "**Dữ liệu:** bộ kịch bản lừa đảo tiếng Việt và bộ đánh giá được cập nhật liên tục từ thực tế vận hành.",
  "**Hiệu ứng mạng lưới gia đình:** mỗi người giám hộ kéo theo nhiều người được bảo vệ; gia đình giới thiệu gia đình.",
  "**Hợp đồng đối tác:** tích hợp sâu vào kênh của ngân hàng, bảo hiểm, nhà mạng tạo chi phí chuyển đổi cao.",
  "**Thương hiệu tin cậy và cộng đồng:** chiến dịch “Mật khẩu gia đình” biến HỏiCon thành một thói quen của gia đình chứ không chỉ là một ứng dụng.",
]));
c5.push(H2("5.4. Phân tích SWOT"));
c5.push(tcap("Ma trận SWOT của HỏiCon"));
const half = Math.floor(CW / 2);
const swotCell = (title, items, fill, color) => new TableCell({
  width: { size: half, type: WidthType.DXA },
  shading: { fill, type: ShadingType.CLEAR, color: "auto" },
  margins: { top: 100, bottom: 100, left: 140, right: 140 }, borders: cellBorders,
  children: [new Paragraph({ children: [new TextRun({ text: title, bold: true, color, size: TSZ + 2, font: FONT })], spacing: { after: 60 } }),
    ...items.map((t) => new Paragraph({ children: inline(t, { size: TSZ }), numbering: { reference: "tbullets", level: 0 }, spacing: { after: 30, line: 264 } }))],
});
c5.push(new Table({
  width: { size: half * 2, type: WidthType.DXA }, columnWidths: [half, half], layout: TableLayoutType.FIXED,
  rows: [
    new TableRow({ cantSplit: true, children: [
      swotCell("ĐIỂM MẠNH (S)", ["Định vị khác biệt: gia đình là trung tâm, can thiệp đúng lúc", "Kiến trúc Agentic AI có ghi vết và bộ đánh giá", "Chi phí vận hành thấp, biên lợi nhuận gộp cao", "Đội ngũ trẻ, hiểu người dùng sinh viên và gia đình"], LIGHT_GR, GREEN),
      swotCell("ĐIỂM YẾU (W)", ["Thương hiệu mới, chưa có dữ liệu hiệu quả thực tế", "Phụ thuộc chính sách của nền tảng Android", "iOS chỉ hỗ trợ một phần tính năng", "Đội ngũ còn là sinh viên, kinh nghiệm bán hàng B2B hạn chế"], LIGHT_OR, ORANGE),
    ] }),
    new TableRow({ cantSplit: true, children: [
      swotCell("CƠ HỘI (O)", ["Thiệt hại lớn, chính sách liên tục siết chặt", "Ngân hàng tăng đầu tư chống gian lận", "Nguồn tài trợ chống lừa đảo (Google.org, CSR)", "Hệ điều hành chưa bản địa hóa tiếng Việt", "Dân số già hóa nhanh"], LIGHT, NAVY),
      swotCell("THÁCH THỨC (T)", ["Hãng công nghệ lớn có thể bản địa hóa tính năng", "Kẻ gian liên tục thay đổi thủ đoạn", "Người dùng cá nhân ngại trả phí", "Chu kỳ bán hàng B2B dài", "Kẻ gian có thể mạo danh chính HỏiCon"], "F3F3F1", GRAYTXT),
    ] }),
  ],
}));

// =================================================================== CHUONG 6 (BMC, trang ngang)
const c6 = [];
c6.push(H1("CHƯƠNG 6. MÔ HÌNH KINH DOANH (BUSINESS MODEL CANVAS)", { noBreak: true }));
const bw = [2600, 2700, 1700, 1700, 2800, 3070];  // tong 14570
const bmcHead = (t, fill = NAVY) => new Paragraph({ children: [new TextRun({ text: t, bold: true, color: "FFFFFF", size: 22, font: FONT })], shading: { fill, type: ShadingType.CLEAR, color: "auto" }, spacing: { after: 60 } });
const bmcCell = (title, items, width, o = {}) => new TableCell({
  width: { size: width, type: WidthType.DXA }, columnSpan: o.span, rowSpan: o.rowSpan,
  shading: { fill: o.fill || "FFFFFF", type: ShadingType.CLEAR, color: "auto" },
  margins: { top: 80, bottom: 80, left: 110, right: 110 }, borders: cellBorders,
  children: [bmcHead(title, o.head || NAVY), ...items.map((t) => new Paragraph({ children: inline(t, { size: 22 }), numbering: { reference: "tbullets", level: 0 }, spacing: { after: 30, line: 252 } }))],
});
c6.push(new Table({
  width: { size: LCW, type: WidthType.DXA }, columnWidths: bw, layout: TableLayoutType.FIXED,
  rows: [
    new TableRow({ children: [
      bmcCell("8. ĐỐI TÁC CHÍNH", ["Nguồn dữ liệu cảnh báo lừa đảo (mục tiêu: dự án Chống Lừa Đảo)", "Zalo (kênh liên lạc)", "Nhà cung cấp mô hình AI và giọng nói", "Ngân hàng, bảo hiểm, nhà mạng", "Công an phường, Đoàn Thanh niên, Hội Người cao tuổi", "Khoa CNTT – TDTU, vườn ươm khởi nghiệp"], bw[0], { rowSpan: 2 }),
      bmcCell("7. HOẠT ĐỘNG CHÍNH", ["Phát triển, vận hành hệ đa tác tử", "Cập nhật kho kịch bản lừa đảo hằng tuần", "Kiểm thử, đánh giá AI", "Bán hàng B2B2C", "Truyền thông cộng đồng", "Tuân thủ dữ liệu cá nhân"], bw[1]),
      bmcCell("2. GIẢI PHÁP GIÁ TRỊ", ["Người cao tuổi: khoảng dừng an toàn đúng lúc, không cần thao tác phức tạp", "Con cái: biết ngay khi cha mẹ gặp rủi ro, đủ bằng chứng để quyết định trong 30 giây", "Sinh viên: tự bảo vệ trước việc nhẹ lương cao, giả danh công an", "Đối tác: lớp phòng vệ “trước giao dịch”, giảm tổn thất và khiếu nại", "Tiếng Việt, không ghi âm, tuân thủ pháp luật"], bw[2] + bw[3], { span: 2, rowSpan: 2, fill: "FFF8F2", head: ORANGE }),
      bmcCell("4. QUAN HỆ KHÁCH HÀNG", ["Tự động qua tác tử AI, chuyển người thật khi có sự cố", "Cộng đồng “Mật khẩu gia đình”", "Diễn tập hằng tuần, báo cáo tháng", "Chương trình giới thiệu"], bw[4]),
      bmcCell("1. PHÂN KHÚC KHÁCH HÀNG", ["Gia đình có cha mẹ, ông bà từ 55 tuổi dùng Android tại TP.HCM (người trả tiền: con cái 25–45 tuổi)", "Sinh viên, người trẻ đi làm", "Ngân hàng, công ty bảo hiểm, nhà mạng (B2B2C)", "Phường/xã, tổ chức xã hội, doanh nghiệp tài trợ"], bw[5], { rowSpan: 2 }),
    ] }),
    new TableRow({ children: [
      bmcCell("6. NGUỒN LỰC CHÍNH", ["Đội ngũ CNTT và kinh doanh", "Bộ kịch bản và bộ đánh giá tiếng Việt", "Nền tảng tác tử (LangGraph, MCP)", "Thương hiệu tin cậy, mạng lưới gia đình"], bw[1]),
      bmcCell("3. KÊNH", ["Zalo HỏiCon, Google Play, website", "TikTok, Facebook", "Đại sứ sinh viên các trường", "Workshop cộng đồng", "Kênh đồng thương hiệu của đối tác"], bw[4]),
    ] }),
    new TableRow({ children: [
      bmcCell("9. CƠ CẤU CHI PHÍ", ["Nhân sự (≈ 50–60% chi phí cố định)", "Hạ tầng AI: mô hình ngôn ngữ, giọng nói, máy chủ", "Tin nhắn Zalo ZBS", "Marketing và cộng đồng", "Pháp lý, bảo mật, tuân thủ; R&D dữ liệu"], bw[0] + bw[1] + bw[2], { span: 3, fill: "F7F7F5", head: GRAYTXT }),
      bmcCell("5. DÒNG DOANH THU", ["Gói Gia đình 49.000 đồng/tháng hoặc 490.000 đồng/năm", "Phí đối tác B2B2C: phí triển khai + 5.000 đồng/người dùng hoạt động/tháng", "Tài trợ/CSR: 40 triệu đồng/chương trình cộng đồng", "Tương lai: báo cáo xu hướng lừa đảo ẩn danh cho đối tác"], bw[3] + bw[4] + bw[5], { span: 3, fill: LIGHT_GR, head: GREEN }),
    ] }),
  ],
}));

// =================================================================== CHUONG 7
const c7 = [];
c7.push(H1("CHƯƠNG 7. KẾ HOẠCH TÀI NGUYÊN (CÔNG NGHỆ – NHÂN SỰ)", { noBreak: true }));
c7.push(H2("7.1. Tài nguyên công nghệ"));
c7.push(tcap("Công nghệ dự kiến sử dụng"));
c7.push(table(["Thành phần", "Công nghệ dự kiến", "Lý do lựa chọn"], [
  ["Ứng dụng Android", "Kotlin, Jetpack Compose; CallScreeningService; quyền truy cập dữ liệu sử dụng ứng dụng; dịch vụ chạy nền; giọng nói tiếng Việt", "Dùng API chính thức, tuân thủ chính sách Google Play"],
  ["Ứng dụng iOS (2028)", "Swift; Call Directory Extension; bộ lọc tin nhắn; tiện ích chia sẻ để kiểm tra link, QR", "Phạm vi iOS cho phép: gắn nhãn số, lọc tin nhắn, kiểm tra"],
  ["Kênh người giám hộ", "Zalo Bot Platform (MVP), sau đó Zalo OA và tin mẫu ZBS; trang web Next.js", "Zalo là kênh quen thuộc nhất của gia đình Việt"],
  ["Điều phối tác tử", "Python, LangGraph (lưu trạng thái, điểm dừng chờ duyệt)", "Phù hợp quy trình nhiều bước có con người tham gia"],
  ["Công cụ", "Máy chủ MCP cho Zalo, tra cứu rủi ro, kho kịch bản, mẫu văn bản", "Chuẩn mở, dễ thay thế, có ghi vết"],
  ["Mô hình AI", "Định tuyến: mô hình nhỏ (lớp Gemini Flash, Claude Haiku, GPT mini) cho bước thường, mô hình lớn cho xác minh và soạn hồ sơ; nhận dạng và tổng hợp giọng nói tiếng Việt (Gemini Live, FPT.AI, Viettel AI – thử nghiệm theo vùng miền)", "Cân bằng chi phí và chất lượng; giọng miền Trung khó nhận dạng nhất theo nghiên cứu PhoASR {{phoasr}}"],
  ["Dữ liệu", "PostgreSQL, pgvector, Redis; dữ liệu định danh lưu trên máy chủ đặt tại Việt Nam", "Tuân thủ quy định bảo vệ dữ liệu cá nhân"],
  ["Ghi vết và đánh giá", "Langfuse (mã nguồn mở) để trace; bộ đánh giá ≥ 100 kịch bản tiếng Việt", "Đo lường minh bạch, cải tiến liên tục"],
], [2000, 4271, 2800], { boldFirst: true, firstColFill: true }));
c7.push(H2("7.2. Tài nguyên nhân sự"));
c7.push(tcap("Cơ cấu đội ngũ và phân vai"));
c7.push(table(["Vai trò", "Trách nhiệm", "Năng lực yêu cầu", "Thành viên"], [
  ["Trưởng nhóm – CEO", "Chiến lược, tài chính, quan hệ đối tác, thuyết trình", "Quản trị kinh doanh hoặc Tài chính – Ngân hàng; kỹ năng trình bày", "[[Họ và tên]]"],
  ["CTO – Kỹ sư tác tử AI", "Kiến trúc hệ thống, LangGraph, MCP, mô hình ngôn ngữ", "Sinh viên CNTT/Khoa học máy tính", "[[Họ và tên]]"],
  ["Kỹ sư Android và trải nghiệm người cao tuổi", "Ứng dụng Lính gác, giao diện giọng nói, kiểm thử trên nhiều thiết bị", "Sinh viên CNTT/Kỹ thuật phần mềm", "[[Họ và tên]]"],
  ["Kỹ sư dữ liệu, bảo mật và đánh giá AI", "Bộ kịch bản, bộ đánh giá, quyền riêng tư, bảo mật", "Sinh viên CNTT/An toàn thông tin", "[[Họ và tên]]"],
  ["CMO – Truyền thông và cộng đồng", "Chiến dịch, khảo sát, thí điểm, đối tác cộng đồng", "Marketing, Truyền thông, Tâm lý hoặc Công tác xã hội", "[[Họ và tên]]"],
], [2300, 2700, 2371, 1700], { boldFirst: true }));
c7.push(P("Cơ cấu đề xuất có 3/5 thành viên là sinh viên Khoa CNTT, đáp ứng điều kiện “trên 20% thành viên là sinh viên Khoa CNTT” của thể lệ {{rules}}, đồng thời có đủ các vai trò công nghệ, điều hành, tài chính và marketing như BTC khuyến nghị. Mỗi thành viên cam kết tối thiểu 12 giờ mỗi tuần; đội làm việc theo chu kỳ Scrum 1 tuần, quản lý mã nguồn trên GitHub.", { before: 120 }));
c7.push(P("**Kế hoạch nhân sự sau cuộc thi:** năm 2027 gồm 5 thành viên sáng lập (bán thời gian) và 1 cộng tác viên chăm sóc khách hàng; năm 2028 có 8 nhân sự toàn thời gian (bổ sung 2 kỹ sư, 1 nhân sự bán hàng B2B, 1 nhân sự chăm sóc khách hàng); năm 2029 có 12 nhân sự."));
c7.push(P("**Cố vấn (đang kết nối):** một giảng viên Khoa CNTT chuyên về an toàn thông tin hoặc lập trình di động; một chuyên gia chống gian lận của ngân hàng; một luật sư về bảo vệ dữ liệu cá nhân."));
c7.push(H2("7.3. Đối tác chính"));
c7.push(tcap("Đối tác mục tiêu và trạng thái"));
c7.push(table(["Đối tác", "Vai trò", "Trạng thái"], [
  ["Dự án Chống Lừa Đảo hoặc nguồn dữ liệu cảnh báo tương đương", "Dữ liệu số điện thoại, đường link, tài khoản nghi lừa đảo; nội dung giáo dục", "Mục tiêu kết nối (chưa ký kết)"],
  ["Zalo", "Kênh liên lạc với người giám hộ", "Sử dụng dịch vụ công khai"],
  ["Nhà cung cấp mô hình AI và giọng nói (Google, Anthropic, OpenAI, FPT.AI, Viettel AI)", "Hạ tầng AI", "Sử dụng dịch vụ công khai"],
  ["Ngân hàng, công ty bảo hiểm, nhà mạng", "Kênh phân phối B2B2C, đồng thương hiệu", "Mục tiêu: ít nhất 1 LOI trước 10/01/2027"],
  ["Công an phường, Đoàn Thanh niên, Hội Người cao tuổi, điểm hỗ trợ dịch vụ công {{tt_catlai}}", "Tiếp cận cộng đồng, tổ chức buổi hướng dẫn", "Mục tiêu kết nối"],
  ["Khoa CNTT – TDTU, vườn ươm khởi nghiệp", "Cố vấn, không gian làm việc, kết nối nhà đầu tư", "Mục tiêu kết nối"],
], [3300, 3471, 2300], { boldFirst: true }));

// =================================================================== CHUONG 8
const c8 = [];
c8.push(H1("CHƯƠNG 8. KẾ HOẠCH THƯƠNG MẠI"));
c8.push(H2("8.1. Phân tích khách hàng"));
c8.push(tcap("Phân tích hành vi mua của từng phân khúc"));
c8.push(table(["Phân khúc", "Người ra quyết định", "Thời điểm mua", "Rào cản và cách xử lý"], [
  ["Gia đình có người cao tuổi", "Con cái 25–45 tuổi", "Sau tin tức về lừa đảo, khi người quen bị lừa, dịp Tết, khi cha mẹ bắt đầu dùng ngân hàng số", "Lo quyền riêng tư → cam kết “không ghi âm”; cha mẹ ngại công nghệ → con cài đặt hộ, giao diện giọng nói"],
  ["Sinh viên", "Sinh viên hoặc gia đình", "Khi nhận lời mời việc làm online, cuộc gọi giả danh", "Ngại trả phí → chế độ sinh viên miễn phí, chia sẻ gói Gia đình"],
  ["Đối tác B2B2C", "Khối quản trị rủi ro, chăm sóc khách hàng, CSR", "Khi tổn thất, khiếu nại tăng hoặc có yêu cầu bảo vệ khách hàng", "Chu kỳ dài → thí điểm nhỏ, chia sẻ số liệu hiệu quả, đồng thương hiệu"],
  ["Cộng đồng", "Chính quyền phường/xã, nhà tài trợ", "Chương trình an toàn số, chuyển đổi số cộng đồng", "Ngân sách hạn chế → mô hình tài trợ CSR"],
], [2000, 2100, 2400, 2571], { boldFirst: true }));
c8.push(H2("8.2. Chiến lược giá"));
c8.push(tcap("Các gói dịch vụ"));
c8.push(table(["Gói", "Giá", "Quyền lợi", "Đối tượng"], [
  ["Cơ bản", "Miễn phí", "Gắn nhãn cuộc gọi, nút “Hỏi con”, kiểm tra số/link/QR (giới hạn lượt), mật khẩu gia đình, chế độ sinh viên", "Mọi người dùng"],
  ["Gia đình", "49.000 đồng/tháng hoặc 490.000 đồng/năm", "Tối đa 4 người được bảo vệ và 4 người giám hộ; khoảng dừng an toàn tự động; tác tử chấm rủi ro, xác minh, hồ sơ vụ việc; diễn tập hằng tuần; báo cáo tháng", "Gia đình"],
  ["Đối tác (B2B2C)", "Phí triển khai 100–150 triệu đồng + 5.000 đồng/người dùng hoạt động/tháng", "Đồng thương hiệu, tích hợp kênh đối tác, bảng điều khiển ẩn danh, báo cáo tác động", "Ngân hàng, bảo hiểm, nhà mạng"],
  ["Chương trình cộng đồng", "40 triệu đồng/chương trình", "2 buổi hướng dẫn, thẻ mật khẩu gia đình, diễn tập cho khoảng 150 người cao tuổi, 3 tháng gói Gia đình cho 50 hộ", "Phường/xã, doanh nghiệp tài trợ"],
], [1700, 2300, 3571, 1500], { boldFirst: true, firstColFill: true }));
c8.push(P("Giá gói Gia đình thấp hơn nhiều so với sản phẩm tương tự ở Mỹ – Aura có giá 12 USD/tháng cho cá nhân và 32 USD/tháng cho gói 5 người lớn khi trả theo năm {{aura}} – để phù hợp với thu nhập tại Việt Nam; mức giá sẽ được kiểm chứng bằng khảo sát Van Westendorp.", { before: 120 }));
c8.push(H2("8.3. Kênh phân phối và chiến lược tiếp cận thị trường"));
c8.push(tcap("Lộ trình tiếp cận thị trường"));
c8.push(table(["Giai đoạn", "Thời gian", "Thị trường", "Hoạt động chính", "Chỉ tiêu"], [
  ["Thí điểm", "11/2026 – 02/2027", "Gia đình sinh viên TDTU", "Cài đặt có hướng dẫn, diễn tập, thu thập phản hồi", "50–100 gia đình"],
  ["Ra mắt", "03 – 06/2027", "TP.HCM", "Thành lập công ty, phát hành Android, chiến dịch “Mật khẩu gia đình”, đại sứ sinh viên các trường", "5.000 gia đình"],
  ["Mở rộng kênh", "07 – 12/2027", "TP.HCM", "Thí điểm B2B2C với 1 đối tác; chương trình cộng đồng với phường/xã", "15.000 gia đình; 600 trả phí"],
  ["Tăng trưởng", "2028", "Hà Nội, Đà Nẵng, Cần Thơ", "2 đối tác B2B2C; phiên bản iOS rút gọn", "60.000 gia đình; 3.000 trả phí"],
  ["Quy mô", "2029", "Toàn quốc", "3 đối tác; mô-đun cho hộ kinh doanh, doanh nghiệp nhỏ", "150.000 gia đình; 7.500 trả phí"],
], [1500, 1500, 1800, 2671, 1600], { boldFirst: true }));
c8.push(H2("8.4. Kế hoạch triển khai sản phẩm"));
c8.push(tcap("Các phiên bản sản phẩm"));
c8.push(table(["Phiên bản", "Thời gian", "Nội dung chính"], [
  ["MVP (v0.1)", "01/2027", "Lính gác Android, nút “Hỏi con”, 5 tác tử, kênh Zalo Bot, bộ đánh giá ≥ 100 kịch bản"],
  ["v1.0", "05/2027", "Phát hành trên Google Play; Zalo OA; thanh toán gói Gia đình qua VietQR; báo cáo tháng"],
  ["v1.5", "10/2027", "Tích hợp đối tác B2B2C đầu tiên; bảng điều khiển đối tác"],
  ["v2.0", "2028", "Phiên bản iOS rút gọn; mở rộng kho kịch bản theo vùng miền, giọng địa phương"],
  ["v3.0", "2029", "Mô-đun cho hộ kinh doanh, doanh nghiệp nhỏ; API cho đối tác"],
], [1700, 1500, 5871], { boldFirst: true }));

// =================================================================== CHUONG 9
const c9 = [];
c9.push(H1("CHƯƠNG 9. KẾ HOẠCH TÀI CHÍNH"));
c9.push(P("Toàn bộ số liệu trong chương này là kế hoạch dựa trên các giả định của nhóm (liệt kê tại Phụ lục B) và sẽ được hiệu chỉnh theo kết quả khảo sát, thí điểm."));
c9.push(H2("9.1. Nhu cầu vốn và nguồn vốn"));
c9.push(tcap("Nhu cầu vốn theo giai đoạn"));
c9.push(table(["Giai đoạn", "Nhu cầu", "Nguồn vốn", "Mục đích sử dụng"], [
  ["Cuộc thi (10/2026 – 02/2027)", `${fmt(M.mvp_total / 1e6, 2)} triệu đồng`, "Vốn góp của 5 thành viên (7 triệu đồng/người); tín dụng miễn phí của nhà cung cấp AI", "Xây MVP, khảo sát, thí điểm, truyền thông"],
  ["Ra mắt (03 – 12/2027)", `≈ ${fmt(-Y[2027].net / 1e9, 2)} tỷ đồng bù lỗ hoạt động`, "Vòng tiền hạt giống 2 tỷ đồng (quý II/2027, dự kiến 10–12% cổ phần) từ nhà đầu tư thiên thần, quỹ hoặc vườn ươm; giải thưởng, chương trình hỗ trợ khởi nghiệp", "Nhân sự, hạ tầng, marketing, pháp lý"],
  ["Tăng trưởng (2028)", `≈ ${fmt(-Y[2028].net / 1e9, 2)} tỷ đồng bù lỗ hoạt động`, "Phần còn lại của vòng hạt giống; doanh thu B2B2C", "Mở rộng thị trường, đội ngũ"],
  ["Tự chủ (2029)", "—", "Dòng tiền hoạt động dương", "Tái đầu tư cho sản phẩm và tác động xã hội"],
], [2100, 1900, 3071, 2000], { boldFirst: true }));
c9.push(P(`Lỗ lũy kế đến hết năm 2028 khoảng ${fmt(-Y[2028].cum_net / 1e9, 2)} tỷ đồng nằm trong khả năng của vòng tiền hạt giống 2 tỷ đồng, để lại khoảng dự phòng gần 1 tỷ đồng. Khi đủ điều kiện pháp nhân, đội đăng ký các chương trình tín dụng đám mây (Google for Startups gói Start tới 2.000 USD; AWS Activate Founders tới 5.000 USD) {{gfs}}{{aws}} và tận dụng chính sách hỗ trợ doanh nghiệp khởi nghiệp AI theo Điều 25 Luật Trí tuệ nhân tạo {{ailaw}}. Đội cũng cân nhắc đăng ký mô hình doanh nghiệp xã hội – cam kết dùng tối thiểu 51% lợi nhuận để tái đầu tư cho mục tiêu xã hội {{bc}}.`, { before: 120 }));
c9.push(H2("9.2. Ngân sách giai đoạn cuộc thi"));
c9.push(tcap("Ngân sách từ 10/2026 đến 02/2027"));
c9.push(table(["Hạng mục", "Số tiền (đồng)"],
  [...M.mvp_budget.map(([k, v]) => [k, fmt(v, 0)]), ["**Tổng cộng**", `**${fmt(M.mvp_total, 0)}**`]],
  [CW - 2200, 2200], { rightCols: [1] }));
c9.push(note("Zalo Bot Platform có gói miễn phí nên chưa phát sinh phí Zalo OA ở giai đoạn này; phí mô hình AI chủ yếu nằm trong hạn mức miễn phí của nhà cung cấp."));
c9.push(H2("9.3. Đơn vị kinh tế"));
const U = M.unit;
c9.push(tcap("Đơn vị kinh tế theo từng nguồn doanh thu"));
c9.push(table(["Chỉ tiêu (đồng/tháng)", "Gói Gia đình (mỗi gia đình)", "Đối tác B2B2C (mỗi người dùng hoạt động)"], [
  ["Doanh thu bình quân", fmt(U.family.price, 0), fmt(U.b2b.price, 0)],
  ["Chi phí biến đổi (AI, giọng nói, tin nhắn, phí thanh toán)", fmt(U.family.var, 0), fmt(U.b2b.var, 0)],
  ["Lợi nhuận góp", fmt(U.family.contrib, 0), fmt(U.b2b.contrib, 0)],
  ["Tỷ lệ lợi nhuận góp", fmt(U.family.contrib / U.family.price * 100, 0) + "%", fmt(U.b2b.contrib / U.b2b.price * 100, 0) + "%"],
], [3871, 2600, 2600], { boldFirst: true, rightCols: [1, 2] }));
c9.push(P("Doanh thu bình quân gói Gia đình (45.000 đồng) thấp hơn giá niêm yết do một phần khách hàng chọn gói năm. Chi phí biến đổi được ước tính từ bảng giá công khai của các nhà cung cấp mô hình AI và tin nhắn Zalo {{gemini}}{{claude}}{{zbs}} với khoảng 14 tác vụ/gia đình/tháng (sự kiện rủi ro và diễn tập). Mỗi gia đình dùng gói Cơ bản tốn khoảng 600 đồng/tháng và được xem là chi phí thu hút khách hàng.", { before: 120 }));
c9.push(H2("9.4. Dự báo kết quả kinh doanh 2027–2029"));
const F = M.fixed;
const row = (label, f, bold = false) => [bold ? `**${label}**` : label, ...[2027, 2028, 2029].map((y) => (bold ? `**${f(y)}**` : f(y)))];
c9.push(tcap("Báo cáo kết quả kinh doanh dự kiến (triệu đồng, kịch bản cơ sở)"));
const PL_NO = tableNo;
c9.push(table(["Chỉ tiêu", "2027", "2028", "2029"], [
  row("Doanh thu gói Gia đình (B2C)", (y) => tr(Y[y].rev_b2c)),
  row("Doanh thu đối tác B2B2C", (y) => tr(Y[y].rev_b2b)),
  row("Tài trợ/CSR chương trình cộng đồng", (y) => tr(Y[y].rev_csr)),
  row("Tổng doanh thu", (y) => tr(Y[y].rev), true),
  row("Chi phí biến đổi", (y) => tr(Y[y].var)),
  row("Lợi nhuận gộp", (y) => tr(Y[y].gp), true),
  row("Biên lợi nhuận gộp", (y) => fmt(Y[y].gm * 100, 1) + "%"),
  row("Nhân sự", (y) => fmt(F[y].personnel, 1)),
  row("Hạ tầng nền và công cụ", (y) => fmt(F[y].infra, 1)),
  row("Marketing và cộng đồng", (y) => fmt(F[y].marketing, 1)),
  row("Pháp lý, bảo mật, tuân thủ", (y) => fmt(F[y].legal, 1)),
  row("Văn phòng và hành chính", (y) => fmt(F[y].office, 1)),
  row("R&D dữ liệu và đánh giá", (y) => fmt(F[y].rnd, 1)),
  row("Tổng chi phí cố định", (y) => tr(Y[y].fixed), true),
  row("EBITDA", (y) => tr(Y[y].ebitda), true),
  row("Thuế TNDN (20%, sau chuyển lỗ)", (y) => tr(Y[y].tax)),
  row("Lợi nhuận sau thuế", (y) => tr(Y[y].net), true),
  row("Lợi nhuận lũy kế", (y) => tr(Y[y].cum_net)),
], [3671, 1800, 1800, 1800], { rightCols: [1, 2, 3], zebra: true }));
c9.push(...figure("fig_finance.png", `Dự báo doanh thu theo nguồn và tổng chi phí 2027–2029 (tỷ đồng, kịch bản cơ sở; số liệu chi tiết tại Bảng ${PL_NO})`));
c9.push(P(`Doanh thu tăng khoảng ${fmt(Y[2028].rev / Y[2027].rev, 1)} lần năm 2028 và ${fmt(Y[2029].rev / Y[2028].rev, 1)} lần năm 2029, với động lực chính là kênh B2B2C (chiếm ${fmt(Y[2029].rev_b2b / Y[2029].rev * 100, 0)}% doanh thu năm 2029). Biên lợi nhuận gộp duy trì ở mức khoảng 60%. Dự án đạt EBITDA dương ${tr(Y[2029].ebitda)} triệu đồng và lợi nhuận lũy kế dương vào năm 2029.`));
c9.push(H2("9.5. Phân tích kịch bản"));
const C = M.conservative_2029, O = M.optimistic_2029;
c9.push(tcap("Kết quả năm 2029 theo ba kịch bản"));
c9.push(table(["Kịch bản", "Giả định chính", "Doanh thu 2029 (tỷ đồng)", "EBITDA 2029 (tỷ đồng)", "Năm EBITDA dương"], [
  ["Thận trọng", "B2B2C chậm 12 tháng (30.000 người dùng hoạt động năm 2029); tỷ lệ trả phí thấp hơn 40%; chi phí cố định giữ quanh mức năm 2028", ty(C.rev), ty(C.ebitda), "2030 (ước tính)"],
  ["Cơ sở", `Theo Bảng ${PL_NO} và Phụ lục B`, ty(Y[2029].rev), ty(Y[2029].ebitda), "2029"],
  ["Tích cực", "4 đối tác (150.000 người dùng hoạt động); tỷ lệ trả phí cao hơn 30%", ty(O.rev), ty(O.ebitda), "2029"],
], [1500, 3671, 1300, 1300, 1300], { boldFirst: true, rightCols: [2, 3] }));
c9.push(P("Kết quả cho thấy kênh B2B2C là đòn bẩy quyết định; vì vậy kế hoạch ưu tiên có thư ý định hợp tác (LOI) với ít nhất một đối tác ngay trong giai đoạn cuộc thi và giữ chi phí cố định linh hoạt theo tiến độ ký kết đối tác.", { before: 120 }));

// =================================================================== CHUONG 10
const c10 = [];
c10.push(H1("CHƯƠNG 10. KẾ HOẠCH TRUYỀN THÔNG"));
c10.push(H2("10.1. Định vị và thông điệp"));
c10.push(tcap("Thông điệp theo nhóm đối tượng"));
c10.push(table(["Đối tượng", "Thông điệp"], [
  ["Thông điệp chủ đạo", "“Bị dọa chuyển tiền? Hỏi con trước đã.”"],
  ["Con cái", "“Đừng để cha mẹ một mình với kẻ lừa đảo.”"],
  ["Sinh viên", "“Bạn là người lắp lá chắn cho cả nhà.”"],
  ["Đối tác", "“Lớp phòng vệ trước giao dịch mà hệ thống của bạn không nhìn thấy.”"],
], [2600, CW - 2600], { boldFirst: true, firstColFill: true }));
c10.push(P("Giọng điệu: ấm áp, gần gũi, không gây hoảng sợ; mọi nội dung đều kết thúc bằng một hành động cụ thể (lập mật khẩu gia đình, cài HỏiCon cho cha mẹ, tham gia diễn tập).", { before: 120 }));
c10.push(H2("10.2. Chiến dịch chủ đạo “Mật khẩu gia đình”"));
c10.push(P("Chuyên gia khuyến nghị mỗi gia đình thống nhất một mật khẩu bí mật để xác minh người thân khi nghi bị giả giọng {{vnp}}. HỏiCon biến lời khuyên này thành một chiến dịch có thể đo lường, và đây cũng là điểm khác biệt của kế hoạch truyền thông: **sản phẩm trở thành một thói quen của gia đình, không chỉ là một ứng dụng.**", { keepNext: true }));
c10.push(...bullets([
  "**Thử thách video “Gọi hỏi ba mẹ mật khẩu gia đình”** trên TikTok và Facebook: ghi lại phản ứng thật, lan tỏa tự nhiên.",
  "**Thẻ “Mật khẩu gia đình” in sẵn**, tặng tại sự kiện và buổi hướng dẫn: vật phẩm hữu ích mang về nhà.",
  "**Trang cam kết trực tuyến:** đếm số gia đình đã lập mật khẩu; quét mã QR để trải nghiệm “gia đình demo”.",
  "**Diễn tập lừa đảo an toàn:** như diễn tập phòng cháy, có sự đồng ý, chia sẻ kết quả theo hướng tích cực, không gây sợ hãi.",
]));
c10.push(H2("10.3. Kênh và nội dung"));
c10.push(tcap("Kế hoạch kênh truyền thông"));
c10.push(table(["Kênh", "Nội dung", "Mục tiêu"], [
  ["TikTok, Facebook Reels", "Chuỗi “Ba mẹ mình suýt bị lừa” (câu chuyện thật của sinh viên TDTU, có sự đồng ý); tái hiện thủ đoạn mới trong 30 giây", "Nhận biết, lan tỏa"],
  ["Zalo HỏiCon", "Bản tin cảnh báo thủ đoạn hằng tuần; bài học 1 phút bằng giọng nói cho người cao tuổi", "Giữ chân, giáo dục"],
  ["Cộng đồng sinh viên", "Đại sứ sinh viên, câu lạc bộ, ký túc xá; trò chơi “Bạn có cứu được bà không?”", "Tuyển gia đình thí điểm, xây dựng cộng đồng ủng hộ"],
  ["Cộng đồng dân cư", "Buổi hướng dẫn tại phường/xã, điểm hỗ trợ dịch vụ công {{tt_catlai}}, Hội Người cao tuổi", "Tiếp cận người cao tuổi"],
  ["Báo chí, đối tác", "Thông cáo kết quả thí điểm; nội dung đồng thương hiệu với đối tác", "Uy tín"],
], [2300, 4471, 2300], { boldFirst: true }));
c10.push(H2("10.4. Lịch truyền thông theo các vòng thi"));
c10.push(tcap("Lịch truyền thông và chỉ tiêu"));
c10.push(table(["Giai đoạn", "Hoạt động", "Chỉ tiêu"], [
  ["10 – 11/2026 (Vòng 1)", "Ra mắt fanpage và kênh TikTok; 6 video “Ba mẹ mình suýt bị lừa”; chiến dịch khảo sát; trang cam kết “Mật khẩu gia đình”", "50.000 lượt tiếp cận; ≥ 300 phản hồi khảo sát; ≥ 100 gia đình đăng ký thí điểm"],
  ["12/2026 – 01/2027 (Vòng 2)", "Nhật ký thí điểm; video diễn tập lừa đảo an toàn; kết nối đối tác", "1.000 gia đình cam kết; 3 video trên 10.000 lượt xem"],
  ["02/2027 (Tết và chung kết)", "Chiến dịch “Tết này, hỏi con trước khi chuyển tiền”; mời gia đình thí điểm và bạn bè tới triển lãm poster", "Tối đa lượt bình chọn ngày 27/02/2027"],
], [2400, 4271, 2400], { boldFirst: true }));
c10.push(note("Mọi hoạt động tặng quà và kêu gọi bình chọn sẽ được thực hiện theo quy định của BTC."));
c10.push(H2("10.5. Trải nghiệm tại gian trưng bày poster"));
c10.push(P("Gian trưng bày được thiết kế quanh câu hỏi **“Bạn có cứu được bà không?”**. Khách cầm một điện thoại demo trong vai “bà”, thành viên đội gọi đến trong vai “công an”; điện thoại hiện cảnh báo và phát khoảng dừng an toàn; khách bấm “Hỏi con” – và chính điện thoại của khách, sau khi quét mã QR để vào “gia đình demo”, nhận cảnh báo Zalo sau vài giây. Màn hình lớn hiển thị trace của các tác tử theo thời gian thực, giúp cả người không học CNTT thấy rõ AI đang “suy nghĩ” và hành động thế nào. Poster nhấn mạnh ba con số: 8.000 tỷ đồng thiệt hại, 50% vụ có nạn nhân cao tuổi vì sợ liên lụy con cháu, 32% nạn nhân trình báo; quà mang về là thẻ “Mật khẩu gia đình”."));

// =================================================================== CHUONG 11
const c11 = [];
c11.push(H1("CHƯƠNG 11. GIỚI THIỆU ĐỘI NGŨ THỰC HIỆN"));
c11.push(P("Đội thi gồm 5 thành viên với cơ cấu liên ngành: công nghệ (3 sinh viên Khoa CNTT), kinh doanh – tài chính và truyền thông – cộng đồng. Thông tin chi tiết:", { keepNext: true }));
c11.push(tcap("Thành viên đội thi"));
c11.push(table(["STT", "Họ và tên", "MSSV – Khoa – Trường", "Vai trò", "Kinh nghiệm, kỹ năng nổi bật"], [
  ["1", "[[Họ và tên]]", "[[MSSV – Khoa – Trường]]", "Trưởng nhóm – CEO", "[[Kinh nghiệm, giải thưởng, dự án]]"],
  ["2", "[[Họ và tên]]", "[[MSSV – Khoa CNTT]]", "CTO – Kỹ sư tác tử AI", "[[Kinh nghiệm, giải thưởng, dự án]]"],
  ["3", "[[Họ và tên]]", "[[MSSV – Khoa CNTT]]", "Kỹ sư Android", "[[Kinh nghiệm, giải thưởng, dự án]]"],
  ["4", "[[Họ và tên]]", "[[MSSV – Khoa CNTT]]", "Kỹ sư dữ liệu, bảo mật và đánh giá AI", "[[Kinh nghiệm, giải thưởng, dự án]]"],
  ["5", "[[Họ và tên]]", "[[MSSV – Khoa – Trường]]", "CMO – Truyền thông và cộng đồng", "[[Kinh nghiệm, giải thưởng, dự án]]"],
], [700, 2000, 2100, 2071, 2200], { centerCols: [0] }));
c11.push(P("**Vì sao đội phù hợp với dự án:** các thành viên đều là con, cháu trong những gia đình có người cao tuổi – chính là người dùng mục tiêu; đội có đủ năng lực kỹ thuật để xây hệ đa tác tử và ứng dụng di động, đồng thời có thành viên phụ trách kinh doanh và cộng đồng để thực hiện thí điểm, kết nối đối tác.", { before: 120 }));
c11.push(tcap("Cố vấn của dự án"));
c11.push(table(["Lĩnh vực", "Vai trò", "Trạng thái"], [
  ["Giảng viên Khoa CNTT (an toàn thông tin hoặc lập trình di động)", "Cố vấn kỹ thuật, kiến trúc, bảo mật", "[[Đang liên hệ]]"],
  ["Chuyên gia chống gian lận ngân hàng", "Cố vấn nghiệp vụ, kết nối đối tác B2B2C", "[[Đang liên hệ]]"],
  ["Luật sư về bảo vệ dữ liệu cá nhân", "Cố vấn tuân thủ pháp luật", "[[Đang liên hệ]]"],
], [3600, 3271, 2200], { boldFirst: true }));

// =================================================================== CHUONG 12
const c12 = [];
c12.push(H1("CHƯƠNG 12. KẾ HOẠCH THỰC HIỆN VÀ TRIỂN KHAI"));
c12.push(H2("12.1. Kế hoạch theo các vòng thi"));
c12.push(tcap("Kế hoạch thực hiện trong thời gian cuộc thi"));
c12.push(table(["Thời gian", "Công việc", "Sản phẩm bàn giao"], [
  ["05/10 – 25/10/2026", "Khảo sát, phỏng vấn sâu; thiết kế trải nghiệm; kiểm chứng kỹ thuật (CallScreeningService, Zalo Bot Platform)", "Báo cáo khảo sát sơ bộ; bản mẫu giao diện"],
  ["26/10 – 15/11/2026", "Hoàn thiện thuyết minh, Business Model Canvas, video 3 phút; danh sách gia đình thí điểm", "Hồ sơ Vòng 1"],
  ["Tuần 1: 23/11 – 29/11/2026", "Đăng ký Zalo Bot Platform/OA, gửi duyệt mẫu tin; màn hình đồng ý và công khai AI; thiết lập hạ tầng", "Hạ tầng sẵn sàng"],
  ["Tuần 2–3: 30/11 – 13/12/2026", "Lính gác Android; bot cho người giám hộ", "Bản Android nội bộ"],
  ["Tuần 4: 14/12 – 20/12/2026", "Tác tử Chấm rủi ro và Can thiệp; điểm dừng chờ duyệt", "Luồng cảnh báo hoàn chỉnh"],
  ["Tuần 5: 21/12 – 27/12/2026", "Tác tử Xác minh, Hồ sơ vụ việc, Huấn luyện", "Đủ 5 tác tử"],
  ["Tuần 6: 28/12/2026 – 03/01/2027", "Chạy bộ đánh giá 100 kịch bản; trang trace; sửa lỗi", "Báo cáo đánh giá"],
  ["Tuần 7: 04/01 – 10/01/2027", "Tổng hợp số liệu thí điểm; poster; video 5 phút", "Hồ sơ Vòng 2"],
  ["18/01 – 21/02/2027", "Hoàn thiện theo góp ý của BGK; chiến dịch Tết; slide 10 phút; chuẩn bị gian trưng bày", "Hồ sơ chung kết"],
  ["27/02/2027", "Thuyết trình và triển lãm poster tại Hội trường 10F", "—"],
], [2400, 4271, 2400], { boldFirst: true }));
c12.push(note("Thí điểm với gia đình được triển khai theo từng đợt trong suốt tháng 11/2026 – 01/2027 để có số liệu thực tế trước khi nộp hồ sơ Vòng 2."));
c12.push(H2("12.2. Lộ trình phát triển 2027–2029"));
c12.push(tcap("Các cột mốc phát triển"));
c12.push(table(["Thời gian", "Cột mốc"], [
  ["Quý II/2027", "Thành lập công ty; gọi vốn hạt giống; phát hành trên Google Play"],
  ["Quý III/2027", "5.000 gia đình sử dụng; ký thí điểm với đối tác B2B2C đầu tiên"],
  ["Quý IV/2027", "Tích hợp đối tác đầu tiên; 15.000 gia đình sử dụng"],
  ["Năm 2028", "Mở rộng Hà Nội, Đà Nẵng, Cần Thơ; phiên bản iOS rút gọn; đối tác thứ hai"],
  ["Năm 2029", "Phủ sóng toàn quốc; đối tác thứ ba; EBITDA dương; nghiên cứu mở rộng sang các nước ASEAN có thủ đoạn lừa đảo tương tự"],
], [2400, CW - 2400], { boldFirst: true, firstColFill: true }));

// =================================================================== CHUONG 13
const c13 = [];
c13.push(H1("CHƯƠNG 13. ĐÁNH GIÁ RỦI RO VÀ GIẢI PHÁP"));
c13.push(tcap("Ma trận rủi ro"));
c13.push(table(["#", "Rủi ro", "Khả năng", "Tác động", "Giải pháp"], [
  ["1", "Chính sách của Google Play hoặc Android thay đổi", "Trung bình", "Cao", "Chỉ dùng API chính thức, quy tắc tất định, công bố nổi bật; không xin quyền SMS, Accessibility; rà soát chính sách hằng quý"],
  ["2", "Giới hạn của iOS", "Cao", "Trung bình", "Phiên bản iOS rút gọn: gắn nhãn số, lọc tin nhắn, kiểm tra link/QR và vòng xác minh gia đình"],
  ["3", "Quyền riêng tư, dữ liệu cá nhân", "Trung bình", "Cao", "Không ghi âm; tối thiểu hóa; đồng ý theo từng quyền; nhật ký đồng ý; đánh giá tác động; lưu dữ liệu tại Việt Nam"],
  ["4", "Báo nhầm gây phiền hoặc bỏ sót gây thiệt hại", "Trung bình", "Cao", "Ngưỡng thận trọng; người giám hộ quyết định; điều khoản “hỗ trợ, không bảo đảm”; công bố kết quả bộ đánh giá"],
  ["5", "Kẻ gian mạo danh HỏiCon", "Trung bình", "Cao", "Không gửi link qua SMS; chỉ dùng kênh Zalo đã xác thực; mật khẩu gia đình"],
  ["6", "Hãng công nghệ lớn bản địa hóa tính năng chống lừa đảo", "Trung bình", "Trung bình", "Tập trung vào vai trò gia đình, tiếng Việt, xử lý hậu quả; tích hợp thay vì cạnh tranh; hợp đồng B2B2C"],
  ["7", "Người dùng cá nhân không sẵn lòng trả phí", "Cao", "Trung bình", "Kiểm chứng giá bằng khảo sát; tập trung B2B2C và tài trợ; ưu đãi gói năm"],
  ["8", "Chu kỳ bán hàng B2B2C kéo dài", "Cao", "Cao", "Bắt đầu với công ty bảo hiểm, ngân hàng số, fintech; thí điểm nhỏ có số liệu; tận dụng ngân sách CSR"],
  ["9", "Người cao tuổi ngại sử dụng", "Trung bình", "Cao", "Con cái cài đặt hộ; giao diện giọng nói, nút lớn; hướng dẫn tại cộng đồng"],
  ["10", "Nhận dạng giọng nói vùng miền kém chính xác", "Trung bình", "Trung bình", "Thử nghiệm 30–50 mẫu giọng mỗi vùng {{phoasr}}; phương án nút bấm thay thế; chọn nhà cung cấp phù hợp"],
  ["11", "Nhân sự sinh viên bận lịch học, thi", "Trung bình", "Trung bình", "Phân vai rõ, chu kỳ Scrum, cố vấn đồng hành, dự phòng chéo vai trò"],
  ["12", "Thay đổi pháp lý về AI và dữ liệu", "Thấp", "Trung bình", "Theo dõi văn bản mới; tham vấn luật sư; thiết kế tuân thủ cao hơn mức tối thiểu"],
], [500, 2500, 1200, 1200, 3671], { centerCols: [0, 2, 3], keep: false }));

// =================================================================== CHUONG 14
const c14 = [];
c14.push(H1("CHƯƠNG 14. KẾT QUẢ DỰ KIẾN"));
c14.push(tcap("Chỉ tiêu kết quả dự kiến"));
c14.push(table(["Chỉ tiêu", "02/2027", "2027", "2028", "2029"], [
  ["Gia đình sử dụng (cuối kỳ)", "50–100 (thí điểm)", "15.000", "60.000", "150.000"],
  ["Gia đình trả phí (cuối kỳ)", "—", "600", "3.000", "7.500"],
  ["Đối tác B2B2C", "≥ 1 LOI", "1", "2", "3"],
  ["Người dùng hoạt động qua đối tác (bình quân)", "—", "5.000 (quý IV)", "30.000", "100.000"],
  ["Chương trình cộng đồng", "1 buổi thí điểm", "3", "8", "15"],
  ["Doanh thu (tỷ đồng)", "—", ty(Y[2027].rev), ty(Y[2028].rev), ty(Y[2029].rev)],
  ["EBITDA (tỷ đồng)", "—", ty(Y[2027].ebitda), ty(Y[2028].ebitda), ty(Y[2029].ebitda)],
  ["Lợi nhuận sau thuế (tỷ đồng)", "—", ty(Y[2027].net), ty(Y[2028].net), ty(Y[2029].net)],
], [3071, 1650, 1450, 1450, 1450], { boldFirst: true, rightCols: [1, 2, 3, 4] }));
c14.push(P("**Chỉ tiêu chất lượng của hệ thống AI trong giai đoạn thí điểm:** tỷ lệ phát hiện ≥ 90% trên bộ đánh giá; báo nhầm ≤ 1 lần/gia đình/tuần; thời gian phản hồi của người giám hộ (trung vị) ≤ 3 phút; độ trễ kích hoạt khoảng dừng an toàn ≤ 3 giây.", { before: 120 }));
c14.push(P("**Tăng trưởng:** doanh thu dự kiến tăng nhanh nhờ mở rộng kênh B2B2C, từ 0,46 tỷ đồng (2027) lên 9,59 tỷ đồng (2029); số gia đình được bảo vệ tăng gấp 10 lần trong hai năm. Về tác động xã hội, đến năm 2029 HỏiCon hướng tới bảo vệ khoảng 250.000 người dùng (gia đình trực tiếp và khách hàng của đối tác)."));

// =================================================================== KET LUAN, TAI LIEU, PHU LUC
const cEnd = [];
cEnd.push(H1("KẾT LUẬN"));
cEnd.push(P("Lừa đảo trực tuyến không chỉ là vấn đề công nghệ mà là vấn đề của sự cô lập: kẻ gian thắng khi nạn nhân ở một mình. HỏiCon giải quyết đúng điểm đó bằng một hệ thống Agentic AI tiếng Việt biết dừng đúng lúc, hỏi đúng câu, báo đúng người và hỗ trợ xử lý hậu quả – trong khi vẫn tôn trọng quyền riêng tư và để con người giữ quyền quyết định."));
cEnd.push(P("Dự án có nhu cầu thị trường rõ ràng, thời điểm pháp lý thuận lợi, mô hình doanh thu kết hợp B2C, B2B2C và tài trợ, cùng kế hoạch thí điểm khả thi với chính gia đình của sinh viên. Nhóm tin rằng HỏiCon có thể trở thành “lớp an toàn gia đình” cho hàng trăm nghìn gia đình Việt Nam – bắt đầu từ những gia đình của chính sinh viên Trường Đại học Tôn Đức Thắng."));
cEnd.push(callout("", ["**Lừa đảo nhắm vào khoảnh khắc con người cô đơn nhất. HỏiCon đưa gia đình trở lại đúng khoảnh khắc đó.**"], NAVY, LIGHT));

const appA = [];
appA.push(H1("PHỤ LỤC A. BỘ CÂU HỎI KHẢO SÁT (DỰ THẢO)"));
appA.push(P("Bảng hỏi trực tuyến dành cho sinh viên và người đi làm có cha mẹ từ 55 tuổi; thời gian trả lời khoảng 7 phút; dữ liệu được thu thập ẩn danh, người trả lời có thể để lại liên hệ nếu muốn tham gia thí điểm."));
const qa = [
  ["A. Thông tin chung", ["Năm sinh của bạn; nghề nghiệp; tỉnh/thành phố đang sống.", "Cha mẹ/ông bà của bạn bao nhiêu tuổi? Sống cùng hay ở riêng?"]],
  ["B. Trải nghiệm lừa đảo", ["Trong 12 tháng qua, bạn hoặc người thân có nhận cuộc gọi, tin nhắn lừa đảo không? Thủ đoạn gì?", "Có ai bị mất tiền không? Ai là người phát hiện, phát hiện vào lúc nào?"]],
  ["C. Công nghệ", ["Cha mẹ bạn dùng điện thoại Android hay iPhone?", "Cha mẹ có dùng Zalo và ứng dụng ngân hàng không?"]],
  ["D. Nhu cầu", ["Mức độ lo lắng của bạn về việc cha mẹ bị lừa (thang 1–5).", "Bạn muốn được báo khi nào? Xếp hạng các tính năng quan trọng nhất."]],
  ["E. Quyền riêng tư", ["Bạn và cha mẹ có chấp nhận các quyền sau không: gắn nhãn cuộc gọi; biết khi ứng dụng ngân hàng được mở trong lúc đang gọi; gửi cảnh báo cho con?"]],
  ["F. Mức giá (Van Westendorp)", ["Ở mức giá nào mỗi tháng bạn thấy gói Gia đình: quá rẻ đến mức nghi ngờ chất lượng; rẻ và đáng mua; bắt đầu đắt; quá đắt để mua?"]],
  ["G. Kênh và thí điểm", ["Bạn thường biết thông tin chống lừa đảo qua đâu?", "Bạn có muốn đăng ký cho gia đình tham gia thí điểm HỏiCon miễn phí không?"]],
];
for (const [sec, qs] of qa) {
  appA.push(new Paragraph({ children: inline(`**${sec}**`), spacing: { before: 120, after: 60 }, keepNext: true }));
  appA.push(...numbered(qs));
}

const appB = [];
appB.push(H1("PHỤ LỤC B. CÁC GIẢ ĐỊNH CỦA MÔ HÌNH TÀI CHÍNH"));
appB.push(tcap("Giả định chính của mô hình tài chính"));
const V = M.volumes;
appB.push(table(["Giả định", "Giá trị", "Ghi chú"], [
  ["Giá gói Gia đình", "49.000 đồng/tháng; 490.000 đồng/năm", "Thấp hơn nhiều so với sản phẩm tương tự ở Mỹ {{aura}}"],
  ["Doanh thu bình quân gói Gia đình", "45.000 đồng/tháng", "Một phần khách hàng chọn gói năm"],
  ["Phí đối tác B2B2C", "5.000 đồng/người dùng hoạt động/tháng; phí triển khai 100 triệu đồng (thí điểm 2027), 150 triệu đồng (từ 2028)", "Kiểm chứng qua phỏng vấn đối tác"],
  ["Chương trình cộng đồng", "40 triệu đồng/chương trình; chi phí trực tiếp 30%", "3 / 8 / 15 chương trình (2027 / 2028 / 2029)"],
  ["Chi phí biến đổi", "600 đồng (gói Cơ bản) và 6.000 đồng (gói Gia đình) mỗi gia đình/tháng; 2.000 đồng/người dùng B2B2C/tháng; phí thanh toán 2%", "Ước tính từ bảng giá công khai {{gemini}}{{claude}}{{zbs}}"],
  ["Gia đình sử dụng cuối năm", `${fmt(V[2027].free_end, 0)} / ${fmt(V[2028].free_end, 0)} / ${fmt(V[2029].free_end, 0)}`, "Bình quân năm bằng trung bình đầu kỳ và cuối kỳ"],
  ["Gia đình trả phí cuối năm", `${fmt(V[2027].paid_end, 0)} / ${fmt(V[2028].paid_end, 0)} / ${fmt(V[2029].paid_end, 0)}`, "Tỷ lệ trả phí 4–5%"],
  ["Người dùng B2B2C bình quân", `${fmt(V[2027].b2b_mau_avg, 0)} (3 tháng) / ${fmt(V[2028].b2b_mau_avg, 0)} / ${fmt(V[2029].b2b_mau_avg, 0)}`, "1 / 2 / 3 đối tác"],
  ["Nhân sự", "2027: 5 sáng lập bán thời gian và 1 cộng tác viên; 2028: 8 người; 2029: 12 người", "Lương bình quân 16–18 triệu đồng/tháng"],
  ["Thuế thu nhập doanh nghiệp", "20%, được chuyển lỗ", "Chưa tính các ưu đãi thuế có thể có"],
  ["Tỷ giá tham khảo", "1 USD ≈ 26.000 đồng", "Dùng cho các quy đổi tham khảo"],
], [2700, 3571, 2800], { boldFirst: true, keep: false }));

// Tai lieu tham khao (sinh sau cung de dung thu tu trich dan)
function referencesSection() {
  const out = [H1("TÀI LIỆU THAM KHẢO")];
  ORDER.forEach((k, i) => {
    out.push(new Paragraph({
      children: [new TextRun({ text: `[${i + 1}]`, font: FONT, size: 24, bold: true }), new TextRun({ children: [new Tab()] }), ...inline(REFS[k], { size: 24 })],
      tabStops: [{ type: TabStopType.LEFT, position: 680 }],
      indent: { left: 680, hanging: 680 }, alignment: AlignmentType.LEFT,
      spacing: { after: 80, line: 264 },
    }));
  });
  return out;
}

// =================================================================== LAP RAP
const headerP = (w) => new Header({ children: [new Paragraph({
  children: [
    new TextRun({ text: "HỏiCon – Trợ lý AI chống lừa đảo cho cả nhà", italics: true, size: 20, color: GRAYTXT, font: FONT }),
    new TextRun({ children: [new Tab(), "Tech Startup Challenger 2027"], italics: true, size: 20, color: GRAYTXT, font: FONT }),
  ],
  tabStops: [{ type: TabStopType.RIGHT, position: w }],
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: LINE, space: 4 } },
})] });
const footerP = () => new Footer({ children: [new Paragraph({
  alignment: AlignmentType.CENTER,
  children: [new TextRun({ children: ["Trang ", PageNumber.CURRENT], size: 22, color: GRAYTXT, font: FONT })],
})] });
const portrait = { size: { width: PW, height: PH }, margin: MARGIN };
const landscape = { size: { width: PW, height: PH, orientation: PageOrientation.LANDSCAPE }, margin: { top: 1134, bottom: 1134, left: 1134, right: 1134, header: 567, footer: 567 } };

// noi dung chinh duoc tao truoc de dem trich dan dung thu tu
const partA = [...front, ...c1, ...c2, ...c3, ...c4, ...c5];
const partB = [...c6];
const partC = [...c7, ...c8, ...c9, ...c10, ...c11, ...c12, ...c13, ...c14, ...cEnd];
const refs = referencesSection();
const partD = [...refs, ...appA, ...appB];

const doc = new Document({
  creator: "Đội HỏiCon",
  title: "HỏiCon – Bản mô tả ý tưởng dự án (Tech Startup Challenger 2027)",
  description: "Thuyết minh ý tưởng khởi nghiệp HỏiCon – trợ lý AI chống lừa đảo cho cả nhà",
  styles: {
    default: { document: { run: { font: FONT, size: BODY }, paragraph: { spacing: { line: 300, after: 120 } } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 30, bold: true, color: NAVY },
        paragraph: { spacing: { before: 120, after: 240 }, outlineLevel: 0, keepNext: true } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 28, bold: true, color: NAVY },
        paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 1, keepNext: true } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 28, bold: true, italics: true, color: NAVY },
        paragraph: { spacing: { before: 160, after: 80 }, outlineLevel: 2, keepNext: true } },
      { id: "TOC1", name: "toc 1", basedOn: "Normal", next: "Normal", run: { font: FONT, size: 26, bold: true }, paragraph: { spacing: { before: 60, after: 0, line: 276 } } },
      { id: "TOC2", name: "toc 2", basedOn: "Normal", next: "Normal", run: { font: FONT, size: 24 }, paragraph: { indent: { left: 440 }, spacing: { after: 0, line: 264 } } },
    ],
  },
  numbering: { config: [
    { reference: "bullets", levels: [
      { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 567, hanging: 284 } } } },
      { level: 1, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1134, hanging: 284 } } } },
    ] },
    { reference: "tbullets", levels: [
      { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 227, hanging: 170 } } } },
    ] },
    { reference: "numbers", levels: [
      { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 567, hanging: 340 } } } },
    ] },
  ] },
  sections: [
    { properties: { page: portrait, titlePage: false }, children: cover },
    { properties: { page: { ...portrait, pageNumbers: { start: 1 } } }, headers: { default: headerP(CW) }, footers: { default: footerP() }, children: partA },
    { properties: { page: landscape }, headers: { default: headerP(LCW) }, footers: { default: footerP() }, children: partB },
    { properties: { page: portrait }, headers: { default: headerP(CW) }, footers: { default: footerP() }, children: [...partC, ...partD] },
  ],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(OUT, buf);
  console.log("OK", OUT, "| bang:", tableNo, "| hinh:", figNo, "| tai lieu:", ORDER.length);
});
