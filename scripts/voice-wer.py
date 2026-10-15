#!/usr/bin/env python3
"""WER + độ chính xác ý định cho kết quả nhận dạng giọng nói (spike P1-S5, spec 004-voice-vi).

Chỉ dùng thư viện chuẩn. Đầu vào: câu chuẩn (`data/voice/sentences.v1.json`) + một hay nhiều tệp kết quả
(mảng JSON hoặc JSONL; mỗi bản ghi: avd, set, recognizer, sentence_id, transcript, latency_ms, error).
Đầu ra: `<out>/wer.md` và `<out>/wer.json`.

Quy ước (đăng ký trước, docs/spikes/P1-S5-giong-noi.md §0): lượt lỗi/trống tính là sai (WER 1,0, ý định sai);
độ chính xác ý định chỉ tính trên câu `answer`; bộ phân loại ý định là của spike, không phải của sản phẩm.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

# Cụm từ khóa theo thứ tự ưu tiên: "không biết" phải xét trước "không".
_INTENT_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("unsure", ("không biết", "không rõ", "không chắc", "chắc không", "hông biết", "hông rõ", "hông chắc")),
    ("no", ("không", "chưa", "hông", "đâu có")),
    ("yes", ("có", "ừ", "vâng", "dạ", "phải", "đúng")),
)


def normalize(text: str) -> str:
    """NFC, chữ thường, bỏ dấu câu (giữ dấu tiếng Việt), gom khoảng trắng."""
    text = unicodedata.normalize("NFC", text).lower()
    text = "".join(" " if unicodedata.category(c)[0] in "PSZC" else c for c in text)
    return re.sub(r"\s+", " ", text).strip()


def wer(reference: str, hypothesis: str) -> float:
    """WER mức từ (Levenshtein). Tham chiếu rỗng: 0 nếu giả thuyết cũng rỗng, ngược lại 1."""
    ref, hyp = normalize(reference).split(), normalize(hypothesis).split()
    if not ref:
        return 0.0 if not hyp else 1.0
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i] + [0] * len(hyp)
        for j, h in enumerate(hyp, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h))
        prev = cur
    return prev[-1] / len(ref)


def _contains_phrase(words: list[str], phrase: str) -> bool:
    p = phrase.split()
    return any(words[i : i + len(p)] == p for i in range(len(words) - len(p) + 1))


def classify_intent(text: str) -> str:
    words = normalize(text).split()
    for label, phrases in _INTENT_RULES:
        if any(_contains_phrase(words, p) for p in phrases):
            return label
    return "none"


def percentile(values: list[float], pct: float) -> float | None:
    """Phân vị theo hạng gần nhất (nearest-rank)."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(math.ceil(pct / 100 * len(ordered)) - 1, 0)]


def load_results(paths: list[Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in paths:
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
            records.extend(data if isinstance(data, list) else [data])
        except json.JSONDecodeError:
            records.extend(json.loads(line) for line in raw.splitlines() if line.strip())
    return records


def summarize(records: list[dict[str, Any]], sentences: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for rec in records:
        if "sentence_id" not in rec:
            raise ValueError("bản ghi không có sentence_id — đây là log thăm dò? chỉ truyền tệp kết quả stt-<bộ>-<avd>-*.jsonl")
        if rec["sentence_id"] not in sentences:
            raise ValueError(f"sentence_id lạ: {rec['sentence_id']!r}")
        groups[(rec.get("avd", "?"), rec.get("set", "?"), rec.get("recognizer", "?"))].append(rec)

    rows: list[dict[str, Any]] = []
    for (avd, sset, recognizer), recs in sorted(groups.items()):
        wers: list[float] = []
        correct = total = errors = 0
        latencies: list[float] = []
        for rec in recs:
            ref = sentences[rec["sentence_id"]]
            failed = bool(rec.get("error")) or not (rec.get("transcript") or "").strip()
            errors += bool(rec.get("error"))
            hyp = "" if failed else rec["transcript"]
            wers.append(wer(ref["text"], hyp))
            if ref["kind"] == "answer":
                total += 1
                correct += (not failed) and classify_intent(hyp) == ref["intent"]
            if rec.get("latency_ms") is not None and not rec.get("error"):
                latencies.append(rec["latency_ms"])
        rows.append({
            "avd": avd, "set": sset, "recognizer": recognizer, "n": len(recs), "errors": errors,
            "wer": sum(wers) / len(wers), "intent_total": total, "intent_correct": correct,
            "intent_accuracy": (correct / total) if total else None,
            "latency_p50": percentile(latencies, 50), "latency_p95": percentile(latencies, 95),
        })
    return rows


def _fmt(value: float | None, pct: bool = False) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.1f}%" if pct else f"{value:.0f}"


def to_markdown(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| AVD | Bộ | Bộ nhận dạng | n | Lỗi | WER | Ý định đúng | Độ chính xác ý định | p50 ms | p95 ms |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['avd']} | {r['set']} | {r['recognizer']} | {r['n']} | {r['errors']} | {_fmt(r['wer'], True)} | "
            f"{r['intent_correct']}/{r['intent_total']} | {_fmt(r['intent_accuracy'], True)} | "
            f"{_fmt(r['latency_p50'])} | {_fmt(r['latency_p95'])} |")
    lines.append("\nLượt lỗi/trống tính là sai (WER 1,0). Nhãn môi trường: máy ảo/máy thật theo cột AVD; "
                 "`default_network` = dùng mạng, không dùng cho sản phẩm.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sentences", type=Path, required=True)
    ap.add_argument("--results", type=Path, nargs="+", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    data = json.loads(args.sentences.read_text(encoding="utf-8"))
    sentences = {s["id"]: s for s in data["sentences"]}
    try:
        rows = summarize(load_results(args.results), sentences)
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"voice-wer: {exc}", file=sys.stderr)
        return 1
    os.umask(0o077)  # kết quả đến từ bản thu của đội: chỉ chủ sở hữu đọc được
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "wer.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = to_markdown(rows)
    (args.out / "wer.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
