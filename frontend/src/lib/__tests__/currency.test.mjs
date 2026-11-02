/**
 * GraphGuard — Tests for currency.ts & Hover Tooltip Formatting
 * =============================================================
 * Tests the currency conversion and formatting utility.
 *
 * Run with: npm test (or node --experimental-strip-types src/lib/__tests__/currency.test.mjs)
 *
 * Uses deterministic exchange rates — no external service calls.
 */

import assert from "node:assert/strict";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

// ── Import the module under test ──────────────────────────────────────────────
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const tsPath = path.resolve(__dirname, "../currency.ts");

let usdToInr, formatUsdAsInr, formatUsdAsInrCompact, USD_TO_INR_RATE;

const mod = await import(pathToFileURL(tsPath).href);
({ usdToInr, formatUsdAsInr, formatUsdAsInrCompact, USD_TO_INR_RATE } = mod);

// ── Helper ────────────────────────────────────────────────────────────────────
let passed = 0;
let failed = 0;

function test(label, fn) {
  try {
    fn();
    console.log(`  ✓ ${label}`);
    passed++;
  } catch (err) {
    console.error(`  ✗ ${label}`);
    console.error(`    ${err.message}`);
    failed++;
  }
}

// ── Test Suite ────────────────────────────────────────────────────────────────
console.log("\n── currency.ts & Tooltip Formatting Tests ───────────────────────");

// 1. Configured Exchange Rate Check
test("USD_TO_INR_RATE is configured as a positive demonstration rate (85.0)", () => {
  assert.equal(typeof USD_TO_INR_RATE, "number");
  assert.equal(USD_TO_INR_RATE, 85.0);
});

// 2. Exact User Example from Master Prompt
test("Converts illustrative example $119,919.61 to exactly ₹1,01,93,166.85 at rate 85", () => {
  const result = formatUsdAsInr(119919.61);
  // Normalizing non-breaking spaces if any from Intl formatting
  const normalized = result.replace(/\u00a0/g, " ");
  assert.equal(normalized, "₹1,01,93,166.85");
});

// 3. usdToInr mathematical correctness
test("usdToInr converts basic positive amount accurately without float drift", () => {
  const result = usdToInr(1000);
  assert.equal(result, 85000);
});

// 4. Zero amounts
test("Zero amount displays correctly as ₹0.00", () => {
  const result = formatUsdAsInr(0).replace(/\u00a0/g, " ");
  assert.equal(result, "₹0.00");
  assert.equal(usdToInr(0), 0);
});

// 5. Null, undefined, NaN, Infinity guards
test("Missing and invalid amounts safely default to ₹0.00 without crashing", () => {
  assert.equal(formatUsdAsInr(null).replace(/\u00a0/g, " "), "₹0.00");
  assert.equal(formatUsdAsInr(undefined).replace(/\u00a0/g, " "), "₹0.00");
  assert.equal(formatUsdAsInr(NaN).replace(/\u00a0/g, " "), "₹0.00");
  assert.equal(formatUsdAsInr(Infinity).replace(/\u00a0/g, " "), "₹0.00");
  assert.equal(usdToInr(null), 0);
  assert.equal(usdToInr(undefined), 0);
  assert.equal(usdToInr(NaN), 0);
  assert.equal(usdToInr(Infinity), 0);
});

// 6. Negative values
test("Handles negative values safely", () => {
  const inr = usdToInr(-100);
  assert.equal(inr, -8500);
  const formatted = formatUsdAsInr(-100).replace(/\u00a0/g, " ");
  assert.ok(formatted.includes("8,500.00"), `Expected 8,500.00 in ${formatted}`);
});

// 7. Indian comma grouping
test("Applies correct en-IN comma grouping for multiple lakhs and crores", () => {
  // USD 100,000 * 85 = INR 85,00,000 (85 Lakhs)
  const result85L = formatUsdAsInr(100000).replace(/\u00a0/g, " ");
  assert.equal(result85L, "₹85,00,000.00");

  // USD 1,000,000 * 85 = INR 8,50,00,000 (8.5 Crores)
  const result8_5Cr = formatUsdAsInr(1000000).replace(/\u00a0/g, " ");
  assert.equal(result8_5Cr, "₹8,50,00,000.00");
});

// 8. Compact INR formatting
test("formatUsdAsInrCompact formats thousands, lakhs, and crores", () => {
  // 100 USD = 8,500 INR -> 8.5K
  assert.equal(formatUsdAsInrCompact(100), "₹8.5K");
  // 2,000 USD = 1,70,000 INR -> 1.70L
  assert.equal(formatUsdAsInrCompact(2000), "₹1.70L");
  // 200,000 USD = 1,70,00,000 INR -> 1.70Cr
  assert.equal(formatUsdAsInrCompact(200000), "₹1.70Cr");
  // 0 USD
  assert.equal(formatUsdAsInrCompact(0).replace(/\u00a0/g, " "), "₹0.00");
  // null
  assert.equal(formatUsdAsInrCompact(null).replace(/\u00a0/g, " "), "₹0.00");
});

// 9. Simulation of Account Node Hover Tooltip
test("Account-node hover simulation preserves all non-monetary node fields", () => {
  const node = {
    id: "80609B4C0",
    risk_score: 66,
    risk_level: "HIGH",
    incoming_count: 3,
    outgoing_count: 0,
    incoming_total: 119919.61,
    outgoing_total: 0,
    role: "NORMAL",
  };

  // Rendering tooltip values
  const displayTotalReceived = formatUsdAsInr(node.incoming_total).replace(/\u00a0/g, " ");
  const displayTotalSent = formatUsdAsInr(node.outgoing_total).replace(/\u00a0/g, " ");
  const displayRiskScore = `${Math.round(node.risk_score)} / 100`;
  const displayTxCount = node.incoming_count + node.outgoing_count;
  const displayFanInOut = `${node.incoming_count} in / ${node.outgoing_count} out`;

  assert.equal(displayTotalReceived, "₹1,01,93,166.85");
  assert.equal(displayTotalSent, "₹0.00");
  assert.equal(displayRiskScore, "66 / 100");
  assert.equal(displayTxCount, 3);
  assert.equal(displayFanInOut, "3 in / 0 out");
  assert.equal(node.role, "NORMAL");
  assert.equal(node.risk_level, "HIGH");

  // Ensure underlying data is strictly unmutated
  assert.equal(node.incoming_total, 119919.61);
  assert.equal(node.outgoing_total, 0);
});

// 10. Repeated Hovering & No Double-Conversion Test
test("Repeated hover over the same and different nodes does not re-convert or mutate data", () => {
  const nodeA = { id: "A102", incoming_total: 332500.0, outgoing_total: 305000.0 };
  const nodeB = { id: "B201", incoming_total: 5000.0, outgoing_total: 0.0 };

  // Hover Node A (1st time)
  const a1_in = formatUsdAsInr(nodeA.incoming_total);
  const a1_out = formatUsdAsInr(nodeA.outgoing_total);

  // Hover Node B
  const b1_in = formatUsdAsInr(nodeB.incoming_total);
  const b1_out = formatUsdAsInr(nodeB.outgoing_total);

  // Hover Node A (2nd time)
  const a2_in = formatUsdAsInr(nodeA.incoming_total);
  const a2_out = formatUsdAsInr(nodeA.outgoing_total);

  // Hover Node A (3rd time)
  const a3_in = formatUsdAsInr(nodeA.incoming_total);
  const a3_out = formatUsdAsInr(nodeA.outgoing_total);

  assert.equal(a1_in, a2_in);
  assert.equal(a2_in, a3_in);
  assert.equal(a1_out, a2_out);
  assert.equal(a2_out, a3_out);

  // Underlying node object remains unaltered original USD numbers
  assert.equal(nodeA.incoming_total, 332500.0);
  assert.equal(nodeA.outgoing_total, 305000.0);
  assert.equal(nodeB.incoming_total, 5000.0);
  assert.equal(nodeB.outgoing_total, 0.0);
});

// ── Summary ───────────────────────────────────────────────────────────────────
console.log(`\n── Results: ${passed} passed, ${failed} failed ──────────────────────────────`);
if (failed > 0) {
  process.exit(1);
}
