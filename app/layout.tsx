import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Company Search",
  description: "Search and filter companies from cleaned_companies.tsv",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
