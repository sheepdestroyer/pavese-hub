"""Contract tests for deploy/: the production Quadlet and its install script.

The Quadlet is the source of truth for the prod unit (E10). These tests pin the invariants that must
survive edits (loopback publish, SELinux labels, log-priority splitter, pasta port range) and
exercise deploy/install.sh against a temporary destination with a fake `systemctl`.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

DEPLOY = Path(__file__).resolve().parents[1] / "deploy"
QUADLET = DEPLOY / "pavese-hub.container"
INSTALL = DEPLOY / "install.sh"
QUADLET_GENERATOR = Path("/usr/libexec/podman/quadlet")
SYSCTL_LINE = 'Sysctl="net.ipv4.ip_local_port_range=62000 65000"'


def _lines() -> list[str]:
    return [line.strip() for line in QUADLET.read_text(encoding="utf-8").splitlines()]


def test_quadlet_sets_pasta_ephemeral_port_range():
    assert SYSCTL_LINE in _lines()


def test_quadlet_keeps_deployment_invariants():
    lines = _lines()
    assert "PublishPort=127.0.0.1:5003:5003" in lines  # E4: loopback only
    assert "Network=pasta:-a,10.0.2.1/24" in lines
    forbidden = ("Network=host", "SecurityLabelDisable", "PodmanArgs=--security-opt")
    assert not any(line.startswith(forbidden) for line in lines)
    # SEL3: private data :Z, shared auth dir and CA bundle :z
    assert "Volume=/mnt/DATA/boy/prod/pavese-hub/data:/app/data:Z" in lines
    assert "Volume=/mnt/DATA/boy/prod/auth:/app/auth:z" in lines
    assert "Volume=/mnt/DATA/boy/prod/haproxy/certs/ca-bundle.crt:/etc/ssl/certs/ca-bundle.crt:ro,z" in lines
    # LOG5: shared splitter, lowercase :ro,z, used as entrypoint
    assert (
        "Volume=/mnt/DATA/boy/prod/infra/bin/log-priority-splitter.sh:/usr/local/bin/log-priority-splitter.sh:ro,z"
        in lines
    )
    assert "Entrypoint=/usr/local/bin/log-priority-splitter.sh" in lines


def test_quadlet_contains_no_secret_values():
    text = QUADLET.read_text(encoding="utf-8").lower()
    for word in ("password", "secret=", "token", "api_key", "apikey"):
        assert word not in text


@pytest.mark.skipif(not QUADLET_GENERATOR.exists(), reason="podman quadlet generator not installed")
def test_quadlet_generator_accepts_unit_and_emits_one_sysctl():
    env = {**os.environ, "QUADLET_UNIT_DIRS": str(DEPLOY)}
    proc = subprocess.run(
        [str(QUADLET_GENERATOR), "-dryrun", "-user"], capture_output=True, text=True, env=env, timeout=60, check=False
    )
    assert proc.returncode == 0, proc.stderr
    assert "warning" not in proc.stderr.lower()
    assert '--sysctl "net.ipv4.ip_local_port_range=62000\\x2065000"' in proc.stdout


@pytest.fixture
def env(tmp_path: Path) -> dict[str, str]:
    """Environment with a fake `systemctl` and `timeout` shim logging every call."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "calls.log"
    fake = bin_dir / "systemctl"
    fake.write_text(f'#!/bin/sh\necho "systemctl $*" >> "{log}"\n')
    fake.chmod(0o755)
    return {
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "HOME": str(tmp_path / "home"),
        "QUADLET_DEST_DIR": str(tmp_path / "dest"),
    }


def _install(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(INSTALL), *args], capture_output=True, text=True, env=env, timeout=60, check=False
    )


def _calls(env: dict[str, str]) -> list[str]:
    log = Path(env["QUADLET_DEST_DIR"]).parent / "calls.log"
    return log.read_text().splitlines() if log.exists() else []


def test_install_fresh_copies_unit_and_reloads(env):
    proc = _install(env)
    assert proc.returncode == 0, proc.stderr
    dest = Path(env["QUADLET_DEST_DIR"])
    assert (dest / "pavese-hub.container").read_bytes() == QUADLET.read_bytes()
    assert list(dest.glob("*.bak-*")) == []
    assert _calls(env) == ["systemctl --user daemon-reload"]
    assert "1 unit(s) changed" in proc.stdout


def test_install_is_idempotent(env):
    assert _install(env).returncode == 0
    Path(env["QUADLET_DEST_DIR"]).parent.joinpath("calls.log").unlink()
    proc = _install(env, "--restart")
    assert proc.returncode == 0, proc.stderr
    assert "unchanged" in proc.stdout
    assert list(Path(env["QUADLET_DEST_DIR"]).glob("*.bak-*")) == []
    # nothing changed: no daemon-reload, but an explicit restart is still honoured
    assert _calls(env) == ["systemctl --user restart pavese-hub.service"]


def test_install_backs_up_a_differing_unit(env):
    dest = Path(env["QUADLET_DEST_DIR"])
    dest.mkdir(parents=True)
    (dest / "pavese-hub.container").write_text("[Container]\nold=1\n")
    proc = _install(env, "--restart")
    assert proc.returncode == 0, proc.stderr
    backups = list(dest.glob("pavese-hub.container.bak-*"))
    assert len(backups) == 1
    assert backups[0].read_text() == "[Container]\nold=1\n"
    assert (dest / "pavese-hub.container").read_bytes() == QUADLET.read_bytes()
    assert _calls(env) == [
        "systemctl --user daemon-reload",
        "systemctl --user restart pavese-hub.service",
    ]


def test_install_dry_run_changes_nothing(env):
    dest = Path(env["QUADLET_DEST_DIR"])
    proc = _install(env, "--dry-run", "--restart")
    assert proc.returncode == 0, proc.stderr
    assert "[dry-run]" in proc.stdout
    assert not dest.exists()
    assert _calls(env) == []


def test_install_no_reload_skips_daemon_reload(env):
    assert _install(env, "--no-reload").returncode == 0
    assert _calls(env) == []


def test_install_dest_option(env, tmp_path):
    other = tmp_path / "other"
    proc = _install(env, "--dest", str(other), "--no-reload")
    assert proc.returncode == 0, proc.stderr
    assert (other / "pavese-hub.container").is_file()


def test_install_dest_requires_value(env):
    proc = _install(env, "--dest")
    assert proc.returncode == 2
    assert "--dest needs a directory" in proc.stderr


def test_install_rejects_unknown_option(env):
    proc = _install(env, "--bogus")
    assert proc.returncode == 2
    assert "unknown option" in proc.stderr


def test_install_help(env):
    proc = _install(env, "--help")
    assert proc.returncode == 0
    assert "--dry-run" in proc.stdout


def test_install_fails_when_unit_missing(env, tmp_path):
    copy = tmp_path / "copy"
    copy.mkdir()
    shutil.copy(INSTALL, copy / "install.sh")
    proc = subprocess.run(
        ["bash", str(copy / "install.sh")], capture_output=True, text=True, env=env, timeout=60, check=False
    )
    assert proc.returncode == 1
    assert "missing" in proc.stderr
