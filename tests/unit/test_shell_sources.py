from __future__ import annotations

import subprocess

from ch_diag.content_loader import load_content


def test_all_declared_shell_sources_have_posix_syntax() -> None:
    content = load_content()
    files = {
        content.path / "scripts" / str(script["file"])
        for script in content.scripts.values()
    }
    files.update(
        content.path / "scripts" / str(script["library"])
        for script in content.scripts.values()
        if script.get("library")
    )
    files.update(
        content.path / "scripts" / str(value)
        for provider in content.sampler_providers.values()
        for key, value in (provider.get("config") or {}).items()
        if str(key).endswith(("_script", "_library"))
    )
    files.update((content.path / "scripts").glob("samplers/*.sh"))
    for path in sorted(files):
        result = subprocess.run(
            ["/bin/sh", "-n", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"{path}: {result.stderr}"
