from __future__ import annotations

import hashlib

from runtime.cpt.sanitizer import quote_untrusted_prompt, sanitize_original_prompt
from runtime.cpt.schema import CriticTransformationRecord
from runtime.cpt.templates import (
    CRITIC_MODE_BALANCED,
    DETERMINISTIC_CREATED_AT,
    FORBIDDEN_BEHAVIORS,
    PROVENANCE_NOTE,
    REQUIRED_SECTIONS,
    SCHEMA_VERSION,
    TEMPLATE_VERSION,
    TRANSFORMATION_VERSION,
    build_balanced_critic_prompt,
)


def transform_prompt(original_prompt: str, mode: str = CRITIC_MODE_BALANCED) -> CriticTransformationRecord:
    if mode != CRITIC_MODE_BALANCED:
        raise ValueError("CPT-A1 supports only mode='balanced_critic'")

    sanitized_prompt = sanitize_original_prompt(original_prompt)
    quoted_prompt = quote_untrusted_prompt(sanitized_prompt)
    transformed_prompt = build_balanced_critic_prompt(quoted_prompt)
    original_prompt_hash = _sha256_text(original_prompt)
    transformed_prompt_hash = _sha256_text(transformed_prompt)
    transformation_id = _build_transformation_id(sanitized_prompt, transformed_prompt)

    return CriticTransformationRecord(
        schema_version=SCHEMA_VERSION,
        transformation_id=transformation_id,
        created_at=DETERMINISTIC_CREATED_AT,
        original_prompt=original_prompt,
        sanitized_original_prompt=sanitized_prompt,
        transformed_prompt=transformed_prompt,
        critic_mode=mode,
        template_version=TEMPLATE_VERSION,
        transformation_version=TRANSFORMATION_VERSION,
        required_sections=REQUIRED_SECTIONS,
        forbidden_behaviors=FORBIDDEN_BEHAVIORS,
        provider_call_permitted=False,
        execution_permitted=False,
        browser_action_permitted=False,
        human_review_required=True,
        canonical_status="DRAFT",
        original_prompt_hash=original_prompt_hash,
        transformed_prompt_hash=transformed_prompt_hash,
        provenance_note=PROVENANCE_NOTE,
    )


def _build_transformation_id(sanitized_prompt: str, transformed_prompt: str) -> str:
    payload = "\n".join(
        (
            "cpt-a1",
            CRITIC_MODE_BALANCED,
            TEMPLATE_VERSION,
            TRANSFORMATION_VERSION,
            sanitized_prompt,
            transformed_prompt,
        )
    )
    return "cpt-a1-" + _sha256_text(payload)[:24]


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
