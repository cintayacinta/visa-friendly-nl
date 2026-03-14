"use client";

import { useEffect, useMemo, useState } from "react";

import {
  PAGE_SIZE,
  filterCompanies,
  sortCompanies,
  uniqueSortedValues,
  type CompanyFilters,
} from "@/lib/company-filters";
import type { CompanyRecord, SortKey } from "@/types/company";

type Props = {
  companies: CompanyRecord[];
};

const SORT_OPTIONS: Array<{ key: SortKey; label: string }> = [
  { key: "display_name_clean", label: "Display name" },
  { key: "city_clean", label: "City" },
  { key: "province_clean", label: "Province" },
  { key: "industry_category_clean", label: "Industry category" },
];

const INITIAL_FILTERS: CompanyFilters = {
  query: "",
  categories: [],
  detailQuery: "",
  details: [],
  city: "",
  province: "",
  hasWebsite: false,
  hasCareerUrl: false,
  hasCareerEmail: false,
  sortKey: "display_name_clean",
  sortDirection: "asc",
};

function useDebouncedValue<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(timeout);
  }, [value, delay]);

  return debounced;
}

function toggleValue(values: string[], value: string): string[] {
  return values.includes(value)
    ? values.filter((entry) => entry !== value)
    : [...values, value];
}

function formatFallback(value: string, fallback = "Not available"): string {
  return value || fallback;
}

function PageButton({
  active,
  children,
  onClick,
}: {
  active?: boolean;
  children: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      className={`rounded-full border px-3 py-1.5 text-sm transition ${
        active
          ? "border-fern bg-fern text-white"
          : "border-line bg-white text-ink hover:border-moss"
      }`}
      onClick={onClick}
      type="button"
    >
      {children}
    </button>
  );
}

export function CompanySearchApp({ companies }: Props) {
  const [filters, setFilters] = useState<CompanyFilters>(INITIAL_FILTERS);
  const [page, setPage] = useState(1);

  const debouncedQuery = useDebouncedValue(filters.query, 180);
  const debouncedDetailQuery = useDebouncedValue(filters.detailQuery, 120);

  const categoryOptions = useMemo(
    () => uniqueSortedValues(companies, (company) => company.industry_category_clean),
    [companies],
  );
  const detailOptions = useMemo(
    () => uniqueSortedValues(companies, (company) => company.industry_detail_clean),
    [companies],
  );
  const cityOptions = useMemo(
    () => uniqueSortedValues(companies, (company) => company.city_clean),
    [companies],
  );
  const provinceOptions = useMemo(
    () => uniqueSortedValues(companies, (company) => company.province_clean),
    [companies],
  );

  const filteredDetailOptions = useMemo(() => {
    const query = debouncedDetailQuery.trim().toLowerCase();
    if (!query) {
      return detailOptions;
    }

    return detailOptions.filter((detail) => detail.toLowerCase().includes(query));
  }, [debouncedDetailQuery, detailOptions]);

  const filteredCompanies = useMemo(() => {
    return filterCompanies(companies, {
      ...filters,
      query: debouncedQuery,
      detailQuery: debouncedDetailQuery,
    });
  }, [companies, debouncedDetailQuery, debouncedQuery, filters]);

  const sortedCompanies = useMemo(() => {
    return sortCompanies(filteredCompanies, filters.sortKey, filters.sortDirection);
  }, [filteredCompanies, filters.sortDirection, filters.sortKey]);

  const totalPages = Math.max(1, Math.ceil(sortedCompanies.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const paginatedCompanies = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE;
    return sortedCompanies.slice(start, start + PAGE_SIZE);
  }, [currentPage, sortedCompanies]);

  useEffect(() => {
    setPage(1);
  }, [
    debouncedQuery,
    debouncedDetailQuery,
    filters.categories,
    filters.city,
    filters.details,
    filters.hasCareerEmail,
    filters.hasCareerUrl,
    filters.hasWebsite,
    filters.province,
    filters.sortDirection,
    filters.sortKey,
  ]);

  const pageNumbers = useMemo(() => {
    const start = Math.max(1, currentPage - 2);
    const end = Math.min(totalPages, start + 4);
    return Array.from({ length: end - start + 1 }, (_, index) => start + index);
  }, [currentPage, totalPages]);

  return (
    <main className="min-h-screen px-4 py-8 md:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <section className="overflow-hidden rounded-[2rem] border border-line bg-white/90 shadow-panel">
          <div className="grid gap-6 px-6 py-8 md:grid-cols-[1.2fr_0.8fr] md:px-8">
            <div className="space-y-4">
              <p className="text-sm uppercase tracking-[0.22em] text-fern">VisaFriendly NL</p>
              <h1 className="max-w-3xl text-4xl leading-tight text-ink md:text-5xl">
                Find officially-recognized work visa sponsor companies in the Netherlands
              </h1>
              <p className="max-w-2xl text-sm text-slate-600 md:text-base">
                VisaFriendly NL is a personal project built to help you start your journey toward
                working and living in the heart of Europe. While I&apos;ve tried to compile the
                information carefully, the data may contain mistakes or become outdated. Please use
                your own discretion and always verify visa sponsorship and job opportunities with
                official sources and the companies themselves.
                <br />
                <br />
                If you spot an error or have feedback, feel free to email me at
                {" "}
                <a className="text-fern underline-offset-2 hover:underline" href="mailto:hello.lovecinta@gmail.com">
                  hello.lovecinta@gmail.com
                </a>
              </p>
            </div>
            <div className="flex min-h-[220px] items-center justify-center rounded-[1.5rem] border border-dashed border-line bg-mist p-5 text-center text-sm text-slate-500">
              Photo placeholder
            </div>
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[340px_minmax(0,1fr)]">
          <aside className="space-y-5 rounded-[1.75rem] border border-line bg-white/90 p-5 shadow-panel">
            <div className="flex items-center justify-between">
              <h2 className="text-xl text-ink">Filters</h2>
              <button
                className="rounded-full border border-line px-3 py-1.5 text-sm text-slate-600 transition hover:border-fern hover:text-fern"
                onClick={() => setFilters(INITIAL_FILTERS)}
                type="button"
              >
                Clear filters
              </button>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-ink" htmlFor="query">
                Full-text search
              </label>
              <input
                id="query"
                className="w-full rounded-2xl border border-line bg-mist px-4 py-3 outline-none transition focus:border-fern"
                onChange={(event) =>
                  setFilters((current) => ({ ...current, query: event.target.value }))
                }
                placeholder="Search names, city, category, detail..."
                value={filters.query}
              />
            </div>

            <div className="space-y-2">
              <p className="text-sm font-medium text-ink">Industry category</p>
              <div className="max-h-56 space-y-2 overflow-auto rounded-2xl border border-line bg-mist p-3">
                {categoryOptions.map((category) => (
                  <label className="flex items-start gap-3 text-sm text-slate-700" key={category}>
                    <input
                      checked={filters.categories.includes(category)}
                      className="mt-0.5 h-4 w-4 rounded border-line text-fern focus:ring-fern"
                      onChange={() =>
                        setFilters((current) => ({
                          ...current,
                          categories: toggleValue(current.categories, category),
                        }))
                      }
                      type="checkbox"
                    />
                    <span>{category}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-ink" htmlFor="detail-query">
                Industry detail
              </label>
              <input
                id="detail-query"
                className="w-full rounded-2xl border border-line bg-mist px-4 py-3 outline-none transition focus:border-fern"
                onChange={(event) =>
                  setFilters((current) => ({ ...current, detailQuery: event.target.value }))
                }
                placeholder="Search detail values..."
                value={filters.detailQuery}
              />
              <div className="max-h-64 space-y-2 overflow-auto rounded-2xl border border-line bg-mist p-3">
                {filteredDetailOptions.slice(0, 150).map((detail) => (
                  <label className="flex items-start gap-3 text-sm text-slate-700" key={detail}>
                    <input
                      checked={filters.details.includes(detail)}
                      className="mt-0.5 h-4 w-4 rounded border-line text-fern focus:ring-fern"
                      onChange={() =>
                        setFilters((current) => ({
                          ...current,
                          details: toggleValue(current.details, detail),
                        }))
                      }
                      type="checkbox"
                    />
                    <span>{detail}</span>
                  </label>
                ))}
                {filteredDetailOptions.length === 0 ? (
                  <p className="text-sm text-slate-500">No detail values match this search.</p>
                ) : null}
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
              <div className="space-y-2">
                <label className="text-sm font-medium text-ink" htmlFor="city">
                  City
                </label>
                <select
                  className="w-full rounded-2xl border border-line bg-mist px-4 py-3 outline-none transition focus:border-fern"
                  id="city"
                  onChange={(event) =>
                    setFilters((current) => ({ ...current, city: event.target.value }))
                  }
                  value={filters.city}
                >
                  <option value="">All cities</option>
                  {cityOptions.map((city) => (
                    <option key={city} value={city}>
                      {city}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-ink" htmlFor="province">
                  Province
                </label>
                <select
                  className="w-full rounded-2xl border border-line bg-mist px-4 py-3 outline-none transition focus:border-fern"
                  id="province"
                  onChange={(event) =>
                    setFilters((current) => ({ ...current, province: event.target.value }))
                  }
                  value={filters.province}
                >
                  <option value="">All provinces</option>
                  {provinceOptions.map((province) => (
                    <option key={province} value={province}>
                      {province}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="space-y-3 rounded-2xl border border-line bg-mist p-4">
              <p className="text-sm font-medium text-ink">Availability</p>
              {[
                ["hasWebsite", "Has website"],
                ["hasCareerUrl", "Has career URL"],
                ["hasCareerEmail", "Has career email"],
              ].map(([key, label]) => (
                <label className="flex items-center gap-3 text-sm text-slate-700" key={key}>
                  <input
                    checked={filters[key as keyof CompanyFilters] as boolean}
                    className="h-4 w-4 rounded border-line text-fern focus:ring-fern"
                    onChange={(event) =>
                      setFilters((current) => ({
                        ...current,
                        [key]: event.target.checked,
                      }))
                    }
                    type="checkbox"
                  />
                  <span>{label}</span>
                </label>
              ))}
            </div>
          </aside>

          <section className="space-y-5">
            <div className="flex flex-col gap-3 rounded-[1.75rem] border border-line bg-white/90 p-5 shadow-panel md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-sm uppercase tracking-[0.18em] text-slate-500">Results</p>
                <p className="mt-1 text-2xl text-ink">{sortedCompanies.length.toLocaleString()} companies</p>
              </div>
              <div className="flex flex-col gap-3 md:flex-row">
                <select
                  className="rounded-2xl border border-line bg-mist px-4 py-3 outline-none transition focus:border-fern"
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      sortKey: event.target.value as SortKey,
                    }))
                  }
                  value={filters.sortKey}
                >
                  {SORT_OPTIONS.map((option) => (
                    <option key={option.key} value={option.key}>
                      Sort by {option.label}
                    </option>
                  ))}
                </select>
                <select
                  className="rounded-2xl border border-line bg-mist px-4 py-3 outline-none transition focus:border-fern"
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      sortDirection: event.target.value as "asc" | "desc",
                    }))
                  }
                  value={filters.sortDirection}
                >
                  <option value="asc">Ascending</option>
                  <option value="desc">Descending</option>
                </select>
              </div>
            </div>

            <div className="space-y-4">
              {paginatedCompanies.map((company) => (
                <article
                  className="rounded-[1.6rem] border border-line bg-white/90 p-5 shadow-panel"
                  key={`${company.kvk_number}-${company.source_row_number}`}
                >
                  <div className="flex flex-col gap-5 lg:flex-row lg:justify-between">
                    <div className="space-y-3">
                      <div>
                        <h3 className="text-2xl text-ink">
                          {formatFallback(company.display_name || company.legal_name)}
                        </h3>
                        <p className="text-sm text-slate-500">
                          Legal name: {formatFallback(company.legal_name)}
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2 text-sm">
                        <span className="rounded-full bg-mist px-3 py-1.5 text-slate-700">
                          {formatFallback(company.industry_category_clean)}
                        </span>
                        <span className="rounded-full bg-[#fdf1eb] px-3 py-1.5 text-clay">
                          {formatFallback(company.industry_detail_clean)}
                        </span>
                        <span className="rounded-full bg-[#eef7f0] px-3 py-1.5 text-fern">
                          {formatFallback(company.province_clean)}
                        </span>
                      </div>
                    </div>

                    <div className="grid gap-3 text-sm text-slate-600 sm:grid-cols-2 lg:min-w-[360px]">
                      <div>
                        <dt className="font-medium text-ink">City</dt>
                        <dd>{formatFallback(company.city || company.city_clean)}</dd>
                      </div>
                      <div>
                        <dt className="font-medium text-ink">Province</dt>
                        <dd>{formatFallback(company.province || company.province_clean)}</dd>
                      </div>
                      <div>
                        <dt className="font-medium text-ink">KVK</dt>
                        <dd>{formatFallback(company.kvk_number)}</dd>
                      </div>
                    </div>
                  </div>

                  <div className="mt-5 grid gap-3 md:grid-cols-3">
                    <a
                      className={`rounded-2xl border px-4 py-3 text-sm transition ${
                        company.website_url_clean
                          ? "border-line bg-mist text-ink hover:border-fern hover:text-fern"
                          : "cursor-not-allowed border-line bg-slate-50 text-slate-400"
                      }`}
                      href={company.website_url_clean || undefined}
                      rel="noreferrer"
                      target="_blank"
                    >
                      <div className="font-medium">Website</div>
                      <div className="mt-1 break-all text-xs">
                        {formatFallback(company.website_url || company.website_url_clean)}
                      </div>
                    </a>
                    <a
                      className={`rounded-2xl border px-4 py-3 text-sm transition ${
                        company.career_url_clean
                          ? "border-line bg-mist text-ink hover:border-fern hover:text-fern"
                          : "cursor-not-allowed border-line bg-slate-50 text-slate-400"
                      }`}
                      href={company.career_url_clean || undefined}
                      rel="noreferrer"
                      target="_blank"
                    >
                      <div className="font-medium">Career page</div>
                      <div className="mt-1 break-all text-xs">
                        {formatFallback(company.career_url || company.career_url_clean)}
                      </div>
                    </a>
                    <div className="rounded-2xl border border-line bg-mist px-4 py-3 text-sm">
                      <div className="font-medium text-ink">Career email</div>
                      <div className="mt-1 break-all text-xs text-slate-600">
                        {formatFallback(company.career_email || company.career_email_clean)}
                      </div>
                    </div>
                  </div>
                </article>
              ))}
            </div>

            {sortedCompanies.length === 0 ? (
              <div className="rounded-[1.6rem] border border-dashed border-line bg-white/80 p-10 text-center text-slate-500 shadow-panel">
                No companies match the current search and filter combination.
              </div>
            ) : null}

            <div className="flex flex-col items-center justify-between gap-4 rounded-[1.6rem] border border-line bg-white/90 p-5 shadow-panel md:flex-row">
              <p className="text-sm text-slate-600">
                Showing {(currentPage - 1) * PAGE_SIZE + 1}-
                {Math.min(currentPage * PAGE_SIZE, sortedCompanies.length)} of{" "}
                {sortedCompanies.length.toLocaleString()}
              </p>
              <div className="flex flex-wrap items-center gap-2">
                <PageButton onClick={() => setPage((value) => Math.max(1, value - 1))}>
                  Previous
                </PageButton>
                {pageNumbers.map((pageNumber) => (
                  <PageButton
                    active={pageNumber === currentPage}
                    key={pageNumber}
                    onClick={() => setPage(pageNumber)}
                  >
                    {pageNumber}
                  </PageButton>
                ))}
                <PageButton onClick={() => setPage((value) => Math.min(totalPages, value + 1))}>
                  Next
                </PageButton>
              </div>
            </div>
          </section>
        </section>
      </div>
    </main>
  );
}
