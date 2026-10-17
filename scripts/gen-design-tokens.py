#!/usr/bin/env python3
"""Sinh theme Compose + CSS từ design-system/hoicon/tokens.json (một nguồn sự thật, spec 010 / P1-05).

Ghi đè (tất định, chạy hai lần cho cùng byte):
  - apps/android/app/src/main/java/vn/hoicon/sentinel/ui/theme/Tokens.kt  (object HoiConTokens)
  - khối giữa hai dấu BEGIN/END trong apps/android/app/src/main/res/values/colors.xml
  - apps/web/src/app/tokens.css  (Tailwind v4 `@theme inline`)

Kiểm trước khi ghi (sai ⇒ exit 2, không ghi tệp nào): cấu trúc, định dạng hex, tên khóa, luật 15 của CLAUDE.md
(chữ thân ≥ 20sp, nhãn nút chính ≥ 24sp và đậm ≥ 600, vùng chạm ≥ 64dp), cặp tương phản trỏ tới token có thật.
Tỷ lệ tương phản do scripts/tests/test_design_tokens.py đo.

    python3 scripts/gen-design-tokens.py            # sinh
    python3 scripts/gen-design-tokens.py --check    # không ghi; exit 1 nếu tệp sinh ra lệch (CI)

`--tokens` và `--out-root` chỉ để test ghi vào thư mục tạm.
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKENS = ROOT / "design-system" / "hoicon" / "tokens.json"
KOTLIN = Path("apps/android/app/src/main/java/vn/hoicon/sentinel/ui/theme/Tokens.kt")
COLORS_XML = Path("apps/android/app/src/main/res/values/colors.xml")
CSS = Path("apps/web/src/app/tokens.css")
BEGIN = "<!-- BEGIN design_tokens: sinh bởi scripts/gen-design-tokens.py, không sửa tay -->"
END = "<!-- END design_tokens -->"
HEADER = "bởi scripts/gen-design-tokens.py từ design-system/hoicon/tokens.json — không sửa tay"

HEX = re.compile(r"#[0-9A-Fa-f]{6}")
NAME = re.compile(r"[a-z][a-z0-9_]*")
VERSION = re.compile(r"\d+\.\d+\.\d+")
FAMILY = re.compile(r"[A-Za-z0-9 ]+")
SECTIONS = ("version", "color", "font", "type", "size", "motion", "contrast_pairs")
TYPE_FIELDS = ("size_sp", "line_sp", "weight")
# Tên đang dùng ở màn hình/theme (không đổi để màn hiện có không phải sửa): tên XML ↔ token (+ alpha, nếu có).
XML_COLORS = (
    ("brand_navy", "brand.navy", None),
    ("brand_orange", "brand.orange", None),
    ("surface_white", "surface.base", None),
    ("navy_40", "brand.navy", 0x66),
)
CSS_ALIASES = {"surface.base": "background", "text.primary": "foreground"}


def pascal(*parts: str) -> str:
    return "".join(w.capitalize() for part in parts for w in part.replace(".", "_").split("_"))


def kebab(path: str) -> str:
    return path.replace(".", "-").replace("_", "-")


def colors(node: dict, prefix: str = "") -> list[tuple[str, str]]:
    """Mọi màu lá của cây `color` theo thứ tự trong JSON: [(đường dẫn, '#RRGGBB')]."""
    out: list[tuple[str, str]] = []
    for key, value in node.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict):
            out += colors(value, f"{path}.")
        else:
            out.append((path, value))
    return out


def names_ok(node: object, where: str, errors: list[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if not NAME.fullmatch(key):
                errors.append(f"tên khóa không hợp lệ: {where}.{key} (chỉ a-z, 0-9, gạch dưới; bắt đầu bằng chữ)")
            names_ok(value, f"{where}.{key}", errors)


def is_int_map(node: object) -> bool:
    """Giá trị được chèn thẳng vào Kotlin/CSS ⇒ chỉ nhận số nguyên không âm (bool không tính)."""
    return isinstance(node, dict) and bool(node) and all(
        isinstance(v, int) and not isinstance(v, bool) and v >= 0 for v in node.values()
    )


def validate(data: object) -> list[str]:
    if not isinstance(data, dict):
        return ["tokens.json phải là một đối tượng JSON"]
    errors = [f"thiếu mục bắt buộc: {s}" for s in SECTIONS if s not in data]
    if errors:
        return errors
    for section in ("color", "type", "size", "motion"):
        names_ok(data[section], section, errors)
    if not isinstance(data["color"], dict):
        return ["color phải là một đối tượng JSON"]
    leaves = colors(data["color"])
    for path, value in leaves:
        if not isinstance(value, str) or not HEX.fullmatch(value):
            errors.append(f"màu sai định dạng #RRGGBB: color.{path} = {value!r}")
    known = {p for p, _ in leaves}
    pairs = data["contrast_pairs"]
    if not isinstance(pairs, list) or not pairs or not all(isinstance(p, dict) for p in pairs):
        errors.append("contrast_pairs phải là danh sách không rỗng các đối tượng {fg, bg, kind, use}")
        pairs = []
    for i, pair in enumerate(pairs):
        for side in ("fg", "bg"):
            if not isinstance(pair.get(side), str) or pair.get(side) not in known:
                errors.append(f"contrast_pairs[{i}].{side} trỏ tới token không có: {pair.get(side)!r}")
        if pair.get("kind") not in ("text", "non_text"):
            errors.append(f"contrast_pairs[{i}].kind phải là text hoặc non_text")
    # version và family được chèn thẳng vào mã Kotlin ⇒ chỉ nhận ký tự an toàn.
    if not isinstance(data["version"], str) or not VERSION.fullmatch(data["version"]):
        errors.append(f"version sai định dạng X.Y.Z: {data['version']!r}")
    family = data["font"].get("family") if isinstance(data["font"], dict) else None
    if not isinstance(family, str) or not FAMILY.fullmatch(family):
        errors.append(f"font.family chỉ gồm chữ, số, khoảng trắng: {family!r}")
    size = data["size"] if isinstance(data["size"], dict) else {}
    int_maps = {
        "motion": data["motion"],
        "size.space_dp": size.get("space_dp"),
        "size.radius_dp": size.get("radius_dp"),
    }
    if isinstance(data["motion"], dict):
        if "reduced_ms" not in data["motion"]:
            errors.append("motion.reduced_ms là bắt buộc (giảm chuyển động ⇒ 0)")
        errors += [f"motion.{k} phải có đuôi _ms" for k in data["motion"] if not k.endswith("_ms")]
    for section, node in int_maps.items():
        if not is_int_map(node):
            errors.append(f"{section} phải là đối tượng các số nguyên ≥ 0")
    if not isinstance(data["type"], dict):
        return [*errors, "type phải là một đối tượng JSON"]
    try:
        for name, t in data["type"].items():
            for field in TYPE_FIELDS:
                if not isinstance(t.get(field), int) or isinstance(t.get(field), bool):
                    errors.append(f"type.{name}.{field} phải là số nguyên")
        types = data["type"]
        for name, t in types.items():
            if t["size_sp"] < 20:
                errors.append(f"vi phạm luật 15: type.{name}.size_sp = {t['size_sp']} < 20sp (mọi chữ ≥ 20sp)")
        button = types["button"]
        if button["size_sp"] < 24 or button["weight"] < 600:
            errors.append(
                f"vi phạm luật 15: type.button = {button['size_sp']}sp/đậm {button['weight']}, cần ≥ 24sp và đậm ≥ 600"
            )
        touch = size["touch_min_dp"]
        if not isinstance(touch, int) or isinstance(touch, bool) or touch < 64:
            errors.append(f"vi phạm luật 15: size.touch_min_dp = {touch!r}, cần số nguyên ≥ 64dp")
    except (KeyError, TypeError, AttributeError) as exc:
        errors.append(f"thiếu hoặc sai kiểu trường bắt buộc của type/size: {exc!r}")
    return errors


def argb(value: str, alpha: int = 0xFF) -> str:
    return f"0x{alpha:02X}{value[1:].upper()}"


def rem(sp: int) -> str:
    return f"{sp / 16:g}rem"


def kotlin(data: dict) -> str:
    lines = [
        f"// SINH TỰ ĐỘNG {HEADER}.",
        "package vn.hoicon.sentinel.ui.theme",
        "",
        "import androidx.compose.ui.graphics.Color",
        "",
        f"/** Token thiết kế HỏiCon v{data['version']} (docs/DESIGN-SYSTEM.md); bí danh ở Color.kt/Type.kt. */",
        "object HoiConTokens {",
        f'    const val Version = "{data["version"]}"',
        f'    const val FontFamilyName = "{data["font"]["family"]}"',
        "",
        "    object Colors {",
    ]
    lines += [f"        val {pascal(path)} = Color({argb(v)})" for path, v in colors(data["color"])]
    lines += ["    }", "", "    object Type {"]
    for name, t in data["type"].items():
        lines += [
            f"        const val {pascal(name)}Sp = {t['size_sp']}",
            f"        const val {pascal(name)}LineSp = {t['line_sp']}",
            f"        const val {pascal(name)}Weight = {t['weight']}",
        ]
    size = data["size"]
    lines += ["    }", "", "    object Size {", f"        const val TouchMinDp = {size['touch_min_dp']}"]
    lines += [f"        const val {pascal('space', k)}Dp = {v}" for k, v in size["space_dp"].items()]
    lines += [f"        const val {pascal('radius', k)}Dp = {v}" for k, v in size["radius_dp"].items()]
    lines += ["    }", "", "    object Motion {"]
    lines += [f"        const val {pascal(k)} = {v}" for k, v in data["motion"].items()]
    lines += ["    }", "}", ""]
    return "\n".join(lines)


def xml_block(data: dict) -> str:
    values = dict(colors(data["color"]))
    rows = []
    for name, path, alpha in XML_COLORS:
        hex8 = f"#{alpha:02X}{values[path][1:].upper()}" if alpha is not None else values[path].upper()
        rows.append(f'    <color name="{name}">{hex8}</color>')
    return f"{BEGIN}\n" + "\n".join(rows) + f"\n    {END}"


def css(data: dict) -> str:
    lines = [f"/* SINH TỰ ĐỘNG {HEADER}. */", "@theme inline {"]
    leaves = colors(data["color"])
    for path, value in leaves:
        lines.append(f"  --color-{CSS_ALIASES.get(path, kebab(path))}: {value.lower()};")
    lines.append("  --font-sans: var(--font-be-vietnam-pro), Arial, sans-serif;")
    for name, t in data["type"].items():
        k = kebab(name)
        lines += [
            f"  --text-{k}: {rem(t['size_sp'])};",
            f"  --text-{k}--line-height: {rem(t['line_sp'])};",
            f"  --text-{k}--font-weight: {t['weight']};",
        ]
    for name, px in data["size"]["radius_dp"].items():
        lines.append(f"  --radius-{kebab(name)}: {rem(px)};")
    lines += ["}", "", ":root {"]
    lines += [f"  --motion-{kebab(k[:-3])}: {v}ms;" for k, v in data["motion"].items() if k != "reduced_ms"]
    lines += ["  --touch-min: " + rem(data["size"]["touch_min_dp"]) + ";", "}", ""]
    lines += ["@media (prefers-reduced-motion: reduce) {", "  :root {"]
    reduced = data["motion"]["reduced_ms"]
    lines += [f"    --motion-{kebab(k[:-3])}: {reduced}ms;" for k in data["motion"] if k != "reduced_ms"]
    lines += ["  }", "}", ""]
    return "\n".join(lines)


def render(data: dict, out_root: Path) -> tuple[dict[Path, str], list[str]]:
    """Nội dung mong đợi của từng tệp; lỗi (vd. thiếu dấu BEGIN/END) trả về trong danh sách."""
    xml_path = out_root / COLORS_XML
    errors: list[str] = []
    xml = ""
    if not xml_path.exists():
        errors.append(f"không thấy {xml_path}")
    else:
        current = xml_path.read_text(encoding="utf-8")
        block = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.DOTALL)
        if current.count(BEGIN) != 1 or current.count(END) != 1 or current.index(BEGIN) > current.index(END):
            errors.append(f"cần đúng một cặp dấu {BEGIN!r} … {END!r} (BEGIN trước END) trong {xml_path}")
        else:
            xml = block.sub(lambda _: xml_block(data), current)
    return {out_root / KOTLIN: kotlin(data), xml_path: xml, out_root / CSS: css(data)}, errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="không ghi; exit 1 nếu tệp sinh ra lệch")
    ap.add_argument("--tokens", type=Path, default=TOKENS)
    ap.add_argument("--out-root", type=Path, default=ROOT)
    args = ap.parse_args()

    try:
        data = json.loads(args.tokens.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"không đọc được {args.tokens}: {exc}", file=sys.stderr)
        return 2
    errors = validate(data)
    outputs: dict[Path, str] = {}
    if not errors:
        outputs, errors = render(data, args.out_root)
    if errors:
        print("tokens.json bị từ chối, chưa ghi tệp nào:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 2

    if args.check:
        stale = [p for p, text in outputs.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
        for p in stale:
            print(f"LỆCH: {p} — chạy python3 scripts/gen-design-tokens.py", file=sys.stdout)
        return 1 if stale else 0

    for path, text in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    n = len(colors(data["color"]))
    print(f"tokens v{data['version']}: {n} màu, {len(data['type'])} cỡ chữ ⇒ {', '.join(str(p) for p in outputs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
