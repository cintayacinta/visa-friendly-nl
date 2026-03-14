export function parseTsv(input: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = "";

  for (let i = 0; i < input.length; i += 1) {
    const char = input[i];

    if (char === "\r") {
      continue;
    }

    if (char === "\t") {
      row.push(cell);
      cell = "";
      continue;
    }

    if (char === "\n") {
      row.push(cell);
      rows.push(row);
      row = [];
      cell = "";
      continue;
    }

    cell += char;
  }

  if (cell !== "" || row.length > 0) {
    row.push(cell);
    rows.push(row);
  }

  return rows;
}
