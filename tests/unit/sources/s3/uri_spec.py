"""URI policy is independent of S3 network and transfer behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from docpipe.plugins.errors import UnsafeSourceError
from docpipe.sources.s3.uri import parse_s3_source
from tests.unit.sources.s3.support import s3_config


def should_canonicalize_an_allowed_encoded_key(tmp_path: Path) -> None:
    bucket, key, identity = parse_s3_source(
        s3_config(tmp_path), "s3://documents/reports/annual%20report.txt"
    )
    assert (bucket, key, identity) == (
        "documents",
        "reports/annual report.txt",
        "s3://documents/reports/annual%20report.txt",
    )


@pytest.mark.parametrize(
    "source",
    [
        "s3://other/reports/report.txt",
        "s3://documents/private/report.txt",
        "s3://documents/reports/report.txt?signature=private",
        "s3://documents/reports/%5Cunsafe.txt",
    ],
)
def should_reject_uris_outside_operator_policy(tmp_path: Path, source: str) -> None:
    with pytest.raises(UnsafeSourceError):
        parse_s3_source(s3_config(tmp_path), source)
