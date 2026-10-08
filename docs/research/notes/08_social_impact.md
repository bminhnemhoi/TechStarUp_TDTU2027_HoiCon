# Social-impact business domain (Vietnam / HCMC, 2025–2026): problems an Agentic AI social business could address, and evaluation of candidate ideas for TDTU "Tech Startup Challenger 2027"

> **Scope and method (as of 04/10/2026).**
> - **How evidence was gathered.** The session-wide WebSearch cap (200 calls) ran out early. Almost all evidence therefore comes from direct page fetches: news articles and news tag pages, official portals, Wikipedia, developer documentation and vendor pricing pages. The fetches were done by me and by four sub-researchers covering disaster, food safety, public services/elderly/disability, and environment/migrant/funding.
> - **Unreachable official sites:**
>   - thuvienphapluat.vn (HTTP 403)
>   - vfa.gov.vn detail pages (HTTP 500)
>   - attp.hochiminhcity.gov.vn (DNS failure)
>   - mae.gov.vn (expired certificate)
>   - dolab.gov.vn (connection refused)
> - **Tags used:**
>   - **[BG]** = background, dated before 2025.
>   - **"headline"** = only the article title or tag-page summary was seen, not the full article.
>   - **"unverified"** = no URL confirmed in this session.
> - **Caution:** an AI summariser read each page, so spot-check numbers against the linked page before publishing.
> - **Exchange rate**, where used: US$1 ≈ 26,000 VND. This rate is my own assumption, not sourced.

---

## 1. Online fraud: scale, victims (especially the elderly), tactics, regulation, existing tools, what is unsolved, and what a family-guardian can technically do

### Takeaway
- **Scale.** Online fraud costs Vietnamese people **VND 6,000–8,000 billion a year (2025)**. The leading tactic is **police and authority impersonation aimed at the elderly**; investment, task and deepfake "relative" scams are rising.
- **Existing protection has a hole.** State, bank and OS-level defences are growing (biometrics, SIMO account warnings, SIM penalties from 01/07/2026, iOS 27 risk signals). But Vietnamese tools are free lookup databases (nTrust, chongluadao) or bank-side checks.
- **The open gap is the moment of manipulation.** An elder on a live call, told to keep it secret, under time pressure. Today only an attentive bank teller catches that.
- **What a guardian app can do.** A family-network, Vietnamese-language agent can do this on Android. On iOS it is limited to call labelling and blocking plus a family verification loop.

### Cited Findings

#### Scale and trend
- **2020–2025 totals (MPS).** The country had **24,295 online-fraud cases** with losses of **almost VND 40,000 billion**.
  - That is about VND 1.65 billion per case (simple division).
  - From 2022 to Oct 2025 there were about **17,200 cases** and "hundreds of thousands" of victims.
  - Speaker: Col. Nguyễn Thanh Hà, Deputy Director of the Criminal Police Dept. (MPS), at a seminar on 29/12/2025. He said 2025 cases were **cut by more than 20%**.
  - Source: [Tuổi Trẻ/NLĐ, 29/12/2025](https://tuoitre.vn/nld/bo-cong-an-5-nam-viet-nam-mat-gan-40000-ti-dong-vi-lua-dao-truc-tuyen-19625122919210539.htm)
- **2025 losses: two official figures.**
  - **NCA (National Cybersecurity Association), 07/01/2026, survey of 60,300 users:** losses over **VND 6,000 billion in the first 11 months of 2025**. Also 62,952 new mobile-malware types, and 88.05% of users received unsolicited offers (a sign of leaked personal data) — [CafeF](https://cafef.vn/nam-2025-thiet-hai-do-lua-dao-truc-tuyen-o-viet-nam-uoc-tinh-tren-6000-ty-dong-18826010807091841.chn)
  - **MPS figure:** **over VND 8,000 billion in 2025**. Released as data for the "Digital Trust in Finance 2026" forum. The Mr Pips case alone caused over VND 1,300 billion in losses across 738 cases — [VOV, 24/04/2026](https://vov.vn/phap-luat/thiet-hai-tu-lua-dao-truc-tuyen-len-toi-8000-ty-dong-trong-nam-2025-post1286479.vov). The same 8,000 bn figure is attributed to MPS in [Báo Pháp luật, 22/06/2026](https://doanhnhan.baophapluat.vn/hon-8-000-ty-dong-boc-hoi-vi-lua-dao-truc-tuyen-bo-cong-an-canh-bao-thu-doan-dau-hieu-nhan-biet-va-cach-phong-tranh-9b93d880.html)
- **NCA victim rate and reporting.**
  - Victim rate fell to **0.18% in 2025** (about 1 in 555) from **0.45% in 2024**.
  - Only **32.12% of victims reported to authorities**.
  - 34.13% of users experienced malware incidents.
  - Source: [Báo Hải Phòng (NCA report)](https://baohaiphong.vn/cac-hinh-thuc-lua-dao-truc-tuyen-nao-pho-bien-nhat-nam-2025-532711.html)
- **First 8 months of 2025 (A05, MPS Cybersecurity Dept.).**
  - **More than 1,500 cases, up 65% year on year**, with about VND 1,660 billion lost.
  - 4,532 malicious domains detected, up 90% — [Thanh Niên, 23/10/2025](https://thanhnien.vn/lua-dao-tang-manh-thiet-hai-hang-ngan-ti-dong-185251022190804651.htm)
  - Same 1,500 cases / VND 1,660 bn cited at an 18/12/2025 workshop — [Tuổi Trẻ/NLĐ](https://tuoitre.vn/nld/8-thang-dau-nam-2025-hon-1500-vu-lua-dao-truc-tuyen-tong-thiet-hai-1660-ti-dong-196251218171430287.htm)
  - Nhân Dân gives "gần 1.500 vụ… hơn 1.660 tỷ đồng" (nearly 1,500 cases, over VND 1,660 billion), plus one ring that took **more than VND 50 billion from more than 10,000 victims in about 100 days** — [Nhân Dân, 08/10/2025](https://nhandan.vn/so-nan-nhan-cua-lua-dao-tren-khong-gian-mang-ngay-cang-gia-tang-post913682.html)
  - **Conflict:** A05 reports +65% cases (8 months), the Criminal Police report −20% (full year), and NCA reports a falling victim rate. The report should show these side by side.
- **2026 data points.**
  - A Laos-based "task scam" ring (fake e-commerce order tasks, recruiting through Facebook) took **more than VND 1,500 billion from thousands of Vietnamese** from early 2026. 91 people were arrested on 12/09/2026 — [Tuổi Trẻ, 16/09/2026](https://tuoitre.vn/cong-an-sang-lao-bat-gon-o-nhom-lua-dao-qua-mang-chiem-doat-1500-ti-dong-cua-hang-ngan-nguoi-viet-100260916204859951.htm)
  - Chongluadao counts **more than 40,000 new malicious websites per day**, about 4.8 million per month — [Thanh Niên, 07/04/2026](https://thanhnien.vn/moi-ngay-xuat-hien-hon-40000-website-doc-hai-lua-dao-185260407153624153.htm)
- **Regional context (GASA).**
  - GASA's State of Scams in Southeast Asia 2025 (published 27/08/2025, 6,000 adults): **about 20% of Vietnamese encounter scams daily, the highest in the region**.
  - Region-wide: 63% experienced a scam; US$23.6 billion lost; phone calls (62%), SMS (56%) and instant messaging (49%) are the main channels.
  - Source: [GASA](https://gasa.org/knowledge-base/blog/new-study-reveals-63-of-southeast-asians-experienced-scams-in-past-year)
  - [BG] GASA put 2023 losses at **VND 391.8 trillion (US$16.23 billion), about 3.6% of GDP**. Only 1% of victims fully recovered their money — [VietnamPlus EN, 08/01/2024](https://en.vietnamplus.vn/vietnamese-loss-1623-billion-usd-to-online-scams-post276711.vnp)
- **Under-reporting.** Reported scam cases rose 70% from 2022 to 2024, and 54% of victims do not report — [Tech for Good Institute, 10/09/2025](https://techforgoodinstitute.org/insights/country-spotlights/building-digital-resilience-lessons-from-vietnam-2/)

#### Victims, especially the elderly and students
- **Elderly population.** Vietnam has about **16.1 million elderly people (more than 16% of the population)**.
  - HCMC police: **50% of fraud cases with elderly victims stem from fear of involving their grandchildren and lack of technology understanding**.
  - People aged 60+ are reported to be 6 times more likely to encounter fake news.
  - The article recommends family passwords and calling back on known numbers.
  - Source: [VietnamPlus, 27/03/2026](https://www.vietnamplus.vn/bao-ve-nguoi-cao-tuoi-truoc-cac-chieu-lua-dao-tinh-vi-tren-khong-gian-mang-post1101437.vnp)
- **Hà Tĩnh, Sept 2026** — [CAND, 02/10/2026](https://cand.vn/ma-tran-lua-dao-tren-khong-gian-mang-nham-vao-nguoi-gia-yeu-the-post823770.html):
  - A bank alert saved more than VND 1 billion in savings.
  - A woman born 1958 lost 4 chỉ vàng (taels of gold).
  - A man born 1950 was targeted for VND 6 billion.
  - Scripts: "you are linked to a drug ring"; fake police "guiding VNeID installation" and then sending malicious links.
- **Bank staff as the last line of defence.** On 30/09/2026 Agribank staff noticed a woman acting abnormally while withdrawing more than VND 1 billion under a fake-police script ("tell no one"). They called police, who stopped the transaction — [Tuổi Trẻ, 01/10/2026](https://tuoitre.vn/nguoi-phu-nu-di-rut-tien-ti-voi-thai-do-bat-thuong-nhan-vien-ngan-hang-bao-cong-an-100261001104136065.htm)
- **Students and parents.** HCMC Police, through the Department of Education and Training (DOET), warned **168 wards/communes and about 3,500 schools**. Scammers pose as a classmate to get a student's number, then call the student posing as police — [Thanh Niên, 02/01/2026](https://thanhnien.vn/tu-cong-van-cua-cong-an-tphcm-so-gd-dt-canh-bao-thu-doan-lua-dao-moi-185260102133152052.htm)
- **2026 victim profiles.** Elderly people, single people, students who need tuition money (predatory student-loan apps), and workers seeking jobs ("Kiếm tiền online" groups) — [Thanh Niên, 15/08/2026](https://thanhnien.vn/lua-dao-truc-tuyen-giang-bay-khap-noi-185260814221226634.htm)
- Young, tech-savvy people are now also victims — [Thanh Niên, 23/10/2025](https://thanhnien.vn/lua-dao-tang-manh-thiet-hai-hang-ngan-ti-dong-185251022190804651.htm)
- **Demand signal.** Citizens queued for hours to join an anti-scam learning activity — [Thanh Niên, 14/06/2026](https://thanhnien.vn/nguoi-dan-xep-hang-chen-kin-de-hoc-chong-lua-dao-qua-mang-185260614110904479.htm)

#### Dominant tactics
- **NCA top 5 for 2025:**
  1. Impersonating police or authorities
  2. Prize and gift scams
  3. "High-profit" investment
  4. Fake delivery staff
  5. Romance scams
  - Source: [CafeF](https://cafef.vn/nam-2025-thiet-hai-do-lua-dao-truc-tuyen-o-viet-nam-uoc-tinh-tren-6000-ty-dong-18826010807091841.chn)
- **MPS warnings (2026):**
  - Deepfake video calls impersonating relatives or officials.
  - Fake investment platforms.
  - Malicious **.apk files** that allow remote control and OTP theft.
  - Look-alike bank and government domains.
  - Source: [Báo Pháp luật, 22/06/2026](https://doanhnhan.baophapluat.vn/hon-8-000-ty-dong-boc-hoi-vi-lua-dao-truc-tuyen-bo-cong-an-canh-bao-thu-doan-dau-hieu-nhan-biet-va-cach-phong-tranh-9b93d880.html)
- **ACB's 30 scenarios:**
  - Deepfake video and voice of relatives.
  - **"Silent calls" made to record voice samples for deepfakes.**
  - Fake teacher or health-worker emergency videos.
  - Social-media account takeover.
  - Source: [Thanh Niên, 23/06/2026](https://thanhnien.vn/acb-canh-bao-30-kich-ban-lua-dao-truc-tuyen-pho-bien-tai-viet-nam-185260623105131392.htm)
- **Chongluadao's 8 scams aimed at the elderly:**
  1. Fake legal authority ("transfer to a safe account")
  2. Family emergency
  3. Fake bank SMS
  4. Hijacked relatives' accounts
  5. Impersonators visiting the home
  6. Investment scams
  7. Health seminars and "miracle products"
  8. Fake charity
  - Source: [Thanh Niên, 28/07/2026](https://thanhnien.vn/canh-bao-8-chieu-tro-lua-dao-nham-vao-nguoi-cao-tuoi-185260728154001279.htm)
- **Utility impersonation.** Fake EVN (electricity) calls threaten "power cut within 20 hours", backed by a fake fanpage and a fake app or Zalo contact. PayTech logged 546 contacts from affected customers between 31/10/2024 and 22/01/2025 in HCMC — [Thanh Niên, 25/02/2025](https://thanhnien.vn/ro-thu-doan-gia-nhan-vien-doi-cat-dien-diem-mat-cach-lua-dao-185250225200811774.htm)
- **Tax impersonation (HCMC Tax warning).**
  - Links to "verify tax debt" or claim refunds; fake apps other than eTax Mobile.
  - Genuine calls show the caller name "Thue TP.HCM".
  - Source: [Thanh Niên, 13/08/2026](https://thanhnien.vn/thue-tphcm-luu-y-nhan-dien-lua-dao-tu-cuoc-goi-185260813120338251.htm)
- **"Recovery" scams aimed at past victims.**
  - A fake page, "Viện Kiểm Sát – Liên Kết Ngân Hàng Hỗ Trợ" (fake prosecutor's office "bank support link"), offers to trace lost money for a fee — [Kenh14, 02/10/2026](https://kenh14.vn/cong-an-canh-bao-quan-trong-den-nguoi-dung-facebook-21526100210224978.chn)
  - Google's November 2025 advisory also lists fraud-recovery scams and online job scams among top global trends — [Google](https://blog.google/innovation-and-ai/technology/safety-security/fraud-and-scams-advisory-november-2025/)

#### Regulatory measures (why now)
- **[BG] Biometrics for large transfers.** From 01/07/2024, transfers above VND 10 million require biometric authentication (headline; Decision 2345/QĐ-NHNN text not fetched) — [Thanh Niên, 28/05/2024](https://thanhnien.vn/chuyen-khoan-tren-10-trieu-phai-xac-thuc-sinh-trac-hoc-tu-17-nham-chong-lua-dao-185240528174643297.htm)
- **Circulars 17/2024/TT-NHNN and 18/2024/TT-NHNN.**
  - Customers must match their face to the national population database or VNeID before electronic transactions.
  - Deadlines: **individuals from 01/01/2025; organisations from 01/07/2025** — [Thanh Niên, 29/05/2025](https://thanhnien.vn/diem-mat-chi-ten-gui-tai-khoan-nghi-ngo-lua-dao-sang-ngan-hang-nha-nuoc-18525052912181878.htm)
  - Unverified accounts lose internet/mobile transfers, ATM, card and e-wallet functions — [hatinh.gov.vn](https://hatinh.gov.vn/vi/bai-viet/nhung-giao-dich-se-bi-dung-neu-khong-xac-thuc-tai-khoan-truoc-112025)
  - **From 01/01/2026**, accounts without updated chip-ID/VNeID level-2 data or biometrics are suspended for transfers, withdrawals and payments — [VTV, 01/01/2026](https://vtv.vn/tu-1-1-2026-nhieu-tai-khoan-ngan-hang-bi-ngung-giao-dich-do-chua-cap-nhat-cccd-100260101130903656.htm); [Thị trường Tài chính Tiền tệ, 01/01/2026](https://thitruongtaichinhtiente.vn/nhung-truong-hop-tai-khoan-ngan-hang-nao-bi-ngung-chuc-nang-rut-tien-chuyen-khoan-va-thanh-toan-tu-ngay-1-1-2026-75857.html)
- **SBV suspicious-account database ("SIMO").**
  - Banks report suspicious accounts and **warn customers who transfer to flagged accounts**.
  - BIDV piloted the warnings from **01/04/2025** and retained more than **VND 100 billion**.
  - Scheduled launches at other banks: Vietcombank 30/06, VietinBank 04/07, MB 14/07, Agribank 24/07/2025.
  - Source: [Thanh Niên, 29/05/2025](https://thanhnien.vn/diem-mat-chi-ten-gui-tai-khoan-nghi-ngo-lua-dao-sang-ngan-hang-nha-nuoc-18525052912181878.htm)
- **ACB.**
  - In H1 2025 it blocked **more than 20,000 fraudulent transactions**, protecting about **VND 1,500 billion** — [Thanh Niên, 08/10/2025](https://thanhnien.vn/lua-dao-ngay-cang-tinh-vi-ngan-hang-dang-lam-gi-de-bao-ve-nguoi-dung-185251008090520098.htm)
  - It runs a three-tier alert system; level 3 auto-blocks the transfer — [Thanh Niên, 23/06/2026](https://thanhnien.vn/acb-canh-bao-30-kich-ban-lua-dao-truc-tuyen-pho-bien-tai-viet-nam-185260623105131392.htm)
- **Decree 174 on telecom/IT administrative penalties (effective 01/07/2026; year suffix unverified).**
  - Using SIMs not registered to oneself: **VND 200,000–500,000 per subscription** (1–10 SIMs), rising to **VND 30–50 million** (501+ SIMs) — [Thanh Niên, 02/07/2026](https://thanhnien.vn/co-tinh-su-dung-sim-khong-chinh-chu-se-bi-phat-tien-len-den-50-trieu-dong-185260702000142323.htm)
  - Using technology (AI, deepfakes) to forge identity or biometric data for SIM registration: **VND 80–100 million** — [Thanh Niên, 22/07/2026](https://thanhnien.vn/canh-bao-phat-toi-100-trieu-dong-neu-dung-ai-tao-anh-gia-dang-ky-sim-185260722160744747.htm)
- **Amended Cybersecurity Law, effective 01/07/2026.** It requires account traceability. The government must also research linking social-media accounts to VNeID by Q2 2026. Ngô Minh Hiếu (chongluadao) warns identity checks are "not a cure-all" — [VOV, 27/02/2026](https://vov.vn/xa-hoi/tich-hop-mang-xa-hoi-voi-vneid-xac-thuc-danh-tinh-se-het-lua-dao-truc-tuyen-post1271458.vov)
- **Personal Data Protection Law** (2025), effective 2026 — [Tech for Good Institute](https://techforgoodinstitute.org/insights/country-spotlights/building-digital-resilience-lessons-from-vietnam-2/). The number 91/2025/QH15 and effective date 01/01/2026 are unverified this session.
- **Funding signal.** Google.org gives **US$5 million to "Scam Ready ASEAN" (2025–2027)**, with Chống Lừa Đảo as Vietnam's implementing partner.
  - Vietnam targets: train 90 anti-scam specialists (at least 55% women) and equip 25,000 people.
  - Includes the "Be Scam Ready" game.
  - Source: [Thanh Niên, 26/08/2026](https://thanhnien.vn/du-an-chong-lua-dao-nhan-ho-tro-tu-google-185260826144700166.htm)

#### Existing tools in Vietnam
- **nTrust (NCA, launched 30/07/2024 [BG]).**
  - Free. Checks phone numbers, bank accounts, links and QR codes; scans installed apps; blocks known numbers.
  - Database of 1 million+ records from MPS, the Ministry of Information and Communications (MIC), SBV and member organisations. Suspicious-call detection runs on the device — [VnExpress](https://vnexpress.net/ra-mat-phan-mem-giup-phat-hien-lua-dao-mang-4775737.html)
  - iOS: **3.4/5 from 250 ratings; latest version 1.0.6 dated 11/10/2024**. One review says it seems to "collect victim data rather than protect" — [App Store](https://apps.apple.com/vn/app/ntrust-ph%C3%B2ng-ch%E1%BB%91ng-l%E1%BB%ABa-%C4%91%E1%BA%A3o/id6504554337)
  - Android "100K+ downloads" comes only from a search snippet (unverified).
- **Chống Lừa Đảo (chongluadao.vn)** — figures by mid-2025, from [Tech for Good Institute, 10/09/2025](https://techforgoodinstitute.org/insights/country-spotlights/building-digital-resilience-lessons-from-vietnam-2/):
  - Browser extension: more than 200,000 threats blocked, about 45,000 monthly active users.
  - AI chatbot on Telegram and web: more than 200,000 verifications.
  - Lookup portal: more than 7 million queries, about 270,000 monthly users.
  - **Threat-intelligence API: more than 1 million calls a day across 15+ partners.**
  - 500–1,000 crowd reports a day; more than 26,000 victims assisted.
  - Its free AI website-risk analyser was built by 4 Swinburne Vietnam students (claims over 98% accuracy) — [Thanh Niên, 21/04/2025](https://thanhnien.vn/4-thanh-nien-tao-cong-cu-chong-lua-dao-truc-tuyen-bang-ai-185250421154003719.htm)
- **Bank-side protections:** SIMO warnings and ACB alerts (see above).
- **Government AI precedent.** HCMC Tax launched an AI call centre for debt reminders and exit-ban notices.
  - Serves 650,000 business households, 350,000 enterprises and 8 million individual taxpayers.
  - Safeguards: caller name "Thue TP.HCM", calls of 3 minutes at most, no links, all calls recorded and transcribed.
  - Source: [Tuổi Trẻ, 08/08/2026](https://tuoitre.vn/thue-tphcm-ra-mat-tong-dai-ai-ho-tro-nhac-no-thong-bao-tam-hoan-xuat-canh-100260808181834978.htm)

#### Platform (OS) protections and their limits for Vietnam
- **Google Play Protect "enhanced fraud protection".**
  - Started as a Singapore pilot ([BG] [SecurityWeek, Feb 2024](https://www.securityweek.com/google-announces-enhanced-fraud-protection-for-android/)). It blocks sideloaded apps that request RECEIVE_SMS, READ_SMS, BIND_NOTIFICATIONS or Accessibility.
  - By Feb 2026 it covered **185 markets and 2.8 billion devices**, blocking 266 million risky installs in 2025. Vietnam is not named — [Google, 19/02/2026](https://blog.google/security/keeping-google-play-android-app-ecosystem-safe-2025/)
  - A search snippet said the pilot covered "nine regions including Vietnam" (unverified).
- **In-call protections.** During calls with unknown contacts, Android blocks sideloading, granting Accessibility, and disabling Play Protect. Scam Detection in Google Messages uses on-device AI — [TechCrunch, 13/05/2025](https://techcrunch.com/2025/05/13/google-announces-new-security-features-for-android-for-protection-against-scam-and-theft/)
- **Pixel call "Scam Detection" (Gemini Nano)** is available in the US, Australia, Canada, India, Ireland and the UK. It is expected on Galaxy S26. **Vietnam is not listed** — [Thanh Niên, 01/02/2026](https://thanhnien.vn/galaxy-s26-sap-co-tinh-nang-dang-tien-nhat-tren-pixel-185260201174214127.htm)
- **iOS 27 "Trust Insights".**
  - Mostly on-device analysis of interaction patterns, timing and context. Flags **medium/high risk** to apps, which can add warnings, **transaction delays** or extra verification.
  - Switching it off involves mandatory waiting periods — [Thanh Niên, 03/07/2026](https://thanhnien.vn/tinh-nang-moi-tren-ios-27-giup-tang-cuong-chong-lua-dao-185260703104422657.htm)
  - The "Impersonation Risk Detection" setting is off by default and shares only the risk level with compatible apps — [Thanh Niên, 18/09/2026](https://thanhnien.vn/cach-kich-hoat-tinh-nang-chong-lua-dao-mao-danh-moi-tren-ios-27-185260917081305572.htm)

#### What a family-guardian app can technically do

**Android:**
- **Call screening.** `CallScreeningService` screens incoming calls from contacts and non-contacts. It can reject, silence, or skip the call log or notification. It has **no access to call audio** and needs the call-screening role — [Android docs](https://developer.android.com/reference/android/telecom/CallScreeningService)
- **SMS and call logs.** Google Play allows `READ_SMS/RECEIVE_SMS` only for default handlers or approved exceptions. Exceptions include **"Anti-SMS phishing ('smishing')"** and **"Caller ID, spam detection, and/or spam blocking"** — [Google Play policy](https://support.google.com/googleplay/android-developer/answer/10208820)
- **Notifications.** `NotificationListenerService` receives other apps' notifications, including text, once the user grants "Notification access" — [Android docs](https://developer.android.com/reference/android/service/notification/NotificationListenerService)
  - Android 15 stops **untrusted listeners** reading unredacted notifications that contain OTPs.
  - It hides sensitive content during screen sharing and shows a prominent status-bar chip during screen projection (15 QPR1) — [Android 15 behaviour changes](https://developer.android.com/about/versions/15/behavior-changes-all)
- **Accessibility.** Apps that are not accessibility tools need prominent disclosure and consent. **"Autonomous functionality is prohibited except for deterministic, rule-based automation"** — [Google Play Accessibility policy](https://support.google.com/googleplay/android-developer/answer/10964491)

**iOS:**
- **Call Directory extension:** identifies and labels or blocks incoming numbers from an app-supplied list (iOS 10+) — [Apple docs](https://developer.apple.com/tutorials/data/documentation/callkit/cxcalldirectoryprovider.json)
- **IdentityLookup framework:** SMS/MMS **Message Filter** (not iMessage), unwanted-communication reporting, and **Live Caller ID Lookup** — [Apple docs](https://developer.apple.com/tutorials/data/documentation/identitylookup.json)
- **Live Caller ID Lookup** uses private information retrieval with homomorphic encryption. It needs Apple registration and entitlements and returns metadata only; there is no access to call audio or SMS content — [Apple GitHub example](https://github.com/apple/live-caller-id-lookup-example)

#### Global comparables and pricing
- **Aura** — [Aura pricing](https://www.aura.com/pricing):
  - Individual: **US$12/month** billed annually (US$15 monthly).
  - Couple: US$22/US$29.
  - **Family: US$32/US$50** for 5 adults. Includes "AI Spam Call & Message Protection", "Financial Transaction Alerts", "Family Fraud Alerts Sharing" and US$5M identity-theft insurance.
- **Apate.ai** — [Apate.ai](https://www.apate.ai/):
  - Conversational AI bots that **engage scammers to waste their time and extract intelligence** ("Detect. Divert. Disrupt. Decode.").
  - Customers include TPG Telecom and Commonwealth Bank. Pricing is custom.

### Inferences
- **What remains unsolved: the live-manipulation window.**
  - Lookup tools (nTrust, chongluadao) only help if the user thinks to use them.
  - SIMO warns only at the transfer step, and only for accounts already flagged.
  - The Hà Tĩnh and Agribank cases were stopped only by **in-branch human observation**. App transfers have no equivalent "teller who notices you are scared".
  - An agent that detects risky sequences, such as an unknown caller → claimed authority → screen-sharing, APK install or banking-app activity, and then pulls a trusted family member into the loop, would recreate that intervention digitally.
- **Fraud is moving toward:** VNeID/police impersonation, recovery scams, task and job scams, deepfake relatives, and malware APKs. OS-level AI scam detection is **not offered in Vietnam/Vietnamese** per the available evidence. A Vietnamese-language, family-network agent layer is therefore a real gap. The window may close if Google or Apple localise.
- **Technical design implications:**
  - Build Android first.
  - On iOS, offer labelling and blocking (Call Directory / Live Caller ID), SMS filtering, a link/QR/account checker in the share sheet, and the family verification loop.
  - Do **not** rely on an LLM autonomously driving the elder's phone through Accessibility; Play policy forbids non-deterministic autonomy.
  - Run the "agentic" part on the server and in the guardian app: lookups, escalation, call-back scripts, report drafting, follow-up. On the device, use deterministic rules and user-initiated actions such as an "Ask my child" button.
- **Trust design.** Scammers already impersonate "fund recovery" and "VNeID support", so the product must never send links by SMS. It should use a verified Zalo Official Account (OA), branded caller names (the HCMC Tax pattern) and family code words, as VietnamPlus recommends.
- **Broader audience.** Students are also targets (task scams, fake jobs, fake-police calls to students), so a "family circle" guardian can protect both directions. That strongly raises appeal to the TDTU student voting audience.

### Gaps
- No verified national or HCMC share of victims aged 60+, and no average loss per elderly victim.
- National statistics for H1 or 9 months of 2026 were not found. A search snippet claimed Q1 2026 had more than 700 cases and more than VND 600 billion lost; unverified.
- Not verified:
  - Telco anti-scam measures and their prices (Viettel/VNPT/MobiFone labelling or AI blocking).
  - Whether SIMO or bank APIs are open to third parties (assume not).
  - Local price anchors for consumer security apps (Bkav, Kaspersky VN).
  - Cyber-fraud insurance products (VBI's page could not be read).
- Legal details not fetched: Decision 2345/QĐ-NHNN (only a 2024 headline was seen), the year suffix of Decree 174, and the Personal Data Protection Law (PDPL) number and date.
- Unknown whether iOS 27 risk signals can be read by non-financial third-party apps (for example, a family-guardian app).
- Not verified: the exact Android permissions for detecting app-usage context (UsageStats / special access).

---

## 2. Disaster response: Typhoon Yagi (2024) and the 2025 floods, SOS handling, government systems, and opportunities

### Takeaway
- **2025 matched Yagi's losses.** Bualoi, Matmo and the Oct–Dec Central floods added up to roughly VND 85 trillion, about the same as Yagi's VND 84.5 trillion in 2024. The Central floods left 218 dead or missing.
- **The state system mostly senses and broadcasts.** VNDMS monitors hazards, and in Nov 2025 authorities sent 26.4 million SMS and 24.1 million Zalo warnings. No structured two-way SOS intake, triage and dispatch channel was found.
- **Physical limits.** Telecom outages (9,235 BTS sites down during Yagi) and post-merger place names constrain any solution.
- **How SOS requests were actually collected and coordinated (volunteer maps, spreadsheets, Facebook) could not be verified.** This is a key gap to close with field interviews.
- **Fundability.** Anticipatory action, meaning forecast-triggered aid to households registered in advance, is promoted in the press and may be easier to fund than pure dispatch software.

### Cited Findings
- **Yagi [BG].**
  - Deaths and injuries: at least 321 dead (government figure 325), 24 missing, about 1,978–1,987 injured; total loss **VND 84,543 billion (≈US$3.47 bn)** — [Wikipedia: Typhoon Yagi](https://en.wikipedia.org/wiki/Typhoon_Yagi)
  - **Conflicting figures:** Vietnamese Wikipedia gives 325 dead, **20** missing and **2,046** injured, and VND 84,544 billion — the largest disaster loss on record in Vietnam — [vi.wikipedia: Bão Yagi](https://vi.wikipedia.org/wiki/B%C3%A3o_Yagi_%282024%29)
  - **Telecom collapse:** **9,235 BTS sites lost connectivity**, and some carriers lost more than 50% of their network. A forward command post was set up in Hải Phòng — [vi.wikipedia](https://vi.wikipedia.org/wiki/B%C3%A3o_Yagi_%282024%29)
  - **Response:** **460,000 military personnel** mobilised. The Central Relief Fund had about **VND 1,495 billion by 19/09/2024**, and preliminary insured losses were above VND 2 trillion.
  - **Major incidents:** Làng Nủ flash flood (at least 48 dead, 39 missing) and the Phong Châu bridge collapse — [Wikipedia](https://en.wikipedia.org/wiki/Typhoon_Yagi)
- **2025 storms.**
  - **Bualoi** (landfall 29/09/2025): 57 dead, 10 missing; **VND 23.9 trillion**, the second-costliest tropical cyclone in Vietnam — [Wikipedia: Bualoi](https://en.wikipedia.org/wiki/Typhoon_Bualoi_%282025%29)
  - **Matmo** (Oct 2025): 16 dead, more than 230,000 houses flooded; **VND 21.01 trillion**. The Cầu River exceeded its Yagi record and the Thất Khê 1 dam burst — [Wikipedia: Matmo](https://en.wikipedia.org/wiki/Typhoon_Matmo_%282025%29)
  - **Kalmaegi** (landfall 06/11/2025): 6 dead; **VND 13.097 trillion**; more than **1.6 million households lost power**; about 350,000 people evacuated in Gia Lai; more than 260,000 personnel and 6,700 vehicles deployed — [Wikipedia: Kalmaegi](https://en.wikipedia.org/wiki/Typhoon_Kalmaegi_%282025%29). **Conflict:** 333 vs 2,365 houses collapsed — [Wikipedia: 2025 in Vietnam](https://en.wikipedia.org/wiki/2025_in_Vietnam)
- **Central Vietnam floods, 16/10–06/12/2025** — [vi.wikipedia: Lũ lụt miền Trung 2025](https://vi.wikipedia.org/wiki/L%C5%A9_l%E1%BB%A5t_mi%E1%BB%81n_Trung_Vi%E1%BB%87t_Nam_2025):
  - **218 dead or missing; VND 40,471 billion**.
  - **Đắk Lắk had 113 dead**, and **1.19 million electricity customers** were cut off.
  - Bạch Mã recorded **1,739.6 mm in 24 hours**, a national record.
  - The Central Relief Committee had received more than **VND 1,175 billion** by 05/12/2025.
  - The English article gives about VND 82 trillion with a wider scope — [Wikipedia: 2025 Vietnam floods](https://en.wikipedia.org/wiki/2025_Vietnam_floods)
- **Warnings were one-way.** The Disaster and Dyke Management Authority (VDDMA) and the Telecom Authority sent **two SMS rounds to 26.4 million subscribers** from Hà Tĩnh to Lâm Đồng. **Zalo sent 24.1 million warning messages**, 4.7 million of them on 19/11 alone — [SGGP, 20/11/2025](https://www.sggp.org.vn/share824458.html)
- **Reservoir discharge as a risk signal.** Sông Ba Hạ released 16,100 m³/s on 19/11/2025, its largest ever. The Deputy PM said operating rules assume single floods. MPS is investigating, and the Ministry of Agriculture and Environment (MAE) is revising inter-reservoir rules — [vi.wikipedia](https://vi.wikipedia.org/wiki/L%C5%A9_l%E1%BB%A5t_mi%E1%BB%81n_Trung_Vi%E1%BB%87t_Nam_2025)
- **Ad-hoc rescue.** One volunteer rescued about 100 residents overnight on 18–19/11/2025 in Hòa Thịnh with a single boat. He prioritised elderly people, pregnant women and children; no coordination system is described — [Tuổi Trẻ, 30/11/2025](https://tuoitre.vn/nghia-dong-bao-ky-5-vuot-lu-du-de-cuu-nguoi-20251130100747888.htm)
- **Relief-coordination problems** — [Tuổi Trẻ Cuối tuần, 13/12/2025](https://cuoituan.tuoitre.vn/neu-cuu-tro-den-truoc-thien-tai-20251212102101647.htm):
  - Khánh Hòa paid VND 1 million per person only to registered residents present at home, a rule criticised as "rigid".
  - Lâm Đồng officials were arrested for misappropriating VND 500 million from the Fatherland Front fund.
  - The article proposes **anticipatory, forecast-triggered cash transfers**, pre-registered beneficiary databases and e-wallet payouts ("each $1 before a disaster saves up to $7").
- **Government systems.** VNDMS, run by VDDMA under MAE, publishes public layers: rainfall, water levels against 3 alert levels, **reservoir discharge**, flash-flood and landslide warnings, salinity, erosion and vessel tracking. It offers email alerts and PDF/Excel export but **no documented public API** — [VNDMS](https://vndms.gov.vn/)
- **Coordination body.** 2025 damage was reported through the **National Civil Defense Steering Committee** — [Wikipedia: Bualoi](https://en.wikipedia.org/wiki/Typhoon_Bualoi_%282025%29)
- **2026 so far.**
  - Maysak made landfall at Móng Cái on 04/07/2026; Narra (Aug 2026) killed 1 — [Wikipedia: 2026 Pacific typhoon season](https://en.wikipedia.org/wiki/2026_Pacific_typhoon_season)
  - **HCMC had record flooding on Phan Huy Ích street**, with buses stalled (headline, 30/09/2026) — [Tuổi Trẻ](https://tuoitre.vn/duong-phan-huy-ich-ngap-nang-ky-luc-nuoc-tran-vao-khien-xe-buyt-chet-may-la-liet-10026093021260881.htm)
  - The UN warns El Niño may be the strongest in 40 years (headline, 03/09/2026) — [Tuổi Trẻ](https://tuoitre.vn/el-nino-co-the-manh-nhat-40-nam-lhq-canh-bao-the-gioi-buoc-vao-vung-nguy-hiem-100260903201431119.htm)
  - Khánh Hòa lets schools close in heavy rain (headline, 11/09/2026) — [Tuổi Trẻ](https://tuoitre.vn/khanh-hoa-giao-cac-truong-chu-dong-cho-hoc-sinh-nghi-hoc-khi-mua-lon-lu-lut-100260911200832487.htm)
  - Hà Nội opened a 24/7 "smart police station" for reports and SOS (headline, 15/08/2026) — [Tuổi Trẻ](https://tuoitre.vn/ha-noi-co-tram-canh-sat-thong-minh-ho-tro-trinh-bao-goi-sos-24-7-10026081518511693.htm)
  - A volunteer "SOS đèo Lò Xo" team used drones to supply stranded drivers (headline, 28/10/2025) — [Tuổi Trẻ](https://tuoitre.vn/dung-may-bay-khong-nguoi-lai-dua-nhu-yeu-pham-len-deo-lo-xo-tiep-te-cho-tai-xe-bi-ket-20251028203523158.htm)
- **Open data for an MVP.** The Open-Meteo Flood API uses GloFAS v4 at about 5 km, with 50 ensemble members and forecasts up to 7 months ahead. It is free for non-commercial use; commercial use needs a key — [Open-Meteo](https://open-meteo.com/en/docs/flood-api)
- **[BG] World Bank precedent.** The Can Tho Urban Development and Resilience project "protected 420,000 residents" with infrastructure and digital risk tools — [World Bank](https://www.worldbank.org/en/country/vietnam/overview)
- **Post-merger geography.** 34 provincial units under Resolution 202/2025/QH15 (12/06/2025). HCMC merged with Bình Dương and Bà Rịa–Vũng Tàu. Mekong merges include Cần Thơ + Hậu Giang + Sóc Trăng and Vĩnh Long + Bến Tre + Trà Vinh — [Wikipedia: Provinces of Vietnam](https://en.wikipedia.org/wiki/Provinces_of_Vietnam)

### Inferences
- **What exists vs what is missing.** The verified Vietnamese stack is sensing (VNDMS) plus broadcasting (SMS and Zalo). Missing is the loop that takes in SOS from Zalo, Facebook, SMS and hotlines, removes duplicates, geolocates, ranks severity, dispatches with human approval, tracks status and follows up. This gap is inferred from what was found, not proven: volunteer tools probably existed but could not be verified.
- **Design constraints:**
  - Telecom and power outages (9,235 BTS down; 1.19–1.6 million customers without power) mean SOS messages arrive in bursts after reconnection. The system needs SMS fallback and staleness scoring.
  - Old place names after the 2025 merger require an old-to-new address mapping table.
  - Reservoir-discharge layers in VNDMS can predict where downstream SOS demand will spike.
- **Business reality.**
  - Buyers are state (B2G) and NGO actors, and money flows through the Fatherland Front (VND 1,175–1,495 billion per major event).
  - Insured losses are only about 2.4% of economic loss (Yagi, preliminary).
  - A more fundable framing combines **anticipatory action** (forecast-triggered alerts plus pre-registered vulnerable households for cash or aid, with human approval) with SOS triage. The pitch would go to NGOs, the Red Cross, insurers and telco/platform CSR.
- **HCMC relevance.** Urban and tidal flooding in Sept 2026 and Mekong salinity give a local angle. Flood season (Oct–Dec) overlaps Round 1, which allows field interviews and live data collection.

### Gaps
- **Not verified:** how SOS requests were collected and coordinated in Yagi and in 2025 — Facebook groups, Zalo, volunteer maps, Google Sheets, and the role of hotlines 112/114 and VNeID — and the failure modes (duplicates, stale requests, misinformation). No official after-action reviews were found.
- **Legal and financial texts not verified:**
  - Law on Natural Disaster Prevention and Control 33/2013/QH13 and its amendment 60/2020/QH14.
  - Civil Defense Law 18/2023/QH15 (effective 01/07/2024).
  - The decision creating the National Civil Defense Steering Committee.
  - The annual size of the Natural Disaster Prevention and Control Fund.
- **Market data not verified:** budgets or contract values for disaster technology; 2025–2026 funding calls (UNDP, ADB, Google.org); parametric insurance in Vietnam; pricing of global tools (Ushahidi, Everbridge, Zello).
- **Conflict:** 34 units described as 28 provinces + 6 cities vs Wikipedia's 25 + 9 (as of 20/09/2026).

---

## 3. Food safety: mass poisoning in schools and industrial canteens, legal obligations, existing tools

### Takeaway
- **Incidents are rising.** Collective food poisoning rose in H1 2026, including school kitchens: 12 outbreaks and 741 students per one Tuổi Trẻ report. September 2026 brought large industrial-canteen incidents (Scavi Huế, 222 workers).
- **HCMC has a live school-meal quality crisis (Sept–Oct 2026).** Parents are complaining, schools are changing suppliers, inviting surprise parent inspections and publishing menus, temperature logs and receipts, and the city's Department of Education issued urgent notices on 01/10/2026.
- **The law is being rewritten toward risk-based post-inspection and a national supply-chain database.** That makes digital, verifiable self-monitoring records valuable.
- **No localised digital 3-step-inspection / sample-retention product was found.** Global tools cost about US$300–3,600 per site per year.

### Cited Findings
- **H1 2026 national statistics** — [Tuổi Trẻ, 28/07/2026](https://tuoitre.vn/phong-thuc-pham-ban-hay-xay-them-benh-vien-ky-1-thuc-pham-ban-bua-vay-hon-200-benh-tu-bua-an-100260727210603361.htm):
  - **58 outbreaks, 1,573 people affected, 10 deaths**, 23 more outbreaks than a year earlier.
  - **School kitchens: 12 outbreaks, 741 students**, which is 9 more outbreaks and 686 more students.
  - Police handled **4,688 food-safety violation cases (+102%)**, with 95 criminal cases (+265%) and 192 defendants.
  - The Ministry of Health (MoH) inspected 118,009 facilities and found 5,695 violations (4.83%).
- **Conflicting count.** The next part of the same series reports **36 outbreaks** so far in 2026 (+20 year on year), 9 of them large (30+ victims, 25%), mainly in collective kitchens, school canteens and street food. It quotes Minister Đào Hồng Lan — [Tuổi Trẻ, 29/07/2026](https://tuoitre.vn/phong-thuc-pham-ban-hay-xay-them-benh-vien-ky-2-benh-vien-ganh-them-ap-luc-vi-ngo-doc-thuc-pham-100260727213210473.htm). The two parts may cover different periods or definitions; use both with this caveat.
- **Industrial canteen: Scavi Huế (Phong Điền industrial zone), Sept 2026.**
  - 174 workers hospitalised on 11–12/09, rising to **222**.
  - **E. coli and Bacillus cereus** found in the in-house canteen's dishes, which **served 4,060 meals on 10/09**.
  - The Food Safety Department ordered tracing, sampling, and checks of **3-step inspection and retained samples** — [Tuổi Trẻ, 22/09/2026](https://tuoitre.vn/222-cong-nhan-hue-ngo-doc-thuc-pham-tim-thay-2-loai-vi-khuan-trong-thuc-an-100260922152835031.htm); [Tuổi Trẻ, 12/09/2026](https://tuoitre.vn/yeu-cau-dieu-tra-vu-ngo-doc-thuc-an-174-cong-nhan-nhap-vien-100260912180126796.htm)
  - Scavi paid all treatment costs (headline) — [Tuổi Trẻ, 13/09/2026](https://tuoitre.vn/vu-hon-180-cong-nhan-ngo-doc-thuc-pham-o-hue-cong-ty-scavi-hue-ho-tro-toan-bo-chi-phi-dieu-tri-100260913101126795.htm)
- **Other 2026 incidents (headlines):**
  - Gia Lai: **254 people** poisoned by bánh mì; fine **VND 100 million** plus hospital costs — [Tuổi Trẻ, 17/09/2026](https://tuoitre.vn/254-nguoi-ngo-doc-banh-mi-tai-gia-lai-phat-100-trieu-dong-buoc-lo-vien-phi-cho-thuc-khach-100260917162026479.htm)
  - **HCMC (Lái Thiêu): 20 hospitalised** after bánh mì from a mobile cart — [Tuổi Trẻ, 18/09/2026](https://tuoitre.vn/20-nguoi-nhap-vien-sau-khi-an-banh-mi-ban-tren-xe-luu-dong-tai-lai-thieu-tphcm-100260918193306659.htm)
  - Quảng Trị: 46+ people — [Tuổi Trẻ, 16/09/2026](https://tuoitre.vn/vu-46-nguoi-nghi-ngo-doc-banh-mi-tai-quang-tri-me-va-vo-chu-tiem-cung-nhap-vien-100260916180655591.htm)
  - 84 people after bánh mì; MoH ordered an investigation — [Tuổi Trẻ, 29/07/2026](https://tuoitre.vn/bo-y-te-yeu-cau-dieu-tra-nguyen-nhan-khien-84-nguoi-nhap-vien-sau-khi-an-banh-mi-thit-nuong-pate-100260729161657044.htm)
  - [BG] 350 workers at Shinwon Ebenezer (Vĩnh Phúc); kitchen suspended — [Tuổi Trẻ, 15/05/2024](https://tuoitre.vn/bo-y-te-dinh-chi-bep-an-khien-350-cong-nhan-nhap-vien-nghi-do-ngo-doc-thuc-pham-20240514234406.htm)
  - Regional comparator: more than 500 Indonesian students hospitalised from a free school-meal programme — [Tuổi Trẻ, 02/09/2026](https://tuoitre.vn/hon-500-hoc-sinh-indonesia-nhap-vien-lai-nghi-ngo-doc-tu-bua-an-mien-phi-100260902193349121.htm)
- **HCMC school-meal crisis (Sept–Oct 2026):**
  - **THCS Hồ Văn Long (Bình Tân):** 1,538 students, **100% eat bán trú (school lunch)**. After complaints, the supplier was terminated on 15/09 and parents now co-supervise — [Tuổi Trẻ, 18/09/2026](https://tuoitre.vn/sau-phan-anh-bua-an-kem-chat-luong-truong-o-tphcm-doi-nha-cung-cap-phu-huynh-cung-giam-sat-100260918125118288.htm)
  - **THCS Phú Định:** publishes **daily menus and meal photos, temperature-monitoring records, food-receipt documents** and the principal's phone number. Parents may make surprise inspections — [Tuổi Trẻ, 03/10/2026](https://tuoitre.vn/truong-o-tphcm-moi-phu-huynh-kiem-tra-dot-xuat-bua-an-ban-tru-cong-khai-so-hieu-truong-100261003103220548.htm)
  - Headlines:
    - A school paused bán trú after "toàn tóp mỡ" (all pork fat) complaints — [28/09/2026](https://tuoitre.vn/truong-tam-dung-to-chuc-an-ban-tru-sau-phan-anh-com-toan-top-mo-100260926170042772.htm)
    - A principal invites parents to inspect at any time without notice — [17/09/2026](https://tuoitre.vn/hieu-truong-gui-thu-moi-phu-huynh-kiem-tra-bua-an-ban-tru-bat-cu-luc-nao-khong-can-bao-truoc-100260917082055661.htm)
    - "Cần chế tài mạnh!" (strong sanctions needed) — [16/09/2026](https://tuoitre.vn/bua-an-ban-tru-kem-chat-luong-can-che-tai-manh-100260916105254891.htm)
    - Hà Nội formed **4 working groups to review bán trú processes** — [17/09/2026](https://tuoitre.vn/ha-noi-lap-4-doan-cong-tac-ra-soat-quy-trinh-bua-an-ban-tru-sau-nhieu-lum-xum-100260917192222722.htm)
- **HCMC Department of Education (DOET).**
  - **Urgent notices on 01/10/2026:** guidance on preventing and handling food-safety incidents in schools (document No. 10197, per the summariser), plus a reminder notice — [hcm.edu.vn](https://hcm.edu.vn/thong-bao/tin-khan-vv-huong-dan-thuc-hien-phong-ngua-xu-ly-su-co-an-toan-thuc-pham-trong/ct/41024/90748); [hcm.edu.vn](https://hcm.edu.vn/thong-bao/tin-khan-nhac-lai-ve-viec-tang-cuong-bao-dam-an-toan-thuc-pham-trong-co-so-giao/ct/41024/90747)
  - **Food-safety training** for school-lunch organisers in 07/2025 and 12/2025 — [hcm.edu.vn](https://hcm.edu.vn/tin-tuc-su-kien/tin-khan-tiep-tuc-to-chuc-lop-4-ve-tap-huan-cong-tac-dam-bao-an-toan-thuc-pham/ctfull/39808/82364); [hcm.edu.vn](https://hcm.edu.vn/tin-tuc-su-kien/tap-huan-cong-tac-to-chuc-bua-an-ban-tru-dam-bao-an-toan-thuc-pham-va-dinh-duon/ctfull/39808/84484)
  - The specific requirements in No. 10197 (cameras in kitchens, parent supervision, caterer documents) are **unverified**; the attached PDF was not read.
- **Law in flux.**
  - **Amended Food Safety Law:** reviewed by the National Assembly committee at its 5th plenary and planned for the **2nd session of the 16th National Assembly**. The minister listed 4 focus points: a single focal point led by MoH, a shift to **post-inspection (hậu kiểm)**, **risk-based management**, and micronutrients. It also plans a **national food-safety supply-chain database** — [VFA, 02/10/2026](https://vfa.gov.vn/tin-tuc/bo-truong-dao-hong-lan-neu-4-trong-tam-khi-sua-luat-an-toan-thuc-pham.html)
  - **Decree 46/2026/NĐ-CP (26/01/2026)** gives detailed rules for the Food Safety Law; **Resolution 66.13/2026/NQ-CP (27/01/2026)** covers product declaration (from the documents list) — [VFA documents](https://vfa.gov.vn/van-ban/)
  - **Circular 48/2025/TT-BYT** (issued and effective 30/12/2025) decentralises MoH food-safety tasks — [VFA](https://vfa.gov.vn/van-ban/thong-tu-quy-dinh-viec-phan-cap-thuc-hien-mot-so-nhiem-vu-va-giai-quyet-thu-tuc-hanh-chinh-trong-linh-vuc-an-toan-thuc-pham-thuoc-tham-quyen-cua-bo-y-te.html)
- **Market anchors.**
  - HCMC has **about 3,500 schools** — [Thanh Niên, 02/01/2026](https://thanhnien.vn/tu-cong-van-cua-cong-an-tphcm-so-gd-dt-canh-bao-thu-doan-lua-dao-moi-185260102133152052.htm)
  - **MISA EMIS** says it serves **23,018 schools**. Its homepage shows **no module for kitchens, 3-step inspection or sample retention** — [MISA EMIS](https://emis.misa.vn/)
- **Global tools and pricing:**
  - **FoodDocs:** Lite / Standard / Professional cost **US$79 / 167 / 250 per site per month (annual)** or US$99 / 199 / 299 monthly, plus US$999–1,249 onboarding — [FoodDocs](https://www.fooddocs.com/pricing)
  - **Mitti by SafetyCulture:** free for up to 10 seats; **Premium US$24 per seat per month (annual)** or US$29 monthly. Offers an AI assistant and an **"Agent builder" (early access)** — [Mitti](https://mitti.com/pricing/)
  - **Jolt:** now SmartSense, quote only — [SmartSense](https://www.smartsense.co/request-a-quote)
  - **TE-FOOD:** blockchain traceability, "6,000+ companies" — [TE-FOOD](https://te-food.com/)

### Inferences
- **Three demand drivers line up for 2026–27:**
  1. Parental pressure for transparency in HCMC.
  2. Sharply higher enforcement (+102% violation cases, +265% criminal cases).
  3. A legal shift to risk-based post-inspection with a national supply-chain database, which rewards kitchens holding verifiable, time-stamped records.
- **Industrial canteens are higher-value accounts.** One site serves about 4,000 meals a day (Scavi), and the employer bears medical costs and reputational damage.
- **Encode rules as configurable "policy packs".** Planned packs: QĐ 1246 3-step inspection and 24-hour sample retention, the HCMC DOET incident protocol, and the new decree once verified. Integrate with incumbents such as MISA EMIS rather than compete with them.

### Gaps
- **Unverified legal details:**
  - The exact text of **QĐ 1246/QĐ-BYT (2017)**: the 3 steps, 24-hour sample retention, sample sizes, forms, record-keeping period.
  - Fine amounts under Decree 115/2018 as amended by Decree 124/2021, and whether they have been replaced.
  - The effective date and content of **Decree 46/2026** for collective kitchens.
  - Joint Circular 13/2016 on school health.
- **Unverified data:**
  - 2025 full-year poisoning statistics.
  - Number of HCMC schools serving bán trú and students eating it.
  - Number of industrial-zone canteens and workers in the merged HCMC.
  - Prices per meal.
  - Vietnamese kitchen, nutrition or 3-step-inspection software and its prices.
  - Post-01/07/2025 status of the HCMC Food Safety Management Board (its portal does not resolve).

---

## 4. Elderly and disability: elderly living alone, digital exclusion, assistive tech, autism

### Takeaway
- **Size of the groups.** Vietnam has about 16.1 million elderly people (over 16% of the population). The legal definition is 60+, which is unverified here. The 65+ cohort is growing fast (9.65 million in 2025). About 7% of people aged 2+ have a disability [BG].
- **Digital exclusion is documented in news reports.** Elderly people struggle with VNeID and online dossiers, and police impersonators exploit "VNeID installation help".
- **Data gaps.** Hard data on elderly people living alone, assistive tech in Vietnamese and autism-therapy access could not be verified. Ideas in this space are therefore weakly evidenced for now.

### Cited Findings
- **Elderly counts.**
  - About **16.1 million elderly (>16% of population)** — [VietnamPlus, 27/03/2026](https://www.vietnamplus.vn/bao-ve-nguoi-cao-tuoi-truoc-cac-chieu-lua-dao-tinh-vi-tren-khong-gian-mang-post1101437.vnp)
  - Ages **65+ were 9.05% (2024) and 9.49% (2025), or 9,646,309 people** (World Bank WDI, UN modelled estimates) — [World Bank](https://data.worldbank.org/indicator/SP.POP.65UP.TO.ZS?locations=VN)
  - Population 102.3 million (12/2025); [BG] the 2019 census put 65+ at 7.6% — [Wikipedia: Demographics of Vietnam](https://en.wikipedia.org/wiki/Demographics_of_Vietnam)
- **Digital-exclusion evidence.**
  - **Dec 2025:** VNeID was overloaded around residence-registration enforcement. Ea Na commune had 436 unregistered children; reported fines of up to VND 750,000 per household are disputed. PC06 said "VNeID is a shared national system, occasionally overloaded". The article documents barriers for **elderly people, ethnic minorities, rural residents with poor connectivity, and people without smartphones** — [Tuổi Trẻ, 10/12/2025](https://tuoitre.vn/can-lam-gi-khi-vneid-nghen-khong-thao-tac-duoc-20251210144830132.htm)
  - **2026:** HCMC communes (Thái Mỹ, Tân Nhựt, Củ Chi) set up hamlet support points because **elderly people and busy workers struggle with online submission** — [Tuổi Trẻ, 14/04/2026](https://tuoitre.vn/nhieu-xa-o-tp-hcm-dua-dich-vu-cong-ve-ap-ho-tro-nguoi-dan-nop-ho-so-truc-tuyen-20260414115507841.htm)
  - Elderly people are reported to be 6 times more likely to encounter fake news — [VietnamPlus](https://www.vietnamplus.vn/bao-ve-nguoi-cao-tuoi-truoc-cac-chieu-lua-dao-tinh-vi-tren-khong-gian-mang-post1101437.vnp)
- **[BG] Disability.**
  - The 2016 national survey found **7% of people aged 2+ (about 6.2 million)** have a disability, and 13% (about 12 million) live in a household with a disabled member — [UNICEF Viet Nam](https://www.unicef.org/vietnam/press-releases/launch-key-findings-viet-nams-first-large-scale-national-survey-people-disabilities)
  - School enrolment is 69% for children with disabilities vs 96% for others — [Wikipedia: Disability in Vietnam](https://en.wikipedia.org/wiki/Disability_in_Vietnam)
  - Disability law 2010; UN Convention on the Rights of Persons with Disabilities (CRPD) ratified 28/11/2014 — [VNAH](https://www.vnah-hev.org/projects/inclusion-of-the-vietnamese-with-disabilities/)
- **[BG] Autism.**
  - Prevalence **0.752% (95% CI 0.629–0.893%)** among 17,277 children aged 18–30 months, screened in 2017 in Hanoi and 2 northern provinces.
  - Higher odds in urban areas (OR 2.7) and among boys (OR 4.04). The authors judge prevalence to be rising — [Hoang et al., 2019](https://doi.org/10.1186/s13033-019-0285-8)
- **Global comparable: ElliQ.** A proactive AI companion offering medication reminders, caregiver alerts and family messaging. It is **funded by public payers** (New York State Office for the Aging, Otsego County O3A, MetroPlusHealth); the homepage shows a promo rather than a list price — [ElliQ](https://elliq.com/)

### Inferences
- **Two buying units.** Elderly scam protection and elderly digital-inclusion help share the same users and payers: elderly people and their adult children. A family-guardian product can add public-service and wellbeing check-ins later as modules.
- **Why autism and assistive tech are weak candidates for now.** Clinical validation needs, therapy capacity and price data are unverified, and health claims raise regulatory risk.

### Gaps
- **Unverified elderly data:**
  - Share of elderly people living alone or only with a spouse.
  - Elderly smartphone and internet use.
  - The 60+ count for the merged HCMC.
  - Social-pension change (Law 41/2024/QH15: age 75+ from 01/07/2025).
  - Elderly-care tech in Vietnam.
- **Unverified disability and autism data:**
  - 2023 disability-survey results.
  - Counts of visually and hearing impaired people.
  - Assistive tech in Vietnamese: Sao Mai, Vietnamese TTS (Vbee, FPT.AI, Viettel AI); whether Be My Eyes, Seeing AI or Envision support Vietnamese; Vietnamese Sign Language AI projects.
  - Number of autism therapists, waitlists and therapy prices in HCMC.
  - Global autism-app pricing (Cognoa, Otsimo, Floreo).

---

## 5. Public services after the two-tier local-government reform (from 01/07/2025)

### Takeaway
- **Scale of change.** The reform cut commune-level units from 10,035 to 3,321. HCMC now has 168 units serving about 13.7 million people, and 129 of those units have more than 50,000 residents.
- **Ongoing friction.** Address changes at province, commune and neighbourhood level burden citizens. VNeID overloads and the "99% online" push leave elderly and digitally excluded people behind. Communes respond with human support points staffed by the youth union and community digital-technology teams.
- **Market is limited.** The state owns the platforms (the national portal is now under MPS; HCMC Tax runs an AI call centre). No third-party submission API was found, so a private "navigator" would be a co-pilot rather than an autonomous agent.

### Cited Findings
- **Reform size.** Commune-level units went **from 10,035 to 3,321**, and 34 provincial units were created by 34 National Assembly Standing Committee resolutions signed 16/06/2025, effective 01/07/2025 — [Tuổi Trẻ, 16/06/2025](https://tuoitre.vn/chi-tiet-3-321-don-vi-cap-xa-cua-34-tinh-thanh-pho-sau-sap-nhap-20250616183112628.htm). The breakdown is 2,621 communes, 687 wards and 13 special zones (search snippet) — [PLO](https://plo.vn/tra-cuu-chi-tiet-3321-phuong-xa-dac-khu-cua-34-tinh-thanh-pho-sau-sap-xep-post856550.html)
- **Legal basis.** **Resolution 202/2025/QH15** (12/06/2025) rearranged the provinces — [Wikipedia: Provinces of Vietnam](https://en.wikipedia.org/wiki/Provinces_of_Vietnam)
- **HCMC structure.**
  - **168 units: 113 wards, 54 communes and Côn Đảo** — [Tuổi Trẻ](https://tuoitre.vn/chi-tiet-3-321-don-vi-cap-xa-cua-34-tinh-thanh-pho-sau-sap-nhap-20250616183112628.htm)
  - More than 6,772 km² and more than 13.7 million people (proposal-stage figures) — [Đại biểu Nhân dân, 09/05/2025](https://daibieunhandan.vn/chi-tiet-168-don-vi-hanh-chinh-cap-xa-cua-tp-ho-chi-minh-sau-hop-nhat-10371821.html)
  - Headquarters and hotlines for all 168 units were published, and several wards run multiple reception points — [VnExpress, 26/06/2025](https://vnexpress.net/tp-hcm-cong-bo-tru-so-duong-day-nong-168-xa-phuong-dac-khu-4906726.html)
- **HCMC one year on.**
  - The model is "basically stable". The city issued 87 decisions delegating about 1,008 tasks.
  - **Neighbourhoods were cut from 5,947 to 3,923 by 01/07/2026**, and 54 of the 168 units fall below area or population standards.
  - The city warns that further mergers would force citizens to update addresses "trên nhiều hồ sơ, hệ thống" (across many records and systems) — [Thanh Niên, 04/09/2026](https://thanhnien.vn/tphcm-de-xuat-giu-nguyen-168-phuong-xa-dac-khu-185260904205445215.htm)
  - The city Party Committee **decided to keep all 168 units** (11/09/2026) — [Thanh Niên](https://thanhnien.vn/thanh-uy-tphcm-thong-nhat-giu-nguyen-168-phuong-xa-dac-khu-185260911122104153.htm)
  - **129 of the 168 units have more than 50,000 residents**, some 100,000–150,000. The city proposes a Public Administration Service Center in each ward — [Thanh Niên, 10/09/2026](https://thanhnien.vn/tphcm-hoan-thien-bo-khung-cho-phuong-xa-185260910222322744.htm)
- **Platforms.**
  - The National Public Service Portal is now titled "Trung tâm dữ liệu quốc gia, Bộ Công an" (National Data Center, Ministry of Public Security) — [dichvucong.gov.vn](https://dichvucong.gov.vn/p/home/dvc-trang-chu.html)
  - VNeID opened to foreigners from 01/07/2025 — [Viet Nam News](https://vietnamnews.vn/society/1720598/public-security-ministry-begins-rollout-of-eid-for-foreigners-in-viet-nam.html)
- **Assisted-digital support points.**
  - **Tân Nhựt commune (Q1 2026):** 6,259 dossiers, **online submissions above 99%**, yet "many citizens, particularly elderly, still faced obstacles". Staff help create VNeID accounts and submit birth, marriage, marital-status and social-assistance dossiers — [Tuổi Trẻ, 14/04/2026](https://tuoitre.vn/nhieu-xa-o-tp-hcm-dua-dich-vu-cong-ve-ap-ho-tro-nguoi-dan-nop-ho-so-truc-tuyen-20260414115507841.htm)
  - **Cát Lái ward (opened 06/06/2026):** staffed by youth-union members and community digital-technology teams. About 18,000 residents need help with land, housing, compensation and welfare procedures — [Tuổi Trẻ](https://tuoitre.vn/nguoi-dan-cat-lai-vui-mung-khi-phuong-co-diem-ho-tro-dich-vu-cong-truc-tuyen-20260606102336007.htm)
- **System strain.** VNeID was overloaded and penalties loomed during residence-registration enforcement (Dec 2025) — [Tuổi Trẻ, 10/12/2025](https://tuoitre.vn/can-lam-gi-khi-vneid-nghen-khong-thao-tac-duoc-20251210144830132.htm)
- **Government AI.** HCMC Tax AI call centre (Aug 2026) — [Tuổi Trẻ](https://tuoitre.vn/thue-tphcm-ra-mat-tong-dai-ai-ho-tro-nhac-no-thong-bao-tam-hoan-xuat-canh-100260808181834978.htm)
- **Trust risk.**
  - Police impersonators "guide VNeID installation" and then send malicious links — [CAND, 02/10/2026](https://cand.vn/ma-tran-lua-dao-tren-khong-gian-mang-nham-vao-nguoi-gia-yeu-the-post823770.html)
  - A VNeID-related scam ring was raided in Laos, with 40 arrested (headline, 23/07/2026) — [Thanh Niên](https://thanhnien.vn/dot-kich-o-lua-dao-qua-vneid-o-lao-bat-giu-40-doi-tuong-185260723104227203.htm)

### Inferences
- **District-scale loads.** Average load is about 81,500 residents per HCMC unit (13.7M ÷ 168) and about 30,800 nationally (102.3M ÷ 3,321).
- **Volunteers as a channel.** Human support points staffed by youth-union and community digital teams are the natural channel and pilot partner for any assistant.
- **Co-pilot, not agent.** With no public third-party submission API and strong scam impersonation of "VNeID support", a private agent should plan, prepare checklists and pre-fill forms, route and remind. It should then hand off to the citizen, a relative or a volunteer for submission, and never hold credentials. This limits how "agentic" the product can be and adds trust risk.
- **Stable window.** Keeping the 168 units (decided 11/09/2026) gives a stable period for an MVP by 01/2027.

### Gaps
- **Unverified legal texts:**
  - Law on Organization of Local Government 72/2025/QH15.
  - Decree 118/2025/NĐ-CP (one-stop shop; dossiers accepted regardless of administrative boundary).
  - VNeID "authorisation" features.
  - VNPost public-administration service fees.
- **Unverified data:** national online-dossier shares; VNeID account totals; existence and features of AI assistants on the national portal or VNeID; private legal chatbots.
- **Conflict:** the number of provinces vs centrally-run cities (28 + 6 vs 25 + 9).

---

## 6. Environment (waste sorting, EPR, waste pickers) and scams against migrant / labour-export workers

### Takeaway
- **HCMC waste.** HCMC is shifting waste fees toward volume and weight: Decision 67/2025, then new prices from 01/09/2026. But sorted waste is still collected together again.
- **EPR.** Decree 05/2025 tightened the proof chain: licensed recyclers only, no sub-delegation, national-system listing, and a single annual payment to the fund. This creates **B2B demand for verifiable chain-of-custody data** from roughly 3 million informal collectors to recyclers. Consumer recycling-points apps are already crowded (GRAC, XanhNét).
- **Labour scams.** Trafficking into scam compounds (Myanmar, Cambodia, Laos) and task and job scams remain serious in 2025–2026. However, payers and data access for a "safe-job verifier" are unproven.

### Cited Findings
- **[BG] Sorting mandate and volumes.**
  - HCMC households must sort into 3 groups; deadline 31/12/2024; about 9,700 t/day of household waste — [Tiền Phong, 14/08/2024](https://tienphong.vn/tphcm-phan-rac-thai-sinh-hoat-thanh-3-loai-post1663719.tpo)
  - About 10,000 t/day, of which 1,800 t/day is recyclable; informal collectors handle about 60% — [HCMC Press Center, 2023](https://ttbc-hcm.gov.vn/tp-hcm-tim-giai-phap-tang-thoi-quen-phan-loai-rac-tai-nguon-cua-dan-1003067.html)
- **HCMC fee decisions.**
  - **Decision 67/2025** (issued 07/05/2025, effective 01/06/2025): households pay a fixed fee by zone until sorting is fully implemented; businesses pay by weight or volume — [VOV Giao thông, 30/05/2025](https://vovgiaothong.vn/newsaudio/thu-gom-rac-theo-ky-can-can-do-cong-bang-va-minh-bach-d45089.html)
  - **New prices from 01/09/2026 to 30/06/2027:** 1 m³ ≈ 420 kg, with 6-monthly reviews — [doanhnghiepkinhtexanh, 22/08/2026](https://doanhnghiepkinhtexanh.vn/infographic-tphcm-ap-dung-gia-dich-vu-rac-moi-thuc-day-phan-loai-tai-nguon-a52728.html)
- **Decision 65/2026 in practice** — [SGGP, 29/09/2026](https://www.sggp.org.vn/phan-loai-rac-tai-nguon-dung-chi-la-khau-hieu-post873917.html):
  - Businesses sort into 2 groups, but "**rác đã phân loại bị thu gom chung**" (sorted waste is collected together again).
  - A restaurant's waste bill is going from about VND 7 million to about VND 10 million a month.
  - Specialised trucks cost VND 300–800 million.
  - **Unilever–GRAC station** in Tân Mỹ ward (04/2026) records drop-offs and awards points in the GRAC app.
- **Community models.**
  - Tam Thắng "Green House": about 220 women earn VND 1–1.5 million a month and collect more than 2,000 kg of paper and more than 1,000 kg of bottles and cans a year — [SGGP DTTC](https://dttc.sggp.org.vn/phan-loai-rac-tai-nguon-can-dong-bo-tu-khau-gom-den-van-chuyen-post137950.html)
  - "Plastic Circular Journey 2026" by the HCMC Department of Agriculture and Environment, Unilever and the Women's Union — [SGGP, 26/08/2026](https://www.sggp.org.vn/phoi-hop-phan-loai-chat-thai-ran-sinh-hoat-tai-nguon-post868958.html)
  - HCMC targets more than 90% recycled or modern treatment by 2030 and has 8 waste-to-energy projects — [HTV, 20/09/2026](https://htv.vn/tp-ho-chi-minh-day-manh-xu-ly-rac-thai-bang-cong-nghe-dot-phat-dien-giai-doan-2026-2030-22226092012003187.htm)
- **EPR: Decree 05/2025/NĐ-CP** (issued and effective **06/01/2025**), amending Decree 08/2022 — [KPMG](https://kpmg.com/vn/vi/insights/2025/02/key-amendments-to-vietnam-environment-protection-regulations.html):
  - The obligated party is whoever is responsible for product quality and labelling.
  - The importer exemption threshold rises from **VND 20 to 30 billion**.
  - **Only licensed recyclers count.** Producer responsibility organisations (PROs) **may not sub-delegate**.
  - Qualified recyclers are listed on the national EPR system within 5 working days.
  - **A single annual payment to the Vietnam Environment Protection Fund (VEPF) before 20/04.**
  - Fund-support procedures were removed pending new guidance.
- **EPR timeline** — [VnEconomy, 19/01/2025](https://vneconomy.vn/quy-dinh-moi-ve-ty-le-tai-che-quy-cach-tai-che-bat-buoc-voi-nha-san-xuat-nhap-khau.htm):
  - Recycling duty applies to packaging, batteries, lubricants and tyres from 01/01/2024; electrical and electronic goods from 01/01/2025; vehicles from 01/01/2027.
  - Rates are reviewed every 3 years, and the fund charges a 2% management fee.
  - MAE has a page titled "Xây dựng nghị định EPR" (building an EPR decree), suggesting a standalone decree is being drafted; it could not be opened — [MAE](https://mae.gov.vn/moi-truong/xay-dung-nghi-dinh-epr-huong-di-ben-vung-cho-nganh-tai-che-18406.htm)
- **Informal waste pickers.**
  - **About 3 million** informal scrap workers, mostly without contracts or insurance; recyclers are starting to train them and offer contracts and insurance — [VTV, 01/10/2026](https://vtv.vn/tung-buoc-chuyen-nghiep-hoa-luc-luong-thu-gom-phe-lieu-100261001134315091.htm)
  - [BG] 90% are women; UNDP says more than 30% of collected waste passes through informal networks — [VOV2](https://vov2.vov.vn/doi-song-xa-hoi/giam-rac-thai-nhua-tu-nhung-luc-luong-phi-chinh-thuc-49760.vov2)
  - [BG] HCMC has about 5,000 pickers and **1,800 scrap yards**; they gather 65–70% of alley waste — [VnEconomy, 2022](https://vneconomy.vn/can-xac-dinh-luc-luong-ve-chai-dong-nat-la-mot-nghe-de-co-co-che-ho-tro-phu-hop.htm)
  - [BG] VietCycle and Unilever support more than 3,000 pickers through "The Plastic Reborn" and XanhNét — [TheLeader, 2024](https://theleader.vn/tuong-lai-moi-cho-nguoi-thu-gom-phe-lieu-d37574.html)
- **Migrant and labour scams:**
  - **572 Vietnamese** were among 7,141 foreigners rescued from Myanmar scam centres from 01/2025 to 26/02/2025 — [tamdamedia (republishing Tuổi Trẻ), 27/02/2025](https://tamdamedia.eu/myanmar-giai-cuu-572-nguoi-viet-tu-cac-o-lua-dao-truc-tuyen)
  - Myanmar arrested 10,119 foreigners in 9 months — [Tuổi Trẻ, 28/10/2025](https://tuoitre.vn/myanmar-bat-hon-10-000-nguoi-trum-lua-dao-chay-khoi-khu-kk-park-gan-thai-lan-20251028160202351.htm)
  - **83 Vietnamese** were among 516 people arrested in Myawaddy on 12/12/2025 — [Tuổi Trẻ, 15/12/2025](https://tuoitre.vn/myanmar-pha-huy-them-17-toa-nha-co-bac-truc-tuyen-o-kk-park-bat-516-nguoi-nuoc-ngoai-20251215154656718.htm)
  - All 635 KK Park structures were demolished by 01/2026 — [Tuổi Trẻ](https://tuoitre.vn/toan-bo-635-cong-trinh-phuc-vu-lua-dao-co-bac-o-kk-park-bi-xoa-so-20260111162034621.htm)
  - Cambodia **arrested about 21,000 people in 6 months** (headline, 22/09/2026) — [Thanh Niên](https://thanhnien.vn/campuchia-bat-21000-nguoi-trong-6-thang-truy-quet-lua-dao-truc-tuyen-185260922182752028.htm) — and **deported more than 72,000 foreigners** (headline, 18/09/2026) — [Thanh Niên](https://thanhnien.vn/campuchia-da-truc-xuat-hon-72000-nguoi-nuoc-ngoai-cam-vinh-vien-co-bac-truc-tuyen-185260918111459789.htm)
  - 42 Vietnamese escaped a Cambodian scam facility (headline, 12/2025) — [Thanh Niên](https://thanhnien.vn/42-cong-dan-viet-nam-chay-thoat-khoi-co-so-lua-dao-truc-tuyen-o-campuchia-18525121719171216.htm)
  - Cà Mau police sought victims trafficked to Cambodia for forced labour (headline, 07/06/2026) — [Thanh Niên](https://thanhnien.vn/cong-an-ca-mau-tim-bi-hai-vu-mua-ban-nguoi-sang-campuchia-de-cuong-buc-lao-dong-185260607002408105.htm)
  - [BG] Students were lured to Cambodia by "easy job, high pay" (headline, 01/2024) — [Thanh Niên](https://thanhnien.vn/sinh-vien-de-bi-lua-sang-campuchia-vi-tin-viec-nhe-luong-cao-185240105172402795.htm)
  - Online job scams are a top global trend — [Google, 11/2025](https://blog.google/innovation-and-ai/technology/safety-security/fraud-and-scams-advisory-november-2025/)
  - The Laos-based task-scam ring took **more than VND 1,500 billion** in 2026 — [Tuổi Trẻ](https://tuoitre.vn/cong-an-sang-lao-bat-gon-o-nhom-lua-dao-qua-mang-chiem-doat-1500-ti-dong-cua-hang-ngan-nguoi-viet-100260916204859951.htm)

### Inferences
- **Waste: where the bottleneck is now.** It has moved from household awareness to **collection logistics and verification**. The clearest payers are businesses, which already pay by weight or volume, and EPR-obligated producers and PROs, which must prove licensed-recycler volumes.
- **Where the gap is.** It is not consumer apps but the data layer linking scrap yards, pickers and recyclers: weight tickets, prices, payments, insurance, and EPR evidence. The Unilever–GRAC station and the Green House model are natural pilot partners.
- **Job verification fits best inside the anti-scam guardian.** A "safe-job / recruiter verifier" is socially strong, especially for students, but has weak payers. Labelling a recruiter as fraudulent needs human review because of defamation risk.

### Gaps
- **Unverified environment data:**
  - Full text of Decision 65/2026 and tariff levels.
  - HCMC daily waste after the merger (often quoted as about 14,000 t/day).
  - VEPF collections and disbursements for 2024–2026.
  - Number of producers registered under EPR and the EPR portal URL.
  - Picker incomes.
  - Vietnamese recycling apps other than GRAC and XanhNét.
  - Global comparators (Recykal, Kabadiwalla Connect, Plastic Bank).
  - Law 72/2020/QH14 Art. 79; fines for not sorting under Decree 45/2022.
- **Unverified labour-scam data:**
  - Total Vietnamese repatriated in 2025–2026.
  - Statistics on fake labour-export and factory-job deposit scams in HCMC industrial zones.
  - The official licensed-recruiter lookup (dolab.gov.vn unreachable on 04/10/2026).
  - Law 69/2020/QH14 details.
  - IOM/ILO safe-migration tools.

---

## 7. Social-enterprise funding and revenue models in Vietnam

### Takeaway
Vietnamese social enterprises have historically relied on donations ([BG] British Council 2019). Verified 2025–2026 money pools point to **hybrid models** instead:
- B2B2C distribution through banks, telcos and insurers.
- B2B compliance SaaS, with caterers and EPR-obligated producers as payers.
- B2G contracts with wards and provinces.
- Platform and corporate CSR or grants (Google.org's US$5M Scam Ready ASEAN; Unilever's waste programmes; Zalo's disaster messaging).

Impact-investor activity in 2024–2026 could not be verified.

### Cited Findings
- **[BG] British Council / CIEM / CSIP (2019).**
  - About **19,000 social enterprises**.
  - **Donations are the most common funding source.**
  - Legal definition: an enterprise that **reinvests at least 51% of profits** for its social or environmental purpose.
  - Barriers: cash flow, skills, impact measurement.
  - Source: [Pioneers Post](https://www.pioneerspost.com/news-views/20190409/vietnam-s-vibrant-social-enterprise-sector-has-more-give); [British Council report PDF](https://www.britishcouncil.org/sites/default/files/state_of_social_enterprise_in_vietnam_british_council_web_final.pdf)
- **Grant / CSR (anti-scam).** Google.org **US$5 million Scam Ready ASEAN (2025–2027)**, implemented in Vietnam by Chống Lừa Đảo — [Thanh Niên, 26/08/2026](https://thanhnien.vn/du-an-chong-lua-dao-nhan-ho-tro-tu-google-185260826144700166.htm)
- **Bank anti-fraud spending.** Banks invest in anti-fraud because it saves them money: ACB blocked more than 20,000 fraudulent transactions (about VND 1,500 billion) in H1 2025 — [Thanh Niên](https://thanhnien.vn/lua-dao-ngay-cang-tinh-vi-ngan-hang-dang-lam-gi-de-bao-ve-nguoi-dung-185251008090520098.htm); BIDV's SIMO warnings retained more than VND 100 billion — [Thanh Niên](https://thanhnien.vn/diem-mat-chi-ten-gui-tai-khoan-nghi-ngo-lua-dao-sang-ngan-hang-nha-nuoc-18525052912181878.htm)
- **B2B AI anti-scam sold to telcos and banks abroad:** Apate.ai (TPG Telecom, Commonwealth Bank) — [Apate.ai](https://www.apate.ai/)
- **Corporate / EPR money in waste:** Unilever–GRAC station; Plastic Circular Journey — [SGGP](https://www.sggp.org.vn/phan-loai-rac-tai-nguon-dung-chi-la-khau-hieu-post873917.html); [SGGP](https://www.sggp.org.vn/phoi-hop-phan-loai-chat-thai-ran-sinh-hoat-tai-nguon-post868958.html)
- **Disaster money flows:**
  - Through the Fatherland Front: about VND 1,495 billion for Yagi — [Wikipedia](https://en.wikipedia.org/wiki/Typhoon_Yagi); more than VND 1,175 billion for the 2025 floods — [vi.wikipedia](https://vi.wikipedia.org/wiki/L%C5%A9_l%E1%BB%A5t_mi%E1%BB%81n_Trung_Vi%E1%BB%87t_Nam_2025)
  - Platform partnership: Zalo and VDDMA sent 24.1 million messages — [SGGP](https://www.sggp.org.vn/share824458.html)
  - [BG] World Bank resilience projects — [World Bank](https://www.worldbank.org/en/country/vietnam/overview)
- **Government buying AI services:** HCMC Tax AI call centre — [Tuổi Trẻ](https://tuoitre.vn/thue-tphcm-ra-mat-tong-dai-ai-ho-tro-nhac-no-thong-bao-tam-hoan-xuat-canh-100260808181834978.htm)
- **Public payers for AI elderly companions abroad:** ElliQ — [ElliQ](https://elliq.com/)

### Inferences
- **Best fit for a student team:** a **paid B2B / B2B2C core plus CSR or grant co-funding for the social reach.** Examples:
  - Anti-scam: banks or insurers pay per protected user; Google.org-style grants fund elderly training.
  - Food safety: caterers and factories pay per kitchen or meal.
  - EPR: PROs or brands pay per verified tonne.
  - Pure donation or B2G-only models are slow; procurement cycles exceed the competition timeline.
- **Financial-plan framing.** Mentors will expect a hybrid "social enterprise" story: social mission (e.g., 51% reinvestment if registered as a social enterprise), unit economics from the paying segment, and impact KPIs (money protected, outbreaks prevented, tonnes verified).

### Gaps
- **Impact investors and programmes (2024–2026), with ticket sizes, unverified:** Lotus Impact, Patamar, Insitor, ThinkZone, Seedstars, Ascend Vietnam Ventures, UNDP Youth Co:Lab, KOICA, British Council DICE.
- **Spending data unverified:** CSR budgets of banks and telcos for digital literacy or anti-fraud.
- **Policy incentives unverified:**
  - Resolution 57-NQ/TW (22/12/2024)
  - Resolution 68-NQ/TW (04/05/2025)
  - Law on Science, Technology and Innovation 93/2025/QH15
  - Digital Technology Industry Law 71/2025/QH15 (AI provisions, sandbox)
  - Decree 94/2025/NĐ-CP (fintech sandbox)
  - Whether a standalone AI law has passed
- Current number of registered social enterprises.

---

## 8. Candidate Agentic AI social-impact ideas: evaluation, scores, ranked shortlist, and saturated ideas to avoid

### Takeaway
- **Top two ideas:**
  - **(A) an Agentic "family-circle" anti-scam guardian** (elders plus students), with the strongest audience appeal.
  - **(C) an Agentic food-safety compliance and parent-transparency agent for school and industrial canteens**, with the lowest risk and clearest B2B payer.
- **(B) Disaster SOS triage** is the best agentic showcase but has a weak business case. Reframe it with anticipatory action, NGO, insurer or CSR funders and an HCMC urban-flood angle.
- **(E) EPR / recycling traceability** is a credible B2B dark horse.
- **(D) Public-service navigator** is socially strong but government-owned, has limited autonomy, and carries trust risk.
- **(F) Safe-job verifier:** fold it into (A).

### Cited Findings
Key evidence per idea; full sources are in sections 1–7:
- **A (anti-scam guardian):**
  - Losses VND 6,000–8,000 bn in 2025 — [CafeF/NCA](https://cafef.vn/nam-2025-thiet-hai-do-lua-dao-truc-tuyen-o-viet-nam-uoc-tinh-tren-6000-ty-dong-18826010807091841.chn), [VOV/MPS](https://vov.vn/phap-luat/thiet-hai-tu-lua-dao-truc-tuyen-len-toi-8000-ty-dong-trong-nam-2025-post1286479.vov)
  - Police impersonation is the #1 tactic — [CafeF](https://cafef.vn/nam-2025-thiet-hai-do-lua-dao-truc-tuyen-o-viet-nam-uoc-tinh-tren-6000-ty-dong-18826010807091841.chn)
  - 16.1 million elderly; HCMC police "50%" finding — [VietnamPlus](https://www.vietnamplus.vn/bao-ve-nguoi-cao-tuoi-truoc-cac-chieu-lua-dao-tinh-vi-tren-khong-gian-mang-post1101437.vnp)
  - SIMO warnings since 04/2025 — [Thanh Niên](https://thanhnien.vn/diem-mat-chi-ten-gui-tai-khoan-nghi-ngo-lua-dao-sang-ngan-hang-nha-nuoc-18525052912181878.htm)
  - Decree 174 effective 01/07/2026 — [Thanh Niên](https://thanhnien.vn/co-tinh-su-dung-sim-khong-chinh-chu-se-bi-phat-tien-len-den-50-trieu-dong-185260702000142323.htm)
  - Amended Cybersecurity Law effective 01/07/2026 — [VOV](https://vov.vn/xa-hoi/tich-hop-mang-xa-hoi-voi-vneid-xac-thuc-danh-tinh-se-het-lua-dao-truc-tuyen-post1271458.vov)
  - Incumbent tools are free lookups — [VnExpress (nTrust)](https://vnexpress.net/ra-mat-phan-mem-giup-phat-hien-lua-dao-mang-4775737.html), [Tech for Good Institute (chongluadao)](https://techforgoodinstitute.org/insights/country-spotlights/building-digital-resilience-lessons-from-vietnam-2/)
  - Pixel scam detection not offered in Vietnam — [Thanh Niên](https://thanhnien.vn/galaxy-s26-sap-co-tinh-nang-dang-tien-nhat-tren-pixel-185260201174214127.htm)
  - Aura family plan US$32–50/month — [Aura](https://www.aura.com/pricing)
- **B (disaster SOS):**
  - 2025 Central floods: 218 dead or missing, VND 40,471 bn — [vi.wikipedia](https://vi.wikipedia.org/wiki/L%C5%A9_l%E1%BB%A5t_mi%E1%BB%81n_Trung_Vi%E1%BB%87t_Nam_2025)
  - Yagi: 9,235 BTS down — [vi.wikipedia](https://vi.wikipedia.org/wiki/B%C3%A3o_Yagi_%282024%29)
  - One-way warnings (26.4M SMS, 24.1M Zalo) — [SGGP](https://www.sggp.org.vn/share824458.html)
  - VNDMS has no public API — [VNDMS](https://vndms.gov.vn/)
  - Anticipatory-action proposal — [Tuổi Trẻ Cuối tuần](https://cuoituan.tuoitre.vn/neu-cuu-tro-den-truoc-thien-tai-20251212102101647.htm)
- **C (food safety):**
  - H1 2026: 58 outbreaks, school kitchens 12 outbreaks / 741 students — [Tuổi Trẻ](https://tuoitre.vn/phong-thuc-pham-ban-hay-xay-them-benh-vien-ky-1-thuc-pham-ban-bua-vay-hon-200-benh-tu-bua-an-100260727210603361.htm)
  - Scavi Huế, 222 workers — [Tuổi Trẻ](https://tuoitre.vn/222-cong-nhan-hue-ngo-doc-thuc-pham-tim-thay-2-loai-vi-khuan-trong-thuc-an-100260922152835031.htm)
  - HCMC school-meal transparency moves — [Tuổi Trẻ](https://tuoitre.vn/truong-o-tphcm-moi-phu-huynh-kiem-tra-dot-xuat-bua-an-ban-tru-cong-khai-so-hieu-truong-100261003103220548.htm)
  - Amended Food Safety Law pipeline — [VFA](https://vfa.gov.vn/tin-tuc/bo-truong-dao-hong-lan-neu-4-trong-tam-khi-sua-luat-an-toan-thuc-pham.html)
  - Pricing comparators — [FoodDocs](https://www.fooddocs.com/pricing), [Mitti](https://mitti.com/pricing/)
  - MISA EMIS: 23,018 schools — [MISA EMIS](https://emis.misa.vn/)
  - HCMC has about 3,500 schools — [Thanh Niên](https://thanhnien.vn/tu-cong-van-cua-cong-an-tphcm-so-gd-dt-canh-bao-thu-doan-lua-dao-moi-185260102133152052.htm)
- **D (public-service navigator):**
  - Communes cut from 10,035 to 3,321 — [Tuổi Trẻ](https://tuoitre.vn/chi-tiet-3-321-don-vi-cap-xa-cua-34-tinh-thanh-pho-sau-sap-nhap-20250616183112628.htm)
  - 129 HCMC units with more than 50,000 residents — [Thanh Niên](https://thanhnien.vn/tphcm-hoan-thien-bo-khung-cho-phuong-xa-185260910222322744.htm)
  - Hamlet support points; elderly obstacles — [Tuổi Trẻ](https://tuoitre.vn/nhieu-xa-o-tp-hcm-dua-dich-vu-cong-ve-ap-ho-tro-nguoi-dan-nop-ho-so-truc-tuyen-20260414115507841.htm)
  - VNeID overload — [Tuổi Trẻ](https://tuoitre.vn/can-lam-gi-khi-vneid-nghen-khong-thao-tac-duoc-20251210144830132.htm)
- **E (EPR / recycling):**
  - Decree 05/2025 — [KPMG](https://kpmg.com/vn/vi/insights/2025/02/key-amendments-to-vietnam-environment-protection-regulations.html)
  - HCMC fees and mixed collection — [SGGP](https://www.sggp.org.vn/phan-loai-rac-tai-nguon-dung-chi-la-khau-hieu-post873917.html)
  - About 3 million informal collectors — [VTV](https://vtv.vn/tung-buoc-chuyen-nghiep-hoa-luc-luong-thu-gom-phe-lieu-100261001134315091.htm)
- **F (safe-job verifier):**
  - Scam-compound rescues and arrests — [tamdamedia](https://tamdamedia.eu/myanmar-giai-cuu-572-nguoi-viet-tu-cac-o-lua-dao-truc-tuyen), [Tuổi Trẻ](https://tuoitre.vn/myanmar-pha-huy-them-17-toa-nha-co-bac-truc-tuyen-o-kk-park-bat-516-nguoi-nuoc-ngoai-20251215154656718.htm)
  - Laos task-scam ring, VND 1,500 bn — [Tuổi Trẻ](https://tuoitre.vn/cong-an-sang-lao-bat-gon-o-nhom-lua-dao-qua-mang-chiem-doat-1500-ti-dong-cua-hang-ngan-nguoi-viet-100260916204859951.htm)

### Inferences
All market sizes below are **my own estimates with stated assumptions**, not sourced figures. All scores are my judgement (1 = worst, 5 = best; for regulatory risk, 5 = lowest risk).

#### Idea A — Agentic "family-circle" anti-scam guardian (elders and students)

**Target users and payers**
- **Protected users:** elderly parents and grandparents, plus students (task-scam, fake-job and fake-police targets).
- **Guardians:** adult children or siblings.
- **Payers:**
  - B2C family subscription.
  - **B2B2C white-label** for banks (they lose money and reputation to fraud; ACB and BIDV figures above), telcos and insurers.
  - Grant or CSR co-funding (Google.org Scam Ready precedent).

**Pain evidence:** see Cited Findings. The headline points are VND 6,000–8,000 bn in 2025 losses, police impersonation as #1 tactic, the HCMC "50%" elderly finding, the Sept 2026 Hà Tĩnh cases, and student-targeted scripts in HCMC (Jan 2026).

**Why now (dated hooks):**
- Circulars 17/18/2024 and full enforcement from 01/01/2026.
- SIMO warnings since 01/04/2025.
- Decree 174 penalties from 01/07/2026, including VND 80–100M for AI-forged SIM biometrics.
- Amended Cybersecurity Law effective 01/07/2026.
- PDPL in force in 2026.
- iOS 27 Trust Insights (2026).
- Deepfake and "silent call" voice harvesting (ACB, 06/2026).
- Google.org US$5M ASEAN programme (2025–27).
- Timing: the final pitch (27/02/2027) falls right after Tết. The MPS has issued Tết-season scam warnings before (e.g., [VOV](https://vov.vn/phap-luat/bo-cong-an-canh-bao-chieu-lua-dao-truc-tuyen-dip-tet-va-mua-le-hoi-post1265119.vov)); calling it an "annual peak" is my inference.

**Market size (assumptions)**

| Tier | Calculation | Result |
|---|---|---|
| **TAM** (theoretical B2C ceiling) | 16.1M elderly ÷ 1.5 elderly per household ≈ 10.7M households × VND 588k/year (VND 49k/month, priced well below Aura's US$12/month) | **≈ VND 6.3 trillion/year** |
| **SAM** (HCMC) | 13.7M people × assumed 12% elderly share (assumed below the national 16%) ≈ 1.64M elderly ≈ 1.1M households × assumed 60% smartphone use ≈ 0.66M households × VND 588k | **≈ VND 390 bn/year** |
| **SOM** (by 2028) | 1% of SAM ≈ 6,600 families | ≈ VND 3.9 bn/year |
| **SOM, B2B2C alternative** | One bank pilot: 50,000 elderly customers × VND 5,000/user/month | ≈ VND 3 bn/year |

Value at risk: VND 6,000–8,000 bn lost per year nationally.

**Competitors and the gap**
- **Vietnam:**
  - nTrust: free lookup and blocking; weak iOS traction (3.4★ from 250 ratings; last iOS update 10/2024).
  - chongluadao: free lookup, extension, chatbot, threat API; Google.org-backed.
  - Bank SIMO warnings and ACB alerts: transfer-time only.
  - HCMC Tax branded AI calls: not a competitor, but a design pattern.
- **Global:**
  - Aura: US$12–32/month (annual), with AI spam call and message protection and family alerts.
  - Apate.ai: B2B scam-baiting bots, custom pricing.
  - Pixel / Galaxy S26 Scam Detection: not offered in Vietnam.
  - iOS 27 Trust Insights: OS-level, app integration needed.
- **Gap:** no verified Vietnamese product is family-centric and proactive. None runs a **"pause → verify → escalate → report → follow-up" loop** in Vietnamese with a trusted family member in the loop.

**Agentic workflow** (multi-agent, with a human in the loop)
1. **Sentinel (on device, rule-based):**
   - Uses Android `CallScreeningService` to label or flag unknown and suspicious numbers against nTrust- and chongluadao-style lists (data access to be negotiated).
   - Watches notification signals with consent, for example "unknown call then banking-app notification".
   - Provides an "Ask my child / Hỏi con" panic button.
   - On iOS: Call Directory or Live Caller ID labels plus the share-sheet checker.
2. **Risk agent (server LLM):** scores the context (claimed authority, secrecy, urgency, money request) using the elder's memory profile: known contacts, usual transfers, family code word.
3. **Intervention agent:**
   - Triggers a "safe pause": a Vietnamese voice prompt such as "Công an không yêu cầu chuyển tiền qua điện thoại" (Police never ask for money transfers by phone).
   - Asks for the family code word.
   - Pings the guardian with a summary and call-back options; the guardian approves next steps.
4. **Verification agent:** checks numbers, URLs, QR codes and bank accounts through threat-intel lookups (e.g., chongluadao's partner API); calls back the "relative" on the known number; checks claims against official sources (e.g., "Thue TP.HCM" caller ID rules).
5. **Case agent:** if a loss or attempt occurs, drafts the police report and bank-hotline script, logs evidence, reminds the family to lock accounts, and **warns against "recovery" scammers**.
6. **Coach agent:** runs weekly personalised scam drills based on the latest tactics (deepfake relatives, VNeID "support", task scams for students).

**MVP (about 7 weeks)**
- Android elder app (call screening, link/QR/account checker, panic button, Vietnamese TTS warnings).
- Guardian side through a Zalo Official Account / Telegram bot or a light app.
- Backend LLM orchestrator with tool calls (lookups, call-back script, report generator) and memory.
- Demo: scripted "fake police" and "deepfake grandchild" scenarios that end with a guardian alert and an escalation.
- iOS: labelling-only proof of concept.

**Pilot near HCMC**
- TDTU students' own families (a beta of 50–100 families).
- Ward support points and community digital teams (e.g., Cát Lái).
- HCMC Police / DOET anti-scam communication channels (168 wards, about 3,500 schools).
- A bank branch or chongluadao for data and co-branding (partnerships unverified).

**Revenue model**
- B2C: VND 39–79k per family per month (assumption).
- B2B2C: per-active-user fee to banks, insurers and telcos.
- Grants and CSR for elderly training.
- Benchmarks: Aura US$12–32/month (annual); Vietnamese competitors free.

**Key risks**
- Google Play policy (SMS exceptions need review; no autonomous Accessibility use).
- iOS limits.
- Sensitive monitoring data under the PDPL (needs consent and minimal processing).
- False positives and annoyance; liability if it misses a scam.
- OS vendors localising their scam detection.
- Scammers impersonating the product (counter with no links and a verified Zalo OA).
- B2C willingness to pay unproven.

**Scores**

| Criterion | Score | Justification |
|---|---|---|
| (1) Agentic AI depth | 4 | Multi-step detect → pause → verify → escalate → report with memory and human-in-the-loop; capped by OS limits (no call audio; no Accessibility autonomy). |
| (2) Pain severity and why-now | 5 | VND 6–8 trillion in 2025 losses; elderly targeted; several 2025–26 rules and platform shifts. |
| (3) Novelty vs Vietnamese products | 4 | Vietnamese tools are free lookups or bank-side; no family-loop agent found (search was limited). |
| (4) Market size and willingness to pay | 3 | Huge exposure, but B2C willingness to pay unproven and free incumbents; B2B2C plausible. |
| (5) MVP and pilot feasibility by Jan 2027 | 4 | Android prototype plus bot is buildable; families of students are an easy pilot. |
| (6) Regulatory/data/trust risk (5 = low) | 3 | Consent-based, no audio, but sensitive data, Play-policy review and impersonation risk. |
| (7) Appeal to student voters | 5 | Every student has parents or grandparents at risk, and students themselves are targeted. |
| (8) Appeal to judges and mentors | 4 | Strong agentic and security story; must show distribution (bank/telco) and a privacy design. |

#### Idea B — Agentic disaster SOS triage and dispatch, with anticipatory action

**Target users and payers**
- **Users:** commune and provincial civil-defense commands, Red Cross chapters, volunteer rescue teams; victims via Zalo OA, SMS, web and hotline transcripts.
- **Payers:** provinces (B2G), NGOs and donors, insurers, telco/platform CSR (Zalo precedent).

**Pain evidence:** see section 2. 2025 losses were near Yagi scale; 218 dead or missing in the Central floods; 9,235 BTS down during Yagi; outages for 1.19–1.6 million customers; one-way warnings only.

**Why now**
- 2025 record floods.
- Two-tier government since 01/07/2025, which puts communes on the front line.
- National Civil Defense Steering Committee.
- PDPL from 2026 (location and health data handling).
- A possibly strong El Niño (2026 warning).
- HCMC record urban flooding (30/09/2026).

**Market size (assumptions)**

| Tier | Calculation | Result |
|---|---|---|
| **TAM** | 34 provinces × VND 0.5 bn/year platform licence + 3,321 communes × VND 20M/year | ≈ **VND 83 bn/year** |
| **SAM** | About 15 flood- and landslide-exposed Central, South-Central and Mekong provinces × VND 0.5 bn + about 1,500 communes × VND 20M | ≈ VND 37 bn/year |
| **SOM** | 1 province + 2 NGO/CSR contracts | ≈ VND 0.6–1 bn/year |

Alternative funding pools: VND 1.2–1.5 trillion in relief money per major event, flowing through the Fatherland Front.

**Competitors and the gap**
- **Vietnam:** VNDMS (monitoring); SMS and Zalo broadcasts (warnings). Volunteer SOS maps or sheets are likely but unverified.
- **Global:** Ushahidi, Everbridge, Google Flood Hub / Crisis Response, HOT/OSM (pricing unverified).
- **Gap:** two-way intake, deduplication, geocoding of old place names, triage, dispatch, status tracking and anticipatory triggers, all in Vietnamese.

**Agentic workflow**
1. **Intake agent:** takes in Zalo OA, Facebook page, SMS gateway, web form and call-transcript inputs.
2. **Extraction agent:** pulls out people and vulnerabilities, phone numbers and addresses, and normalises **pre-merger place names** to new communes.
3. **Dedup/merge agent:** combines repeated or forwarded posts and scores staleness.
4. **Triage agent:** ranks severity (children, elderly, medical need, water level) using VNDMS layers such as reservoir discharge and flash-flood warnings, plus Open-Meteo/GloFAS.
5. **Dispatch agent:** proposes the nearest capable team and route; **a human coordinator approves**.
6. **Follow-up agent:** sends SMS or Zalo re-confirmation, closes cases and produces situation reports.
7. **Anticipatory agent:** when forecast thresholds are crossed, pre-alerts registered vulnerable households (elderly living alone, disabled people) and drafts aid or cash lists for NGO approval.

**MVP (about 7 weeks):** web dashboard and map, a Zalo/Telegram/SMS intake bot, LLM extraction and deduplication, geocoding with an old-to-new mapping table, triage scoring and dispatch suggestions. Evaluate on synthetic or replayed scenarios: Central floods and an HCMC urban-flood scenario.

**Pilot near HCMC:** tabletop or shadow-mode trials with HCMC Red Cross or volunteer groups (contacts unverified); one HCMC flood-prone ward; one South-Central province during the Oct–Dec 2026 flood season for data.

**Revenue model:** grants (UNDP, Google.org — unverified), B2G licences, CSR sponsorship, and insurer claims-triage add-ons. Price benchmarks are unverified.

**Key risks**
- Life-critical triage errors and liability.
- The state may build this into VNeID or 112.
- Facebook and Zalo data-access limits.
- Seasonality and slow procurement.
- Location and health data are sensitive.

**Scores**

| Criterion | Score | Justification |
|---|---|---|
| (1) Agentic AI depth | 5 | A textbook multi-agent loop with real-world actions and human approval. |
| (2) Pain severity and why-now | 4 | Extreme losses in 2025, but SOS-handling failures are not yet documented (gap) and the link to HCMC is indirect. |
| (3) Novelty vs Vietnamese products | 4 | Only warning systems were verified; volunteer tools probably exist. |
| (4) Market size and willingness to pay | 2 | Buyers are state and NGO, seasonal, with slow procurement. |
| (5) MVP and pilot feasibility by Jan 2027 | 3 | MVP is easy on replayed data; a live pilot depends on partners and flood timing. |
| (6) Regulatory/data/trust risk (5 = low) | 2 | Life-critical decisions, sensitive data, state ownership of the channel. |
| (7) Appeal to student voters | 4 | Emotionally powerful after 2025 and HCMC flooding. |
| (8) Appeal to judges and mentors | 4 | Best agentic showcase; mentors will challenge revenue. |

#### Idea C — Agentic food-safety compliance and parent-transparency agent for school and industrial canteens

**Target users and payers**
- **Users:** kitchen managers, school health staff, principals, contract caterers, factory HR and unions; parents as viewers.
- **Payers:** caterers and factories (B2B); private schools; public schools through the meal budget or parents' association; wards and DOET dashboards (B2G, later).

**Pain evidence:** see section 3. H1 2026 had 58 outbreaks, 1,573 affected and 10 deaths, including 12 school-kitchen outbreaks with 741 students. Scavi had 222 workers poisoned (in-house canteen, about 4,000 meals a day). HCMC school-meal complaints led to supplier changes and parent inspections, and enforcement rose (+102% cases, +265% criminal cases).

**Why now**
- Amended Food Safety Law (risk-based post-inspection, national supply-chain database) heading to the 2nd session of the 16th National Assembly.
- Decree 46/2026/NĐ-CP.
- Circular 48/2025/TT-BYT.
- HCMC DOET urgent notices of 01/10/2026.
- Hà Nội's 4 review teams (09/2026).
- The school year (Sept 2026) brought the transparency demand.

**Market size (assumptions)**

| Tier | Calculation | Result |
|---|---|---|
| **TAM** | 23,018 schools already on MISA EMIS (a floor for SaaS-adopting schools) × VND 6M/year, plus industrial canteens (count unknown) | ≥ **VND 138 bn/year** |
| **SAM** (HCMC schools) | About 3,500 schools × assumed 60% with bán trú kitchens or catering ≈ 2,100 kitchens × VND 6M/year | ≈ VND 12.6 bn/year, plus industrial canteens in the merged HCMC (Bình Dương and Bà Rịa–Vũng Tàu industrial zones; count unverified) |
| **SOM** (year 2) | 60–100 school kitchens + 5–10 large industrial canteens | ≈ VND 1.5–2.5 bn/year |

Per-meal alternative (assumption): a 4,000-meal-a-day factory canteen × 300 days × VND 150 per meal ≈ **VND 180M/year per site**. A 1,538-student school × 175 days × VND 100–200 per meal ≈ VND 27–54M/year.

**Competitors and the gap**
- **Global:**
  - FoodDocs: US$79–250 per site per month (annual), AI reports in enterprise.
  - Mitti / SafetyCulture: US$24 per seat per month, with an "Agent builder" in early access.
  - Jolt (SmartSense): quote only.
  - TE-FOOD: traceability.
- **Vietnam:** MISA EMIS has no visible kitchen module. Nutrition and menu software is unverified.
- **Gap:** QĐ 1246 forms in Vietnamese, sample-retention timers, supplier-document verification, a parent-transparency feed, and an incident protocol aligned with HCMC DOET.

**Agentic workflow**
1. **Planner agent:** turns the day's menu and supplier list into required checks and a schedule.
2. **Intake and verification agent:** reads delivery photos, invoices and certificates with vision and OCR, checks expiry and origin, and flags gaps.
3. **3-step inspection agent:** runs guided checklists with photo evidence and temperature and time logs, and finds anomalies (missing steps, inconsistent timestamps).
4. **Sample-retention agent:** handles photo and label checks, a 24-hour timer and the disposal log.
5. **Transparency agent:** sends a daily menu and photo digest to parents through a Zalo OA and triages complaints.
6. **Incident agent:** when symptoms are reported, launches the protocol: preserve samples, notify the principal, ward health station and DOET, and compile an evidence pack.
7. **Compliance agent:** produces monthly reports and audit readiness, and keeps memory of supplier history.
- **Human in the loop:** the kitchen manager confirms; the principal approves outward communication.

**MVP (about 7 weeks):** a mobile-web PWA for kitchen staff, vision LLM for photos and labels, OCR for invoices and certificates, timers and notifications, a Zalo OA parent digest, and a principal dashboard. Policy packs are configurable.

**Pilot near HCMC**
- University and campus canteens: TDTU canteen access is unverified but plausible.
- A caterer serving several HCMC schools (Hồ Văn Long's new supplier "already supplies multiple schools").
- Private schools.
- Factory canteens in former Bình Dương industrial zones.
- The DOET training channel.

**Revenue model**
- SaaS per kitchen: VND 300–800k/month (assumption).
- Or per meal: VND 100–200 (assumption) billed to caterers.
- Premium tiers: parent portal and audit pack.

**Key risks**
- Data quality depends on honest logging; photos and timestamps help.
- Incumbents (MISA) could add a module, so integrate instead of competing.
- Children's privacy: never film children, keep data in Vietnam.
- Legal changes over 2026–27.
- Tight public-school budgets.

**Scores**

| Criterion | Score | Justification |
|---|---|---|
| (1) Agentic AI depth | 4 | Plans the day, gathers and verifies evidence, runs timers, escalates incidents, keeps memory; actions are mostly notifications and reports. |
| (2) Pain severity and why-now | 5 | Rising outbreaks, a live HCMC school-meal crisis, law revision, rising enforcement. |
| (3) Novelty vs Vietnamese products | 4 | No localised digital 3-step / sample-retention agent found (search was limited). |
| (4) Market size and willingness to pay | 3 | Clear B2B payers (caterers, factories) but small per-school budgets. |
| (5) MVP and pilot feasibility by Jan 2027 | 4 | Simple stack; canteens and caterers in HCMC are accessible. |
| (6) Regulatory/data/trust risk (5 = low) | 4 | Low if focused on kitchen records; cameras optional. |
| (7) Appeal to student voters | 3 | Relatable (campus canteens, younger siblings) but less dramatic. |
| (8) Appeal to judges and mentors | 4 | A compliance-driven B2B SaaS with ROI and a credible agent workflow. |

#### Idea D — Agentic public-service navigator for elderly and digitally excluded citizens

**Target users and payers**
- **Users:** elderly people, migrants and low-literacy citizens, plus their adult children, ward one-stop staff and youth-union volunteers.
- **Payers:** wards and the city (B2G); VNPost, telcos and banks (B2B2C; unverified); families.

**Pain evidence:** see section 5. Communes cut from 10,035 to 3,321; HCMC averages about 81,500 residents per unit; neighbourhoods cut from 5,947 to 3,923 (address updates); VNeID overload and penalties in Dec 2025; elderly obstacles despite more than 99% online submission.

**Why now**
- Two-tier government from 01/07/2025.
- HCMC keeps its 168 units (11/09/2026), giving a stable window.
- Support points emerging in 2026.
- Government starting to use AI (HCMC Tax AI call centre, 08/2026).

**Market size (assumptions)**

| Tier | Calculation | Result |
|---|---|---|
| **SAM** (HCMC) | 168 units × VND 60M/year | ≈ **VND 10 bn/year** |
| **National** | 3,321 units × VND 30M/year | ≈ VND 100 bn/year |
| **SOM** | 5–10 HCMC wards | ≈ VND 0.3–0.6 bn/year |

B2C willingness to pay is low.

**Competitors and the gap**
- **Existing:** the National Public Service Portal (under MPS), VNeID, the HCMC portal, the HCMC Tax AI call centre, and human volunteer teams. AI assistants on the portal or VNeID and private legal chatbots are unverified.
- **Gap:** a voice-first, Vietnamese co-pilot that turns a life event into the right procedure, a document checklist, pre-filled forms, the right reception point, and status follow-up, with a handover to a human.

**Agentic workflow**
1. **Intake (voice):** identifies the life event and procedure using the post-reform procedure database.
2. **Document agent:** OCRs existing papers, builds the checklist and pre-fills forms.
3. **Routing agent:** maps the old address to the new one and picks the ward or support point and its hours.
4. **Follow-up agent:** tracks the dossier code the citizen provides and sends reminders.
5. **Escalation:** hands off to a volunteer or officer.
- **Constraint:** no credential holding and no submission on the citizen's behalf without legal authorisation.

**MVP (about 7 weeks):** 5–10 common procedures (newborn birth and residence registration, address updates, social-pension applications, VNeID level 2), using voice ASR/TTS, form generation and routing.

**Pilot near HCMC:** ward support points (Cát Lái; Tân Nhựt and Thái Mỹ hamlet points) with youth-union volunteers.

**Revenue model:** B2G subscription per ward (assumption), white-label for VNPost or telcos (unverified), small B2C.

**Key risks**
- The state is the natural provider.
- No API, so limited autonomy.
- Impersonation of "VNeID support" undermines trust.
- Personal data handling.
- Rapidly changing procedures.

**Scores**

| Criterion | Score | Justification |
|---|---|---|
| (1) Agentic AI depth | 3 | Plans, prepares and reminds, but cannot legally submit: a co-pilot more than an agent. |
| (2) Pain severity and why-now | 4 | Reform burden and VNeID friction are well documented. |
| (3) Novelty vs Vietnamese products | 3 | State portals, AI call centres and volunteer teams already occupy the space. |
| (4) Market size and willingness to pay | 2 | Uncertain B2G budgets; free state alternatives. |
| (5) MVP and pilot feasibility by Jan 2027 | 4 | Guided flows for a few procedures; support points are accessible. |
| (6) Regulatory/data/trust risk (5 = low) | 2 | Personal data, government gatekeeping, impersonation risk. |
| (7) Appeal to student voters | 4 | Students help parents with VNeID. |
| (8) Appeal to judges and mentors | 3 | Social value clear, but business model and defensibility weak. |

#### Idea E (other) — Agentic EPR and recycling chain-of-custody agent (scrap yards → PROs and licensed recyclers)

**Target users and payers**
- **Users:** scrap yards and informal collectors.
- **Payers:** EPR-obligated producers and PROs (compliance evidence), licensed recyclers, and brands' CSR (Unilever pattern).

**Pain and why now**
- Decree 05/2025 (effective 06/01/2025): licensed recyclers only, no sub-delegation, national-system listing, annual VEPF payment by 20/04.
- EPR recycling duties since 2024–2025, with vehicles from 01/01/2027.
- HCMC weight- and volume-based fees from 01/09/2026, while sorted waste is still collected mixed.
- About 3 million informal collectors without contracts; [BG] about 1,800 scrap yards in HCMC.

**Market size (assumptions):** HCMC 1,800 scrap yards × VND 3M/year SaaS ≈ VND 5.4 bn/year, plus per-tonne verification fees from PROs (volumes unknown). SOM: 50–100 yards and 1–2 PRO or brand contracts.

**Competitors and the gap**
- Consumer points apps are crowded (GRAC, XanhNét).
- Global comparators (Recykal, Kabadiwalla, Plastic Bank) are unverified.
- **Gap:** the data and verification layer for scrap yards and pickers.

**Agentic workflow:** weight tickets captured by Zalo photo or voice → vision classifies the material → price and payment record → chain-of-custody ledger → reconcile against licensed-recycler lists → generate EPR evidence packs → detect anomalies (double counting) → human auditor signs off.

**MVP (about 7 weeks):** a Zalo mini-app or PWA plus a dashboard, piloted at one yard and one PRO or brand programme (the Unilever–GRAC station or Green House model are candidates).

**Key risks:** needs partners; low-literacy data entry; possible standalone EPR decree; data fraud.

**Scores**

| Criterion | Score | Justification |
|---|---|---|
| (1) Agentic AI depth | 4 | Capture → classify → reconcile → verify → report loop. |
| (2) Pain severity and why-now | 4 | Fresh EPR and fee rules. |
| (3) Novelty vs Vietnamese products | 4 | Few verified B2B data-layer players. |
| (4) Market size and willingness to pay | 3 | Compliance spend exists but volumes unknown. |
| (5) MVP and pilot feasibility by Jan 2027 | 3 | Partner-dependent. |
| (6) Regulatory/data/trust risk (5 = low) | 3 | Moderate. |
| (7) Appeal to student voters | 3 | Green appeal, but less personal. |
| (8) Appeal to judges and mentors | 4 | B2B, ESG and EPR revenue. |

#### Idea F (other) — Agentic safe-job and migration verifier (anti-trafficking, task scams)

**Summary**
- **Pain:** Vietnamese rescued from Myanmar scam compounds; Cambodia's mass arrests and deportations in 2026; the Laos task-scam ring (more than VND 1,500 bn); students lured by "easy jobs".
- **Agent:** checks the recruiter's licence and business registry, analyses the job post, runs red-flag checks (deposits, border destinations, unrealistic pay), drafts questions, and escalates to hotlines with human review before any labelling.
- **Payers:** universities' career centres, job platforms, NGOs (IOM/ILO; unverified). Willingness to pay is low.
- **Data risk:** the official lookup (dolab.gov.vn) was unreachable.

**Scores**

| Criterion | Score | Justification |
|---|---|---|
| (1) Agentic AI depth | 4 | Verification across several sources, then escalation. |
| (2) Pain severity and why-now | 4 | Severe, but local statistics on fake jobs are unverified. |
| (3) Novelty vs Vietnamese products | 3 | Lookups and chongluadao overlap. |
| (4) Market size and willingness to pay | 2 | Weak payers. |
| (5) MVP and pilot feasibility by Jan 2027 | 3 | Feasible, but official data access is a problem. |
| (6) Regulatory/data/trust risk (5 = low) | 3 | Defamation risk. |
| (7) Appeal to student voters | 4 | Students are targets. |
| (8) Appeal to judges and mentors | 3 | — |

**Recommendation:** make this a module of Idea A.

#### Score summary
Scores are judgement-based. Criteria: (1) agentic depth, (2) pain and why-now, (3) novelty in Vietnam, (4) market and willingness to pay, (5) MVP and pilot feasibility, (6) regulatory/data/trust risk (5 = low), (7) student-voter appeal, (8) judge/mentor appeal.

| Idea | (1) | (2) | (3) | (4) | (5) | (6) | (7) | (8) | Total /40 |
|---|---|---|---|---|---|---|---|---|---|
| A. Family-circle anti-scam guardian | 4 | 5 | 4 | 3 | 4 | 3 | 5 | 4 | **32** |
| C. Canteen food-safety compliance and transparency agent | 4 | 5 | 4 | 3 | 4 | 4 | 3 | 4 | **31** |
| B. Disaster SOS triage and dispatch (+ anticipatory action) | 5 | 4 | 4 | 2 | 3 | 2 | 4 | 4 | **28** |
| E. EPR / recycling chain-of-custody agent | 4 | 4 | 4 | 3 | 3 | 3 | 3 | 4 | **28** |
| F. Safe-job / migration verifier | 4 | 4 | 3 | 2 | 3 | 3 | 4 | 3 | **26** |
| D. Public-service navigator | 3 | 4 | 3 | 2 | 4 | 2 | 4 | 3 | **25** |

#### Ranked shortlist
1. **A — Agentic family-circle anti-scam guardian.**
   - Highest combined pain, timeliness and student-vote appeal (the audience vote is 30% of the final score). Clear agentic loop. Pitch timing falls right after Tết, the peak scam season.
   - **Must solve:** Android-first technical design, consent and privacy, and a B2B2C partner story (bank, insurer or telco).
   - **Add F as a "student mode"** covering task scams, fake jobs and fake-police calls.
2. **C — Agentic food-safety compliance and parent-transparency agent.**
   - The most bankable and lowest-risk option. Strong 2026 news hooks: the HCMC school-meal crisis and the Scavi incident.
   - **Must solve:** verification of QĐ 1246 and Decree 46/2026 requirements, one caterer or canteen pilot, and integration rather than competition with MISA-type incumbents.
3. **B — Disaster SOS triage, reframed** with anticipatory action, NGO, insurer and CSR funding, and an HCMC urban-flood scenario. Best agentic demo; weakest revenue.
4. **E — EPR / recycling chain-of-custody agent.** Credible B2B option if the team can secure a PRO, brand or scrap-yard partner quickly.
5. **D — Public-service navigator.** Better as a later module of A (the same elderly and family users) than as a standalone startup.

#### Saturated ideas to avoid (social-impact domain)
- **Standalone "check this number / link / account / QR" scam apps or chatbots.**
  - nTrust (free, 1M+ records), chongluadao (free: extension, AI website analyser, Telegram chatbot with 200k+ verifications, threat API at 1M+ calls/day).
  - Bank SIMO and ACB warnings, Google Play Protect, iOS 27.
  - Sources: [VnExpress](https://vnexpress.net/ra-mat-phan-mem-giup-phat-hien-lua-dao-mang-4775737.html), [Tech for Good Institute](https://techforgoodinstitute.org/insights/country-spotlights/building-digital-resilience-lessons-from-vietnam-2/), [Thanh Niên](https://thanhnien.vn/diem-mat-chi-ten-gui-tai-khoan-nghi-ngo-lua-dao-sang-ngan-hang-nha-nuoc-18525052912181878.htm)
- **Scam-awareness games or quizzes as the core product.** Chống Lừa Đảo's Google.org-funded "Be Scam Ready" exists — [Thanh Niên](https://thanhnien.vn/du-an-chong-lua-dao-nhan-ho-tro-tu-google-185260826144700166.htm)
- **One-way disaster-warning apps or alert broadcasting.** VNDMS, 26.4M SMS and 24.1M Zalo messages are state- and platform-owned — [SGGP](https://www.sggp.org.vn/share824458.html), [VNDMS](https://vndms.gov.vn/)
- **Plain Q&A chatbots on administrative or legal procedures.** State platforms (portal under MPS, VNeID, HCMC Tax AI call centre) occupy the space — [dichvucong.gov.vn](https://dichvucong.gov.vn/p/home/dvc-trang-chu.html), [Tuổi Trẻ](https://tuoitre.vn/thue-tphcm-ra-mat-tong-dai-ai-ho-tro-nhac-no-thong-bao-tam-hoan-xuat-canh-100260808181834978.htm). Private legal chatbots are unverified.
- **Consumer "book a scrap pickup / earn green points" apps.** GRAC (Unilever station) and XanhNét/VietCycle — [SGGP](https://www.sggp.org.vn/phan-loai-rac-tai-nguon-dung-chi-la-khau-hieu-post873917.html), [TheLeader](https://theleader.vn/tuong-lai-moi-cho-nguoi-thu-gom-phe-lieu-d37574.html)
- **Food traceability QR or blockchain stamping, or a whole school-management system.** TE-FOOD (6,000+ companies) and MISA EMIS (23,018 schools) — [TE-FOOD](https://te-food.com/), [MISA EMIS](https://emis.misa.vn/). Integrate with them; do not rebuild them.
- **Likely crowded but unverified:** donation and charity-transparency ("sao kê") platforms; hardware elderly-companion robots (ElliQ-style hardware is capital-intensive for a 7-week MVP — [ElliQ](https://elliq.com/)).

### Gaps
- **Not verified, needs follow-up:**
  - Whether any Vietnamese startup already offers a family-guardian anti-scam agent, a kitchen 3-step-inspection app or an SOS triage platform. Searches were blocked, so the novelty scores rest on absence of evidence.
  - Local willingness-to-pay anchors (consumer security apps in VND, school SaaS prices, B2G budgets).
  - Partner access: chongluadao and nTrust data APIs, bank or insurer B2B2C appetite, the TDTU canteen, HCMC Red Cross, PROs.
  - Legal texts flagged as unverified above (QĐ 1246, Decree 46/2026 details, Decree 174 year, PDPL number and date, disaster and civil-defense laws, Decree 118/2025).
- **Tip for the team:** primary research would close most of these. Run 10–15 interviews each with families, canteen operators and ward support points during Oct–Nov 2026; the market-survey section of Round 1 needs this anyway.
- **Search budget:** if the coordinator raises `CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION`, the highest-value searches are:
  - "bản đồ SOS cứu hộ lũ 2025" (SOS rescue map, 2025 floods)
  - "Quyết định 1246 kiểm thực ba bước lưu mẫu" (Decision 1246, 3-step inspection, sample retention)
  - "Nghị định 46/2026 bếp ăn tập thể" (Decree 46/2026, collective kitchens)
  - "lừa đảo trực tuyến 6 tháng đầu năm 2026" (online fraud, first 6 months of 2026)
  - "ứng dụng bảo vệ người cao tuổi lừa đảo" (apps protecting the elderly from scams)
  - "giá phần mềm quản lý bán trú" (price of school-lunch management software)
