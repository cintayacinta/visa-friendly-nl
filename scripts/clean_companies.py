#!/usr/bin/env python3
"""Conservative cleanup pipeline for nlcompanies.tsv.

Usage:
    python3 scripts/clean_companies.py \
        --input nlcompanies.tsv \
        --mapping-config config/category_mapping.json \
        --cleaned output/cleaned_companies.tsv \
        --review output/cleanup_review.tsv \
        --summary output/cleanup_summary.md \
        --mapping-output output/category_mapping.json
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple
from urllib.parse import urlsplit, urlunsplit


EXPECTED_COLUMNS = [
    "kvk_number",
    "legal_name",
    "display_name",
    "website_url",
    "career_url",
    "career_email",
    "city",
    "province",
    "industry_category",
    "industry_detail",
]

INPUT_ALIASES = {
    "email": "career_email",
}

TEXT_COLUMNS = [
    "legal_name",
    "display_name",
    "city",
    "province",
    "industry_category",
    "industry_detail",
]

URL_COLUMNS = ["website_url", "career_url"]
EMAIL_COLUMNS = ["career_email"]

MISSING_TOKENS = {
    "",
    "n/a",
    "na",
    "null",
    "none",
    "nil",
    "undefined",
    "not available",
    "not_applicable",
}

DEFAULT_MAPPING_PAYLOAD = {
    "schema_version": 1,
    "policy": "Only obvious spelling/formatting variants are canonicalized automatically.",
    "canonical_map": {
        "Realestate": "RealEstate",
    },
    "review_candidates": {
        "Beverages": "Beverage",
        "Biotech": "Biotechnology",
        "Telecom": "Telecommunications",
    },
    "display_labels": {
        "AI": "AI",
        "ConsumerElectronics": "Consumer Electronics",
        "Consumergoods": "Consumer Goods",
        "Datacenter": "Data Center",
        "Ecommerce": "Ecommerce",
        "FinancialServices": "Financial Services",
        "Healthtech": "Healthtech",
        "IT": "IT",
        "MarketResearch": "Market Research",
        "Medtech": "Medtech",
        "Nonprofit": "Nonprofit",
        "RealEstate": "Real Estate",
        "Telecommunications": "Telecommunications",
        "Venture Capital": "Venture Capital",
    },
    "do_not_merge_examples": [
        ["Finance", "FinancialServices"],
        ["Technology", "Software"],
        ["AI", "Software"],
        ["Services", "Consulting"],
    ],
}

REPEATED_WHITESPACE_RE = re.compile(r"\s+")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
SUSPICIOUS_CITY_RE = re.compile(r"[?]| / |/|\\")
SUSPICIOUS_PLACEHOLDER_RE = re.compile(
    r"^(unknown|tbd|to be determined|misc|other)$",
    re.IGNORECASE,
)


@dataclass
class RowRecord:
    source_row_number: int
    raw: Dict[str, str]
    cleaned: Dict[str, str]
    flags: List[str]
    malformed_reason: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean a company TSV for app use.")
    parser.add_argument("--input", default="nlcompanies.tsv", help="Path to input TSV")
    parser.add_argument(
        "--mapping-config",
        default="config/category_mapping.json",
        help="Path to persistent category mapping config input",
    )
    parser.add_argument(
        "--cleaned",
        default="output/cleaned_companies.tsv",
        help="Path to cleaned TSV output",
    )
    parser.add_argument(
        "--review",
        default="output/cleanup_review.tsv",
        help="Path to cleanup review TSV output",
    )
    parser.add_argument(
        "--summary",
        default="output/cleanup_summary.md",
        help="Path to markdown summary output",
    )
    parser.add_argument(
        "--mapping-output",
        default="output/category_mapping.json",
        help="Path to generated category mapping JSON snapshot",
    )
    return parser.parse_args()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_mapping_config(path: Path) -> Dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    for key in [
        "canonical_map",
        "review_candidates",
        "display_labels",
        "do_not_merge_examples",
    ]:
        if key not in payload:
            raise ValueError(f"Mapping config missing required key: {key}")

    payload.setdefault("schema_version", DEFAULT_MAPPING_PAYLOAD["schema_version"])
    payload.setdefault("policy", DEFAULT_MAPPING_PAYLOAD["policy"])
    return payload


def normalize_missing(value: str | None) -> str:
    if value is None:
        return ""
    stripped = value.strip()
    if stripped.casefold() in MISSING_TOKENS:
        return ""
    return stripped


def collapse_whitespace(value: str) -> str:
    return REPEATED_WHITESPACE_RE.sub(" ", value).strip()


def normalize_text(value: str) -> str:
    return collapse_whitespace(normalize_missing(value))


def normalize_email(value: str) -> Tuple[str, str]:
    raw = normalize_missing(value)
    if not raw:
        return "", ""
    candidate = raw.casefold()
    if not EMAIL_RE.fullmatch(candidate):
        return raw, ""
    return raw, candidate


def normalize_url(value: str) -> Tuple[str, str]:
    raw = normalize_missing(value)
    if not raw:
        return "", ""
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return raw, ""
    if parsed.scheme.lower() not in {"http", "https"}:
        return raw, ""
    if not parsed.netloc:
        return raw, ""
    normalized = urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path,
            parsed.query,
            parsed.fragment,
        )
    )
    return raw, normalized


def canonicalize_category(
    value: str,
    canonical_map: Dict[str, str],
    display_labels: Dict[str, str],
) -> Tuple[str, str, str]:
    raw = normalize_text(value)
    if not raw:
        return "", "", ""
    canonical = canonical_map.get(raw, raw)
    display = display_labels.get(canonical, canonical)
    return raw, canonical, display


def non_empty_count(row: Dict[str, str], columns: Sequence[str]) -> int:
    return sum(1 for column in columns if row.get(column, "") != "")


def read_input(
    path: Path,
    mapping_payload: Dict[str, object],
) -> Tuple[List[RowRecord], List[Dict[str, str]], str, List[str]]:
    records: List[RowRecord] = []
    review_events: List[Dict[str, str]] = []
    header_notes: List[str] = []
    raw_header_name = ""

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        try:
            header = next(reader)
        except StopIteration:
            raise ValueError("Input TSV is empty")

        raw_header_name = ",".join(header)
        normalized_header = [INPUT_ALIASES.get(c.strip(), c.strip()) for c in header]
        header_notes.extend(
            note
            for note in detect_header_issues(header, normalized_header)
            if note
        )

        for line_number, row in enumerate(reader, start=2):
            row_values = list(row)
            malformed_reason = ""
            if len(row_values) < len(normalized_header):
                row_values.extend([""] * (len(normalized_header) - len(row_values)))
                malformed_reason = "short_row_padded"
            elif len(row_values) > len(normalized_header):
                malformed_reason = "long_row_extra_columns"
                row_values = row_values[: len(normalized_header)]

            raw_row = {column: value for column, value in zip(normalized_header, row_values)}
            canonical_raw = {column: raw_row.get(column, "") for column in EXPECTED_COLUMNS}
            for column in EXPECTED_COLUMNS:
                canonical_raw.setdefault(column, "")

            cleaned, flags = clean_row(canonical_raw, mapping_payload)
            record = RowRecord(
                source_row_number=line_number,
                raw=canonical_raw,
                cleaned=cleaned,
                flags=flags[:],
                malformed_reason=malformed_reason,
            )
            if malformed_reason:
                record.flags.append(f"malformed_row:{malformed_reason}")
                review_events.append(
                    make_review_event(
                        record,
                        issue_type="malformed_row",
                        field_name="*",
                        raw_value=malformed_reason,
                        clean_value="",
                        detail="Row length did not match header and was safely adjusted.",
                    )
                )
            records.append(record)

    return records, review_events, raw_header_name, header_notes


def detect_header_issues(header: Sequence[str], normalized_header: Sequence[str]) -> List[str]:
    issues: List[str] = []
    missing = [column for column in EXPECTED_COLUMNS if column not in normalized_header]
    extra = [column for column in normalized_header if column not in EXPECTED_COLUMNS]
    if missing:
        issues.append(f"Missing expected columns: {', '.join(missing)}")
    if extra:
        issues.append(f"Extra input columns ignored: {', '.join(extra)}")
    if "email" in header and "career_email" not in header:
        issues.append("Input column `email` was aliased to `career_email`.")
    return issues


def clean_row(
    raw_row: Dict[str, str],
    mapping_payload: Dict[str, object],
) -> Tuple[Dict[str, str], List[str]]:
    cleaned: Dict[str, str] = {}
    flags: List[str] = []
    canonical_map = mapping_payload["canonical_map"]
    display_labels = mapping_payload["display_labels"]
    review_candidates = mapping_payload["review_candidates"]

    for column in EXPECTED_COLUMNS:
        cleaned[column] = normalize_missing(raw_row.get(column, ""))

    cleaned["kvk_number_clean"] = cleaned["kvk_number"]
    cleaned["legal_name_clean"] = normalize_text(raw_row.get("legal_name", ""))
    cleaned["display_name_clean"] = normalize_text(raw_row.get("display_name", ""))

    for column in TEXT_COLUMNS:
        cleaned[column] = normalize_text(raw_row.get(column, ""))

    for column in URL_COLUMNS:
        raw_url, clean_url = normalize_url(raw_row.get(column, ""))
        cleaned[column] = raw_url
        cleaned[f"{column}_clean"] = clean_url
        if raw_url and not clean_url:
            flags.append(f"invalid_{column}")

    for column in EMAIL_COLUMNS:
        raw_email, clean_email = normalize_email(raw_row.get(column, ""))
        cleaned[column] = raw_email
        cleaned[f"{column}_clean"] = clean_email
        if raw_email and not clean_email:
            flags.append(f"invalid_{column}")

    category_raw, category_clean, category_display = canonicalize_category(
        raw_row.get("industry_category", ""),
        canonical_map,
        display_labels,
    )
    cleaned["industry_category"] = category_raw
    cleaned["industry_category_raw"] = category_raw
    cleaned["industry_category_clean"] = category_clean
    cleaned["industry_category_display"] = category_display

    cleaned["city_clean"] = cleaned["city"]
    cleaned["province_clean"] = cleaned["province"]
    cleaned["industry_detail_clean"] = cleaned["industry_detail"]

    if cleaned["display_name"] == "" and cleaned["legal_name"] != "":
        flags.append("missing_display_name")
    if cleaned["city"] == "" and cleaned["province"] != "":
        flags.append("missing_city_with_province")
    if cleaned["city"] != "" and cleaned["province"] == "":
        flags.append("missing_province_with_city")
    if cleaned["industry_category"] == "" and cleaned["industry_detail"] != "":
        flags.append("missing_industry_category_with_detail")
    if cleaned["industry_category"] != "" and cleaned["industry_detail"] == "":
        flags.append("missing_industry_detail_with_category")
    if cleaned["city"] and SUSPICIOUS_CITY_RE.search(cleaned["city"]):
        flags.append("suspicious_city_value")
    if cleaned["province"] and SUSPICIOUS_CITY_RE.search(cleaned["province"]):
        flags.append("suspicious_province_value")
    if cleaned["industry_category"] and SUSPICIOUS_PLACEHOLDER_RE.search(cleaned["industry_category"]):
        flags.append("suspicious_industry_category")
    if cleaned["industry_detail"] and SUSPICIOUS_PLACEHOLDER_RE.search(cleaned["industry_detail"]):
        flags.append("suspicious_industry_detail")
    if cleaned["industry_category"] in review_candidates:
        flags.append("industry_category_mapping_candidate")

    return cleaned, sorted(set(flags))


def make_review_event(
    record: RowRecord,
    issue_type: str,
    field_name: str,
    raw_value: str,
    clean_value: str,
    detail: str,
    related_row_numbers: str = "",
) -> Dict[str, str]:
    return {
        "source_row_number": str(record.source_row_number),
        "kvk_number": record.cleaned.get("kvk_number", ""),
        "issue_type": issue_type,
        "field_name": field_name,
        "raw_value": raw_value,
        "clean_value": clean_value,
        "detail": detail,
        "related_row_numbers": related_row_numbers,
    }


def row_signature(cleaned: Dict[str, str]) -> Tuple[Tuple[str, str], ...]:
    return tuple((column, cleaned.get(column, "")) for column in EXPECTED_COLUMNS)


def merge_duplicate_group(
    records: Sequence[RowRecord],
    review_events: List[Dict[str, str]],
    mapping_payload: Dict[str, object],
) -> Tuple[RowRecord, List[RowRecord], Dict[str, int], Dict[str, object]]:
    stats = {
        "duplicate_groups": 1,
        "exact_duplicate_groups": 0,
        "conflicting_duplicate_groups": 0,
        "complementary_duplicate_groups": 0,
        "exact_duplicates_removed": 0,
    }
    decision = {
        "kvk_number": records[0].cleaned.get("kvk_number", ""),
        "source_row_numbers": ",".join(str(record.source_row_number) for record in records),
        "kept_source_row_number": "",
        "decision": "",
        "conflict_fields": "",
        "merged_fields": "",
    }
    duplicate_source_rows = ",".join(str(record.source_row_number) for record in records)
    signatures = {row_signature(record.cleaned) for record in records}
    duplicates_dropped: List[RowRecord] = []
    if len(signatures) == 1:
        stats["exact_duplicate_groups"] = 1
        stats["exact_duplicates_removed"] = len(records) - 1
        winner = min(records, key=lambda record: record.source_row_number)
        winner.cleaned["dedupe_action"] = "kept_exact_duplicate"
        winner.flags = sorted(set(winner.flags + ["exact_duplicate_group"]))
        winner.cleaned["duplicate_group_size"] = str(len(records))
        winner.cleaned["duplicate_source_rows"] = duplicate_source_rows
        winner.cleaned["merged_from_source_rows"] = ""
        winner.cleaned["duplicate_conflict_fields"] = ""
        decision["kept_source_row_number"] = str(winner.source_row_number)
        decision["decision"] = "kept_exact_duplicate"
        for duplicate in records:
            if duplicate is winner:
                continue
            duplicates_dropped.append(duplicate)
            review_events.append(
                make_review_event(
                    duplicate,
                    issue_type="exact_duplicate_removed",
                    field_name="kvk_number",
                    raw_value=duplicate.cleaned.get("kvk_number", ""),
                    clean_value=winner.cleaned.get("kvk_number", ""),
                    detail="Exact duplicate row removed; winner kept deterministically by first source row.",
                    related_row_numbers=str(winner.source_row_number),
                )
            )
        return winner, duplicates_dropped, stats, decision

    ranked = sorted(
        records,
        key=lambda record: (
            -non_empty_count(record.cleaned, EXPECTED_COLUMNS),
            record.source_row_number,
        ),
    )
    winner = ranked[0]
    merged = dict(winner.cleaned)
    winner_flags = set(winner.flags)
    conflict_fields = {
        field
        for field in EXPECTED_COLUMNS
        if len({record.cleaned.get(field, "") for record in records if record.cleaned.get(field, "") != ""}) > 1
    }
    had_conflict = bool(conflict_fields)
    had_complementary_merge = False
    merged_fields = set()
    merged_from_rows = set()

    for duplicate in ranked[1:]:
        duplicates_dropped.append(duplicate)

    if had_conflict:
        for duplicate in ranked[1:]:
            for field in sorted(conflict_fields):
                duplicate_value = duplicate.cleaned.get(field, "")
                winner_value = winner.cleaned.get(field, "")
                if duplicate_value != "" and winner_value != "" and duplicate_value != winner_value:
                    winner_flags.add(f"duplicate_conflict:{field}")
                    review_events.append(
                        make_review_event(
                            duplicate,
                            issue_type="duplicate_conflict",
                            field_name=field,
                            raw_value=duplicate.raw.get(field, ""),
                            clean_value=winner.raw.get(field, ""),
                            detail=(
                                "Conflicting non-empty duplicate values; no automatic merge "
                                "was performed for this duplicate group."
                            ),
                            related_row_numbers=str(winner.source_row_number),
                        )
                    )
    else:
        for duplicate in ranked[1:]:
            for field in EXPECTED_COLUMNS:
                winner_value = merged.get(field, "")
                duplicate_value = duplicate.cleaned.get(field, "")
                if winner_value == "" and duplicate_value != "":
                    merged[field] = duplicate_value
                    had_complementary_merge = True
                    merged_fields.add(field)
                    merged_from_rows.add(duplicate.source_row_number)
                    review_events.append(
                        make_review_event(
                            duplicate,
                            issue_type="duplicate_complementary_merge",
                            field_name=field,
                            raw_value=duplicate.raw.get(field, ""),
                            clean_value=duplicate_value,
                            detail=(
                                "Value filled from duplicate row into kept record because "
                                "the duplicate group had no conflicting non-empty fields."
                            ),
                            related_row_numbers=str(winner.source_row_number),
                        )
                    )

    winner.cleaned = finalize_merged_cleaned(merged, mapping_payload)
    winner.flags = sorted(
        set(list(winner_flags) + list(derive_post_merge_flags(winner.cleaned, mapping_payload)))
    )
    winner.cleaned["duplicate_group_size"] = str(len(records))
    winner.cleaned["duplicate_source_rows"] = duplicate_source_rows
    winner.cleaned["merged_from_source_rows"] = ",".join(str(row) for row in sorted(merged_from_rows))
    winner.cleaned["duplicate_conflict_fields"] = ",".join(sorted(conflict_fields))

    if had_conflict:
        stats["conflicting_duplicate_groups"] = 1
        winner.cleaned["dedupe_action"] = "kept_winner_with_conflicts"
        decision["decision"] = "kept_winner_with_conflicts"
    elif had_complementary_merge:
        stats["complementary_duplicate_groups"] = 1
        winner.cleaned["dedupe_action"] = "merged_complementary_duplicates"
        decision["decision"] = "merged_complementary_duplicates"
    else:
        winner.cleaned["dedupe_action"] = "kept_best_duplicate"
        decision["decision"] = "kept_best_duplicate"
    decision["kept_source_row_number"] = str(winner.source_row_number)
    decision["conflict_fields"] = ",".join(sorted(conflict_fields))
    decision["merged_fields"] = ",".join(sorted(merged_fields))
    return winner, duplicates_dropped, stats, decision


def finalize_merged_cleaned(
    cleaned: Dict[str, str],
    mapping_payload: Dict[str, object],
) -> Dict[str, str]:
    finalized = dict(cleaned)
    for column in TEXT_COLUMNS:
        finalized[column] = normalize_text(finalized.get(column, ""))
    for column in URL_COLUMNS:
        raw_url, clean_url = normalize_url(finalized.get(column, ""))
        finalized[column] = raw_url
        finalized[f"{column}_clean"] = clean_url
    for column in EMAIL_COLUMNS:
        raw_email, clean_email = normalize_email(finalized.get(column, ""))
        finalized[column] = raw_email
        finalized[f"{column}_clean"] = clean_email
    category_raw, category_clean, category_display = canonicalize_category(
        finalized.get("industry_category", ""),
        mapping_payload["canonical_map"],
        mapping_payload["display_labels"],
    )
    finalized["industry_category"] = category_raw
    finalized["industry_category_raw"] = category_raw
    finalized["industry_category_clean"] = category_clean
    finalized["industry_category_display"] = category_display
    finalized["city_clean"] = finalized.get("city", "")
    finalized["province_clean"] = finalized.get("province", "")
    finalized["industry_detail_clean"] = finalized.get("industry_detail", "")
    return finalized


def derive_post_merge_flags(
    cleaned: Dict[str, str],
    mapping_payload: Dict[str, object],
) -> Iterable[str]:
    _, flags = clean_row(cleaned, mapping_payload)
    return flags


def dedupe_records(
    records: Sequence[RowRecord],
    review_events: List[Dict[str, str]],
    mapping_payload: Dict[str, object],
) -> Tuple[List[RowRecord], Dict[str, int], List[Dict[str, object]]]:
    grouped: Dict[str, List[RowRecord]] = defaultdict(list)
    unique_records: List[RowRecord] = []
    decisions: List[Dict[str, object]] = []
    stats = {
        "duplicate_groups": 0,
        "exact_duplicate_groups": 0,
        "conflicting_duplicate_groups": 0,
        "complementary_duplicate_groups": 0,
        "exact_duplicates_removed": 0,
    }

    for record in records:
        kvk_number = record.cleaned.get("kvk_number", "")
        if kvk_number == "":
            record.cleaned["dedupe_action"] = "unique_missing_kvk"
            record.cleaned["duplicate_group_size"] = "1"
            record.cleaned["duplicate_source_rows"] = str(record.source_row_number)
            record.cleaned["merged_from_source_rows"] = ""
            record.cleaned["duplicate_conflict_fields"] = ""
            unique_records.append(record)
        else:
            grouped[kvk_number].append(record)

    for kvk_number in sorted(grouped):
        rows = grouped[kvk_number]
        if len(rows) == 1:
            rows[0].cleaned["dedupe_action"] = "unique"
            rows[0].cleaned["duplicate_group_size"] = "1"
            rows[0].cleaned["duplicate_source_rows"] = str(rows[0].source_row_number)
            rows[0].cleaned["merged_from_source_rows"] = ""
            rows[0].cleaned["duplicate_conflict_fields"] = ""
            unique_records.append(rows[0])
            continue
        winner, _dropped, group_stats, decision = merge_duplicate_group(
            rows,
            review_events,
            mapping_payload,
        )
        for key in stats:
            stats[key] += group_stats[key]
        decisions.append(decision)
        unique_records.append(winner)

    unique_records.sort(key=lambda record: (record.cleaned.get("kvk_number", ""), record.source_row_number))
    decisions.sort(key=lambda decision: (decision["kvk_number"], decision["kept_source_row_number"]))
    return unique_records, stats, decisions


def collect_review_events(
    records: Sequence[RowRecord],
    existing_events: List[Dict[str, str]],
) -> List[Dict[str, str]]:
    review_events = list(existing_events)
    for record in records:
        for flag in record.flags:
            if flag.startswith("duplicate_conflict:"):
                continue
            review_events.append(
                make_review_event(
                    record,
                    issue_type="review_flag",
                    field_name=flag_field_name(flag),
                    raw_value=record.raw.get(flag_field_name(flag), ""),
                    clean_value=record.cleaned.get(flag_field_name(flag), ""),
                    detail=flag,
                )
            )
    review_events.sort(
        key=lambda event: (
            int(event["source_row_number"]),
            event["issue_type"],
            event["field_name"],
        )
    )
    return review_events


def flag_field_name(flag: str) -> str:
    if flag.startswith("invalid_"):
        return flag.replace("invalid_", "")
    if flag == "missing_city_with_province":
        return "city"
    if flag == "missing_province_with_city":
        return "province"
    if flag.startswith("missing_industry_category"):
        return "industry_category"
    if flag.startswith("missing_industry_detail"):
        return "industry_detail"
    if flag.startswith("suspicious_city"):
        return "city"
    if flag.startswith("suspicious_province"):
        return "province"
    if flag.startswith("suspicious_industry_category"):
        return "industry_category"
    if flag.startswith("suspicious_industry_detail"):
        return "industry_detail"
    if flag == "missing_display_name":
        return "display_name"
    if flag == "industry_category_mapping_candidate":
        return "industry_category"
    return "*"


def write_cleaned_output(path: Path, records: Sequence[RowRecord]) -> None:
    ensure_parent(path)
    fieldnames = [
        "source_row_number",
        "duplicate_group_size",
        "duplicate_source_rows",
        "merged_from_source_rows",
        "duplicate_conflict_fields",
        "kvk_number",
        "kvk_number_clean",
        "legal_name",
        "legal_name_clean",
        "display_name",
        "display_name_clean",
        "website_url",
        "career_url",
        "career_email",
        "city",
        "province",
        "industry_category",
        "industry_detail",
        "website_url_clean",
        "career_url_clean",
        "career_email_clean",
        "city_clean",
        "province_clean",
        "industry_category_raw",
        "industry_category_clean",
        "industry_category_display",
        "industry_detail_clean",
        "review_flags",
        "dedupe_action",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for record in records:
            row = {field: "" for field in fieldnames}
            row["source_row_number"] = str(record.source_row_number)
            for field in [
                "kvk_number",
                "legal_name",
                "display_name",
                "website_url",
                "career_url",
                "career_email",
                "city",
                "province",
                "industry_category",
                "industry_detail",
            ]:
                row[field] = record.raw.get(field, "")
            for field in fieldnames:
                if field in record.cleaned and (field not in row or row[field] == ""):
                    row[field] = record.cleaned[field]
            row["review_flags"] = "|".join(sorted(set(record.flags)))
            writer.writerow(row)


def write_review_output(path: Path, review_events: Sequence[Dict[str, str]]) -> None:
    ensure_parent(path)
    fieldnames = [
        "source_row_number",
        "kvk_number",
        "issue_type",
        "field_name",
        "raw_value",
        "clean_value",
        "detail",
        "related_row_numbers",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for event in review_events:
            writer.writerow(event)


def write_mapping_output(
    path: Path,
    mapping_payload: Dict[str, object],
    mapping_config_path: Path,
) -> Dict[str, object]:
    ensure_parent(path)
    snapshot = dict(mapping_payload)
    snapshot["source_config"] = str(mapping_config_path)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    return snapshot


def count_missing(rows: Sequence[Dict[str, str]], columns: Sequence[str]) -> Dict[str, int]:
    counts = {}
    for column in columns:
        counts[column] = sum(1 for row in rows if normalize_missing(row.get(column, "")) == "")
    return counts


def count_clean_missing(records: Sequence[RowRecord], columns: Sequence[str]) -> Dict[str, int]:
    counts = {}
    for column in columns:
        counts[column] = sum(1 for record in records if record.cleaned.get(column, "") == "")
    return counts


def summary_flag_counts(records: Sequence[RowRecord]) -> Counter:
    counter: Counter = Counter()
    for record in records:
        counter.update(record.flags)
    return counter


def write_summary(
    path: Path,
    input_path: Path,
    original_records: Sequence[RowRecord],
    cleaned_records: Sequence[RowRecord],
    review_events: Sequence[Dict[str, str]],
    dedupe_stats: Dict[str, int],
    dedupe_decisions: Sequence[Dict[str, object]],
    mapping_payload: Dict[str, object],
    header_notes: Sequence[str],
) -> None:
    ensure_parent(path)

    original_raw_rows = [record.raw for record in original_records]
    missing_before = count_missing(original_raw_rows, EXPECTED_COLUMNS)
    missing_after = count_clean_missing(cleaned_records, EXPECTED_COLUMNS)
    invalid_url_count = sum(
        1
        for record in original_records
        for column in URL_COLUMNS
        if record.cleaned.get(column, "") and record.cleaned.get(f"{column}_clean", "") == ""
    )
    invalid_email_count = sum(
        1
        for record in original_records
        for column in EMAIL_COLUMNS
        if record.cleaned.get(column, "") and record.cleaned.get(f"{column}_clean", "") == ""
    )
    flagged_rows = sum(1 for record in cleaned_records if record.flags)
    flag_counts = summary_flag_counts(cleaned_records)
    mapping_rows = [
        (source, target, mapping_payload["display_labels"].get(target, target))
        for source, target in mapping_payload["canonical_map"].items()
    ]

    lines: List[str] = []
    lines.append("# Cleanup Summary")
    lines.append("")
    lines.append(f"- Input file: `{input_path}`")
    lines.append(f"- Input row count: `{len(original_records)}`")
    lines.append(f"- Output row count: `{len(cleaned_records)}`")
    lines.append(f"- Exact duplicate groups: `{dedupe_stats['exact_duplicate_groups']}`")
    lines.append(f"- Exact duplicates removed: `{dedupe_stats['exact_duplicates_removed']}`")
    lines.append(f"- Conflicting duplicate groups found: `{dedupe_stats['conflicting_duplicate_groups']}`")
    lines.append(f"- Complementary duplicate groups merged: `{dedupe_stats['complementary_duplicate_groups']}`")
    lines.append(f"- Rows flagged for review: `{flagged_rows}`")
    lines.append(f"- Invalid URLs found: `{invalid_url_count}`")
    lines.append(f"- Invalid emails found: `{invalid_email_count}`")
    lines.append("")
    if header_notes:
        lines.append("## Input Notes")
        lines.append("")
        for note in header_notes:
            lines.append(f"- {note}")
        lines.append("")
    lines.append("## Missing Values")
    lines.append("")
    lines.append("| Column | Before normalization | After cleanup output |")
    lines.append("| --- | ---: | ---: |")
    for column in EXPECTED_COLUMNS:
        lines.append(f"| `{column}` | {missing_before[column]} | {missing_after[column]} |")
    lines.append("")
    lines.append("## Category Mapping")
    lines.append("")
    lines.append("| Raw value | Canonical value | Display label |")
    lines.append("| --- | --- | --- |")
    for source, target, label in mapping_rows:
        lines.append(f"| `{source}` | `{target}` | `{label}` |")
    lines.append("")
    lines.append("## Category Review Candidates")
    lines.append("")
    lines.append("| Raw value | Suggested canonical value |")
    lines.append("| --- | --- |")
    for source, target in mapping_payload["review_candidates"].items():
        lines.append(f"| `{source}` | `{target}` |")
    lines.append("")
    lines.append("## Top Review Flags")
    lines.append("")
    lines.append("| Flag | Count |")
    lines.append("| --- | ---: |")
    for flag, count in flag_counts.most_common(20):
        lines.append(f"| `{flag}` | {count} |")
    lines.append("")
    lines.append("## Dedupe Behavior")
    lines.append("")
    lines.append("- Exact duplicate rows are reduced to one kept row.")
    lines.append("- Duplicate rows with the same `kvk_number` are ranked by non-empty field count, then by source row number.")
    lines.append("- Complementary non-conflicting values are merged into the kept row.")
    lines.append("- Conflicting non-empty values are not guessed. The kept row remains deterministic and the conflict is written to `cleanup_review.tsv`.")
    lines.append("")
    lines.append("## Duplicate Decisions")
    lines.append("")
    lines.append("| KVK | Source rows | Kept row | Decision | Conflict fields | Merged fields |")
    lines.append("| --- | --- | ---: | --- | --- | --- |")
    for decision in dedupe_decisions:
        lines.append(
            "| `{kvk}` | `{sources}` | {kept} | `{action}` | `{conflicts}` | `{merged}` |".format(
                kvk=decision["kvk_number"],
                sources=decision["source_row_numbers"],
                kept=decision["kept_source_row_number"],
                action=decision["decision"],
                conflicts=decision["conflict_fields"] or "-",
                merged=decision["merged_fields"] or "-",
            )
        )
    lines.append("")
    lines.append("## Assumptions")
    lines.append("")
    lines.append("- The raw input file remains unchanged.")
    lines.append("- `email` input headers are aliased to `career_email` when needed.")
    lines.append("- Only obvious category spelling/format variants are merged automatically.")
    lines.append("- Abbreviation or plurality-based category candidates are left for manual review.")
    lines.append("- `industry_detail` remains an independent searchable field and is not treated as a strict child taxonomy.")
    lines.append("- Invalid URLs and emails are not repaired beyond safe normalization.")
    lines.append("")
    lines.append("## Future App Filter Recommendation")
    lines.append("")
    lines.append("- Text search across `display_name`, `legal_name`, `industry_detail`, `city`, and `province`.")
    lines.append("- Independent multi-select facet for `industry_category_clean`.")
    lines.append("- Searchable independent multi-select facet for `industry_detail`.")
    lines.append("- `city` and `province` filters with exact-value matching against cleaned values.")
    lines.append("- Toggles for `has website`, `has career URL`, and `has career email` based on clean columns.")
    lines.append("- Sortable results with stable pagination or virtualization.")
    lines.append("- Clear-filters control and visible active-filter chips.")
    lines.append("")
    lines.append("## Review Guidance")
    lines.append("")
    lines.append("- Inspect `cleanup_review.tsv` first for `duplicate_conflict`, `invalid_*`, and suspicious location/category flags.")
    lines.append("- Confirm the category mapping is still intentionally conservative before expanding it.")
    lines.append("- Review rows with merged duplicates to decide whether manual source corrections are needed before app generation.")

    with path.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
        handle.write("\n")


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    mapping_config_path = Path(args.mapping_config)
    cleaned_path = Path(args.cleaned)
    review_path = Path(args.review)
    summary_path = Path(args.summary)
    mapping_path = Path(args.mapping_output)

    mapping_payload = load_mapping_config(mapping_config_path)
    records, initial_review_events, _raw_header_name, header_notes = read_input(
        input_path,
        mapping_payload,
    )
    deduped_records, dedupe_stats, dedupe_decisions = dedupe_records(
        records,
        initial_review_events,
        mapping_payload,
    )
    review_events = collect_review_events(deduped_records, initial_review_events)

    write_cleaned_output(cleaned_path, deduped_records)
    write_review_output(review_path, review_events)
    mapping_output_payload = write_mapping_output(
        mapping_path,
        mapping_payload,
        mapping_config_path,
    )
    write_summary(
        summary_path,
        input_path,
        records,
        deduped_records,
        review_events,
        dedupe_stats,
        dedupe_decisions,
        mapping_output_payload,
        header_notes,
    )


if __name__ == "__main__":
    main()
