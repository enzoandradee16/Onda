"""Shared UI catalog; persisted identifiers and user content stay unchanged."""

from functools import lru_cache
import json
from pathlib import Path
import re

LANGUAGES = ("pt-BR", "es", "en")
_language = "pt-BR"


def normalize_language(value):
    return value if value in LANGUAGES else "pt-BR"


def set_language(value):
    global _language
    _language = normalize_language(value)


@lru_cache(maxsize=2)
def catalog(language):
    if language not in ("es", "en"):
        return {}
    return json.loads(
        (Path(__file__).parent / "locales" / f"{language}.json").read_text(
            encoding="utf-8"
        )
    )


def english_catalog():
    return catalog("en")


@lru_cache(maxsize=2)
def patterns(language="en"):
    result = []
    for key, value in catalog(language).items():
        parts = re.split(r"(\{[a-zA-Z_][a-zA-Z_0-9]*\})", key)
        names = [
            part[1:-1] for part in parts if part.startswith("{") and part.endswith("}")
        ]
        if not names:
            continue
        pattern = "".join(
            "(.+?)" if part.startswith("{") and part.endswith("}") else re.escape(part)
            for part in parts
        )
        result.append((re.compile(pattern, re.DOTALL), names, value))
    result.sort(key=lambda row: len(row[0].pattern.replace("(.+?)", "")), reverse=True)
    return result


def tr(text, language=None):
    selected = normalize_language(language or _language)
    if not isinstance(text, str):
        return text
    if selected == "pt-BR":
        return text
    direct = catalog(selected).get(text)
    if direct is not None:
        return direct
    if "\n" in text:
        return "\n".join(tr(line, selected) for line in text.split("\n"))
    # Extractors/Java/Python often wrap a catalog message with a tool name and ID.
    if re.match(
        r"^(?:(?:ERROR|ERRO|WARNING|AVISO):|[\w.]+(?:Error|Exception):|\[(?:Errno|WinError) )",
        text,
    ):
        for colon in re.finditer(": ", text):
            suffix = text[colon.end() :]
            direct = catalog(selected).get(suffix)
            if direct is not None:
                from error_localization import technical_text

                return technical_text(text[: colon.end()], selected) + direct
    for pattern, names, value in patterns(selected):
        match = pattern.fullmatch(text)
        if match:
            for name, part in zip(names, match.groups()):
                value = value.replace(
                    "{" + name + "}",
                    (
                        tr(part, language=selected)
                        if name
                        in ("state", "status", "message", "reason", "size", "label")
                        else part
                    ),
                )
            return value
    return text
