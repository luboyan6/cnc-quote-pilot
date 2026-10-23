"""Read-only, bounded local CAD research for the three fixed authorized samples only."""

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import platform
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from validate_inputs import PARENT_RESEARCH, SAMPLE_DIRECTORY, Sample, check_sample, recorded_samples

RESEARCH = Path(__file__).resolve().parent
TIMEOUT_SECONDS = 60
MAX_SOLIDS = 32
C_FILENAME = "292.1001A (CS ring 5mm).STEP"


def fixed_samples() -> list[Sample]:
    """Reuse the A/B record parser; reconcile fixed C against both prior records."""
    parent = (PARENT_RESEARCH / "step-samples-2026-10-21.md").read_text(encoding="utf-8")
    samples = recorded_samples(parent)
    live = (RESEARCH / "live-validation-2026-10-21.md").read_text(encoding="utf-8")
    rows = [tuple(cell.strip() for cell in line.split("|")[1:-1]) for line in live.splitlines() if line.startswith("|")]
    for sample in samples:
        expected = (sample.label, sample.filename, str(sample.size), f"`{sample.sha256}`")
        if rows.count(expected) != 1:
            raise ValueError("A/B identity differs between authorized records")
    matches = [row for row in rows if len(row) == 4 and row[0] == "C, fallback" and row[1] == C_FILENAME]
    if len(matches) != 1:
        raise ValueError("Missing or ambiguous C identity")
    size, digest = matches[0][2], matches[0][3].strip("`")
    if not size.isdecimal() or not re.fullmatch(r"[a-f0-9]{64}", digest) or f"| 备用 | `{digest}` |" not in parent:
        raise ValueError("Invalid or inconsistent C identity")
    samples.append(Sample("C", C_FILENAME, int(size), digest))
    return samples


def fingerprint(path: Path) -> dict:
    """Bounded-memory SHA-256; no bytes, names or source paths in the result."""
    with path.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    return {"bytes": path.stat().st_size, "sha256": digest, "mtime_ns": path.stat().st_mtime_ns}


def matches_identity(sample: Sample, value: dict) -> bool:
    return value["bytes"] == sample.size and value["sha256"] == sample.sha256


def validate_metrics(value: dict) -> None:
    """Reject nonfinite/zero/negative geometry rather than serializing a success."""
    count = value["solid_count"]
    if type(count) is not int or not 1 <= count <= MAX_SOLIDS:
        raise ValueError("Invalid or unbounded solid count")
    dimensions = value["dimensions_mm"]
    volumes = value["solid_volumes_mm3"]
    bounds = value["bounds_mm"]
    if len(dimensions) != 3 or len(volumes) != count or len(bounds) != 6:
        raise ValueError("Incomplete geometry metrics")
    positive = [*dimensions, *volumes, value["volume_mm3"]]
    if any(type(x) not in (int, float) or not math.isfinite(x) or x <= 0 for x in positive):
        raise ValueError("Nonfinite or nonpositive geometry metric")
    if any(type(x) not in (int, float) or not math.isfinite(x) for x in bounds):
        raise ValueError("Nonfinite bounds")
    if any(bounds[i + 3] <= bounds[i] for i in range(3)):
        raise ValueError("Nonpositive bounds extent")
    if any(not math.isclose(bounds[i + 3] - bounds[i], dimensions[i], rel_tol=1e-9, abs_tol=1e-9) for i in range(3)):
        raise ValueError("Bounds do not match dimensions")
    if not math.isclose(sum(volumes), value["volume_mm3"], rel_tol=1e-9, abs_tol=1e-9):
        raise ValueError("Inconsistent volume total")
    unit = value["system_length_unit_mm"]
    if value["brep_valid"] is not True or type(unit) not in (int, float) or unit != 1.0:
        raise ValueError("Invalid BRep or unconfirmed millimetre output")


def measure_with_ocp(sample: Sample) -> dict:
    path = SAMPLE_DIRECTORY / sample.filename
    # Reject invalid input even on direct worker entry, before loading native code.
    if any(check.status != "PASS" for check in check_sample(sample, path)):
        raise ValueError("Child input identity/unit mismatch")
    # Native messages can contain file details. They are never forwarded by the parent.
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.Message import Message
    from OCP.STEPControl import STEPControl_Reader
    from OCP.TopAbs import TopAbs_SOLID
    from OCP.TopExp import TopExp_Explorer

    Message.DefaultMessenger_s().ChangePrinters().Clear()
    reader = STEPControl_Reader()
    if reader.ReadFile(str(path)) != IFSelect_RetDone:
        raise ValueError("STEP read failed")
    roots = reader.TransferRoots()
    # OCCT initializes the output unit during transfer (0.0 before transfer).
    unit = reader.SystemLengthUnit()
    if unit != 1.0:
        raise ValueError("Unexpected kernel output length unit")
    if roots < 1 or reader.NbShapes() < 1:
        raise ValueError("No transferred roots/shapes")
    shape = reader.OneShape()
    if shape.IsNull():
        raise ValueError("Null imported shape")
    box = Bnd_Box()
    # Analytic geometry only: no mesh creation, triangulation, export, repair or scaling.
    BRepBndLib.AddOptimal_s(shape, box, False, False)
    if box.IsVoid() or box.IsOpen() or box.IsWhole():
        raise ValueError("Unbounded or void shape")
    bounds = list(box.Get())
    volumes = []
    explorer = TopExp_Explorer(shape, TopAbs_SOLID)
    while explorer.More():
        if len(volumes) >= MAX_SOLIDS:
            raise ValueError("Solid count exceeds research bound")
        props = GProp_GProps()
        # Only closed shells; skip shared faces; use exact surfaces, not triangulations.
        BRepGProp.VolumeProperties_s(explorer.Current(), props, True, True, False)
        volumes.append(props.Mass())
        explorer.Next()
    metrics = {
        "transferred_roots": roots,
        "transferred_shapes": reader.NbShapes(),
        "system_length_unit_mm": unit,
        "solid_count": len(volumes),
        "brep_valid": BRepCheck_Analyzer(shape).IsValid(),
        "bounds_mm": bounds,
        "dimensions_mm": [bounds[i + 3] - bounds[i] for i in range(3)],
        "solid_volumes_mm3": volumes,
        "volume_mm3": sum(volumes),
    }
    validate_metrics(metrics)
    return metrics


def bounded_worker(sample: Sample) -> dict:
    completed = subprocess.run(
        [sys.executable, "-B", str(Path(__file__).resolve()), "--worker", sample.label],
        capture_output=True,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )
    if completed.returncode != 0:
        raise ValueError("Kernel worker failed; native output withheld")
    # Only the last JSON line is consumed. Native diagnostics never enter reports/logs.
    result = json.loads(completed.stdout.splitlines()[-1])
    if result.get("status") != "MEASURED":
        raise ValueError("Kernel worker did not produce measurements")
    validate_metrics(result["metrics"])
    return result["metrics"]


def probe_sample(sample: Sample, path: Path, kernel_available: bool) -> dict:
    result = {"sample": sample.label, "status": "FAIL", "local_only": True}
    try:
        result["before"] = fingerprint(path)
        checks = check_sample(sample, path)
        result["input_checks"] = {check.name.rsplit(".", 1)[-1]: check.status for check in checks}
        if not matches_identity(sample, result["before"]) or any(check.status != "PASS" for check in checks):
            result["reason"] = "Input identity/unit mismatch; CAD import not executed"
        elif not kernel_available:
            result.update(status="NOT_EXECUTED", reason="OCP unavailable; no geometry was inferred from STEP text")
        else:
            result["metrics"] = bounded_worker(sample)
            result["status"] = "MEASURED"
    except subprocess.TimeoutExpired:
        result["reason"] = "CAD worker exceeded the 60-second bound; terminated and waited"
    except Exception as exc:
        # Exception messages/native diagnostics may contain model content or paths.
        result["reason"] = f"Local check/import failed ({type(exc).__name__}); details withheld"
    finally:
        try:
            result["after"] = fingerprint(path)
            result["identity_unchanged"] = result.get("before") == result["after"] and matches_identity(sample, result["after"])
        except OSError:
            result["identity_unchanged"] = False
        if not result["identity_unchanged"]:
            result.update(status="FAIL", reason="Source identity changed or could not be verified")
            result.pop("metrics", None)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", choices=("A", "B", "C"), help=argparse.SUPPRESS)
    args = parser.parse_args()
    samples = fixed_samples()
    if args.worker:
        try:
            sample = next(sample for sample in samples if sample.label == args.worker)
            output = {"status": "MEASURED", "metrics": measure_with_ocp(sample)}
            print(json.dumps(output, allow_nan=False))
            return 0
        except Exception:
            return 1
    available = importlib.util.find_spec("OCP") is not None
    packages = {dist.metadata["Name"]: dist.version for dist in importlib.metadata.distributions()}
    report = {
        "started_at_utc": datetime.now(UTC).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "packages": dict(sorted(packages.items())),
        "per_sample_timeout_seconds": TIMEOUT_SECONDS,
        "samples": [probe_sample(sample, SAMPLE_DIRECTORY / sample.filename, available) for sample in samples],
        "platform_geometry_dfm_quote": "NOT_ASSESSED",
    }
    report["finished_at_utc"] = datetime.now(UTC).isoformat()
    print(json.dumps(report, indent=2, allow_nan=False))
    # Missing dependency is a distinct non-success, never an apparent pass.
    if any(sample["status"] == "FAIL" for sample in report["samples"]):
        return 1
    return 2 if any(sample["status"] == "NOT_EXECUTED" for sample in report["samples"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
