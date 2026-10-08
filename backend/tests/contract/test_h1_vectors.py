"""Vector E.164/h1 dùng chung với Android (:rules PhoneHasherVectorsTest) — ADR-006.

Backend không chuẩn hóa số (máy làm), nhưng phải tính h1 giống hệt khi so khớp danh sách đe dọa / liên hệ tin cậy.
"""

import hashlib
import json
import re
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[3] / "docs" / "schemas" / "fixtures" / "h1_vectors.json"
E164 = re.compile(r"^\+[1-9]\d{7,14}$")


def _load() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_h1_is_sha256_of_prefixed_e164() -> None:
    data = _load()
    assert data["prefix"] == "hoicon:v1:"
    hashed = [v for v in data["vectors"] if v["e164"]]
    assert len(hashed) >= 8
    for v in hashed:
        assert E164.match(v["e164"]), v
        assert v["h1"] == hashlib.sha256((data["prefix"] + v["e164"]).encode()).hexdigest(), v["input"]
        assert v["last3"] == v["e164"][-3:]


def test_rejected_inputs_have_no_hash() -> None:
    rejected = [v for v in _load()["vectors"] if v["e164"] is None]
    assert rejected, "cần có ca bị từ chối (ẩn số, đầu số dịch vụ…)"
    assert all(v["h1"] is None and v["last3"] is None for v in rejected)


def test_inputs_unique() -> None:
    inputs = [v["input"] for v in _load()["vectors"]]
    assert len(inputs) == len(set(inputs))
