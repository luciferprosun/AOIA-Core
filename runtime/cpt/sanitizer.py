from __future__ import annotations

MAX_ORIGINAL_PROMPT_CHARS = 20_000
UNTRUSTED_BLOCK_START = "[BEGIN_UNTRUSTED_USER_PROMPT]"
UNTRUSTED_BLOCK_END = "[END_UNTRUSTED_USER_PROMPT]"
ESCAPED_BLOCK_START = "[USER_TEXT_CONTAINED_BEGIN_UNTRUSTED_USER_PROMPT]"
ESCAPED_BLOCK_END = "[USER_TEXT_CONTAINED_END_UNTRUSTED_USER_PROMPT]"


def sanitize_original_prompt(original_prompt: str) -> str:
    if not isinstance(original_prompt, str):
        raise TypeError("original_prompt must be a string")
    if not original_prompt.strip():
        raise ValueError("original_prompt must not be empty or whitespace-only")
    if len(original_prompt) > MAX_ORIGINAL_PROMPT_CHARS:
        raise ValueError(f"original_prompt exceeds {MAX_ORIGINAL_PROMPT_CHARS} characters")

    cleaned = "".join(char for char in original_prompt if _is_allowed_character(char))
    cleaned = cleaned.replace(UNTRUSTED_BLOCK_START, ESCAPED_BLOCK_START)
    cleaned = cleaned.replace(UNTRUSTED_BLOCK_END, ESCAPED_BLOCK_END)

    if not cleaned.strip():
        raise ValueError("original_prompt has no usable text after sanitization")
    return cleaned


def quote_untrusted_prompt(sanitized_prompt: str) -> str:
    if not isinstance(sanitized_prompt, str) or not sanitized_prompt.strip():
        raise ValueError("sanitized_prompt must be a non-empty string")
    return f"{UNTRUSTED_BLOCK_START}\n{sanitized_prompt}\n{UNTRUSTED_BLOCK_END}"


def _is_allowed_character(char: str) -> bool:
    if char in "\n\r\t":
        return True
    return char >= " " and char != "\x7f"
