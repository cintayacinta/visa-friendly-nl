export type CompanyRecord = {
  source_row_number: string;
  duplicate_group_size: string;
  duplicate_source_rows: string;
  merged_from_source_rows: string;
  duplicate_conflict_fields: string;
  kvk_number: string;
  kvk_number_clean: string;
  legal_name: string;
  legal_name_clean: string;
  display_name: string;
  display_name_clean: string;
  website_url: string;
  career_url: string;
  career_email: string;
  city: string;
  province: string;
  industry_category: string;
  industry_detail: string;
  website_url_clean: string;
  career_url_clean: string;
  career_email_clean: string;
  city_clean: string;
  province_clean: string;
  industry_category_raw: string;
  industry_category_clean: string;
  industry_category_display: string;
  industry_detail_clean: string;
  review_flags: string;
  dedupe_action: string;
};

export type SortKey =
  | "display_name_clean"
  | "city_clean"
  | "province_clean"
  | "industry_category_clean";
