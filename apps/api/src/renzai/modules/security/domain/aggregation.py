"""Stable duplicate suppression, overlap grouping and ordering."""

from __future__ import annotations

import hashlib
from dataclasses import replace

from renzai.modules.security.domain.types import DetectorFinding


def aggregate(findings: list[DetectorFinding]) -> tuple[DetectorFinding, ...]:
    deduplicated: dict[tuple[object, ...], DetectorFinding] = {}
    for finding in findings:
        key = (
            finding.detector_id,
            finding.category,
            finding.normalized_start,
            finding.normalized_end,
            finding.metadata.get("rule_id"),
        )
        previous = deduplicated.get(key)
        if previous is None or finding.confidence > previous.confidence:
            deduplicated[key] = finding
    ordered = sorted(
        deduplicated.values(),
        key=lambda item: (
            item.normalized_start if item.normalized_start is not None else 2**31,
            item.normalized_end if item.normalized_end is not None else 2**31,
            item.detector_id,
            item.metadata.get("rule_id", ""),
        ),
    )
    groups: list[list[int]] = []
    for index, finding in enumerate(ordered):
        if finding.normalized_start is None or finding.normalized_end is None:
            continue
        matching = next(
            (
                group
                for group in groups
                if any(
                    ordered[member].normalized_start is not None
                    and finding.normalized_start < (ordered[member].normalized_end or 0)
                    and (ordered[member].normalized_start or 0) < finding.normalized_end
                    for member in group
                )
            ),
            None,
        )
        if matching is None:
            groups.append([index])
        else:
            matching.append(index)
    for group in groups:
        if len(group) < 2:
            continue
        identity = "|".join(
            f"{ordered[index].detector_id}:{ordered[index].normalized_start}:{ordered[index].normalized_end}"
            for index in group
        )
        overlap_group = f"og_{hashlib.sha256(identity.encode()).hexdigest()[:16]}"
        for index in group:
            ordered[index] = replace(ordered[index], overlap_group=overlap_group)
    return tuple(ordered)
