"""Prompt loading, hashing, and freeze verification.

Prompts are loaded from the prompts/ directory. Once frozen, their SHA-256
hashes are stored in FROZEN.json and verified on every load (Rule R1.4).
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class PromptHashMismatchError(Exception):
    """Raised when a frozen prompt's hash does not match FROZEN.json."""


def _prompts_dir(base: str | Path = "prompts") -> Path:
    return Path(base)


def _frozen_path(base: str | Path = "prompts") -> Path:
    return _prompts_dir(base) / "FROZEN.json"


def compute_hash(text: str) -> str:
    """Compute SHA-256 hash of prompt text.

    Args:
        text: The prompt text.

    Returns:
        Hex-encoded SHA-256 hash.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_prompt(name: str, base: str | Path = "prompts") -> str:
    """Load a prompt file by name.

    Args:
        name: Filename (e.g. 'judge_v1.txt').
        base: Base directory for prompts.

    Returns:
        The prompt text.

    Raises:
        FileNotFoundError: If the prompt file does not exist.
    """
    path = _prompts_dir(base) / name
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")

    text = path.read_text(encoding="utf-8")
    logger.info("Loaded prompt '%s' (%d chars)", name, len(text))
    return text


def verify_frozen(name: str, base: str | Path = "prompts") -> str:
    """Load a prompt and verify its hash against FROZEN.json.

    Args:
        name: Filename (e.g. 'judge_v1.txt').
        base: Base directory for prompts.

    Returns:
        The prompt text if verification succeeds.

    Raises:
        PromptHashMismatchError: If the hash does not match.
        FileNotFoundError: If the prompt or FROZEN.json is missing.
        KeyError: If the prompt is not listed in FROZEN.json.
    """
    text = load_prompt(name, base)
    actual_hash = compute_hash(text)

    frozen_file = _frozen_path(base)
    if not frozen_file.exists():
        raise FileNotFoundError(f"FROZEN.json not found: {frozen_file}")

    with open(frozen_file) as f:
        frozen: dict[str, str] = json.load(f)

    if name not in frozen:
        raise KeyError(f"Prompt '{name}' is not listed in FROZEN.json")

    expected_hash = frozen[name]
    if actual_hash != expected_hash:
        raise PromptHashMismatchError(
            f"Prompt '{name}' hash mismatch!\n"
            f"  Expected: {expected_hash}\n"
            f"  Actual:   {actual_hash}\n"
            f"The prompt has been modified after freezing. "
            f"This is not allowed (Rule R1.4, R8.4)."
        )

    logger.info("Prompt '%s' hash verified: %s", name, actual_hash[:12])
    return text


def freeze_prompt(name: str, base: str | Path = "prompts") -> str:
    """Freeze a prompt by writing its hash to FROZEN.json.

    Args:
        name: Filename (e.g. 'judge_v1.txt').
        base: Base directory for prompts.

    Returns:
        The computed SHA-256 hash.

    Raises:
        FileNotFoundError: If the prompt file does not exist.
    """
    text = load_prompt(name, base)
    prompt_hash = compute_hash(text)

    frozen_file = _frozen_path(base)
    frozen: dict[str, str] = {}
    if frozen_file.exists():
        with open(frozen_file) as f:
            frozen = json.load(f)

    frozen[name] = prompt_hash

    with open(frozen_file, "w") as f:
        json.dump(frozen, f, indent=2)
        f.write("\n")

    logger.info("Froze prompt '%s' with hash %s", name, prompt_hash[:12])
    return prompt_hash


def fill_prompt(template: str, context: str, answer: str) -> str:
    """Fill a prompt template with context and answer.

    Uses str.replace (not str.format) since the prompt contains literal
    JSON braces (Design.md §5.2).

    Args:
        template: The prompt template text.
        context: The context to insert.
        answer: The answer to insert.

    Returns:
        The filled prompt string.
    """
    return template.replace("{context}", context).replace("{answer}", answer)
