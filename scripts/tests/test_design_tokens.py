"""Kiểm design-system/hoicon/tokens.json và scripts/gen-design-tokens.py (spec 010).

Chạy: python3 -m unittest discover -s scripts/tests   (từ thư mục gốc repo)
"""

import colorsys
import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOKENS = ROOT / "design-system" / "hoicon" / "tokens.json"
GEN = ROOT / "scripts" / "gen-design-tokens.py"
COLORS_XML = Path("apps/android/app/src/main/res/values/colors.xml")
OUTPUTS = (
    Path("apps/android/app/src/main/java/vn/hoicon/sentinel/ui/theme/Tokens.kt"),
    COLORS_XML,
    Path("apps/web/src/app/tokens.css"),
)
TEXT_MIN = 7.0
NON_TEXT_MIN = 3.0
HUE_GAP_MIN = 30.0
MIN_PAIRS = 20


def load() -> dict:
    return json.loads(TOKENS.read_text(encoding="utf-8"))


def resolve(data: dict, path: str) -> str:
    node = data["color"]
    for part in path.split("."):
        node = node[part]
    if not isinstance(node, str):
        raise TypeError(f"{path} không phải một màu")
    return node


def luminance(hex_color: str) -> float:
    channels = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def hue(hex_color: str) -> float:
    r, g, b = (int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5))
    return colorsys.rgb_to_hsv(r, g, b)[0] * 360


def hue_gap(a: str, b: str) -> float:
    d = abs(hue(a) - hue(b))
    return min(d, 360 - d)


def run_gen(*args: str) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(GEN), *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)  # noqa: S603


def sandbox(tmp: Path, data: dict | None = None) -> tuple[Path, Path]:
    """Cây làm việc tạm: chỉ có colors.xml (có dấu BEGIN/END) để generator ghi vào; trả về (out_root, tokens)."""
    out = tmp / "out"
    target = out / COLORS_XML
    target.parent.mkdir(parents=True)
    shutil.copy(ROOT / COLORS_XML, target)
    tokens = tmp / "tokens.json"
    tokens.write_text(json.dumps(data if data is not None else load(), ensure_ascii=False), encoding="utf-8")
    return out, tokens


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ContrastTest(unittest.TestCase):
    def test_every_declared_pair_meets_threshold(self) -> None:
        data = load()
        pairs = data["contrast_pairs"]
        self.assertGreaterEqual(len(pairs), MIN_PAIRS)
        rows, failures = [], []
        for p in pairs:
            ratio = contrast(resolve(data, p["fg"]), resolve(data, p["bg"]))
            need = TEXT_MIN if p["kind"] == "text" else NON_TEXT_MIN
            ok = ratio >= need
            mark = "OK " if ok else "LỖI"
            rows.append(f"{mark} {p['kind']:8} {ratio:5.2f} (≥ {need})  {p['fg']} / {p['bg']}  — {p['use']}")
            if not ok:
                failures.append(f"{p['fg']} trên {p['bg']} = {ratio:.2f}:1 < {need}:1 ({p['kind']})")
        print("\n" + "\n".join(rows))
        self.assertEqual(failures, [], "cặp màu dưới ngưỡng tương phản")

    def test_pair_kinds_are_valid(self) -> None:
        for p in load()["contrast_pairs"]:
            self.assertIn(p["kind"], ("text", "non_text"), p)

    def test_required_pairs_present(self) -> None:
        data = load()
        declared = {(p["fg"], p["bg"], p["kind"]) for p in data["contrast_pairs"]}
        required = {
            ("text.primary", "surface.base", "text"),
            ("text.primary", "surface.muted", "text"),
            ("text.on_primary", "brand.navy", "text"),
            ("brand.orange_text", "surface.base", "text"),
            ("brand.green_text", "surface.base", "text"),
            ("brand.orange", "surface.base", "non_text"),
            ("brand.green", "surface.base", "non_text"),
        }
        for level in ("low", "medium", "high", "critical"):
            required |= {
                (f"risk.{level}.fg", "surface.base", "text"),
                (f"risk.{level}.fg", f"risk.{level}.bg", "text"),
                (f"risk.{level}.accent", "surface.base", "non_text"),
            }
        required |= {
            ("drill.fg", "surface.base", "text"),
            ("drill.fg", "drill.bg", "text"),
            ("drill.accent", "surface.base", "non_text"),
            ("sim.fg", "surface.base", "text"),
            ("sim.fg", "sim.bg", "text"),
            ("sim.accent", "surface.base", "non_text"),
        }
        self.assertEqual(sorted(required - declared), [])

    def test_orange_and_green_never_used_as_text(self) -> None:
        for p in load()["contrast_pairs"]:
            if p["fg"] in ("brand.orange", "brand.green"):
                self.assertEqual(p["kind"], "non_text", f"{p['fg']} chỉ được khai báo là non_text")


class DrillHueTest(unittest.TestCase):
    def test_drill_hue_differs_from_every_risk_level(self) -> None:
        data = load()
        drill = resolve(data, "drill.fg")
        for level in ("low", "medium", "high", "critical"):
            gap = hue_gap(drill, resolve(data, f"risk.{level}.fg"))
            self.assertGreaterEqual(gap, HUE_GAP_MIN, f"drill gần màu rủi ro {level}: {gap:.0f}°")


class SimHueTest(unittest.TestCase):
    """Spec 033 FR-015: băng MÔ PHỎNG có màu riêng, tách khỏi diễn tập (luật 15) và khỏi các mức rủi ro."""

    def test_sim_hue_differs_from_drill_and_every_risk_level(self) -> None:
        data = load()
        for part in ("fg", "accent"):
            sim = resolve(data, f"sim.{part}")
            gap = hue_gap(sim, resolve(data, f"drill.{part}"))
            self.assertGreaterEqual(gap, HUE_GAP_MIN, f"sim.{part} gần màu diễn tập: {gap:.0f}°")
            for level in ("low", "medium", "high", "critical"):
                gap = hue_gap(sim, resolve(data, f"risk.{level}.{part}"))
                self.assertGreaterEqual(gap, HUE_GAP_MIN, f"sim.{part} gần risk.{level}.{part}: {gap:.0f}°")


class Rule15Test(unittest.TestCase):
    def test_shipped_tokens_obey_elder_rules(self) -> None:
        data = load()
        for name, t in data["type"].items():
            if name.startswith("body"):
                self.assertGreaterEqual(t["size_sp"], 20, name)
        self.assertGreaterEqual(data["type"]["button"]["size_sp"], 24)
        self.assertGreaterEqual(data["type"]["button"]["weight"], 600)
        self.assertGreaterEqual(data["size"]["touch_min_dp"], 64)


class GeneratorTest(unittest.TestCase):
    def test_deterministic_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out, tokens = sandbox(Path(tmp))
            first = run_gen("--tokens", str(tokens), "--out-root", str(out))
            self.assertEqual(first.returncode, 0, first.stderr)
            hashes = {str(p): sha(out / p) for p in OUTPUTS}
            second = run_gen("--tokens", str(tokens), "--out-root", str(out))
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(hashes, {str(p): sha(out / p) for p in OUTPUTS})

    def test_check_passes_then_detects_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out, tokens = sandbox(Path(tmp))
            self.assertEqual(run_gen("--tokens", str(tokens), "--out-root", str(out)).returncode, 0)
            self.assertEqual(run_gen("--check", "--tokens", str(tokens), "--out-root", str(out)).returncode, 0)
            css = out / OUTPUTS[2]
            css.write_text(css.read_text(encoding="utf-8") + "/* sửa tay */\n", encoding="utf-8")
            drift = run_gen("--check", "--tokens", str(tokens), "--out-root", str(out))
            self.assertEqual(drift.returncode, 1)
            self.assertIn("tokens.css", drift.stdout + drift.stderr)

    def test_check_never_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out, tokens = sandbox(Path(tmp))
            before = sha(out / COLORS_XML)
            self.assertEqual(run_gen("--check", "--tokens", str(tokens), "--out-root", str(out)).returncode, 1)
            self.assertEqual(before, sha(out / COLORS_XML))
            self.assertFalse((out / OUTPUTS[0]).exists())

    def test_committed_outputs_are_up_to_date(self) -> None:
        result = run_gen("--check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_generated_files_keep_legacy_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out, tokens = sandbox(Path(tmp))
            self.assertEqual(run_gen("--tokens", str(tokens), "--out-root", str(out)).returncode, 0)
            xml = (out / COLORS_XML).read_text(encoding="utf-8")
            for name in ("brand_navy", "brand_orange", "surface_white", "navy_40"):
                self.assertIn(f'name="{name}"', xml)
            css = (out / OUTPUTS[2]).read_text(encoding="utf-8")
            for name in ("--color-background", "--color-foreground", "--color-brand-navy", "--color-brand-orange-text"):
                self.assertIn(name, css)
            kt = (out / OUTPUTS[0]).read_text(encoding="utf-8")
            for name in ("BrandNavy", "BrandOrangeText", "SurfaceBase"):
                self.assertIn(name, kt)


class GeneratedValuesTest(unittest.TestCase):
    """Đối chiếu độc lập tệp sinh ra với tokens.json (không so generator với chính nó)."""

    def test_values_match_json(self) -> None:
        data = load()
        with tempfile.TemporaryDirectory() as tmp:
            out, tokens = sandbox(Path(tmp))
            self.assertEqual(run_gen("--tokens", str(tokens), "--out-root", str(out)).returncode, 0)
            kt = (out / OUTPUTS[0]).read_text(encoding="utf-8")
            css = (out / OUTPUTS[2]).read_text(encoding="utf-8")
            xml = (out / COLORS_XML).read_text(encoding="utf-8")
        navy = resolve(data, "brand.navy")[1:].upper()
        self.assertIn(f"val BrandNavy = Color(0xFF{navy})", kt)
        self.assertIn(f"val RiskCriticalFg = Color(0xFF{resolve(data, 'risk.critical.fg')[1:].upper()})", kt)
        self.assertIn(f'<color name="brand_navy">#{navy}</color>', xml)
        self.assertIn(f'<color name="navy_40">#66{navy}</color>', xml)
        self.assertIn(f"--color-foreground: {resolve(data, 'text.primary').lower()};", css)
        self.assertIn(f"--color-risk-high-fg: {resolve(data, 'risk.high.fg').lower()};", css)
        body = data["type"]["body"]
        self.assertIn(f"const val BodySp = {body['size_sp']}", kt)
        self.assertIn(f"--text-body: {body['size_sp'] / 16:g}rem;", css)
        self.assertIn(f"const val TouchMinDp = {data['size']['touch_min_dp']}", kt)

    def test_drill_accent_and_bg_not_close_to_risk(self) -> None:
        data = load()
        for part in ("accent", "bg"):
            drill = resolve(data, f"drill.{part}")
            for level in ("low", "medium", "high", "critical"):
                other = resolve(data, f"risk.{level}.{part}")
                if part == "bg" and drill == other:
                    self.fail(f"drill.bg trùng risk.{level}.bg")
                if part == "accent":
                    self.assertGreaterEqual(hue_gap(drill, other), HUE_GAP_MIN, f"drill.accent gần risk.{level}.accent")


class GeneratorMarkersTest(unittest.TestCase):
    BEGIN = "<!-- BEGIN design_tokens: sinh bởi scripts/gen-design-tokens.py, không sửa tay -->"
    END = "<!-- END design_tokens -->"

    def reject_xml(self, body: str) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out, tokens = sandbox(Path(tmp))
            (out / COLORS_XML).write_text(f"<resources>\n{body}\n</resources>\n", encoding="utf-8")
            result = run_gen("--tokens", str(tokens), "--out-root", str(out))
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertFalse((out / OUTPUTS[2]).exists(), "không được ghi tệp khi dấu sai")

    def test_duplicate_markers_rejected(self) -> None:
        pair = f"{self.BEGIN}\n{self.END}"
        self.reject_xml(f"{pair}\n{pair}")

    def test_end_before_begin_rejected(self) -> None:
        self.reject_xml(f"{self.END}\n{self.BEGIN}")

    def test_missing_end_rejected(self) -> None:
        self.reject_xml(self.BEGIN)


class GeneratorRejectsBadInputTest(unittest.TestCase):
    def reject(self, mutate, expect: str) -> None:
        data = copy.deepcopy(load())
        mutate(data)
        with tempfile.TemporaryDirectory() as tmp:
            out, tokens = sandbox(Path(tmp), data)
            before = sha(out / COLORS_XML)
            result = run_gen("--tokens", str(tokens), "--out-root", str(out))
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn(expect, result.stderr)
            self.assertEqual(before, sha(out / COLORS_XML), "không được ghi tệp khi từ chối")
            self.assertFalse((out / OUTPUTS[0]).exists())
            self.assertFalse((out / OUTPUTS[2]).exists())

    def test_bad_hex(self) -> None:
        self.reject(lambda d: d["color"]["brand"].__setitem__("navy", "#12G456"), "brand.navy")

    def test_body_text_below_20sp(self) -> None:
        self.reject(lambda d: d["type"]["body"].__setitem__("size_sp", 18), "luật 15")

    def test_button_label_below_24sp(self) -> None:
        self.reject(lambda d: d["type"]["button"].__setitem__("size_sp", 18), "luật 15")

    def test_button_label_not_bold(self) -> None:
        self.reject(lambda d: d["type"]["button"].__setitem__("weight", 400), "luật 15")

    def test_touch_target_below_64dp(self) -> None:
        self.reject(lambda d: d["size"].__setitem__("touch_min_dp", 48), "luật 15")

    def test_invalid_token_name(self) -> None:
        self.reject(lambda d: d["color"]["brand"].__setitem__("Bad-Name", "#FFFFFF"), "Bad-Name")

    def test_pair_references_unknown_token(self) -> None:
        self.reject(lambda d: d["contrast_pairs"][0].__setitem__("fg", "text.missing"), "text.missing")

    def test_empty_contrast_pairs(self) -> None:
        self.reject(lambda d: d.__setitem__("contrast_pairs", []), "contrast_pairs")

    def test_contrast_pair_not_object(self) -> None:
        self.reject(lambda d: d["contrast_pairs"].__setitem__(0, "x"), "contrast_pairs")

    def test_version_injection(self) -> None:
        self.reject(lambda d: d.__setitem__("version", '1"; evil'), "version")

    def test_font_family_injection(self) -> None:
        self.reject(lambda d: d["font"].__setitem__("family", 'x"; evil'), "font.family")

    def test_motion_not_numbers(self) -> None:
        self.reject(lambda d: d["motion"].__setitem__("short_ms", "150; evil"), "motion")

    def test_motion_not_object(self) -> None:
        self.reject(lambda d: d.__setitem__("motion", "x"), "motion")

    def test_space_not_integer(self) -> None:
        self.reject(lambda d: d["size"]["space_dp"].__setitem__("xs", 4.5), "size.space_dp")

    def test_missing_reduced_motion(self) -> None:
        self.reject(lambda d: d["motion"].pop("reduced_ms"), "reduced_ms")

    def test_pair_side_not_string(self) -> None:
        self.reject(lambda d: d["contrast_pairs"][0].__setitem__("fg", ["x"]), "contrast_pairs[0].fg")

    def test_any_type_token_below_20sp(self) -> None:
        extra = {"size_sp": 12, "line_sp": 16, "weight": 400}
        self.reject(lambda d: d["type"].__setitem__("caption", extra), "luật 15")

    def test_boolean_weight(self) -> None:
        self.reject(lambda d: d["type"]["body"].__setitem__("weight", True), "type.body.weight")

    def test_motion_key_without_ms_suffix(self) -> None:
        self.reject(lambda d: d["motion"].__setitem__("slow", 400), "_ms")

    def test_missing_section(self) -> None:
        self.reject(lambda d: d.pop("motion"), "motion")


if __name__ == "__main__":
    unittest.main()
