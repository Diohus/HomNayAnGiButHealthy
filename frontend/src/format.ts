// Tránh độ chính xác giả: dữ liệu dinh dưỡng chỉ chính xác khoảng ±10–20%.
export function fmtKcal(v: number): string {
  return `${Math.round(v / 10) * 10}`;
}

export function fmtGrams(v: number): string {
  return `${Math.round(v)}`;
}

// Vi chất: 2 chữ số có nghĩa
export function fmtSig(v: number): string {
  if (v === 0) return "0";
  return Number(v.toPrecision(2)).toString();
}

export function fmtPct(p: number): string {
  return `${p > 0 ? "+" : ""}${Math.round(p * 100)}%`;
}

export function isoDay(d: Date): string {
  const z = new Date(d.getTime() - d.getTimezoneOffset() * 60000);
  return z.toISOString().slice(0, 10);
}

export function addDays(iso: string, n: number): string {
  const d = new Date(`${iso}T00:00:00`);
  d.setDate(d.getDate() + n);
  return isoDay(d);
}
