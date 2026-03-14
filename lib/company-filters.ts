import type { CompanyRecord, SortKey } from "@/types/company";

export type CompanyFilters = {
  query: string;
  categories: string[];
  city: string;
  province: string;
  hasWebsite: boolean;
  hasCareerUrl: boolean;
  hasCareerEmail: boolean;
  sortKey: SortKey;
  sortDirection: "asc" | "desc";
};

export const PAGE_SIZE = 50;

const SEARCH_FIELDS: Array<keyof CompanyRecord> = [
  "display_name_clean",
  "legal_name_clean",
  "city_clean",
  "province_clean",
  "industry_category_clean",
  "industry_detail_clean",
];

export function buildSearchHaystack(record: CompanyRecord): string {
  return SEARCH_FIELDS.map((field) => record[field]).join(" ").toLowerCase();
}

export function filterCompanies(
  companies: CompanyRecord[],
  filters: CompanyFilters,
): CompanyRecord[] {
  const query = filters.query.trim().toLowerCase();

  return companies.filter((company) => {
    if (query && !buildSearchHaystack(company).includes(query)) {
      return false;
    }

    if (
      filters.categories.length > 0 &&
      !filters.categories.includes(company.industry_category_clean)
    ) {
      return false;
    }

    if (filters.city && company.city_clean !== filters.city) {
      return false;
    }

    if (filters.province && company.province_clean !== filters.province) {
      return false;
    }

    if (filters.hasWebsite && company.website_url_clean === "") {
      return false;
    }

    if (filters.hasCareerUrl && company.career_url_clean === "") {
      return false;
    }

    if (filters.hasCareerEmail && company.career_email_clean === "") {
      return false;
    }

    return true;
  });
}

export function sortCompanies(
  companies: CompanyRecord[],
  sortKey: SortKey,
  sortDirection: "asc" | "desc",
): CompanyRecord[] {
  const scoreCompanyOpportunity = (company: CompanyRecord): number => {
    let score = 0;

    if (company.career_url_clean) {
      score += 3;
    }

    if (company.career_email_clean) {
      score += 2;
    }

    if (company.website_url_clean) {
      score += 1;
    }

    if (company.city_clean && company.province_clean) {
      score += 1;
    }

    if (company.industry_category_clean) {
      score += 1;
    }

    return score;
  };

  return [...companies].sort((left, right) => {
    if (sortKey === "best_opportunities") {
      const leftScore = scoreCompanyOpportunity(left);
      const rightScore = scoreCompanyOpportunity(right);
      const scoreCompare =
        sortDirection === "asc" ? rightScore - leftScore : leftScore - rightScore;

      if (scoreCompare !== 0) {
        return scoreCompare;
      }

      return left.display_name_clean.localeCompare(right.display_name_clean, undefined, {
        sensitivity: "base",
      });
    }

    const compare = left.display_name_clean.localeCompare(right.display_name_clean, undefined, {
      sensitivity: "base",
    });

    return compare * (sortDirection === "asc" ? 1 : -1);
  });
}

export function uniqueSortedValues(
  companies: CompanyRecord[],
  selector: (company: CompanyRecord) => string,
): string[] {
  const values = new Set<string>();

  for (const company of companies) {
    const value = selector(company);
    if (value) {
      values.add(value);
    }
  }

  return [...values].sort((left, right) =>
    left.localeCompare(right, undefined, { sensitivity: "base" }),
  );
}
