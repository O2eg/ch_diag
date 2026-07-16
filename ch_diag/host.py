"""Local and SSH host command execution contracts."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import socket
from typing import Protocol


@dataclass(frozen=True)
class CommandResult:
    stdout: str
    stderr: str
    returncode: int


class HostRunner(Protocol):
    async def run_script(self, script: str, *, timeout: float) -> CommandResult: ...

    async def hostname(self) -> str: ...


class LocalHostRunner:
    async def hostname(self) -> str:
        return socket.gethostname()

    async def run_script(self, script: str, *, timeout: float) -> CommandResult:
        process = await asyncio.create_subprocess_exec(
            "/bin/sh",
            "-s",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(script.encode("utf-8")),
                timeout=timeout,
            )
        except asyncio.TimeoutError as exc:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            await process.communicate()
            raise TimeoutError(f"host script timed out after {timeout:g}s") from exc
        return CommandResult(
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
            returncode=int(process.returncode or 0),
        )
