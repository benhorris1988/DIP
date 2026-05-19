"""Asset graph operations: topological layering, upstream / downstream
traversal, and "which pipelines must run" planning."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from app.repositories import AssetRepository


@dataclass
class AssetNode:
    key: str
    pipeline_id: str
    depends_on: list[str]


async def _all_assets(repo: AssetRepository) -> list[AssetNode]:
    rows = await repo.list()
    return [
        AssetNode(
            key=a.key,
            pipeline_id=a.pipeline_id,
            depends_on=list(a.depends_on or []),
        )
        for a in rows
    ]


async def layer_assets(repo: AssetRepository) -> list[list[str]]:
    """Topologically sort assets into layers (Kahn's algorithm).

    Layer 0 = no dependencies. Cycles (which the loader should reject)
    surface in a trailing layer marked with ``? `` prefix.
    """
    nodes = await _all_assets(repo)
    keys = {n.key for n in nodes}
    in_degree: dict[str, int] = {n.key: 0 for n in nodes}
    children: dict[str, list[str]] = defaultdict(list)
    for n in nodes:
        for dep in n.depends_on:
            if dep in keys:
                in_degree[n.key] += 1
                children[dep].append(n.key)

    layers: list[list[str]] = []
    current = sorted([k for k, d in in_degree.items() if d == 0])
    done: set[str] = set()
    while current:
        layers.append(current)
        done.update(current)
        next_layer: list[str] = []
        for k in current:
            for child in children[k]:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    next_layer.append(child)
        current = sorted(next_layer)

    leftover = sorted(k for k in keys if k not in done)
    if leftover:
        layers.append([f"? {k}" for k in leftover])
    return layers


async def upstream_closure(repo: AssetRepository, keys: list[str]) -> list[str]:
    """Returns all assets reachable upstream from ``keys`` (inclusive),
    in topological order (deepest deps first)."""
    nodes = await _all_assets(repo)
    by_key = {n.key: n for n in nodes}
    if not by_key:
        return []
    visited: set[str] = set()
    order: list[str] = []

    def visit(k: str) -> None:
        if k in visited or k not in by_key:
            return
        visited.add(k)
        for dep in by_key[k].depends_on:
            visit(dep)
        order.append(k)

    for k in keys:
        visit(k)
    return order


async def downstream_closure(repo: AssetRepository, keys: list[str]) -> list[str]:
    nodes = await _all_assets(repo)
    children: dict[str, list[str]] = defaultdict(list)
    for n in nodes:
        for dep in n.depends_on:
            children[dep].append(n.key)
    visited: set[str] = set()
    order: list[str] = []
    stack = list(keys)
    while stack:
        k = stack.pop()
        if k in visited:
            continue
        visited.add(k)
        order.append(k)
        stack.extend(children.get(k, ()))
    return order


async def pipelines_for_assets(
    repo: AssetRepository, keys: list[str]
) -> list[tuple[str, list[str]]]:
    """Groups assets by their producing pipeline.

    Returns ``[(pipeline_id, [asset_key, ...]), ...]`` preserving the
    order of ``keys`` (typically pre-ordered by :func:`upstream_closure`).
    """
    nodes = await _all_assets(repo)
    by_key = {n.key: n for n in nodes}
    seen: list[str] = []
    grouped: dict[str, list[str]] = defaultdict(list)
    for k in keys:
        n = by_key.get(k)
        if not n:
            continue
        if n.pipeline_id not in grouped:
            seen.append(n.pipeline_id)
        grouped[n.pipeline_id].append(k)
    return [(pid, grouped[pid]) for pid in seen]
