#!/usr/bin/env python3
"""Remove human-formatted size columns from SQL while retaining raw values."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
FORMAT_FUNCTION = "formatreadablesize"
ROUND_FUNCTION = "round"


def sql_mask(source: str) -> str:
    """Mask strings and comments while retaining offsets and newlines."""

    output = list(source)
    index = 0
    quote = ""
    while index < len(source):
        if quote:
            if source[index] == quote:
                if index + 1 < len(source) and source[index + 1] == quote:
                    output[index] = output[index + 1] = " "
                    index += 2
                    continue
                output[index] = " "
                quote = ""
            elif source[index] != "\n":
                output[index] = " "
            index += 1
            continue
        if source.startswith("--", index):
            end = source.find("\n", index)
            end = len(source) if end < 0 else end
            output[index:end] = " " * (end - index)
            index = end
            continue
        if source.startswith("/*", index):
            end = source.find("*/", index + 2)
            end = len(source) - 2 if end < 0 else end
            for position in range(index, min(end + 2, len(source))):
                if source[position] != "\n":
                    output[position] = " "
            index = end + 2
            continue
        if source[index] in {"'", '"', "`"}:
            quote = source[index]
            output[index] = " "
        index += 1
    return "".join(output)


def select_spans(source: str) -> list[tuple[int, int]]:
    mask = sql_mask(source)
    tokens = [(match.group(0).casefold(), match.start(), match.end()) for match in WORD_RE.finditer(mask)]
    depths: list[int] = [0] * (len(source) + 1)
    depth = 0
    for index, char in enumerate(mask):
        depths[index] = depth
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(depth - 1, 0)
    spans: list[tuple[int, int]] = []
    for token_index, (word, _start, end) in enumerate(tokens):
        if word != "select":
            continue
        target_depth = depths[end]
        for next_word, next_start, _next_end in tokens[token_index + 1 :]:
            if next_word == "from" and depths[next_start] == target_depth:
                spans.append((end, next_start))
                break
    return spans


def split_expressions(select_list: str) -> list[str]:
    mask = sql_mask(select_list)
    depth = 0
    start = 0
    expressions: list[str] = []
    for index, char in enumerate(mask):
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(depth - 1, 0)
        elif char == "," and depth == 0:
            expressions.append(select_list[start:index])
            start = index + 1
    expressions.append(select_list[start:])
    return expressions


def unwrap_format_readable_size(expression: str) -> str:
    mask = sql_mask(expression)
    lowered = mask.casefold()
    search_from = 0
    while True:
        start = lowered.find(FORMAT_FUNCTION, search_from)
        if start < 0:
            return expression
        opening = lowered.find("(", start + len(FORMAT_FUNCTION))
        if opening < 0:
            return expression
        depth = 1
        closing = opening + 1
        while closing < len(mask) and depth:
            if mask[closing] == "(":
                depth += 1
            elif mask[closing] == ")":
                depth -= 1
            closing += 1
        if depth:
            raise ValueError("unbalanced formatReadableSize call")
        inner = expression[opening + 1 : closing - 1]
        expression = expression[:start] + inner + expression[closing:]
        mask = sql_mask(expression)
        lowered = mask.casefold()
        search_from = start + len(inner)


def unwrap_round(expression: str) -> str:
    """Replace round(value, precision) with the lossless value expression."""

    while True:
        mask = sql_mask(expression)
        match = re.search(r"\bround\s*\(", mask, flags=re.IGNORECASE)
        if not match:
            return expression
        opening = mask.find("(", match.start())
        depth = 1
        closing = opening + 1
        while closing < len(mask) and depth:
            if mask[closing] == "(":
                depth += 1
            elif mask[closing] == ")":
                depth -= 1
            closing += 1
        if depth:
            raise ValueError("unbalanced round call")
        arguments = split_expressions(expression[opening + 1 : closing - 1])
        if not arguments or not arguments[0].strip():
            raise ValueError("round call has no value argument")
        value = arguments[0].strip()
        expression = expression[: match.start()] + value + expression[closing:]


def unwrap_direct_to_string(expression: str) -> str:
    """Keep a directly selected value typed; leave toString inside computations."""

    mask = sql_mask(expression)
    match = re.match(r"\s*toString\s*\(", mask, flags=re.IGNORECASE)
    if not match:
        return expression
    opening = mask.find("(", match.start())
    depth = 1
    closing = opening + 1
    while closing < len(mask) and depth:
        if mask[closing] == "(":
            depth += 1
        elif mask[closing] == ")":
            depth -= 1
        closing += 1
    if depth:
        raise ValueError("unbalanced toString call")
    suffix = mask[closing:]
    if not re.fullmatch(
        r"\s+(?:as\s+)?(?:[A-Za-z_][A-Za-z0-9_]*|\"[^\"]+\"|`[^`]+`)\s*",
        suffix,
        flags=re.IGNORECASE,
    ):
        return expression
    return expression[: match.start()] + expression[opening + 1 : closing - 1] + expression[closing:]


def output_alias(expression: str) -> str:
    mask = sql_mask(expression).strip()
    match = re.search(
        r"(?:\bas\s+)?(?:[A-Za-z_][A-Za-z0-9_]*|\"([^\"]+)\"|`([^`]+)`)\s*$",
        mask,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    token = match.group(0).strip()
    token = re.sub(r"^as\s+", "", token, flags=re.IGNORECASE).strip('"`')
    return token


def normalize_select_list(select_list: str) -> str:
    expressions = split_expressions(select_list)
    changed = False
    retained: list[str] = []
    for expression in expressions:
        lowered = sql_mask(expression).casefold()
        has_format = FORMAT_FUNCTION in lowered
        has_round = bool(re.search(r"\bround\s*\(", lowered))
        direct_to_string = bool(re.match(r"\s*toString\s*\(", sql_mask(expression), re.I))
        if not has_format and not has_round and not direct_to_string:
            retained.append(expression)
            continue
        changed = True
        alias = output_alias(expression).casefold()
        if has_format and (alias.startswith("pretty_") or alias.startswith("p_")):
            continue
        normalized = unwrap_format_readable_size(expression) if has_format else expression
        normalized = unwrap_round(normalized) if has_round else normalized
        normalized = unwrap_direct_to_string(normalized) if direct_to_string else normalized
        retained.append(normalized)
    if not changed:
        return select_list
    cleaned = [expression.strip() for expression in retained if expression.strip()]
    return "\n\t" + ",\n\t".join(cleaned) + "\n"


def normalize_sql(source: str) -> str:
    result = source
    while True:
        changed = False
        for start, end in sorted(select_spans(result), reverse=True):
            normalized = normalize_select_list(result[start:end])
            if normalized == result[start:end]:
                continue
            result = result[:start] + normalized + result[end:]
            changed = True
            break
        if not changed:
            break
    if FORMAT_FUNCTION in sql_mask(result).casefold():
        result = unwrap_format_readable_size(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("ch_diag/content/queries"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    changed: list[Path] = []
    for path in sorted(args.root.rglob("*.sql")):
        source = path.read_text(encoding="utf-8")
        normalized = normalize_sql(source)
        if normalized != source:
            changed.append(path)
            if not args.check:
                path.write_text(normalized, encoding="utf-8")
    if args.check and changed:
        for path in changed:
            print(path)
        return 1
    print(f"normalized SQL files: {len(changed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
