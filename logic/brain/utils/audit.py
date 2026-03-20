"""Brain blueprint auditor.

Validates blueprint definitions for:
1. Required fields (name, version, tiers)
2. Path safety — simulates path resolution to detect dangerous relative paths
3. Backend registration — checks if declared backends exist in BACKEND_REGISTRY
4. File structure — verifies referenced files/directories would be created correctly
5. Inheritance — validates base.json linkage
"""
import json
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional

from logic.brain.loader import (
    BACKEND_REGISTRY,
    blueprints_dir,
    load_base,
    resolve_blueprint,
)

REQUIRED_FIELDS = ["name", "version", "tiers"]
REQUIRED_TIER_FIELDS = ["backend", "relative_path", "files"]
VALID_LIFECYCLES = {"session", "permanent"}
VALID_INJECT_AT = {"sessionStart", "on_demand", "postToolUse", "never"}

DANGEROUS_PATH_PATTERNS = [
    "..",
    "~",
    "/etc",
    "/usr",
    "/var",
    "/tmp",
    "/home",
]


class AuditResult:
    """Holds audit findings with severity levels."""

    def __init__(self, blueprint_name: str):
        self.blueprint_name = blueprint_name
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []

    def error(self, msg: str):
        self.errors.append(msg)

    def warning(self, msg: str):
        self.warnings.append(msg)

    def add_info(self, msg: str):
        self.info.append(msg)

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0

    def to_dict(self) -> Dict:
        return {
            "blueprint": self.blueprint_name,
            "passed": self.passed,
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
        }

    def summary(self) -> str:
        lines = [f"Audit: {self.blueprint_name}"]
        if self.passed:
            lines.append(f"  PASSED ({len(self.warnings)} warnings)")
        else:
            lines.append(f"  FAILED ({len(self.errors)} errors, {len(self.warnings)} warnings)")
        for e in self.errors:
            lines.append(f"  [ERROR] {e}")
        for w in self.warnings:
            lines.append(f"  [WARN]  {w}")
        for i in self.info:
            lines.append(f"  [INFO]  {i}")
        return "\n".join(lines)


def audit_blueprint(name: str) -> Dict:
    """Run a full audit on a blueprint definition. Returns dict with results."""
    result = AuditResult(name)

    bp_dir = resolve_blueprint(name)
    if bp_dir is None:
        result.error(f"Blueprint '{name}' not found in {blueprints_dir()}")
        return result.to_dict()

    bp_file = bp_dir / "blueprint.json"
    try:
        bp = json.loads(bp_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        result.error(f"Invalid JSON in blueprint.json: {e}")
        return result.to_dict()

    _check_required_fields(bp, result)
    _check_tiers(bp, result)
    _check_paths(bp, result)
    _check_backends(bp, result)
    _check_inheritance(bp, result)
    _check_documentation(bp_dir, result)
    _simulate_instance_creation(bp, result)

    return result.to_dict()


def audit_all() -> List[Dict]:
    """Audit all available blueprints."""
    results = []
    bp_dir = blueprints_dir()
    if not bp_dir.exists():
        return results
    for d in sorted(bp_dir.iterdir()):
        if d.is_dir() and not d.name.startswith("_") and (d / "blueprint.json").exists():
            results.append(audit_blueprint(d.name))
    return results


def _check_required_fields(bp: Dict, result: AuditResult):
    """Check that required top-level fields exist."""
    for field in REQUIRED_FIELDS:
        if field not in bp:
            result.error(f"Missing required field: '{field}'")
    if "description" not in bp:
        result.warning("Missing 'description' field (recommended)")


def _check_tiers(bp: Dict, result: AuditResult):
    """Validate tier definitions."""
    tiers = bp.get("tiers", {})
    if not tiers:
        result.error("No tiers defined")
        return

    for tier_name, tier_config in tiers.items():
        prefix = f"tiers.{tier_name}"
        if not isinstance(tier_config, dict):
            result.error(f"{prefix}: must be a dict")
            continue

        if "backend" not in tier_config:
            result.error(f"{prefix}: missing 'backend'")
        if "relative_path" not in tier_config and "path" not in tier_config:
            result.error(f"{prefix}: missing 'relative_path' or 'path'")

        lifecycle = tier_config.get("lifecycle")
        if lifecycle and lifecycle not in VALID_LIFECYCLES:
            result.warning(f"{prefix}: unknown lifecycle '{lifecycle}' (expected: {VALID_LIFECYCLES})")

        inject_at = tier_config.get("inject_at")
        if inject_at and inject_at not in VALID_INJECT_AT:
            result.warning(f"{prefix}: unknown inject_at '{inject_at}' (expected: {VALID_INJECT_AT})")


def _check_paths(bp: Dict, result: AuditResult):
    """Simulate path resolution to detect dangerous patterns."""
    tiers = bp.get("tiers", {})
    for tier_name, tier_config in tiers.items():
        path_val = tier_config.get("relative_path") or tier_config.get("path", "")
        if not path_val:
            continue

        posix = PurePosixPath(path_val)

        for dangerous in DANGEROUS_PATH_PATTERNS:
            if dangerous in str(posix):
                result.error(
                    f"tiers.{tier_name}.path contains dangerous pattern '{dangerous}': {path_val}"
                )

        if posix.is_absolute():
            result.error(f"tiers.{tier_name}.path is absolute: {path_val}. Must be relative.")

        parts = posix.parts
        if ".." in parts:
            result.error(
                f"tiers.{tier_name}.path escapes parent via '..': {path_val}. "
                "This could cause data to be written outside the brain instance!"
            )

        if "{session}" in path_val:
            simulated = path_val.replace("{session}", "test-instance")
            result.add_info(f"tiers.{tier_name}: path with session placeholder resolves to: {simulated}")


def _check_backends(bp: Dict, result: AuditResult):
    """Verify declared backends exist in the registry."""
    tiers = bp.get("tiers", {})
    for tier_name, tier_config in tiers.items():
        backend = tier_config.get("backend", "flatfile")
        if backend not in BACKEND_REGISTRY:
            deps = bp.get("dependencies", {})
            if deps:
                result.warning(
                    f"tiers.{tier_name}: backend '{backend}' not in BACKEND_REGISTRY "
                    f"(blueprint declares dependencies: {deps.get('pip', [])})"
                )
            else:
                result.error(
                    f"tiers.{tier_name}: backend '{backend}' not registered. "
                    f"Available: {list(BACKEND_REGISTRY.keys())}"
                )


def _check_inheritance(bp: Dict, result: AuditResult):
    """Check base.json inheritance is valid."""
    inherits = bp.get("inherits")
    if inherits == "base":
        base = load_base()
        if not base:
            result.error("Blueprint declares 'inherits: base' but base.json not found")
        else:
            result.add_info("Inherits from base.json (shared ecosystem rules)")
    elif inherits:
        result.warning(f"Unknown inheritance target: '{inherits}' (only 'base' is supported)")
    else:
        result.warning("No 'inherits' field — this blueprint won't receive shared ecosystem rules")


def _check_documentation(bp_dir: Path, result: AuditResult):
    """Check for recommended documentation files."""
    if not (bp_dir / "README.md").exists():
        result.warning("Missing README.md (recommended for blueprint documentation)")
    else:
        result.add_info("Has README.md")


def _simulate_instance_creation(bp: Dict, result: AuditResult):
    """White-box simulation: what happens when an instance is created from this blueprint.

    Simulates the directory structure that would be created and checks for conflicts,
    overlapping paths, or paths that escape the instance boundary.
    """
    tiers = bp.get("tiers", {})
    paths_created = {}

    for tier_name, tier_config in tiers.items():
        rel_path = tier_config.get("relative_path", "")
        if not rel_path:
            continue

        norm = PurePosixPath(rel_path)
        if str(norm) in paths_created:
            result.error(
                f"Path conflict: tiers.{tier_name} and tiers.{paths_created[str(norm)]} "
                f"both resolve to '{norm}'"
            )
        paths_created[str(norm)] = tier_name

        files = tier_config.get("files", {})
        for file_key, file_path in files.items():
            full = PurePosixPath(rel_path) / file_path
            if ".." in full.parts:
                result.error(
                    f"tiers.{tier_name}.files.{file_key} escapes tier boundary: {full}"
                )

    if not result.errors:
        result.add_info(
            f"Instance simulation passed: {len(paths_created)} tier directories, "
            f"no path conflicts or escapes"
        )
