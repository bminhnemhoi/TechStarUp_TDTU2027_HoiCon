from pathlib import Path

import pytest
from dotenv import dotenv_values

from hoicon.ops import init_env

EXAMPLE = Path(__file__).resolve().parents[2] / ".env.example"
PEPPER = "HOICON_PHONE_PEPPER_1"


@pytest.fixture
def target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / ".env"
    monkeypatch.setattr(init_env, "EXAMPLE", EXAMPLE)
    monkeypatch.setattr(init_env, "TARGET", path)
    return path


def test_creates_env_with_generated_secrets(target: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert init_env.main([]) == 0
    values = dotenv_values(target)
    assert len(values[PEPPER] or "") == 64
    assert 8 <= len(values["HOICON_ZALO_WEBHOOK_SECRET"] or "") <= 256
    assert values["HOICON_ANTHROPIC_API_KEY"] == ""  # chờ Minh dán
    printed = capsys.readouterr()
    for name in (PEPPER, "HOICON_ZALO_WEBHOOK_SECRET"):
        assert (values[name] or "") not in printed.out + printed.err
    assert not target.with_name(".env.tmp").exists()


def test_rerun_is_append_only_and_keeps_values(target: Path) -> None:
    init_env.main([])
    first = target.read_text(encoding="utf-8").replace("HOICON_ANTHROPIC_API_KEY=", "HOICON_ANTHROPIC_API_KEY=sk-fake")
    target.write_text(first, encoding="utf-8")
    assert init_env.main([]) == 0
    assert target.read_text(encoding="utf-8") == first  # không thiếu gì ⇒ không đổi một byte


def test_spaced_assignment_is_recognised_no_second_pepper(target: Path) -> None:
    """PoC review #2: `KEY = value` hợp lệ với dotenv — không được nối thêm pepper mới đè lên."""
    target.write_text(f"{PEPPER} = {'ab' * 32}\nHOICON_ZALO_WEBHOOK_SECRET=x" + "y" * 20 + "\n", encoding="utf-8")
    assert init_env.main([]) == 0
    assert dotenv_values(target)[PEPPER] == "ab" * 32


def test_existing_env_without_pepper_is_refused(target: Path) -> None:
    original = f"# {PEPPER}=old-commented\nHOICON_ANTHROPIC_API_KEY=sk-real\n# HOICON_ANTHROPIC_API_KEY=sk-old\n"
    target.write_text(original, encoding="utf-8")
    assert init_env.main([]) == 2
    assert target.read_text(encoding="utf-8") == original  # không đụng file, không xóa dòng comment

    assert init_env.main(["--new-pepper"]) == 0
    values = dotenv_values(target)
    assert len(values[PEPPER] or "") == 64
    assert values["HOICON_ANTHROPIC_API_KEY"] == "sk-real"  # PoC review #6c: khóa thật không bị dòng comment đè
    assert target.read_text(encoding="utf-8").startswith(original)
