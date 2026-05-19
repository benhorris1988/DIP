"""Shared test fixtures.

The big one is :func:`surreal_store` — it spawns an ephemeral
``surreal`` server on a free port for the test session, connects a
:class:`SurrealStore` to it, and tears it down at the end. Tests that
don't have the ``surreal`` binary available are skipped automatically
so unit tests still run cleanly in environments without it.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import socket
import subprocess
import time
from collections.abc import AsyncIterator, Iterator

import pytest

from app.db import surreal as surreal_module
from app.db.surreal import SurrealStore


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_port(host: str, port: int, timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.25)
            try:
                s.connect((host, port))
                return True
            except OSError:
                time.sleep(0.1)
    return False


@pytest.fixture(scope="session")
def surreal_server() -> Iterator[dict]:
    """Start a ``surreal start --user root --pass root memory`` process.

    Skips the test if the binary isn't on PATH (e.g. CI containers that
    haven't installed SurrealDB).
    """
    binary = shutil.which("surreal")
    if binary is None:
        pytest.skip("surreal binary not available")

    port = _free_port()
    bind = f"127.0.0.1:{port}"
    proc = subprocess.Popen(
        [
            binary,
            "start",
            "--user",
            "root",
            "--pass",
            "root",
            "--bind",
            bind,
            "memory",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={**os.environ, "SURREAL_LOG": "error"},
    )
    try:
        if not _wait_for_port("127.0.0.1", port, timeout=15.0):
            proc.terminate()
            pytest.skip("surreal server did not start in time")
        yield {"url": f"ws://127.0.0.1:{port}/rpc", "user": "root", "pass": "root"}
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture
async def surreal_store(surreal_server: dict) -> AsyncIterator[SurrealStore]:
    """One isolated namespace+database per test."""
    test_id = f"test_{int(time.time() * 1000)}_{os.getpid()}"
    store = SurrealStore(
        url=surreal_server["url"],
        user=surreal_server["user"],
        password=surreal_server["pass"],
        namespace=test_id,
        database=test_id,
    )
    surreal_module.configure(store)
    try:
        await store.connect()
        yield store
    finally:
        await store.disconnect()
        surreal_module.configure(None)


