import { readFileSync } from "node:fs";
import { join } from "node:path";

import { parseTsv } from "@/lib/tsv";
import type { CompanyRecord } from "@/types/company";

const DATA_PATH = join(process.cwd(), "output", "cleaned_companies.tsv");

export function loadCompanies(): CompanyRecord[] {
  const raw = readFileSync(DATA_PATH, "utf-8");
  const rows = parseTsv(raw);

  if (rows.length < 2) {
    return [];
  }

  const [header, ...dataRows] = rows;

  return dataRows
    .filter((row) => row.some((value) => value !== ""))
    .map((row) => {
      const padded = [...row];
      while (padded.length < header.length) {
        padded.push("");
      }

      return header.reduce((record, columnName, index) => {
        record[columnName as keyof CompanyRecord] = padded[index] ?? "";
        return record;
      }, {} as CompanyRecord);
    });
}
