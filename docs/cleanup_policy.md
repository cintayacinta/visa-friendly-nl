# Cleanup Policy

This pipeline is intentionally conservative. It keeps the raw TSV untouched and writes cleaned, reviewable outputs for app preparation.

## Safe Automatic Fixes

- Normalize missing values when a cell is blank or equals a known null-like token after trimming:
  - `""`, `n/a`, `na`, `null`, `none`, `nil`, `undefined`, `not available`, `not_applicable`
- Trim leading and trailing whitespace on all fields.
- Collapse repeated internal whitespace to a single space for text fields only:
  - `legal_name`, `display_name`, `city`, `province`, `industry_category`, `industry_detail`
- Preserve UTF-8 text exactly apart from the whitespace cleanup above.
- Normalize `career_email` by trimming and lowercasing when it passes validation.
- Normalize URLs by trimming, requiring `http` or `https`, and lowercasing only the scheme and host in the clean output.
- Keep raw columns unchanged in the cleaned output and store normalized values in separate audit or `*_clean` columns.
- Canonicalize only obvious category variants:
  - `Realestate` -> `RealEstate`
- Treat these category variants as review candidates rather than automatic merges:
  - `Beverages` -> `Beverage`
  - `Biotech` -> `Biotechnology`
  - `Telecom` -> `Telecommunications`
- Generate human-friendly display labels separately from canonical values where useful:
  - `RealEstate` -> `Real Estate`
  - `FinancialServices` -> `Financial Services`

## Uncertain Transformations That Are Flagged

- Rows with malformed TSV structure, missing required columns, or extra columns.
- Invalid emails and invalid URLs. Raw values are preserved, clean columns are left blank, and review flags are added.
- Duplicate `kvk_number` groups with conflicting non-empty values in the same field.
- City and province rows that look suspicious, including:
  - one of `city` or `province` missing while the other is present
  - punctuation such as `?`
  - multi-location text such as `/`
- Industry rows that look suspicious, including:
  - `industry_detail` present while `industry_category` is missing
  - category values not covered by the conservative mapping but that still look like formatting variants
  - category/detail values containing suspicious punctuation or placeholder text
- When duplicate rows contain complementary non-conflicting values and the group has no conflicting non-empty fields, the merged result is kept and the merge is logged.

## Assumptions Intentionally Not Made

- No enrichment from external sources.
- No inference of missing website, career URL, career email, city, province, category, or detail.
- No aggressive taxonomy merges such as:
  - `Finance` with `FinancialServices`
  - `Technology` with `Software`
  - `AI` with `Software`
  - `Services` with `Consulting`
- No assumption that `industry_detail` is a strict child of `industry_category`.
- No automatic title-casing or recasing of free-text company, city, or detail values.
- No automatic fixing of invalid URLs or emails beyond safe normalization.
- No silent dropping of ambiguous duplicate rows. Conflicts are retained in review outputs and complementary merging is disabled for any duplicate group that contains conflicts.
