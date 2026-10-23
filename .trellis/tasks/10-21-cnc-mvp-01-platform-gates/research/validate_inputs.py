"""Read-only checks of fixed CNC research inputs; never establishes live readiness."""

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PARENT_RESEARCH = REPO_ROOT / ".trellis/tasks/10-21-cnc-pricing-mvp/research"
CONFIG_DIRECTORY = PARENT_RESEARCH / "platform-configs"
SAMPLE_DIRECTORY = Path("E:/AIWorkspace/3d_models")
SAMPLE_FILES = {"A": "D14-TO-CS-ADAPTER_LP0335_P2002B.STEP", "B": "292.1301C (M12-TO-CS-ADAPTER).STEP"}
PROVIDERS = {"xometry_us": "xometry", "jlc_cnc_cn": "jlc", "rapiddirect": "rapiddirect"}
FORBIDDEN_ACTIONS = {"purchase", "checkout", "place_order", "payment", "change_account_security"}
LENGTH_UNIT = rb"LENGTH_UNIT\s*\(\s*\)\s*NAMED_UNIT\s*\(\s*\*\s*\)\s*SI_UNIT\s*\(\s*([^,)]+)\s*,\s*([^,)]+)\s*\)"


@dataclass(frozen=True)
class Sample:
    label: str
    filename: str
    size: int
    sha256: str


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def checked(name: str, passed: bool, detail: str) -> Check:
    return Check(name, "PASS" if passed else "FAIL", detail)


def recorded_samples(record: str) -> list[Sample]:
    """Read only the two known rows and hashes from the existing sample record."""
    rows = [tuple(cell.strip() for cell in line.split("|")[1:-1]) for line in record.splitlines() if line.startswith("|")]
    samples = []
    for label, filename in SAMPLE_FILES.items():
        identities = [row for row in rows if len(row) == 6 and row[1] == f"`{filename}`"]
        hashes = [row for row in rows if len(row) == 2 and row[0] == label]
        if len(identities) != 1 or len(hashes) != 1:
            raise ValueError("Missing or ambiguous recorded sample identity")
        size = identities[0][2].split("/", 1)[0].strip()
        digest = hashes[0][1].strip("`")
        if not size.isdecimal() or identities[0][4] != "mm" or not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValueError("Invalid recorded size, SHA-256 or millimetre declaration")
        samples.append(Sample(label, filename, int(size), digest))
    return samples


def check_sample(sample: Sample, path: Path) -> list[Check]:
    try:
        content = path.read_bytes()
    except OSError:
        return [Check(f"sample.{sample.label}.read", "FAIL", "Known source sample could not be read")]
    units = [tuple(value.strip().upper() for value in unit) for unit in re.findall(LENGTH_UNIT, content, re.IGNORECASE)]
    declared_count = len(re.findall(rb"\bLENGTH_UNIT\s*\(\s*\)", content, re.IGNORECASE))
    return [
        checked(f"sample.{sample.label}.size", len(content) == sample.size, f"Matches recorded {sample.size} bytes"),
        checked(f"sample.{sample.label}.sha256", hashlib.sha256(content).hexdigest() == sample.sha256, "Matches recorded SHA-256"),
        checked(
            f"sample.{sample.label}.unit",
            bool(units) and len(units) == declared_count and all(unit == (b".MILLI.", b".METRE.") for unit in units),
            "All detected length declarations are millimetres; CAD geometry/DFM not assessed",
        ),
    ]


def check_config(platform: str, config: dict, schema_version: str | None) -> list[Check]:
    policy = config.get("policy")
    policy = policy if isinstance(policy, dict) else {}
    forbidden = policy.get("forbidden_actions")
    config_version = config.get("config_version")
    quote = config.get("quote_extraction")
    quote = quote if isinstance(quote, dict) else {}
    return [
        checked(
            f"{platform}.identity",
            config.get("platform_code") == platform and config.get("provider_group") == PROVIDERS[platform],
            "Platform code and independent provider group match the fixed registry",
        ),
        checked(f"{platform}.schema_version", schema_version is not None and config.get("schema_version") == schema_version, "Matches the current local Schema version"),
        checked(f"{platform}.config_version", isinstance(config_version, str) and bool(config_version.strip()), "Configuration version is nonempty"),
        checked(f"{platform}.draft", config.get("lifecycle") == "draft" and config.get("automation_enabled") is False, "Research configuration remains draft with automation disabled"),
        checked(
            f"{platform}.forbidden_actions",
            isinstance(forbidden, list) and all(action in forbidden for action in FORBIDDEN_ACTIONS),
            "Purchase, checkout, final order, payment and account-security changes are forbidden",
        ),
        checked(
            f"{platform}.parameter_policy",
            policy.get("unknown_option") == "reject" and policy.get("missing_required") == "stop_and_report" and policy.get("silent_substitution") is False,
            "Unknown/missing parameters stop execution; silent substitution is disabled",
        ),
        checked(f"{platform}.quote_source", quote.get("raw_material_price_is_quote") is False, "Material catalog prices cannot establish a part quote"),
        Check(f"{platform}.live_readiness", "NOT_ASSESSED", "Static checks do not verify account, geometry, effective parameters, price, currency or lead time"),
    ]


def check_schema(schema: dict, configs: dict[str, dict]) -> list[Check]:
    try:
        from jsonschema import Draft202012Validator
        from jsonschema.exceptions import SchemaError
    except ModuleNotFoundError as exc:
        status = "NOT_EXECUTED" if exc.name == "jsonschema" else "FAIL"
        return [Check("json_schema", status, "Existing jsonschema is unavailable; no dependencies were installed")]
    except ImportError:
        return [Check("json_schema", "FAIL", "Installed jsonschema does not provide the required validator")]
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError:
        return [Check("json_schema", "FAIL", "The local Draft 2020-12 Schema is invalid")]
    validator = Draft202012Validator(schema)
    checks = []
    for platform, config in configs.items():
        errors = sum(1 for _ in validator.iter_errors(config))
        # Do not print validator messages: they can include entire input values.
        checks.append(checked(f"{platform}.json_schema", errors == 0, f"Draft202012Validator structural errors: {errors}"))
    return checks


def run_checks() -> list[Check]:
    checks = []
    try:
        samples = recorded_samples((PARENT_RESEARCH / "step-samples-2026-10-21.md").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        checks.append(Check("sample.record", "FAIL", "Known A/B identity record could not be read or parsed"))
    else:
        for sample in samples:
            checks.extend(check_sample(sample, SAMPLE_DIRECTORY / sample.filename))

    schema = None
    version = None
    try:
        schema = json.loads((CONFIG_DIRECTORY / "platform.schema.json").read_text(encoding="utf-8"))
        version = schema["properties"]["schema_version"]["const"]
        if not isinstance(version, str) or not version.strip():
            raise ValueError("Missing current Schema version")
    except (OSError, UnicodeError, ValueError, KeyError, TypeError):
        checks.append(Check("schema.read", "FAIL", "Current local Schema or its version could not be read"))
        schema = None

    configs = {}
    for platform in PROVIDERS:
        try:
            config = json.loads((CONFIG_DIRECTORY / f"{platform}.json").read_text(encoding="utf-8"))
            if not isinstance(config, dict):
                raise ValueError("Expected a JSON object")
        except (OSError, UnicodeError, ValueError):
            checks.append(Check(f"{platform}.read", "FAIL", "Fixed platform configuration could not be read as a JSON object"))
        else:
            configs[platform] = config
            checks.extend(check_config(platform, config, version))
    if schema is not None:
        checks.extend(check_schema(schema, configs))
    else:
        checks.append(Check("json_schema", "NOT_EXECUTED", "Local Schema could not be loaded"))
    return checks


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    checks = run_checks()
    for check in checks:
        print(f"{check.status} {check.name}: {check.detail}")
    failed = any(check.status == "FAIL" for check in checks)
    print(f"Input checks: {'FAIL' if failed else 'PASS'}; NOT_EXECUTED checks remain unverified; live readiness: NOT_ASSESSED.")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
