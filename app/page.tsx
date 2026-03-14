import { CompanySearchApp } from "@/components/company-search-app";
import { loadCompanies } from "@/lib/load-companies";

export default function HomePage() {
  const companies = loadCompanies();

  return <CompanySearchApp companies={companies} />;
}
