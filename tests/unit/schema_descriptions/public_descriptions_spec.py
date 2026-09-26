"""Ensure every public API model field is documented for generated schemas."""

from __future__ import annotations

import inspect

from pydantic import BaseModel

import docpipe.schemas as public_schemas


def test_public_schema_model_fields_have_descriptions() -> None:
    """Require descriptions on declared and inherited fields in exported models."""
    models = [
        exported
        for name in public_schemas.__all__
        if inspect.isclass(exported := getattr(public_schemas, name))
        and issubclass(exported, BaseModel)
    ]

    assert models, "docpipe.schemas must export at least one Pydantic API model"

    missing_descriptions = [
        f"{model.__name__}.{field_name}"
        for model in models
        for field_name, field in model.model_fields.items()
        if not field.description or not field.description.strip()
    ]

    assert not missing_descriptions, (
        "Public schema fields need meaningful Field(description=...) metadata; "
        "missing descriptions: " + ", ".join(missing_descriptions)
    )
