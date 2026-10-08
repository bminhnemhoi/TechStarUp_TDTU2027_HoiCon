# -*- coding: utf-8 -*-
"""Mo hinh tai chinh HoiCon 2027-2029 (moi so lieu la GIA DINH cua doi, don vi: dong).
Xuat model.json cho file Word va ve bieu do fig_finance.png."""
import json, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

M = 1_000_000  # 1 trieu dong

A = {
    # Gia ban
    "price_family_month": 49_000,        # gia niem yet goi Gia dinh / thang
    "arpu_family_month": 45_000,         # doanh thu binh quan thuc nhan (tron goi thang + nam)
    "b2b_fee_mau_month": 5_000,          # phi B2B2C / nguoi dung hoat dong / thang
    "b2b_setup_fee": 150 * M,            # phi trien khai moi doi tac (tu nam 2028)
    "b2b_setup_fee_pilot": 100 * M,      # phi trien khai doi tac thi diem 2027
    "csr_program_fee": 40 * M,           # moi chuong trinh cong dong (tai tro/CSR)
    # Chi phi bien doi
    "cost_free_family_month": 600,       # AI + tin nhan cho gia dinh dung goi mien phi
    "cost_paid_family_month": 6_000,     # AI + giong noi + ZBS + dien tap cho goi Gia dinh
    "cost_b2b_mau_month": 2_000,         # chi phi phuc vu 1 nguoi dung B2B2C
    "payment_fee_rate": 0.02,            # phi thanh toan tren doanh thu B2C
    "csr_direct_cost_rate": 0.30,        # chi phi truc tiep chuong trinh cong dong
}

years = [2027, 2028, 2029]
V = {  # Gia dinh luong nguoi dung (gia dinh)
    2027: dict(free_end=15_000, free_avg=7_500,  paid_end=600,   paid_avg=300,
               b2b_partners_end=1, b2b_mau_avg=5_000,   b2b_months=3,  new_partner_setup=A["b2b_setup_fee_pilot"],
               csr_programs=3),
    2028: dict(free_end=60_000, free_avg=37_500, paid_end=3_000, paid_avg=1_800,
               b2b_partners_end=2, b2b_mau_avg=30_000,  b2b_months=12, new_partner_setup=A["b2b_setup_fee"],
               csr_programs=8),
    2029: dict(free_end=150_000, free_avg=105_000, paid_end=7_500, paid_avg=5_250,
               b2b_partners_end=3, b2b_mau_avg=100_000, b2b_months=12, new_partner_setup=A["b2b_setup_fee"],
               csr_programs=15),
}
F = {  # Chi phi co dinh (trieu dong) - gia dinh
    2027: dict(personnel=330, infra=60,  marketing=150, legal=80,  office=36,  rnd=40),
    2028: dict(personnel=1536, infra=180, marketing=500, legal=150, office=200, rnd=120),
    2029: dict(personnel=2592, infra=300, marketing=900, legal=200, office=300, rnd=200),
}
HEADCOUNT = {2027: "5 sáng lập (bán thời gian) + 1 CTV", 2028: "8 nhân sự toàn thời gian", 2029: "12 nhân sự toàn thời gian"}

out = {"assumptions": A, "volumes": V, "fixed": F, "years": {}}
cum_loss = 0.0
for y in years:
    v = V[y]
    rev_b2c = v["paid_avg"] * A["arpu_family_month"] * 12
    rev_b2b = v["new_partner_setup"] + v["b2b_mau_avg"] * A["b2b_fee_mau_month"] * v["b2b_months"]
    rev_csr = v["csr_programs"] * A["csr_program_fee"]
    rev = rev_b2c + rev_b2b + rev_csr

    c_free = v["free_avg"] * A["cost_free_family_month"] * 12
    c_paid = v["paid_avg"] * A["cost_paid_family_month"] * 12
    c_b2b = v["b2b_mau_avg"] * A["cost_b2b_mau_month"] * v["b2b_months"]
    c_pay = rev_b2c * A["payment_fee_rate"]
    c_csr = rev_csr * A["csr_direct_cost_rate"]
    var = c_free + c_paid + c_b2b + c_pay + c_csr
    gp = rev - var
    fixed = sum(F[y].values()) * M
    ebitda = gp - fixed
    # Thue TNDN 20% sau khi chuyen lo
    taxable = ebitda
    tax = 0.0
    if ebitda < 0:
        cum_loss += -ebitda
    else:
        offset = min(cum_loss, ebitda)
        cum_loss -= offset
        taxable = ebitda - offset
        tax = taxable * 0.20
    net = ebitda - tax
    out["years"][y] = {
        "rev_b2c": rev_b2c, "rev_b2b": rev_b2b, "rev_csr": rev_csr, "rev": rev,
        "c_free": c_free, "c_paid": c_paid, "c_b2b": c_b2b, "c_pay": c_pay, "c_csr": c_csr, "var": var,
        "gp": gp, "gm": gp / rev, "fixed": fixed, "ebitda": ebitda, "tax": tax, "net": net,
        "total_cost": var + fixed, "headcount": HEADCOUNT[y],
    }

# Luy ke dong tien (chua gom von goi)
cum = 0.0
for y in years:
    cum += out["years"][y]["net"]
    out["years"][y]["cum_net"] = cum

# Kich ban than trong: B2B2C cham 12 thang (nam 2029 chi bang muc 2028), ty le tra phi giam 40%
y = 2029
v = V[y]
paid_avg_c = v["paid_avg"] * 0.6
rev_b2c_c = paid_avg_c * A["arpu_family_month"] * 12
rev_b2b_c = A["b2b_setup_fee"] + 30_000 * A["b2b_fee_mau_month"] * 12
rev_csr_c = 10 * A["csr_program_fee"]
rev_c = rev_b2c_c + rev_b2b_c + rev_csr_c
var_c = (v["free_avg"] * A["cost_free_family_month"] * 12 + paid_avg_c * A["cost_paid_family_month"] * 12
         + 30_000 * A["cost_b2b_mau_month"] * 12 + rev_b2c_c * A["payment_fee_rate"] + rev_csr_c * A["csr_direct_cost_rate"])
# than trong: doi giu chi phi co dinh quanh muc nam 2028 (+10%) vi tang truong cham
fixed_c = 1.10 * sum(F[2028].values()) * M
out["conservative_2029"] = {"rev": rev_c, "var": var_c, "fixed": fixed_c, "ebitda": rev_c - var_c - fixed_c}
# Kich ban tich cuc: 4 doi tac, MAU binh quan 150.000, ty le tra phi +30%
paid_avg_o = v["paid_avg"] * 1.3
rev_b2c_o = paid_avg_o * A["arpu_family_month"] * 12
rev_b2b_o = 2 * A["b2b_setup_fee"] + 150_000 * A["b2b_fee_mau_month"] * 12
rev_csr_o = 20 * A["csr_program_fee"]
rev_o = rev_b2c_o + rev_b2b_o + rev_csr_o
var_o = (v["free_avg"] * 1.3 * A["cost_free_family_month"] * 12 + paid_avg_o * A["cost_paid_family_month"] * 12
         + 150_000 * A["cost_b2b_mau_month"] * 12 + rev_b2c_o * A["payment_fee_rate"] + rev_csr_o * A["csr_direct_cost_rate"])
fixed_o = (14 * 18 * 12 + 360 + 1100 + 250 + 360 + 250) * M
out["optimistic_2029"] = {"rev": rev_o, "var": var_o, "fixed": fixed_o, "ebitda": rev_o - var_o - fixed_o}

# Don vi kinh te
A2 = A
unit_family = {
    "price": A2["arpu_family_month"],
    "var": A2["cost_paid_family_month"] + A2["arpu_family_month"] * A2["payment_fee_rate"],
}
unit_family["contrib"] = unit_family["price"] - unit_family["var"]
unit_b2b = {"price": A2["b2b_fee_mau_month"], "var": A2["cost_b2b_mau_month"]}
unit_b2b["contrib"] = unit_b2b["price"] - unit_b2b["var"]
out["unit"] = {"family": unit_family, "b2b": unit_b2b}

# Ngan sach giai doan cuoc thi (10/2026 - 02/2027), dong
mvp_budget = [
    ("Điện thoại Android thử nghiệm (2 máy đã qua sử dụng, khác đời Android)", 6_000_000),
    ("Tài khoản nhà phát triển Google Play (25 USD, trả một lần)", 650_000),
    ("Tên miền, máy chủ đám mây và công cụ giám sát (5 tháng)", 1_500_000),
    ("API mô hình ngôn ngữ và giọng nói vượt hạn mức miễn phí", 3_500_000),
    ("Khảo sát và phỏng vấn (quà tặng người tham gia)", 5_000_000),
    ("In thẻ “Mật khẩu gia đình”, poster và vật phẩm gian trưng bày", 6_000_000),
    ("Sản xuất video thuyết trình (3 phút và 5 phút)", 4_000_000),
    ("Đi lại, tổ chức buổi hướng dẫn cho gia đình thí điểm", 3_000_000),
]
sub = sum(x for _, x in mvp_budget)
cont = round(sub * 0.10 / 100_000) * 100_000
mvp_budget.append(("Dự phòng (khoảng 10%)", cont))
out["mvp_budget"] = mvp_budget
out["mvp_total"] = sum(x for _, x in mvp_budget)

with open("model.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1, default=str)

# ---------------- Bieu do ----------------
plt.rcParams["font.family"] = "Arial"
fig, ax = plt.subplots(figsize=(6.6, 3.5), dpi=300)
fig.patch.set_facecolor("#ffffff")
ax.set_facecolor("#ffffff")
B = 1e9
b2c = [out["years"][y]["rev_b2c"] / B for y in years]
b2b = [out["years"][y]["rev_b2b"] / B for y in years]
csr = [out["years"][y]["rev_csr"] / B for y in years]
cost = [out["years"][y]["total_cost"] / B for y in years]
tot = [out["years"][y]["rev"] / B for y in years]
x = list(range(len(years)))
w = 0.34
xr = [i - 0.19 for i in x]   # cot doanh thu
xc = [i + 0.19 for i in x]   # cot chi phi
c1, c2, c3 = "#2a78d6", "#eb6834", "#1baf7a"
ccost = "#9a9890"
ink, ink2, muted, grid, base = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
ax.bar(xr, b2c, w, color=c1, edgecolor="#ffffff", linewidth=1.2, label="Gói Gia đình (B2C)", zorder=3)
ax.bar(xr, b2b, w, bottom=b2c, color=c2, edgecolor="#ffffff", linewidth=1.2, label="Đối tác B2B2C", zorder=3)
bot2 = [a + b for a, b in zip(b2c, b2b)]
ax.bar(xr, csr, w, bottom=bot2, color=c3, edgecolor="#ffffff", linewidth=1.2, label="Tài trợ/CSR cộng đồng", zorder=3)
ax.bar(xc, cost, w, color=ccost, edgecolor="#ffffff", linewidth=1.2, label="Tổng chi phí", zorder=3)
def vn(v):
    return f"{v:.2f}".replace(".", ",")
for i in x:
    ax.text(xr[i], tot[i] + 0.15, vn(tot[i]), ha="center", va="bottom", fontsize=8, color=ink, fontweight="bold", bbox=dict(facecolor="#ffffff", edgecolor="none", pad=1.2), zorder=5)
    ax.text(xc[i], cost[i] + 0.15, vn(cost[i]), ha="center", va="bottom", fontsize=8, color=ink2, bbox=dict(facecolor="#ffffff", edgecolor="none", pad=1.2), zorder=5)
ax.set_xticks(x)
ax.set_xticklabels([str(y) for y in years], fontsize=9, color=ink2)
ax.set_xlim(-0.6, 2.6)
ax.set_ylim(0, max(tot + cost) * 1.12)
ax.set_ylabel("Tỷ đồng", fontsize=8.5, color=muted)
ax.tick_params(axis="y", labelsize=8, colors=muted, length=0)
ax.tick_params(axis="x", length=0)
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, p: f"{v:.0f}"))
ax.grid(axis="y", color=grid, linewidth=0.6, zorder=0)
for s in ["top", "right", "left"]:
    ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color(base)
ax.spines["bottom"].set_linewidth(0.8)
leg = ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), fontsize=8, frameon=False, ncol=4,
                handlelength=1.2, columnspacing=1.4, borderaxespad=0)
for t in leg.get_texts():
    t.set_color(ink2)
fig.tight_layout()
fig.savefig("fig_finance.png", dpi=300, facecolor="#ffffff")
print(json.dumps({y: {k: round(v / M, 1) if isinstance(v, float) or isinstance(v, int) else v
                      for k, v in out["years"][y].items()} for y in years}, ensure_ascii=False, indent=1))
print("conservative", {k: round(v / M, 1) for k, v in out["conservative_2029"].items()})
print("optimistic", {k: round(v / M, 1) for k, v in out["optimistic_2029"].items()})
print("unit", out["unit"])
print("mvp_total", out["mvp_total"])
