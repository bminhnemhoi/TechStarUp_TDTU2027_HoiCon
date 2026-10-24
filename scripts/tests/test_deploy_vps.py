"""Test hồi quy cho hạ tầng prod (spec 012): phần kiểm biến của scripts/deploy-vps.sh và các bất biến của compose.prod.yml.

Không cần Postgres hay mạng: dùng `deploy-vps.sh --check` (chỉ kiểm, không đổi gì trên máy) với tệp biến GIẢ sinh ngẫu nhiên,
và `docker compose config` để đọc cấu hình đã nội suy. Bỏ qua nếu máy không có docker/compose.
"""

import json
import secrets
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "deploy-vps.sh"
COMPOSE = ROOT / "infra" / "compose.prod.yml"
HAVE_COMPOSE = (
    shutil.which("docker") is not None
    and subprocess.run(["docker", "compose", "version"], capture_output=True, check=False).returncode == 0
)


def hex64() -> str:
    return secrets.token_hex(32)


def good_config() -> dict[str, str]:
    return {
        "POSTGRES_PASSWORD": secrets.token_hex(24),
        "HOICON_DOMAIN": "hoicon.localhost",
        "HOICON_ACME_EMAIL": "ops@example.com",
        "HOICON_PHONE_PEPPER_1": hex64(),
        "HOICON_DATA_KEY_1": hex64(),
        "HOICON_BACKUP_KEY_1": hex64(),
        "HOICON_DEVICE_JWT_SECRET": hex64(),
        "HOICON_ZALO_BOT_TOKEN": "test-bot-token-0000",
        "HOICON_ZALO_WEBHOOK_SECRET": "test-webhook-secret",
    }


@unittest.skipUnless(HAVE_COMPOSE, "cần docker compose")
class DeployCheck(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def run_check(self, values: dict[str, str], mode: int = 0o600, *extra: str) -> subprocess.CompletedProcess[str]:
        path = Path(self.tmp.name) / "prod.cfg"
        path.write_text("".join(f"{k}={v}\n" for k, v in values.items()), encoding="utf-8")
        path.chmod(mode)
        return subprocess.run(  # noqa: S603 — đối số cố định, tệp biến giả
            ["bash", str(SCRIPT), "--check", "--env-file", str(path), *extra],  # noqa: S607
            capture_output=True,
            text=True,
            cwd=ROOT,
            check=False,
        )

    def assert_rejected(self, result: subprocess.CompletedProcess[str], values: dict[str, str], *names: str) -> None:
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 1, output)
        for name in names:
            self.assertIn(name, output)
        for secret in values.values():  # không bao giờ in giá trị, chỉ tên biến
            if len(secret) >= 16:
                self.assertNotIn(secret, output)

    def test_valid_config_passes(self) -> None:
        result = self.run_check(good_config())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("chưa đổi gì trên máy", result.stdout)

    def test_loose_file_mode_is_rejected(self) -> None:
        result = self.run_check(good_config(), 0o644)
        self.assertEqual(result.returncode, 1)
        self.assertIn("600", result.stdout + result.stderr)

    def test_missing_and_malformed_keys_are_named_not_printed(self) -> None:
        values = good_config()
        del values["HOICON_DEVICE_JWT_SECRET"]
        values["HOICON_PHONE_PEPPER_1"] = "z" * 64
        values["POSTGRES_PASSWORD"] = "short"
        values["HOICON_DOMAIN"] = "https://app.hoicon.vn"
        result = self.run_check(values)
        self.assert_rejected(
            result, values, "HOICON_DEVICE_JWT_SECRET", "HOICON_PHONE_PEPPER_1", "POSTGRES_PASSWORD", "HOICON_DOMAIN"
        )

    def test_reused_key_value_is_rejected(self) -> None:
        values = good_config()
        values["HOICON_BACKUP_KEY_1"] = values["HOICON_DATA_KEY_1"]
        result = self.run_check(values)
        self.assert_rejected(result, values, "HOICON_BACKUP_KEY_1")
        self.assertIn("trùng", result.stdout + result.stderr)

    def test_short_jwt_secret_is_rejected(self) -> None:
        values = good_config()
        values["HOICON_DEVICE_JWT_SECRET"] = "x" * 31
        self.assert_rejected(self.run_check(values), values, "HOICON_DEVICE_JWT_SECRET")

    def test_characters_compose_would_mangle_are_rejected(self) -> None:
        # Compose đọc tệp theo quy tắc dotenv: `$` bị nội suy, ` #` bắt đầu chú thích ⇒ giá trị bị cắt âm thầm (review 012 L-7).
        for name, bad in (
            ("HOICON_ZALO_WEBHOOK_SECRET", "abc$def12345"),
            ("HOICON_ZALO_BOT_TOKEN", "tok #comment12345"),
            ("HOICON_DEVICE_JWT_SECRET", "a" * 31 + "$" + "b" * 10),
        ):
            values = good_config()
            values[name] = bad
            self.assert_rejected(self.run_check(values), values, name)

    def test_unknown_option_is_rejected(self) -> None:
        result = subprocess.run(  # noqa: S603
            ["bash", str(SCRIPT), "--bogus"],  # noqa: S607
            capture_output=True,
            text=True,
            cwd=ROOT,
            check=False,
        )
        self.assertEqual(result.returncode, 1)


@unittest.skipUnless(HAVE_COMPOSE, "cần docker compose")
class ComposeInvariants(unittest.TestCase):
    """Bất biến an toàn của compose.prod.yml, đọc từ cấu hình đã nội suy (không cần dựng container)."""

    @classmethod
    def setUpClass(cls) -> None:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".cfg", delete=False)  # noqa: SIM115
        cls.addClassCleanup(Path(tmp.name).unlink)
        tmp.write("".join(f"{k}={v}\n" for k, v in good_config().items()))
        tmp.close()
        out = subprocess.run(  # noqa: S603
            ["docker", "compose", "-f", str(COMPOSE), "--env-file", tmp.name, "config", "--format", "json"],  # noqa: S607
            capture_output=True,
            text=True,
            check=True,
        )
        cls.cfg = json.loads(out.stdout)
        cls.services = cls.cfg["services"]

    def test_only_caddy_publishes_ports(self) -> None:
        published = {name: svc.get("ports") for name, svc in self.services.items() if svc.get("ports")}
        self.assertEqual(set(published), {"caddy"})
        self.assertEqual({int(p["target"]) for p in published["caddy"]}, {80, 443})

    def test_database_network_is_internal_and_postgres_is_only_on_it(self) -> None:
        self.assertTrue(self.cfg["networks"]["db"]["internal"])
        self.assertEqual(set(self.services["postgres"]["networks"]), {"db"})

    def test_web_container_cannot_reach_backend_database_or_internet(self) -> None:
        """Review 012 M-1: chiếm được web không được bỏ qua các chặn ở Caddy để gọi thẳng backend:18000."""
        web = set(self.services["web"]["networks"])
        self.assertTrue(all(self.cfg["networks"][n].get("internal") for n in web), "web chỉ ở mạng internal")
        self.assertFalse(web & set(self.services["backend"]["networks"]))
        self.assertFalse(web & set(self.services["postgres"]["networks"]))

    def test_only_caddy_shares_a_network_with_backend_besides_the_database(self) -> None:
        api = {name for name, svc in self.services.items() if "api" in svc["networks"]}
        self.assertEqual(api, {"backend", "caddy"})

    def test_consent_strict_reaches_the_container_and_defaults_on(self) -> None:
        """Rà soát 037 T009 Medium #3: cờ trong env.prod.example phải thật sự có tác dụng; mặc định `true`."""
        self.assertEqual(self.services["backend"]["environment"].get("HOICON_CONSENT_STRICT"), "true")

    def test_consent_strict_can_be_switched_off_from_the_env_file(self) -> None:
        cfg = {**good_config(), "HOICON_CONSENT_STRICT": "false"}
        with tempfile.NamedTemporaryFile("w", suffix=".cfg") as tmp:
            tmp.write("".join(f"{k}={v}\n" for k, v in cfg.items()))
            tmp.flush()
            out = subprocess.run(  # noqa: S603
                ["docker", "compose", "-f", str(COMPOSE), "--env-file", tmp.name, "config", "--format", "json"],  # noqa: S607
                capture_output=True,
                text=True,
                check=True,
            )
        self.assertEqual(json.loads(out.stdout)["services"]["backend"]["environment"]["HOICON_CONSENT_STRICT"], "false")

    def test_provider_keys_the_runtime_does_not_use_stay_out_of_the_container(self) -> None:
        env = self.services["backend"]["environment"]
        self.assertFalse([k for k in env if "GEMINI" in k])  # review 012 L-3: router thật chưa dùng

    def test_caddy_mounts_the_directory_and_deploy_reloads_it(self) -> None:
        # Mount từng tệp giữ inode cũ sau `git pull` ⇒ Caddyfile mới không bao giờ có hiệu lực.
        volumes = [v["target"] for v in self.services["caddy"]["volumes"] if v["type"] == "bind"]
        self.assertEqual(volumes, ["/etc/caddy"])
        self.assertIn("caddy reload", SCRIPT.read_text(encoding="utf-8"))

    def test_database_logs_do_not_carry_statements(self) -> None:
        command = " ".join(self.services["postgres"]["command"])
        self.assertIn("log_min_error_statement=panic", command)
        self.assertIn("log_error_verbosity=terse", command)

    def test_environment_is_forced_to_prod_and_live_zalo(self) -> None:
        env = self.services["backend"]["environment"]
        self.assertEqual(env["HOICON_ENV"], "prod")
        self.assertEqual(env["HOICON_ZALO_MODE"], "live")
        self.assertEqual(env["HOICON_RUN_WORKER"], "true")

    def test_backup_key_is_not_given_to_the_application_container(self) -> None:
        for name in ("backend", "web", "caddy"):
            env = self.services[name].get("environment", {})
            self.assertFalse([k for k in env if "BACKUP_KEY" in k], name)

    def test_hardening_flags(self) -> None:
        for name in ("backend", "web", "caddy"):
            svc = self.services[name]
            self.assertTrue(svc.get("read_only"), name)
            self.assertIn("ALL", svc.get("cap_drop", []), name)
            self.assertIn("no-new-privileges:true", svc.get("security_opt", []), name)

    def test_every_service_has_bounded_logs(self) -> None:  # review 012 L-10: nhật ký có IP khách phải có hạn
        for name, svc in self.services.items():
            opts = svc.get("logging", {}).get("options", {})
            self.assertTrue(opts.get("max-size") and opts.get("max-file"), name)

    def test_resource_limits_everywhere(self) -> None:
        for name, svc in self.services.items():
            limits = svc.get("deploy", {}).get("resources", {}).get("limits", {})
            self.assertTrue(limits.get("memory") and limits.get("cpus"), name)


class BackendImageData(unittest.TestCase):
    """Ảnh backend chỉ chép các thư mục `data/` được liệt kê: thiếu thì tính năng đọc dữ liệu đó chết trong container."""

    dockerfile = (ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")

    def test_case_file_guidance_is_copied_into_the_image(self) -> None:  # spec 031 FR-011
        self.assertIn("COPY data/case_file /app/data/case_file", self.dockerfile)
        self.assertTrue((ROOT / "data" / "case_file" / "report_guidance.vi.yaml").is_file())

    def test_eval_baselines_but_not_cassettes_or_reports_reach_the_image(self) -> None:  # spec 033 T010 (FR-012)
        ignore = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        self.assertIn("backend/eval", ignore)  # cassettes/ và reports/ vẫn bị loại
        self.assertLess(ignore.index("backend/eval"), ignore.index("!backend/eval/baseline*.json"))
        self.assertIn("COPY backend/eval/baseline*.json /app/backend/eval/", self.dockerfile)
        self.assertNotIn("backend/eval/reports", self.dockerfile)
        self.assertNotIn("backend/eval/cassettes", self.dockerfile)

    def test_coach_tips_are_copied_into_the_image(self) -> None:  # spec 032 FR-005
        self.assertIn("COPY data/coach /app/data/coach", self.dockerfile)
        self.assertTrue((ROOT / "data" / "coach" / "tips.vi.yaml").is_file())


class CaddyfileInvariants(unittest.TestCase):
    """Kiểm văn bản Caddyfile: các đường không được phơi ra Internet và bộ lọc nhật ký phải có ở CẢ logger mặc định."""

    text = (ROOT / "infra" / "caddy" / "Caddyfile").read_text(encoding="utf-8")

    def test_logs_go_to_stdout_so_docker_log_caps_apply(self) -> None:  # review 012 L-10
        self.assertIn("output stdout", self.text)
        self.assertNotIn("output file", self.text)

    def test_private_paths_are_hidden(self) -> None:
        for path in ("/mcp/*", "/docs", "/redoc", "/openapi.json"):
            self.assertIn(path, self.text.split("@hidden", 1)[1].split("\n", 1)[0])

    def test_redaction_applies_to_default_logger_and_site_logger(self) -> None:
        self.assertEqual(self.text.count("import redact_logs"), 2)

    def test_connection_timeouts_and_header_limit_are_set(self) -> None:  # review 012 M-2
        for needle in ("read_header 10s", "read_body 30s", "idle 2m", "max_header_size 16KB"):
            self.assertIn(needle, self.text)
        self.assertNotIn("write ", self.text.split("timeouts {", 1)[1].split("}", 1)[0])  # SSE giữ kết nối dài

    def test_token_redaction_also_covers_double_slash_and_location(self) -> None:  # review 012 L-1
        self.assertIn('^(/+(?:login|a|join|v1/action)/)', self.text)  # 050 T017: cả /join/<mã> của gian
        self.assertIn("resp_headers>Location delete", self.text)

    def test_port_80_is_declared_so_it_gets_the_timeouts_too(self) -> None:
        self.assertIn("http://{$HOICON_DOMAIN} {", self.text)
        self.assertIn("redir https://{host}{uri} 308", self.text)

    def test_refresh_and_content_location_are_dropped_from_logs(self) -> None:
        # Next đặt `Refresh: 0;url=/login/<token>` khi chuẩn hóa `//login/<token>` (đã thấy lọt vào log Caddy).
        for header in ("Refresh", "Content-Location"):
            self.assertIn(f"resp_headers>{header} delete", self.text)

    def test_powered_by_header_is_removed(self) -> None:  # review 012 L-11
        self.assertIn("-X-Powered-By", self.text)

    def test_secret_headers_are_dropped_from_logs(self) -> None:
        for header in ("Cookie", "Authorization", "X-Bot-Api-Secret-Token", "Referer"):
            self.assertIn(f"request>headers>{header} delete", self.text)


if __name__ == "__main__":
    unittest.main()
