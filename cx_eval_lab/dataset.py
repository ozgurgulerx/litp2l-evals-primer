"""Loading and validation for versioned CX evaluation datasets."""

from __future__ import annotations

import json
from pathlib import Path

from cx_eval_lab.models import RefundCase


def load_refund_cases(path: str | Path) -> tuple[RefundCase, ...]:
    dataset_path = Path(path)
    raw_dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(raw_dataset, dict) or not isinstance(
        raw_dataset.get("cases"), list
    ):
        raise ValueError("refund dataset must be an object containing a cases list")

    dataset_version = raw_dataset.get("dataset_version")
    if not isinstance(dataset_version, str) or not dataset_version:
        raise ValueError("refund dataset must declare a dataset_version")

    cases = tuple(
        RefundCase.from_dict({**case, "dataset_version": dataset_version})
        for case in raw_dataset["cases"]
    )
    case_ids = tuple(case.case_id for case in cases)
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("refund dataset case identifiers must be unique")
    return cases
