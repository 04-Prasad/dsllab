/**
 * GraphGuard — Currency Conversion & Formatting Utility
 * ======================================================
 *
 * SOURCE CURRENCY CONFIRMATION
 * ----------------------------
 * The GraphGuard database stores monetary amounts in USD (US Dollars).
 *
 * Evidence:
 *  - Synthetic dataset (data/generated/transactions.csv): documented as
 *    "Transaction financial value ($)" in datahelp.md and amounts are
 *    generated in USD scale.
 *  - IBM AML dataset (data/LI-Small_Trans.csv): the Payment Currency /
 *    Receiving Currency columns contain "US Dollar" for all sampled rows.
 *  - ibm_adapter.py maps "Amount Paid" → internal "amount" field without
 *    any currency conversion, so stored amounts are USD originals.
 *
 * DISPLAY CURRENCY
 * ----------------
 * All monetary amounts in the UI are displayed in Indian Rupees (INR / ₹)
 * using a configured demonstration exchange rate.
 *
 * RATE NOTE
 * ---------
 * USD_TO_INR_RATE is a configurable demonstration rate. It is NOT a live
 * market rate. Adjust it here to reflect a current or required rate.
 * Do not present this as a real-time exchange rate to end users.
 */

// ── Exchange Rate Configuration ───────────────────────────────────────────────

/**
 * Demonstration USD → INR exchange rate.
 * Configured in one central location; referenced by all formatting helpers.
 * This is NOT a live rate — update to your required reference rate.
 */
export const USD_TO_INR_RATE: number = 85.0;

// ── Conversion ────────────────────────────────────────────────────────────────

/**
 * Convert a USD amount to INR using the configured demonstration rate.
 *
 * Guards against NaN, null, undefined, and non-finite inputs: all of those
 * return 0, which then displays as ₹0.00 rather than crashing the UI.
 *
 * @param usdAmount - Raw amount in USD as stored in the database
 * @returns Equivalent amount in INR
 */
export function usdToInr(usdAmount: number | null | undefined): number {
  if (usdAmount == null || !isFinite(usdAmount)) return 0;
  // Multiply with rounding to avoid floating-point drift on simple scale
  return Math.round(usdAmount * USD_TO_INR_RATE * 100) / 100;
}

// ── Formatting ────────────────────────────────────────────────────────────────

/**
 * Format an INR amount using the en-IN locale (Indian comma grouping).
 * Returns a string like "₹1,01,93,166.85".
 *
 * @param inrAmount - Amount already in INR
 * @returns Locale-formatted INR string
 */
function formatInr(inrAmount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(inrAmount);
}

/**
 * Convert a USD amount to INR and return a fully formatted display string.
 *
 * This is the main entry point for the hover tooltip and edge labels.
 * Input is treated as USD; output is formatted as INR with Indian grouping.
 *
 * Examples (at USD_TO_INR_RATE = 85):
 *   formatUsdAsInr(119919.61)  → "₹1,01,93,166.85"
 *   formatUsdAsInr(0)          → "₹0.00"
 *   formatUsdAsInr(null)       → "₹0.00"
 *   formatUsdAsInr(NaN)        → "₹0.00"
 *
 * @param usdAmount - Raw amount in USD (as stored in the database)
 * @returns Formatted INR string
 */
export function formatUsdAsInr(usdAmount: number | null | undefined): string {
  const inr = usdToInr(usdAmount);
  return formatInr(inr);
}

/**
 * Compact INR formatter for space-constrained displays (e.g. NodeDetailsDrawer).
 * Abbreviates large values: ≥1 Cr → "₹X.XCr", ≥1 L → "₹X.XL", ≥1000 → "₹X.XK".
 *
 * @param usdAmount - Raw amount in USD (as stored in the database)
 * @returns Compact formatted INR string
 */
export function formatUsdAsInrCompact(usdAmount: number | null | undefined): string {
  const inr = usdToInr(usdAmount);
  if (inr >= 1_00_00_000) {
    // ≥ 1 Crore
    return `₹${(inr / 1_00_00_000).toFixed(2)}Cr`;
  }
  if (inr >= 1_00_000) {
    // ≥ 1 Lakh
    return `₹${(inr / 1_00_000).toFixed(2)}L`;
  }
  if (inr >= 1_000) {
    // ≥ 1 Thousand
    return `₹${(inr / 1_000).toFixed(1)}K`;
  }
  return formatInr(inr);
}

