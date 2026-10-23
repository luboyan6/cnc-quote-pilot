"""Offline guard tests use synthetic bytes only; never open authorized source CAD."""

import builtins
import copy
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import geometry_probe as probe
from validate_inputs import Sample


def valid_metrics() -> dict:
    return {
        "solid_count": 1,
        "dimensions_mm": [1.0, 2.0, 3.0],
        "bounds_mm": [0.0, 0.0, 0.0, 1.0, 2.0, 3.0],
        "solid_volumes_mm3": [6.0],
        "volume_mm3": 6.0,
        "brep_valid": True,
        "system_length_unit_mm": 1.0,
    }


class GeometryProbeTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.content = b"#1=(LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT(.MILLI.,.METRE.));\nA"
        self.sample = Sample("A", "synthetic.step", len(self.content), hashlib.sha256(self.content).hexdigest())
        self.path = Path(self.directory.name) / self.sample.filename
        self.path.write_bytes(self.content)

    def test_fixed_identity_records_reconcile_abc(self):
        samples = probe.fixed_samples()
        self.assertEqual([sample.label for sample in samples], ["A", "B", "C"])
        self.assertEqual([sample.size for sample in samples], [300561, 1929001, 3609635])

    def test_same_size_hash_mismatch_never_invokes_kernel(self):
        self.path.write_bytes(self.content[:-1] + b"B")
        with patch.object(probe, "bounded_worker") as worker:
            result = probe.probe_sample(self.sample, self.path, True)
        worker.assert_not_called()
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["input_checks"]["size"], "PASS")
        self.assertEqual(result["input_checks"]["sha256"], "FAIL")
        self.assertNotIn("metrics", result)
        self.assertIn("after", result)

    def test_identity_matched_wrong_units_never_invokes_kernel(self):
        content = self.content.replace(b".MILLI.", b"$      ")
        self.path.write_bytes(content)
        sample = Sample("A", self.sample.filename, len(content), hashlib.sha256(content).hexdigest())
        with patch.object(probe, "bounded_worker") as worker:
            result = probe.probe_sample(sample, self.path, True)
        worker.assert_not_called()
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["input_checks"]["unit"], "FAIL")

    def test_missing_kernel_is_not_executed_not_fake_geometry(self):
        with patch.object(probe, "bounded_worker") as worker:
            result = probe.probe_sample(self.sample, self.path, False)
        worker.assert_not_called()
        self.assertEqual(result["status"], "NOT_EXECUTED")
        self.assertTrue(result["identity_unchanged"])
        self.assertNotIn("metrics", result)

    def test_success_is_local_only_and_preserves_identity(self):
        with patch.object(probe, "bounded_worker", return_value=valid_metrics()):
            result = probe.probe_sample(self.sample, self.path, True)
        self.assertEqual(result["status"], "MEASURED")
        self.assertTrue(result["local_only"])
        self.assertEqual(result["before"], result["after"])
        self.assertTrue(result["identity_unchanged"])

    def test_source_changed_during_import_discards_metrics(self):
        def change_synthetic_source(_sample):
            self.path.write_bytes(self.content[:-1] + b"B")
            return valid_metrics()

        with patch.object(probe, "bounded_worker", side_effect=change_synthetic_source):
            result = probe.probe_sample(self.sample, self.path, True)
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["identity_unchanged"])
        self.assertNotIn("metrics", result)

    def test_timeout_remains_failure_with_after_fingerprint(self):
        with patch.object(probe, "bounded_worker", side_effect=subprocess.TimeoutExpired("synthetic", 60)):
            result = probe.probe_sample(self.sample, self.path, True)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(result["identity_unchanged"])
        self.assertNotIn("metrics", result)

    def test_exception_message_and_source_path_are_not_disclosed(self):
        secret = "private-model-fragment"
        with patch.object(probe, "bounded_worker", side_effect=RuntimeError(secret)):
            result = probe.probe_sample(self.sample, self.path, True)
        self.assertEqual(result["status"], "FAIL")
        text = json.dumps(result)
        self.assertNotIn(secret, text)
        self.assertNotIn(str(self.path), text)

    def test_valid_metrics_are_finite_positive_and_consistent(self):
        probe.validate_metrics(valid_metrics())

    def test_nonfinite_metrics_are_rejected(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            for field in ("dimensions_mm", "bounds_mm", "solid_volumes_mm3", "volume_mm3"):
                with self.subTest(value=value, field=field):
                    metrics = copy.deepcopy(valid_metrics())
                    if isinstance(metrics[field], list):
                        metrics[field][0] = value
                    else:
                        metrics[field] = value
                    with self.assertRaises(ValueError):
                        probe.validate_metrics(metrics)

    def test_zero_negative_invalid_and_inconsistent_metrics_are_rejected(self):
        cases = [
            ("solid_count", 0),
            ("solid_count", True),
            ("solid_count", 33),
            ("volume_mm3", 0),
            ("volume_mm3", -6),
            ("volume_mm3", 7),
            ("dimensions_mm", [0, 2, 3]),
            ("dimensions_mm", [2, 2, 3]),
            ("brep_valid", False),
            ("system_length_unit_mm", 1000.0),
            ("system_length_unit_mm", True),
        ]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                metrics = valid_metrics()
                metrics[field] = value
                with self.assertRaises(ValueError):
                    probe.validate_metrics(metrics)

    def test_direct_worker_rejects_identity_and_units_before_native_import(self):
        original_import = builtins.__import__

        def reject_native(name, *args, **kwargs):
            if name == "OCP" or name.startswith("OCP."):
                self.fail("Native code imported before rejecting invalid source")
            return original_import(name, *args, **kwargs)

        for case in ("hash", "unit"):
            with self.subTest(case=case):
                content = self.content[:-1] + b"B" if case == "hash" else self.content.replace(b".MILLI.", b"$      ")
                self.path.write_bytes(content)
                sample = self.sample if case == "hash" else Sample("A", self.sample.filename, len(content), hashlib.sha256(content).hexdigest())
                with (
                    patch.object(probe, "SAMPLE_DIRECTORY", self.path.parent),
                    patch("builtins.__import__", side_effect=reject_native),
                    self.assertRaisesRegex(ValueError, "Child input identity/unit mismatch"),
                ):
                    probe.measure_with_ocp(sample)

    def test_reversed_or_zero_bounds_cannot_pass_absolute_tolerance(self):
        for upper in (-1e-12, 0.0):
            with self.subTest(upper=upper):
                metrics = valid_metrics()
                metrics["dimensions_mm"][0] = 1e-12
                metrics["bounds_mm"][3] = upper
                with self.assertRaises(ValueError):
                    probe.validate_metrics(metrics)

    def test_subprocess_has_fixed_label_timeout_and_suppressed_native_output(self):
        output = b"native private diagnostic\n" + json.dumps({"status": "MEASURED", "metrics": valid_metrics()}).encode()
        completed = subprocess.CompletedProcess([], 0, stdout=output, stderr=b"private stderr")
        with patch.object(probe.subprocess, "run", return_value=completed) as run:
            metrics = probe.bounded_worker(self.sample)
        self.assertEqual(metrics, valid_metrics())
        args, kwargs = run.call_args
        self.assertEqual(args[0][-2:], ["--worker", "A"])
        self.assertEqual(kwargs["timeout"], 60)
        self.assertTrue(kwargs["capture_output"])
        self.assertNotIn(str(self.path), args[0])

    def test_worker_nonfinite_json_and_failed_native_process_are_rejected(self):
        metrics = valid_metrics()
        metrics["volume_mm3"] = float("nan")
        for completed in (
            subprocess.CompletedProcess([], 0, stdout=json.dumps({"status": "MEASURED", "metrics": metrics}).encode(), stderr=b""),
            subprocess.CompletedProcess([], 1, stdout=b"private native failure", stderr=b"private error"),
        ):
            with self.subTest(returncode=completed.returncode):
                with patch.object(probe.subprocess, "run", return_value=completed), self.assertRaises(ValueError):
                    probe.bounded_worker(self.sample)


if __name__ == "__main__":
    unittest.main()
