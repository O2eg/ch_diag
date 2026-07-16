"""TOML/environment configuration with explicit, testable precedence."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping


CONFIG_FIELDS: dict[str, dict[str, str]] = {
    "connection": {
        "host": "host",
        "port": "port",
        "database": "database",
        "user": "user",
        "password_env": "password_env",
        "secure": "secure",
        "no_verify": "no_verify",
        "ca_certs": "ca_certs",
        "certfile": "certfile",
        "keyfile": "keyfile",
        "server_hostname": "server_hostname",
    },
    "collection": {
        "content": "content",
        "mode": "collection_mode",
        "target_scope": "target_scope",
        "cluster_name": "cluster_name",
        "item_ids": "item_ids",
        "tags": "tags",
    },
    "output": {
        "directory": "out_dir",
        "json": "json_out",
        "html": "html_out",
        "formats": "output_format",
        "strip_meta": "strip_meta",
        "log_file": "log_file",
    },
    "ssh": {
        "host": "ssh_host",
        "port": "ssh_port",
        "user": "ssh_user",
        "key": "ssh_key",
        "known_hosts": "ssh_known_hosts",
    },
    "snapshots": {"duration": "duration", "interval": "interval"},
}

ENV_FIELDS = {
    "CH_DIAG_HOST": "host",
    "CH_DIAG_PORT": "port",
    "CH_DIAG_DATABASE": "database",
    "CH_DIAG_USER": "user",
    "CH_DIAG_PASSWORD_ENV": "password_env",
    "CH_DIAG_SECURE": "secure",
    "CH_DIAG_NO_VERIFY": "no_verify",
    "CH_DIAG_CA_CERTS": "ca_certs",
    "CH_DIAG_CERTFILE": "certfile",
    "CH_DIAG_KEYFILE": "keyfile",
    "CH_DIAG_SERVER_HOSTNAME": "server_hostname",
    "CH_DIAG_CONTENT": "content",
    "CH_DIAG_COLLECTION_MODE": "collection_mode",
    "CH_DIAG_TARGET_SCOPE": "target_scope",
    "CH_DIAG_CLUSTER_NAME": "cluster_name",
    "CH_DIAG_ITEM_IDS": "item_ids",
    "CH_DIAG_TAGS": "tags",
    "CH_DIAG_OUT_DIR": "out_dir",
    "CH_DIAG_JSON_OUT": "json_out",
    "CH_DIAG_HTML_OUT": "html_out",
    "CH_DIAG_OUTPUT_FORMAT": "output_format",
    "CH_DIAG_STRIP_META": "strip_meta",
    "CH_DIAG_LOG_FILE": "log_file",
    "CH_DIAG_SSH_HOST": "ssh_host",
    "CH_DIAG_SSH_PORT": "ssh_port",
    "CH_DIAG_SSH_USER": "ssh_user",
    "CH_DIAG_SSH_KEY": "ssh_key",
    "CH_DIAG_SSH_KNOWN_HOSTS": "ssh_known_hosts",
    "CH_DIAG_DURATION": "duration",
    "CH_DIAG_INTERVAL": "interval",
}

BOOLEAN_FIELDS = {"secure", "no_verify", "strip_meta"}
INTEGER_FIELDS = {"port", "ssh_port"}
FLOAT_FIELDS = {"duration", "interval"}
LIST_FIELDS = {"item_ids", "tags", "output_format"}


def _toml_load(path: Path) -> dict[str, Any]:
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover - Python 3.10 only
        import tomli as tomllib  # type: ignore[no-redef]
    with path.open("rb") as stream:
        document = tomllib.load(stream)
    if not isinstance(document, dict):
        raise ValueError(f"configuration {path} must contain a TOML table")
    return document


def _boolean(value: Any, label: str) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().casefold()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{label} must be true or false")


def _coerce(destination: str, value: Any, label: str) -> Any:
    if destination in BOOLEAN_FIELDS:
        return _boolean(value, label)
    if destination in INTEGER_FIELDS:
        return int(value)
    if destination in FLOAT_FIELDS:
        return float(value)
    if destination in LIST_FIELDS:
        if isinstance(value, list):
            return [str(item) for item in value]
        return [str(value)]
    if value is None:
        return None
    return str(value)


def resolve_cli_defaults(
    config_path: str | None,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Return config+environment defaults; argparse then applies explicit CLI values."""

    defaults: dict[str, Any] = {}
    if config_path:
        path = Path(config_path).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"configuration file does not exist: {path}")
        document = _toml_load(path)
        unknown_sections = sorted(set(document) - set(CONFIG_FIELDS))
        if unknown_sections:
            raise ValueError(
                "unknown configuration section(s): " + ", ".join(unknown_sections)
            )
        for section, fields in CONFIG_FIELDS.items():
            values = document.get(section) or {}
            if not isinstance(values, dict):
                raise ValueError(f"configuration section [{section}] must be a table")
            unknown = sorted(set(values) - set(fields))
            if unknown:
                raise ValueError(
                    f"unknown key(s) in [{section}]: " + ", ".join(unknown)
                )
            for key, value in values.items():
                destination = fields[key]
                defaults[destination] = _coerce(
                    destination,
                    value,
                    f"configuration [{section}].{key}",
                )

    env = environment if environment is not None else os.environ
    for name, destination in ENV_FIELDS.items():
        if name in env:
            defaults[destination] = _coerce(
                destination,
                env[name],
                f"environment variable {name}",
            )
    if defaults.get("collection_mode") not in {
        None,
        "local",
        "remote",
        "remote-db-only",
    }:
        raise ValueError("collection mode must be local, remote, or remote-db-only")
    if defaults.get("target_scope") not in {None, "node", "cluster"}:
        raise ValueError("target scope must be node or cluster")
    for field in ("port", "ssh_port"):
        if field in defaults and not 1 <= int(defaults[field]) <= 65535:
            raise ValueError(f"{field.replace('_', ' ')} must be between 1 and 65535")
    return defaults
