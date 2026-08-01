from __future__ import annotations

import subprocess

import pytest

from ch_diag.collector import _parse_table_json_output
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


def test_clickhouse_thread_sampler_never_reads_every_thread_io_file() -> None:
    content = load_content()
    script = (
        content.path / "scripts" / "samplers" / "clickhouse_process.sh"
    ).read_text(encoding="utf-8")

    assert 'task/[0-9]*/io' not in script
    assert "CH_DIAG_PROCESS_DISCOVERED_THREADS" in script
    assert 'ch_diag_thread_mode=${1:-discover}' in script


def test_lshw_0218_filtered_json_is_repaired_only_for_lshw_sources() -> None:
    malformed = """
    [
      {
        "id" : "host",
        "class" : "system",
        "capabilities" : {
          "smp" : "Symmetric Multi-Processing"
        }  {
        "id" : "pnp00:00",
        "class" : "system"
      },
    ]
    """
    assert [row["id"] for row in _parse_table_json_output(malformed, repair_legacy_lshw=True)] == [
        "host",
        "pnp00:00",
    ]
    with pytest.raises(ValueError, match="invalid table_json output"):
        _parse_table_json_output(malformed, repair_legacy_lshw=False)


def test_lshw_0218_empty_and_unterminated_outputs_are_repaired_narrowly() -> None:
    assert _parse_table_json_output("]", repair_legacy_lshw=True) == []
    assert _parse_table_json_output(
        '[{"id":"host","class":"system","capabilities":{"smp":true}]',
        repair_legacy_lshw=True,
    ) == [{"id": "host", "class": "system", "capabilities": {"smp": True}}]
    with pytest.raises(ValueError, match="invalid table_json output"):
        _parse_table_json_output('{"broken": }', repair_legacy_lshw=True)
