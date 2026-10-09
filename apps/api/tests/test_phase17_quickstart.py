from __future__ import annotations

import subprocess

from scripts import smoke_compose


def test_smoke_compose_uses_selected_environment_for_compose(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0, stdout="ok")

    monkeypatch.setattr(smoke_compose.shutil, "which", lambda _: "docker")
    monkeypatch.setattr(smoke_compose.subprocess, "run", fake_run)

    assert smoke_compose._compose("ps", env_file="deploy/.env.demo") == "ok"
    assert captured["command"] == ["docker", "compose", "--env-file", "deploy/.env.demo", "ps"]
    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    environment = kwargs["env"]
    assert isinstance(environment, dict)
    assert environment["RENZAI_ENV_FILE"] == "deploy/.env.demo"
