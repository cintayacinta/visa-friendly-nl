# Company Search App

This project now includes a Next.js + TypeScript + Tailwind app that consumes [output/cleaned_companies.tsv](/Users/yacintashafira/Documents/Vibe%20coding/VisaFriendly%202/output/cleaned_companies.tsv) directly. Search and filters use cleaned fields, while result cards show original display values where useful.

## App Features

- Full-text search across `display_name_clean`, `legal_name_clean`, `city_clean`, `province_clean`, `industry_category_clean`, and `industry_detail_clean`
- Multi-select filter for `industry_category_clean`
- Searchable multi-select filter for `industry_detail_clean`
- City and province filters
- Toggles for website, career URL, and career email availability
- Result count, sorting, graceful missing-value display, and pagination
- External website and career links opening in a new tab

## Project Structure

- [app](/Users/yacintashafira/Documents/Vibe%20coding/VisaFriendly%202/app): Next.js App Router entrypoints and global styles
- [components/company-search-app.tsx](/Users/yacintashafira/Documents/Vibe%20coding/VisaFriendly%202/components/company-search-app.tsx): client search UI
- [lib/load-companies.ts](/Users/yacintashafira/Documents/Vibe%20coding/VisaFriendly%202/lib/load-companies.ts): TSV loader
- [lib/company-filters.ts](/Users/yacintashafira/Documents/Vibe%20coding/VisaFriendly%202/lib/company-filters.ts): filtering, sorting, pagination helpers
- [types/company.ts](/Users/yacintashafira/Documents/Vibe%20coding/VisaFriendly%202/types/company.ts): app data types
- [output/cleaned_companies.tsv](/Users/yacintashafira/Documents/Vibe%20coding/VisaFriendly%202/output/cleaned_companies.tsv): cleaned dataset used by the app
- [scripts/clean_companies.py](/Users/yacintashafira/Documents/Vibe%20coding/VisaFriendly%202/scripts/clean_companies.py): cleanup pipeline
- [config/category_mapping.json](/Users/yacintashafira/Documents/Vibe%20coding/VisaFriendly%202/config/category_mapping.json): persistent mapping config for the cleanup pipeline

## Setup

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Data Workflow

1. Edit [config/category_mapping.json](/Users/yacintashafira/Documents/Vibe%20coding/VisaFriendly%202/config/category_mapping.json) when you want persistent category mapping changes.
2. Run `python3 scripts/clean_companies.py`.
3. Run `npm run dev`.
4. Inspect the regenerated files in [output](/Users/yacintashafira/Documents/Vibe%20coding/VisaFriendly%202/output) and verify the app behavior against the cleaned dataset.

The app does not rebuild the cleaning pipeline. It reads [output/cleaned_companies.tsv](/Users/yacintashafira/Documents/Vibe%20coding/VisaFriendly%202/output/cleaned_companies.tsv) as-is.
