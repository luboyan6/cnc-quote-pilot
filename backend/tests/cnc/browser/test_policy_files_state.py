import hashlib
import socket
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock, patch

from _support import POLICY, SCOPE, STEP_BYTES, TestCrypto, fixture_step

from app.modules.cnc.browser.contracts import Parameters, SessionScope
from app.modules.cnc.browser.errors import BrowserStop, Reason
from app.modules.cnc.browser.files import upload_step, upload_step_with_chooser
from app.modules.cnc.browser.policy import BrowserPolicy
from app.modules.cnc.browser.state import SessionCodec


class PolicyTests(unittest.TestCase):
    def test_rejects_non_exact_scheme_host_port_credentials_and_encoding(self):
        POLICY.validate_url("https://fixture.example.com/path?token=synthetic#fragment")
        for url in (
            "http://fixture.example.com/",
            "https://fixture.example.com:444/",
            "https://fixture.example.com.evil.test/",
            "https://sub.fixture.example.com/",
            "https://user:secret@fixture.example.com/",
            "https://fixture.example.com@127.0.0.1/",
            "file:///etc/passwd",
            "data:text/html,hello",
            "https://fixture.example.com./",
            "https://fixture.example.com\\@evil.test/",
            "https://fixture.example.com/\nsecret",
            "https://127.0.0.1/",
            "https://[::1]/",
        ):
            with self.subTest(url=url), self.assertRaises(BrowserStop) as error:
                POLICY.validate_url(url)
            self.assertEqual(error.exception.reason, Reason.POLICY_BLOCKED)
            self.assertNotIn("secret", str(error.exception))

    def test_rejects_wildcards_ips_and_mutable_policy(self):
        for hosts in ({"fixture.example.com"}, frozenset(), frozenset({"*.example.com"}), frozenset({"127.0.0.1"}), frozenset({"UPPER.example.com"})):
            with self.subTest(hosts=hosts), self.assertRaises(BrowserStop):
                BrowserPolicy(hosts)

    @staticmethod
    def records(*ips):
        return [(2, 1, 6, "", (ip, 443)) for ip in ips]

    def test_dns_filters_unsafe_candidates_and_rejects_unsafe_only_answers(self):
        for ip in ("127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "fd00::1", "fe80::1", "fec0::1", "feff:ffff::1", "0.0.0.0", "224.0.0.1", "100.64.0.1", "192.0.2.1", "2001:2::120"):
            with self.subTest(unsafe_only=ip), patch("app.modules.cnc.browser.policy.socket.getaddrinfo", return_value=self.records(ip)):
                with self.assertRaises(ValueError) as error:
                    POLICY.resolve("fixture.example.com")
                self.assertEqual(str(error.exception), Reason.POLICY_BLOCKED.value)
            for answers in (("8.8.8.8", ip), (ip, "8.8.8.8")):
                with self.subTest(answers=answers), patch("app.modules.cnc.browser.policy.socket.getaddrinfo", return_value=self.records(*answers)):
                    self.assertEqual(POLICY.resolve("fixture.example.com"), ["8.8.8.8"])

    def test_resolver_returns_only_vetted_literal_ips_and_denies_unknown_host(self):
        with patch("app.modules.cnc.browser.policy.socket.getaddrinfo", return_value=self.records("8.8.8.8", "2001:4860:4860::8888", "8.8.8.8", "1.1.1.1", "2001:4860:4860::8888")) as dns:
            self.assertEqual(POLICY.resolve("fixture.example.com"), ["8.8.8.8", "2001:4860:4860::8888", "1.1.1.1"])
            dns.assert_called_once_with("fixture.example.com", 443, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
            with self.assertRaises(ValueError):
                POLICY.resolve("evil.test")
            self.assertEqual(dns.call_count, 1)

    def test_dns_rejects_empty_or_malformed_answers_with_fixed_reason(self):
        for records in ([], None, self.records("invalid-synthetic-detail"), self.records("8.8.8.8", "invalid-synthetic-detail"), [()], self.records("8.8.8.8") + [()], [(2, 1, 6, "", ())]):
            with self.subTest(records=records), patch("app.modules.cnc.browser.policy.socket.getaddrinfo", return_value=records):
                with self.assertRaises(ValueError) as error:
                    POLICY.resolve("fixture.example.com")
                self.assertEqual(str(error.exception), Reason.POLICY_BLOCKED.value)

    def test_dns_resolver_faults_have_fixed_reason(self):
        for fault in (OSError("synthetic-private-detail"), ValueError("synthetic-private-detail"), TypeError("synthetic-private-detail")):
            with self.subTest(fault=type(fault).__name__), patch("app.modules.cnc.browser.policy.socket.getaddrinfo", side_effect=fault):
                with self.assertRaises(ValueError) as error:
                    POLICY.resolve("fixture.example.com")
                self.assertEqual(str(error.exception), Reason.POLICY_BLOCKED.value)

    def test_scope_and_full_parameters_have_no_global_or_float_default(self):
        for values in (("", "p", "a"), ("o", " ", "a"), ("o", "p", "a\nsecret")):
            with self.assertRaises(BrowserStop):
                SessionScope(*values)
        for values in ({}, {"quantity": 2.0}, {"quantity": ""}):
            with self.assertRaises(BrowserStop):
                Parameters.from_mapping(values)


class StateTests(unittest.TestCase):
    def test_real_cipher_scope_binding_tamper_and_private_origin(self):
        crypto = TestCrypto()
        state_codec = SessionCodec(crypto)
        state = {
            "cookies": [{"domain": "fixture.example.com", "name": "session", "value": "synthetic-cookie"}],
            "origins": [{"origin": "https://fixture.example.com", "localStorage": [{"name": "auth", "value": "synthetic-token"}], "indexedDB": []}],
        }
        ciphertext = state_codec.seal(SCOPE, state, POLICY)
        self.assertNotIn("synthetic-cookie", ciphertext)
        self.assertNotIn("synthetic-token", ciphertext)
        self.assertEqual(state_codec.open(SCOPE, ciphertext, POLICY), state)
        for changed in (replace(SCOPE, owner_id="other"), replace(SCOPE, platform_code="other"), replace(SCOPE, account_id="other")):
            with self.assertRaises(BrowserStop):
                state_codec.open(changed, ciphertext, POLICY)
        with self.assertRaises(BrowserStop):
            state_codec.open(SCOPE, ciphertext[:-5] + "xxxxx", POLICY)
        with self.assertRaises(BrowserStop):
            state_codec.seal(SCOPE, {"cookies": [], "origins": [{"origin": "https://127.0.0.1"}]}, POLICY)
        with self.assertRaises(BrowserStop):
            state_codec.seal(SCOPE, {"cookies": [{"domain": "evil.test"}], "origins": []}, POLICY)


class FileTests(unittest.IsolatedAsyncioTestCase):
    async def test_setp_alias_preserves_verified_bytes_and_sdk_name(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            step = fixture_step(root)
            for suffix in (".setp", ".SETP"):
                path = root / ("alias" + suffix)
                path.write_bytes(STEP_BYTES)
                payload = replace(step, path=path).read_verified()
                self.assertEqual(payload.buffer, STEP_BYTES)
                self.assertEqual(payload.sha256, step.expected_sha256)
                locator = AsyncMock()
                await upload_step(locator, payload)
                locator.set_input_files.assert_awaited_once_with({"name": "part.step", "mimeType": "application/step", "buffer": STEP_BYTES})
                self.assertTrue(path.exists())

    async def test_verified_bytes_avoid_path_reopen_and_sdk_uses_buffer(self):
        with tempfile.TemporaryDirectory() as directory:
            step = fixture_step(Path(directory))
            payload = step.read_verified()
            step.path.write_bytes(b"changed after verification")
            locator = AsyncMock()
            await upload_step(locator, payload)
            sent = locator.set_input_files.call_args.args[0]
            self.assertEqual(sent["buffer"], STEP_BYTES)
            self.assertEqual(sent["name"], "part.step")
            self.assertNotIn(directory, repr(sent))
            self.assertNotIn(STEP_BYTES.decode(), repr(payload))
            with self.assertRaises(BrowserStop):
                step.read_verified()

    async def test_chooser_uses_official_context_manager(self):
        with tempfile.TemporaryDirectory() as directory:
            payload = fixture_step(Path(directory)).read_verified()
            chooser = AsyncMock()

            class EventInfo:
                @property
                def value(self):
                    async def result():
                        return chooser

                    return result()

            class Page:
                def expect_file_chooser(self):
                    context = AsyncMock()
                    context.__aenter__.return_value = EventInfo()
                    return context

            trigger = AsyncMock()
            await upload_step_with_chooser(Page(), trigger, payload)
            trigger.click.assert_awaited_once()
            chooser.set_files.assert_awaited_once_with(payload.sdk_payload())

    async def test_size_hash_extension_and_root_boundary(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            step = fixture_step(root)
            for bad in (replace(step, expected_size=len(STEP_BYTES) + 1), replace(step, expected_sha256="f" * 64), replace(step, max_size=1)):
                with self.assertRaises(BrowserStop):
                    bad.read_verified()
            invalid = root / "bad.txt"
            invalid.write_bytes(STEP_BYTES)
            with self.assertRaises(BrowserStop):
                replace(step, path=invalid).read_verified()
            external = Path(outside) / "external.step"
            external.write_bytes(STEP_BYTES)
            with self.assertRaises(BrowserStop):
                replace(step, path=external).read_verified()
            non_step = b"this is not STEP data"
            step.path.write_bytes(non_step)
            with self.assertRaises(BrowserStop):
                replace(step, expected_sha256=hashlib.sha256(non_step).hexdigest(), expected_size=len(non_step)).read_verified()

    async def test_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            step = fixture_step(root)
            external = Path(outside) / "external.step"
            external.write_bytes(STEP_BYTES)
            link = root / "escape.step"
            try:
                link.symlink_to(external)
            except OSError:
                self.skipTest("UNVERIFIED: Windows symlink privilege unavailable")
            with self.assertRaises(BrowserStop):
                replace(step, path=link).read_verified()
