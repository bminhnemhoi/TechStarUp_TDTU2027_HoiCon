"""`python -m hoicon.ops.mcp_token new --client <tên>` (spec 003 FR-008): token in một lần, cấu hình chỉ có SHA-256."""

import hashlib
import json
import re
from pathlib import Path

import pytest

from hoicon.ops import mcp_token


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str]:
    code = mcp_token.main(list(argv))
    return code, capsys.readouterr().out


def parse(out: str) -> tuple[str, str, str]:
    """(token, tên client, hash) từ output: token ở dòng riêng, cấu hình ở dòng HOICON_MCP_THREAT_CLIENTS=…"""
    token = re.search(r"^TOKEN: (\S+)$", out, re.MULTILINE)
    config = re.search(r"^HOICON_MCP_THREAT_CLIENTS=(\{.*\})$", out, re.MULTILINE)
    assert token and config, out
    ((name, digest),) = json.loads(config.group(1)).items()
    return token.group(1), name, digest


def test_token_is_long_random_and_config_holds_only_its_sha256(capsys: pytest.CaptureFixture[str]) -> None:
    code, out = run(capsys, "new", "--client", "claude-team")
    assert code == 0
    token, name, digest = parse(out)
    assert name == "claude-team" and len(token) >= 43  # token_urlsafe(32) ⇒ ≥ 32 byte ngẫu nhiên
    assert digest == hashlib.sha256(token.encode()).hexdigest()
    assert out.count(token) == 1  # in MỘT lần (dòng cấu hình không chứa token)


def test_every_run_makes_a_different_token(capsys: pytest.CaptureFixture[str]) -> None:
    first = parse(run(capsys, "new", "--client", "a")[1])[0]
    second = parse(run(capsys, "new", "--client", "a")[1])[0]
    assert first != second


@pytest.mark.parametrize("bad", ["", "Có Dấu", "a b", "x" * 33, "../etc", 'a"b'])
def test_client_name_is_validated(bad: str, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        mcp_token.main(["new", "--client", bad])
    assert exc.value.code == 2
    assert "TOKEN" not in capsys.readouterr().out


def test_it_touches_no_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    run(capsys, "new", "--client", "claude-team")
    assert list(tmp_path.iterdir()) == []  # không đọc/ghi .env: người dùng tự dán dòng cấu hình
