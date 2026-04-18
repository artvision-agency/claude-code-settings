"""Contract tests via schemathesis — property-based fuzzing of every endpoint.

Install:
    pip install schemathesis

Run:
    BASE_URL=http://localhost:8000 pytest tests/contract/test_contract.py --run-integration

This loads the OpenAPI schema and generates requests conforming to it, then
checks each response conforms too. Catches: missing fields, wrong types,
undeclared status codes, missing Content-Type.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

schemathesis = pytest.importorskip("schemathesis")

SCHEMA_PATH = Path(__file__).parent / "openapi.yaml"
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")

schema = schemathesis.from_path(str(SCHEMA_PATH), base_url=BASE_URL)


@pytest.mark.integration
@schema.parametrize()
def test_api_conforms_to_schema(case) -> None:  # type: ignore[no-untyped-def]
    """Every generated call must return a response matching the schema."""
    case.call_and_validate()
