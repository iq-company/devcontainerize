#!/usr/bin/env python3
"""
Dependency pinning for reproducible Docker image builds.

Manages version pins in pyproject.toml and the frappe version.
Auto-pinned lines are tagged with a marker comment so the tool can
distinguish them from manually managed constraints.

Marker format (appended to the dependency line):
    "package==1.2.3",  # auto-pin: ops deps

Frappe version is stored in [tool.ops.frappe]:
    [tool.ops.frappe]
    branch = "version-15"       # which branch to track (HEAD when free)
    version = "15.102.1"        # pinned version or commit SHA

The version field accepts either:
  - a semantic version (e.g. "15.102.1") → resolved to git tag v15.102.1
  - a commit SHA (e.g. "abc123...") → used directly as git ref
  - empty string → tracks branch HEAD

Build-script configuration lives in [tool.ops.overrides] sections.
Scripts read these values at build time via read_toml.py.
"""

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import click

PIN_MARKER = "# auto-pin: ops deps"

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _get_app_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _bench_root() -> Path:
    return _get_app_root().parent.parent


def _pyproject_path() -> Path:
    return _get_app_root() / "pyproject.toml"


def _get_app_name() -> str:
    return _get_app_root().name


# ---------------------------------------------------------------------------
# pip helpers (read-only — never installs)
# ---------------------------------------------------------------------------

def _find_bench_pip() -> str | None:
    """Locate the bench venv pip (where app dependencies live)."""
    bench_pip = _bench_root() / "env" / "bin" / "pip"
    return str(bench_pip) if bench_pip.exists() else None


def _find_pip() -> str:
    """Find usable pip binary.  Prefers bench venv, falls back to current env."""
    bench_pip = _find_bench_pip()
    if bench_pip:
        return bench_pip
    import shutil
    return shutil.which("pip") or sys.executable


def _installed_versions(pip: str) -> dict[str, str]:
    """Return {normalised_name: version} for all installed packages."""
    result = subprocess.run([pip, "list", "--format=json"], capture_output=True, text=True)
    if result.returncode != 0:
        return {}
    return {_norm(p["name"]): p["version"] for p in json.loads(result.stdout)}


def _query_latest_versions(pip: str, packages: list[str], pre: bool = False) -> dict[str, str]:
    """Query latest available versions via pip install --dry-run --report.

    Uses --dry-run so nothing is actually installed.  Returns
    {normalised_name: latest_version} for packages that would be upgraded.
    """
    if not packages:
        return {}

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        report_path = Path(f.name)

    cmd = [pip, "install", "--dry-run", "--upgrade", "--report", str(report_path)]
    if pre:
        cmd.append("--pre")
    cmd.extend(packages)

    result = subprocess.run(cmd, capture_output=True, text=True)
    versions: dict[str, str] = {}

    try:
        report = json.loads(report_path.read_text())
        for item in report.get("install", []):
            meta = item.get("metadata", {})
            name = meta.get("name", "")
            version = meta.get("version", "")
            if name and version:
                versions[_norm(name)] = version
    except (json.JSONDecodeError, FileNotFoundError):
        if result.returncode != 0:
            click.echo(f"⚠️  pip query failed: {result.stderr.strip()}", err=True)
    finally:
        report_path.unlink(missing_ok=True)

    return versions


def _norm(name: str) -> str:
    """PEP 503 normalisation."""
    return re.sub(r"[-_.]+", "-", name).lower()


# ---------------------------------------------------------------------------
# pyproject.toml line-level parsing
# ---------------------------------------------------------------------------

_DEP_RE = re.compile(
    r"""
    ^(?P<indent>\s*)                # leading whitespace
    (?P<q>["\'])                    # opening quote
    (?P<name>[\w][\w.-]*)           # package name
    (?P<extras>\[[^\]]+\])?         # optional extras [x,y]
    (?P<version>[><=!~][^"']*?)?    # optional version constraint
    (?P=q)                          # closing quote
    (?P<comma>\s*,?)                # optional trailing comma
    (?P<comment>\s*\#.*)?           # optional comment
    $
    """,
    re.VERBOSE,
)


def _parse_dep(line: str) -> dict | None:
    """Parse one dependency line.  Returns None for non-dep lines."""
    m = _DEP_RE.match(line.rstrip("\n\r"))
    if not m:
        return None
    return {
        "indent": m.group("indent"),
        "name": m.group("name"),
        "extras": m.group("extras") or "",
        "version": (m.group("version") or "").strip(),
        "comma": m.group("comma"),
        "comment": (m.group("comment") or "").strip(),
        "auto": PIN_MARKER in (m.group("comment") or ""),
        "has_ver": bool(m.group("version")),
    }


_KEEP = object()


def _rebuild(p: dict, version: str | object = _KEEP, auto: bool = False) -> str:
    """Rebuild a dependency line from parsed parts."""
    ver = p["version"] if version is _KEEP else version
    comment = ""
    if auto and ver:
        comment = f"  {PIN_MARKER}"
    elif p["comment"] and PIN_MARKER not in p["comment"]:
        comment = f"  {p['comment']}"
    return f'{p["indent"]}"{p["name"]}{p["extras"]}{ver}"{p["comma"]}{comment}\n'


def _find_deps_block(lines: list[str]) -> tuple[int, int]:
    """Return (start, end) line indices of dependencies = [...] block."""
    start = None
    for i, line in enumerate(lines):
        if start is None and re.match(r"^dependencies\s*=\s*\[", line):
            start = i
        if start is not None and "]" in line and i >= start:
            if i == start and "[" in line and "]" in line:
                return start, i
            if i > start:
                return start, i
    return -1, -1


def _collect_auto_pinned(lines: list[str], start: int, end: int) -> list[tuple[int, dict]]:
    """Return [(line_index, parsed)] for all auto-pinned deps."""
    result = []
    for i in range(start, end + 1):
        p = _parse_dep(lines[i])
        if p and p["auto"]:
            result.append((i, p))
    return result


# ---------------------------------------------------------------------------
# Frappe version helpers
# ---------------------------------------------------------------------------

def _frappe_installed_version() -> str | None:
    """Read __version__ from frappe's __init__.py (works without .git)."""
    init_py = _bench_root() / "apps" / "frappe" / "frappe" / "__init__.py"
    if not init_py.exists():
        return None
    content = init_py.read_text()
    m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
    return m.group(1) if m else None


def _read_ops_frappe(pyproject: Path) -> dict:
    """Read [tool.ops.frappe] from pyproject.toml via tomllib."""
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]
    with open(pyproject, "rb") as f:
        data = tomllib.load(f)
    return data.get("tool", {}).get("ops", {}).get("frappe", {})


def _write_frappe_field(pyproject: Path, field: str, value: str):
    """Update a field in [tool.ops.frappe] section (line-level edit)."""
    lines = pyproject.read_text().splitlines(keepends=True)
    in_section = False
    for i, line in enumerate(lines):
        if re.match(r"^\[tool\.ops\.frappe\]", line):
            in_section = True
            continue
        if in_section and line.startswith("["):
            break
        if in_section and line.strip().startswith(field):
            marker = f"  {PIN_MARKER}" if value else ""
            ref_hint = ""
            if value and field == "version":
                ref = _frappe_git_ref(value)
                ref_hint = f"  # git ref: {ref}" if value != ref else ""
            lines[i] = f'{field} = "{value}"{marker}{ref_hint}\n'
            pyproject.write_text("".join(lines))
            return True
    return False


def _is_commit_sha(value: str) -> bool:
    """Check if a string looks like a git commit SHA (7-40 hex chars)."""
    return bool(re.match(r"^[0-9a-f]{7,40}$", value))


def _frappe_git_ref(version: str) -> str:
    """Convert a version/commit value to its git ref representation.

    Returns empty string for empty input, the raw SHA for commit hashes,
    or "v{version}" for semantic version strings.
    """
    if not version:
        return ""
    if _is_commit_sha(version):
        return version
    return f"v{version}"


def _query_frappe_latest_version(branch: str) -> str | None:
    """Query the latest frappe version tag for a branch via git ls-remote.

    Extracts the major version from the branch name (e.g. "version-15" → 15)
    and finds the highest matching tag on GitHub.
    """
    FRAPPE_REPO = "https://github.com/frappe/frappe.git"

    m = re.match(r"version-(\d+)", branch)
    tag_pattern = f"v{m.group(1)}.*" if m else "v*"

    try:
        result = subprocess.run(
            ["git", "ls-remote", "--tags", FRAPPE_REPO, tag_pattern],
            capture_output=True, text=True, timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

    if result.returncode != 0:
        return None

    versions: list[tuple[tuple[int, ...], str]] = []
    for line in result.stdout.splitlines():
        if "^{}" in line:
            continue
        parts = line.split("\t")
        if len(parts) != 2:
            continue
        tag = parts[1].removeprefix("refs/tags/v")
        try:
            ver_tuple = tuple(int(x) for x in tag.split("."))
            versions.append((ver_tuple, tag))
        except ValueError:
            continue

    if not versions:
        return None

    versions.sort(key=lambda x: x[0], reverse=True)
    return versions[0][1]


def _install_hint() -> str:
    """Return the command the user should run to apply dependency changes."""
    app = _get_app_name()
    if (_bench_root() / "sites").exists():
        return "bench setup requirements --python"
    return f"pip install -e apps/{app}"


# ---------------------------------------------------------------------------
# Click commands
# ---------------------------------------------------------------------------

@click.group(invoke_without_command=True)
@click.pass_context
def deps(ctx):
    """Manage dependency version pins for reproducible builds.

    Pins are stored in pyproject.toml (marked with '# auto-pin: ops deps').
    Frappe version is in [tool.ops.frappe].
    Build-script config is in [tool.ops.overrides].
    """
    if ctx.invoked_subcommand is None:
        ctx.invoke(deps_status)


@deps.command("status")
def deps_status():
    """Show current dependency pin state."""
    pyproject = _pyproject_path()
    if not pyproject.exists():
        click.echo("❌ pyproject.toml not found")
        sys.exit(1)

    lines = pyproject.read_text().splitlines(keepends=True)
    start, end = _find_deps_block(lines)
    if start < 0:
        click.echo("❌ No dependencies block found in pyproject.toml")
        sys.exit(1)

    pip = _find_pip()
    versions = _installed_versions(pip)
    pip_label = "bench venv" if _find_bench_pip() else "current env"

    click.echo(f"📦 Dependencies (pyproject.toml)  —  pip source: {pip_label}\n")

    auto_count = 0
    manual_count = 0
    unpinned_count = 0

    for i in range(start, end + 1):
        stripped = lines[i].strip()
        if stripped.startswith("#") or not stripped:
            continue
        p = _parse_dep(lines[i])
        if not p:
            continue

        installed = versions.get(_norm(p["name"]), "?")

        if p["auto"]:
            status = click.style("auto-pin", fg="green")
            auto_count += 1
        elif p["has_ver"]:
            status = click.style("manual ", fg="blue")
            manual_count += 1
        else:
            status = click.style("unpinned", fg="yellow")
            unpinned_count += 1

        ver_display = p["version"] or "(none)"
        click.echo(f"   {status}  {p['name']:<35} {ver_display:<16} installed: {installed}")

    click.echo(f"\n   auto-pin: {auto_count}  |  manual: {manual_count}  |  unpinned: {unpinned_count}")

    # Frappe state from pyproject.toml [tool.ops.frappe]
    frappe_cfg = _read_ops_frappe(pyproject)
    branch = frappe_cfg.get("branch", "")
    pinned_ver = frappe_cfg.get("version", "")
    installed_ver = _frappe_installed_version()

    click.echo(f"\n🔧 Frappe ([tool.ops.frappe])")
    click.echo(f"   branch:    {branch or '(not set)'}")
    if pinned_ver:
        if _is_commit_sha(pinned_ver):
            click.echo(f"   commit:    {pinned_ver}")
        else:
            click.echo(f"   version:   {pinned_ver}  (tag: v{pinned_ver})")
    else:
        click.echo(f"   version:   (not set — tracks branch HEAD)")
    if installed_ver:
        if pinned_ver and not _is_commit_sha(pinned_ver):
            match = "✓" if pinned_ver == installed_ver else "✗ mismatch"
            click.echo(f"   installed: {installed_ver}  [{match}]")
        else:
            click.echo(f"   installed: {installed_ver}")

    if unpinned_count > 0:
        click.echo(f"\n💡 Run 'ops deps fix' to pin {unpinned_count} unpinned dependencies.")


@deps.command("fix")
def deps_fix():
    """Pin unpinned dependencies to their currently installed versions.

    Only affects dependencies WITHOUT a version specifier.
    Dependencies with manual constraints (>=, ~=, ==, etc.) are untouched.
    Also pins the installed frappe version in [tool.ops.frappe].
    """
    pyproject = _pyproject_path()
    lines = pyproject.read_text().splitlines(keepends=True)
    start, end = _find_deps_block(lines)

    if start < 0:
        click.echo("❌ No dependencies block found")
        sys.exit(1)

    pip = _find_pip()
    versions = _installed_versions(pip)

    if not versions:
        click.echo("❌ Could not read installed packages. Are you in the right environment?")
        click.echo("   Run inside the DevContainer or activate the bench venv first.")
        sys.exit(1)

    changed = 0
    for i in range(start, end + 1):
        p = _parse_dep(lines[i])
        if not p or p["has_ver"] or p["auto"]:
            continue

        installed = versions.get(_norm(p["name"]))
        if not installed:
            click.echo(f"   ⚠️  {p['name']}: not installed, skipping")
            continue

        lines[i] = _rebuild(p, version=f"=={installed}", auto=True)
        click.echo(f"   📌 {p['name']}=={installed}")
        changed += 1

    if changed:
        pyproject.write_text("".join(lines))
        click.echo(f"\n✅ Pinned {changed} dependencies in pyproject.toml")
    else:
        click.echo("   No unpinned dependencies found.")

    # Frappe version (from __init__.py — works without .git)
    frappe_ver = _frappe_installed_version()
    if frappe_ver:
        frappe_cfg = _read_ops_frappe(pyproject)
        old = frappe_cfg.get("version", "")
        if old != frappe_ver:
            _write_frappe_field(pyproject, "version", frappe_ver)
            click.echo(f"   📌 frappe: {frappe_ver} (tag: v{frappe_ver})")
        else:
            click.echo(f"   frappe already pinned: {frappe_ver}")


@deps.command("free")
def deps_free():
    """Remove all auto-pins (restore to unpinned state).

    Only affects lines marked with '# auto-pin: ops deps'.
    Manually set version constraints are untouched.
    Also clears the frappe version pin (restores branch HEAD tracking).
    """
    pyproject = _pyproject_path()
    lines = pyproject.read_text().splitlines(keepends=True)
    start, end = _find_deps_block(lines)

    if start < 0:
        click.echo("❌ No dependencies block found")
        sys.exit(1)

    changed = 0
    for i in range(start, end + 1):
        p = _parse_dep(lines[i])
        if not p or not p["auto"]:
            continue

        lines[i] = _rebuild(p, version="", auto=False)
        click.echo(f"   🔓 {p['name']} (was {p['version']})")
        changed += 1

    if changed:
        pyproject.write_text("".join(lines))
        click.echo(f"\n✅ Freed {changed} dependencies in pyproject.toml")
    else:
        click.echo("   No auto-pinned dependencies found.")

    # Clear frappe version pin
    frappe_cfg = _read_ops_frappe(pyproject)
    if frappe_cfg.get("version"):
        _write_frappe_field(pyproject, "version", "")
        click.echo("   🔓 frappe version cleared (tracks branch HEAD)")


def _do_update(pre: bool = False):
    """Shared logic for update-stable and update-experimental.

    Queries available versions via pip --dry-run (never installs anything),
    updates pins in pyproject.toml, and prints the command for the user
    to run after reviewing the changes.

    Also queries the latest frappe version tag for the configured branch
    via git ls-remote and updates [tool.ops.frappe] version accordingly.
    """
    pyproject = _pyproject_path()
    lines = pyproject.read_text().splitlines(keepends=True)
    start, end = _find_deps_block(lines)

    if start < 0:
        click.echo("❌ No dependencies block found")
        sys.exit(1)

    any_changes = False

    # --- pip dependencies ---
    auto_pinned = _collect_auto_pinned(lines, start, end)
    if auto_pinned:
        packages = [p["name"] for _, p in auto_pinned]
        pip = _find_pip()
        label = "experimental (incl. pre-release)" if pre else "stable"
        click.echo(f"🔍 Querying latest {label} versions for {len(packages)} packages...\n")

        available = _query_latest_versions(pip, packages, pre=pre)

        pip_updated = 0
        for i, p in auto_pinned:
            current_ver = p["version"]
            latest = available.get(_norm(p["name"]))

            if not latest:
                click.echo(f"   ✓  {p['name']}{current_ver} (up to date)")
                continue

            new_ver = f"=={latest}"
            if new_ver != current_ver:
                lines[i] = _rebuild(p, version=new_ver, auto=True)
                click.echo(f"   ⬆️  {p['name']}: {current_ver} → =={latest}")
                pip_updated += 1
            else:
                click.echo(f"   ✓  {p['name']}{current_ver} (up to date)")

        if pip_updated:
            pyproject.write_text("".join(lines))
            click.echo(f"\n✅ Updated {pip_updated} pip version pins")
            any_changes = True
        else:
            click.echo("\n   All pip dependencies already at latest versions.")
    else:
        click.echo("   No auto-pinned pip dependencies found.")
        click.echo("   Run 'ops deps fix' first to create auto-pins.\n")

    # --- frappe version ---
    frappe_cfg = _read_ops_frappe(pyproject)
    branch = frappe_cfg.get("branch", "")
    current_frappe = frappe_cfg.get("version", "")

    if branch:
        click.echo(f"\n🔍 Querying latest frappe version for branch '{branch}'...")
        latest_frappe = _query_frappe_latest_version(branch)

        if latest_frappe is None:
            click.echo("   ⚠️  Could not query frappe tags (no network or git not found)")
        elif not current_frappe:
            _write_frappe_field(pyproject, "version", latest_frappe)
            click.echo(f"   📌 frappe: (none) → {latest_frappe}  (tag: v{latest_frappe})")
            any_changes = True
        elif _is_commit_sha(current_frappe):
            click.echo(f"   ⏭️  frappe pinned to commit {current_frappe}, skipping tag update")
        elif current_frappe != latest_frappe:
            _write_frappe_field(pyproject, "version", latest_frappe)
            click.echo(f"   ⬆️  frappe: {current_frappe} → {latest_frappe}  (tag: v{latest_frappe})")
            any_changes = True
        else:
            click.echo(f"   ✓  frappe {current_frappe} (up to date)")

    if any_changes:
        click.echo(f"\n📋 Review the changes, then apply:")
        click.echo(f"   {_install_hint()}")
    else:
        click.echo("\n   Everything already at latest versions.")


@deps.command("update-stable")
def deps_update_stable():
    """Update auto-pinned dependencies to latest stable versions.

    Queries available versions via pip (dry-run, nothing is installed),
    updates the version pins in pyproject.toml, and prints the command
    for you to run after reviewing the changes.
    """
    _do_update(pre=False)


@deps.command("update-experimental")
def deps_update_experimental():
    """Update auto-pinned deps to latest versions (including pre-release).

    Same as update-stable but considers pre-release versions.
    """
    _do_update(pre=True)
