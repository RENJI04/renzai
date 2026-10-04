"""Cross-platform Phase 14 test entry points suitable for local use and later CI wiring."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
REPORTS = ROOT / ".reports"


def run(*command: str, cwd: Path = ROOT) -> None:
    print(f"[{cwd.relative_to(ROOT) if cwd != ROOT else '.'}] {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, check=True)  # noqa: S603 - fixed repository commands only


def python(*arguments: str, cwd: Path = ROOT) -> None:
    run(sys.executable, *arguments, cwd=cwd)


def pnpm(*arguments: str, cwd: Path = ROOT) -> None:
    executable = shutil.which("pnpm")
    if executable is None:
        raise RuntimeError("pnpm is required for frontend and TypeScript SDK checks")
    run(executable, *arguments, cwd=cwd)


def backend_fast() -> None:
    python("-m", "pytest", "-m", "not integration and not e2e and not slow")


def backend_full() -> None:
    python("-m", "ruff", "check", ".")
    python("-m", "ruff", "format", "--check", ".")
    python("-m", "mypy")
    python("-m", "pytest")


def backend_coverage() -> None:
    REPORTS.mkdir(exist_ok=True)
    python(
        "-m",
        "pytest",
        "--cov=renzai",
        "--cov=renzai_worker",
        "--cov-branch",
        "--cov-report=term-missing",
        f"--cov-report=xml:{REPORTS / 'backend-coverage.xml'}",
        f"--cov-report=json:{REPORTS / 'backend-coverage.json'}",
        f"--junitxml={REPORTS / 'backend-junit.xml'}",
    )


def frontend() -> None:
    for command in ("format:check", "lint", "typecheck", "test", "build"):
        pnpm("--dir", "apps/web", command)


def frontend_coverage() -> None:
    pnpm("--dir", "apps/web", "test:coverage")


def python_sdk() -> None:
    package = ROOT / "packages/python-sdk"
    python("-m", "ruff", "check", ".", cwd=package)
    python("-m", "ruff", "format", "--check", ".", cwd=package)
    python("-m", "mypy", cwd=package)
    python("-m", "pytest", cwd=package)
    REPORTS.mkdir(exist_ok=True)
    python("-m", "build", ".", "--outdir", str(REPORTS / "python-sdk-dist"), cwd=package)


def python_sdk_coverage() -> None:
    package = ROOT / "packages/python-sdk"
    REPORTS.mkdir(exist_ok=True)
    python(
        "-m",
        "pytest",
        "--cov=renzai_sdk",
        "--cov-branch",
        "--cov-report=term-missing",
        f"--cov-report=xml:{REPORTS / 'python-sdk-coverage.xml'}",
        f"--cov-report=json:{REPORTS / 'python-sdk-coverage.json'}",
        cwd=package,
    )


def typescript_sdk() -> None:
    for command in ("format:check", "lint", "typecheck", "test", "build"):
        pnpm("--dir", "packages/typescript-sdk", command)


def typescript_sdk_coverage() -> None:
    pnpm("--dir", "packages/typescript-sdk", "test:coverage")


def e2e() -> None:
    python("-m", "pytest", "-m", "e2e")


def postgresql() -> None:
    if not os.environ.get("RENZAI_TEST_DATABASE_URL"):
        raise RuntimeError("RENZAI_TEST_DATABASE_URL must name a disposable PostgreSQL database")
    python("-m", "pytest", "-m", "postgresql")


def redis() -> None:
    if not os.environ.get("RENZAI_TEST_REDIS_URL"):
        raise RuntimeError("RENZAI_TEST_REDIS_URL must name a disposable Redis database")
    python("-m", "pytest", "-m", "redis")


def compatibility() -> None:
    pnpm("--dir", "packages/typescript-sdk", "build")
    python("scripts/verify_phase12_compatibility.py")


def frontend_backend() -> None:
    python("scripts/verify_phase14_frontend_backend.py")


PROFILES = {
    "fast": (backend_fast,),
    "backend": (backend_full,),
    "backend-coverage": (backend_coverage,),
    "frontend": (frontend,),
    "frontend-coverage": (frontend_coverage,),
    "python-sdk": (python_sdk,),
    "python-sdk-coverage": (python_sdk_coverage,),
    "typescript-sdk": (typescript_sdk,),
    "typescript-sdk-coverage": (typescript_sdk_coverage,),
    "e2e": (e2e,),
    "postgresql": (postgresql,),
    "redis": (redis,),
    "compatibility": (compatibility,),
    "frontend-backend": (frontend_backend,),
    "coverage": (backend_coverage, frontend_coverage, python_sdk_coverage, typescript_sdk_coverage),
    "release": (
        backend_full,
        frontend,
        python_sdk,
        typescript_sdk,
        e2e,
        postgresql,
        redis,
        frontend_backend,
        compatibility,
    ),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", choices=sorted(PROFILES))
    args = parser.parse_args()
    for operation in PROFILES[args.profile]:
        operation()


if __name__ == "__main__":
    main()
