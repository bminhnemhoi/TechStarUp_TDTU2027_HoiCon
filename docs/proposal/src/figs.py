# -*- coding: utf-8 -*-
"""Ve so do kien truc tac tu (fig_arch.png) va ban do dinh vi canh tranh (fig_position.png)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams["font.family"] = "Arial"
NAVY, ORANGE, GREEN, GRAY = "#1F3A5F", "#C4561D", "#1E7B53", "#6B6A66"
INK, INK2, MUTED = "#0b0b0b", "#33475F", "#6B6A66"


def box(ax, x, y, w, h, title, body="", fc="#FFFFFF", ec=NAVY, ls="-", tsize=7.4, bsize=6.6, lw=0.9):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.06",
                                fc=fc, ec=ec, lw=lw, ls=ls, zorder=3))
    cx = x + w / 2
    if body:
        n = body.count("\n") + 1
        total = 0.13 + n * 0.105
        top = y + h / 2 + total / 2
        ax.text(cx, top - 0.065, title, ha="center", va="center", fontsize=tsize, fontweight="bold", color=INK, zorder=4)
        ax.text(cx, top - 0.13 - n * 0.105 / 2, body, ha="center", va="center", fontsize=bsize, color="#262626",
                linespacing=1.15, zorder=4)
    else:
        ax.text(cx, y + h / 2, title, ha="center", va="center", fontsize=tsize, fontweight="bold", color=INK, zorder=4)


def cluster(ax, x, y, w, h, title, fc, ec):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.09", fc=fc, ec=ec, lw=1.0, zorder=1))
    ax.text(x + 0.1, y + h - 0.1, title, ha="left", va="center", fontsize=7.2, fontweight="bold", color=ec, zorder=2)


def arrow(ax, p, q, color=NAVY, ls="-", both=False, lw=0.95):
    st = "<|-|>" if both else "-|>"
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=st, mutation_scale=7.5, lw=lw, color=color, ls=ls,
                                 shrinkA=0, shrinkB=0, zorder=5))


def label(ax, x, y, s, ha="left", color=INK2, size=6.2):
    ax.text(x, y, s, ha=ha, va="center", fontsize=size, color=color, style="italic", zorder=6,
            bbox=dict(fc="white", ec="none", pad=0.6))


# ---------------------------------------------------------------- Kien truc
W, H = 6.3, 4.95
fig = plt.figure(figsize=(W, H), dpi=300)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")

cluster(ax, 0.05, 3.58, 3.05, 1.32, "ĐIỆN THOẠI NGƯỜI ĐƯỢC BẢO VỆ (Android)", "#FDF3EC", ORANGE)
cluster(ax, 3.20, 3.58, 3.05, 1.32, "NGƯỜI GIÁM HỘ (con, cháu) · qua Zalo", "#EEF6F1", GREEN)
cluster(ax, 0.05, 1.47, 6.20, 1.66, "MÁY CHỦ HỎICON", "#F1F5FA", NAVY)
cluster(ax, 0.05, 0.05, 6.20, 1.08, "CÔNG CỤ (đóng gói theo chuẩn MCP)", "#F5F5F3", GRAY)

# Thiet bi
box(ax, 0.15, 3.70, 0.90, 0.80, "Tín hiệu", "(người dùng đồng ý)\nsố lạ gọi; mở app\nngân hàng khi đang\ngọi; cài app lạ")
box(ax, 1.15, 3.70, 0.90, 0.80, "Lính gác", "quy tắc tất định\nchạy trên máy;\nkhông ghi âm, không\nđọc giao dịch", fc="#FDEBDD", ec=ORANGE)
box(ax, 2.15, 3.70, 0.85, 0.80, "Khoảng dừng", "an toàn: giọng\nnói tiếng Việt,\nnút lớn «Hỏi con»")
arrow(ax, (1.05, 4.10), (1.15, 4.10))
arrow(ax, (2.05, 4.10), (2.15, 4.10), ls=(0, (2, 1.4)))

# Nguoi giam ho
box(ax, 3.30, 3.70, 1.38, 0.80, "Cảnh báo kèm tóm tắt", "mức rủi ro, bằng chứng,\nnút: Gọi mẹ · Xác minh ·\nCho phép tiếp tục")
box(ax, 4.80, 3.70, 1.35, 0.80, "Con người quyết định", "gọi lại, yêu cầu xác\nminh, cho phép hoặc\nlập hồ sơ trình báo", fc="#E3F4EC", ec=GREEN)
arrow(ax, (4.68, 4.10), (4.80, 4.10))

# May chu: hang tac tu
box(ax, 0.15, 2.22, 0.90, 0.66, "5. Huấn luyện", "diễn tập hằng tuần\ntheo thủ đoạn mới", fc="#EAF1F8")
box(ax, 1.15, 2.22, 0.90, 0.66, "1. Chấm rủi ro", "hỏi 2–3 câu, đối\nchiếu bộ nhớ", fc="#EAF1F8")
box(ax, 2.15, 2.22, 0.85, 0.66, "2. Can thiệp", "chọn mức can\nthiệp, báo con", fc="#EAF1F8")
box(ax, 3.30, 2.22, 1.38, 0.66, "Điều phối (LangGraph)", "lập kế hoạch từng bước,\ndừng chờ người duyệt,\nchọn mô hình theo độ khó")
box(ax, 4.80, 2.22, 1.35, 0.66, "3. Xác minh", "tra số, link, QR, tài\nkhoản; gọi lại người thân", fc="#EAF1F8")
# hang duoi
box(ax, 0.15, 1.57, 1.90, 0.50, "Bộ nhớ dài hạn", "danh bạ tin cậy, mật khẩu gia đình,\nlịch sử sự kiện, kết quả diễn tập")
box(ax, 2.15, 1.57, 2.53, 0.50, "Rào chắn & giám sát", "ẩn danh hóa trước khi gọi LLM · chống chèn lệnh\ntrace từng lượt chạy · bộ đánh giá 100+ kịch bản", ls=(0, (3, 1.6)))
box(ax, 4.80, 1.57, 1.35, 0.50, "4. Hồ sơ vụ việc", "đơn trình báo, kịch bản\ngọi ngân hàng", fc="#EAF1F8")

# Mui ten chinh (nhan dat trong dai trong giua hai tang)
arrow(ax, (1.60, 3.70), (1.60, 2.88))
label(ax, 1.55, 3.36, "sự kiện rủi ro\n(chỉ siêu dữ liệu)", ha="right")
arrow(ax, (2.575, 2.88), (2.575, 3.70))
label(ax, 2.62, 3.36, "lời nhắc", ha="left")
arrow(ax, (2.05, 2.55), (2.15, 2.55))
arrow(ax, (3.00, 2.84), (3.50, 3.70))
label(ax, 3.32, 3.20, "báo con", ha="left")
arrow(ax, (5.475, 3.70), (5.475, 2.88))
label(ax, 5.52, 3.36, "yêu cầu\nxác minh", ha="left")
arrow(ax, (5.475, 2.22), (5.475, 2.07), ls=(0, (2, 1.4)))
arrow(ax, (1.60, 2.22), (1.60, 2.07), both=True, color=GRAY)

# Cong cu
tools = [("Zalo OA", "tin mẫu ZBS"), ("Tra cứu rủi ro", "số, link, QR, tài khoản\n(đối tác dữ liệu)"),
         ("Kho kịch bản", "thủ đoạn lừa đảo và\nquy tắc chính thức"), ("Giọng nói tiếng Việt", "nhận dạng · tổng hợp"),
         ("Mẫu văn bản", "đơn trình báo, kịch bản\ngọi ngân hàng")]
tw, gap, x0 = 1.13, 0.0875, 0.15
for i, (t, b) in enumerate(tools):
    box(ax, x0 + i * (tw + gap), 0.17, tw, 0.66, t, b, ec=GRAY, tsize=7.1)
arrow(ax, (3.15, 1.47), (3.15, 1.13), both=True)
label(ax, 3.22, 1.30, "gọi công cụ qua MCP · mọi lượt gọi đều được ghi vết", ha="left")

fig.savefig("fig_arch.png", dpi=300, facecolor="white")
plt.close(fig)

# ---------------------------------------------------------------- Ban do dinh vi
fig, ax = plt.subplots(figsize=(6.3, 3.9), dpi=300)
ax.set_xlim(0, 1); ax.set_ylim(0, 1)
for s in ["top", "right"]:
    ax.spines[s].set_visible(False)
for s in ["left", "bottom"]:
    ax.spines[s].set_color("#c3c2b7"); ax.spines[s].set_linewidth(0.8)
ax.axhline(0.5, color="#e1e0d9", lw=0.7, zorder=0)
ax.axvline(0.5, color="#e1e0d9", lw=0.7, zorder=0)
ax.set_xticks([]); ax.set_yticks([])
ax.set_xlabel("Thời điểm can thiệp  →\nTra cứu khi người dùng tự nghĩ tới                                  Ngay trong lúc đang bị thao túng",
              fontsize=7.6, color="#52514e", labelpad=6)
ax.set_ylabel("Vai trò của gia đình  →\nMột mình tự xử lý                      Cả nhà cùng quyết định", fontsize=7.6, color="#52514e", labelpad=6)
others = [
    (0.14, 0.12, "nTrust (Hiệp hội An ninh mạng)", "left"),
    (0.22, 0.27, "Chống Lừa Đảo (tra cứu, chatbot)", "left"),
    (0.60, 0.13, "Cảnh báo của ngân hàng\n(chỉ ở bước chuyển tiền)", "left"),
    (0.86, 0.41, "Phát hiện lừa đảo trong cuộc gọi\ncủa Google Pixel (chưa có tại VN)", "right"),
    (0.44, 0.66, "Aura – gói gia đình (Mỹ,\nchưa có tại VN)", "left"),
]
for x, y, t, ha in others:
    ax.scatter([x], [y], s=46, color="#9a9890", edgecolor="white", linewidth=1.2, zorder=3)
    dx = 0.025 if ha == "left" else -0.025
    ax.text(x + dx, y, t, ha=ha, va="center", fontsize=7, color="#52514e")
ax.scatter([0.86], [0.86], s=120, color="#2a78d6", edgecolor="white", linewidth=1.6, zorder=4)
ax.text(0.835, 0.86, "HỏiCon", ha="right", va="center", fontsize=9, fontweight="bold", color="#0b0b0b")
ax.text(0.835, 0.79, "can thiệp đúng lúc +\nkéo người thân vào quyết định", ha="right", va="center", fontsize=7, color="#52514e")
fig.tight_layout()
fig.savefig("fig_position.png", dpi=300, facecolor="white")
print("figs OK")
