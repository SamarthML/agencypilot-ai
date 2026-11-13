import type { KpiUnit } from "@/lib/types";

const compactCurrency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  notation: "compact",
  maximumFractionDigits: 1,
});
const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2,
});
const compactNumber = new Intl.NumberFormat("en-US", {
  notation: "compact",
  maximumFractionDigits: 1,
});
const integer = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });

/** KPI value for a card: compact for big numbers, exact for small ones. */
export function formatKpiValue(value: number | null, unit: KpiUnit): string {
  if (value === null) return "—";
  switch (unit) {
    case "currency":
      return Math.abs(value) >= 10_000 ? compactCurrency.format(value) : currency.format(value);
    case "percent":
      return `${value.toFixed(2)}%`;
    case "ratio":
      return `${value.toFixed(2)}×`;
    case "count":
      return Math.abs(value) >= 10_000 ? compactNumber.format(value) : integer.format(value);
  }
}

export function formatCurrency(value: number): string {
  return currency.format(value);
}

export function formatCompactCurrency(value: number): string {
  return compactCurrency.format(value);
}

export function formatInteger(value: number): string {
  return integer.format(value);
}

export function formatCompactNumber(value: number): string {
  return compactNumber.format(value);
}

export function formatDeltaPct(delta: number | null): string {
  if (delta === null) return "—";
  return `${delta > 0 ? "+" : ""}${delta.toFixed(1)}%`;
}

/** "2026-11-12" -> "Nov 12" (dates are calendar days, so format in UTC). */
export function formatShortDate(isoDate: string): string {
  return new Date(`${isoDate}T00:00:00Z`).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

export function formatUsd(cost: number): string {
  if (cost === 0) return "$0";
  return cost < 0.01 ? `$${cost.toFixed(6)}` : currency.format(cost);
}
