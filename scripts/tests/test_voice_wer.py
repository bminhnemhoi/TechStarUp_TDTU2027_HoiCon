"""Test cho scripts/voice-wer.py và data/voice/sentences.v1.json — chạy: python3 -m unittest discover -s scripts/tests"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / "scripts" / "voice-wer.py"
_SENTENCES = _ROOT / "data" / "voice" / "sentences.v1.json"


def _load():
    spec = importlib.util.spec_from_file_location("voice_wer", _SCRIPT)
    if spec is None or spec.loader is None:
        raise ImportError(_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["voice_wer"] = mod
    spec.loader.exec_module(mod)
    return mod


vw = _load()


class NormalizeTest(unittest.TestCase):
    def test_lowercase_punctuation_and_spaces(self) -> None:
        self.assertEqual(vw.normalize("  Vâng,  ĐÚNG rồi ạ! "), "vâng đúng rồi ạ")

    def test_keeps_vietnamese_marks_nfc(self) -> None:
        decomposed = "ngân hàng".replace("â", "â")  # NFD
        self.assertEqual(vw.normalize(decomposed), "ngân hàng")
        self.assertNotEqual(vw.normalize("hỏi con"), vw.normalize("hoi con"))


class WerTest(unittest.TestCase):
    def test_identical_is_zero(self) -> None:
        self.assertEqual(vw.wer("tôi không biết", "Tôi không biết."), 0.0)

    def test_substitution_deletion_insertion(self) -> None:
        self.assertAlmostEqual(vw.wer("tôi không biết nữa", "tôi có biết nữa"), 0.25)
        self.assertAlmostEqual(vw.wer("tôi không biết nữa", "tôi biết nữa"), 0.25)
        self.assertAlmostEqual(vw.wer("tôi không biết", "tôi không biết nữa"), 1 / 3)

    def test_empty_hypothesis_is_one(self) -> None:
        self.assertEqual(vw.wer("tôi không biết", ""), 1.0)

    def test_wer_can_exceed_one(self) -> None:
        self.assertGreater(vw.wer("có", "tôi có biết nữa"), 1.0)


class IntentTest(unittest.TestCase):
    def test_unsure_before_no(self) -> None:
        self.assertEqual(vw.classify_intent("Tôi không biết nữa"), "unsure")
        self.assertEqual(vw.classify_intent("Hông biết nữa, tui lú lắm"), "unsure")
        self.assertEqual(vw.classify_intent("chắc không phải đâu"), "unsure")

    def test_no(self) -> None:
        self.assertEqual(vw.classify_intent("Không, tôi chưa chuyển tiền"), "no")
        self.assertEqual(vw.classify_intent("Hông, tui hông có đưa mã"), "no")
        self.assertEqual(vw.classify_intent("Không có, tôi vẫn chưa làm gì"), "no")

    def test_yes(self) -> None:
        self.assertEqual(vw.classify_intent("Dạ có nha"), "yes")
        self.assertEqual(vw.classify_intent("Vâng, đúng rồi ạ"), "yes")

    def test_dạ_không_is_no_and_unknown_is_none(self) -> None:
        self.assertEqual(vw.classify_intent("dạ không"), "no")
        self.assertEqual(vw.classify_intent("hôm nay trời đẹp"), "none")
        self.assertEqual(vw.classify_intent(""), "none")

    def test_word_boundary(self) -> None:
        self.assertEqual(vw.classify_intent("cóc cần"), "none")


class PercentileTest(unittest.TestCase):
    def test_nearest_rank(self) -> None:
        vals = list(range(1, 21))
        self.assertEqual(vw.percentile(vals, 50), 10)
        self.assertEqual(vw.percentile(vals, 95), 19)
        self.assertIsNone(vw.percentile([], 50))


class SentencesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.data = json.loads(_SENTENCES.read_text(encoding="utf-8"))
        self.items = self.data["sentences"]

    def test_counts_and_ids(self) -> None:
        self.assertEqual(len(self.items), 20)
        ids = [s["id"] for s in self.items]
        self.assertEqual(len(set(ids)), 20)
        self.assertEqual(sum(s["kind"] == "answer" for s in self.items), 12)
        self.assertEqual(sum(s["kind"] == "story" for s in self.items), 8)

    def test_answers_have_intent_and_regions(self) -> None:
        answers = [s for s in self.items if s["kind"] == "answer"]
        self.assertTrue(all(s["intent"] in {"yes", "no", "unsure"} for s in answers))
        self.assertEqual({s["intent"] for s in answers}, {"yes", "no", "unsure"})
        self.assertTrue({"north", "central", "south"} <= {s["region"] for s in answers})
        self.assertTrue(all(s["intent"] is None for s in self.items if s["kind"] == "story"))

    def test_intent_classifier_matches_labels(self) -> None:
        for s in self.items:
            if s["kind"] == "answer":
                self.assertEqual(vw.classify_intent(s["text"]), s["intent"], s["id"])

    def test_no_pii_like_digits(self) -> None:
        for s in self.items:
            self.assertIsNone(re.search(r"\d{7,}", s["text"].replace(" ", "")), s["id"])
            self.assertIsNone(re.search(r"\d", s["text"]), s["id"])


class SummaryTest(unittest.TestCase):
    def _records(self) -> list[dict]:
        return [
            {"avd": "hc-api36", "set": "synthetic", "recognizer": "on_device", "sentence_id": "a01",
             "transcript": "Vâng, đúng rồi ạ, tôi có đang nghe điện thoại.", "latency_ms": 400, "error": None},
            {"avd": "hc-api36", "set": "synthetic", "recognizer": "on_device", "sentence_id": "a05",
             "transcript": "", "latency_ms": None, "error": "timeout"},
            {"avd": "hc-api36", "set": "synthetic", "recognizer": "on_device", "sentence_id": "s01",
             "transcript": "họ xưng là công an và nói tài khoản của tôi liên quan đến một vụ án", "latency_ms": 600,
             "error": None},
        ]

    def test_summarize_groups_and_counts_errors_as_wrong(self) -> None:
        sentences = {s["id"]: s for s in json.loads(_SENTENCES.read_text(encoding="utf-8"))["sentences"]}
        rows = vw.summarize(self._records(), sentences)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual((row["avd"], row["set"], row["recognizer"]), ("hc-api36", "synthetic", "on_device"))
        self.assertEqual(row["n"], 3)
        self.assertEqual(row["errors"], 1)
        self.assertEqual(row["intent_total"], 2)
        self.assertEqual(row["intent_correct"], 1)
        self.assertAlmostEqual(row["intent_accuracy"], 0.5)
        self.assertAlmostEqual(row["wer"], (0.0 + 1.0 + 0.0) / 3)
        self.assertEqual(row["latency_p50"], 400)

    def test_unknown_sentence_id_is_rejected(self) -> None:
        bad = [{"avd": "x", "set": "synthetic", "recognizer": "on_device", "sentence_id": "zzz", "transcript": "a"}]
        with self.assertRaises(ValueError):
            vw.summarize(bad, {})

    def test_probe_record_without_sentence_id_gives_clear_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "sentence_id"):
            vw.summarize([{"probe": "stt", "kind": "availability"}], {})

    def test_cli_writes_markdown_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            res = Path(tmp) / "res.json"
            res.write_text(json.dumps(self._records(), ensure_ascii=False), encoding="utf-8")
            out = Path(tmp) / "out"
            proc = subprocess.run(
                [sys.executable, "-I", str(_SCRIPT), "--sentences", str(_SENTENCES), "--results", str(res),
                 "--out", str(out)], capture_output=True, text=True, check=False)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((out / "wer.json").is_file())
            md = (out / "wer.md").read_text(encoding="utf-8")
            self.assertIn("hc-api36", md)
            self.assertIn("WER", md)

    def test_jsonl_input_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            res = Path(tmp) / "res.jsonl"
            res.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in self._records()) + "\n", encoding="utf-8")
            self.assertEqual(len(vw.load_results([res])), 3)


if __name__ == "__main__":
    unittest.main()
