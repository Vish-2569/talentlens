#!/usr/bin/env node
/**
 * Smoke test: hits the live backend with GET /health, POST /analyze,
 * and POST /decisions.  Prints scores, panel text, and token counts.
 *
 * Usage:  node scripts/smoke.mjs
 * Requires the backend running on http://127.0.0.1:8000
 */

const BASE = "http://127.0.0.1:8000";

const DEMO_SENTENCE =
  "Senior Full Stack Developer, Bengaluru, on-site, 5+ years, must know React, Node.js and Kubernetes, budget ₹28L, need in 30 days.";

async function get(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`GET ${path} → ${res.status}: ${text}`);
  }
  return res.json();
}

async function post(path, body, expectedStatus = 200) {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (expectedStatus && res.status !== expectedStatus) {
    const text = await res.text();
    throw new Error(
      `POST ${path} → ${res.status} (expected ${expectedStatus}): ${text}`,
    );
  }
  return { status: res.status, body: await res.json() };
}

function hr(label) {
  console.log(`\n${"─".repeat(60)}`);
  console.log(`  ${label}`);
  console.log(`${"─".repeat(60)}`);
}

async function main() {
  // 1. Health check
  hr("1. GET /api/health");
  const health = await get("/api/health");
  console.log("  ok:", health.ok, " cache:", health.cache_loaded, " llm:", health.llm_configured);
  console.log("  PASS ✓");

  // 2. Analyse the demo sentence
  hr("2. POST /api/analyze");
  const { status: aStatus, body: analysis } = await post(
    "/api/analyze",
    { text: DEMO_SENTENCE },
  );
  console.log("  HTTP", aStatus);
  console.log("  req_id:", analysis.parsed.req_id);

  // Print five-option scores
  console.log("\n  Five-option scores:");
  for (const opt of analysis.options.five) {
    console.log(
      `    ${opt.name.padEnd(15)} score=${opt.score ?? "add-on"}\tready=${opt.ready_by_p80_days}d\tcost=₹${opt.year_one_cost_lpa}L`,
    );
  }

  // Print mix scores
  console.log("\n  Mix scores:");
  for (const mix of analysis.options.mixes) {
    console.log(
      `    ${mix.name.padEnd(20)} score=${mix.score}\tcost=₹${mix.year_one_cost_lpa}L`,
    );
  }

  // Print panel text for mask 00000 (as-written) and the location+skill relaxed mask
  const mask00000 = analysis.redline.scenarios["00000"];
  console.log("\n  Panel text (00000 — as written):");
  console.log(`    "${mask00000.panel_text}"`);

  // location=bit0, skill=bit2 → "10100"
  const locSkillMask = "10100";
  const maskRelaxed = analysis.redline.scenarios[locSkillMask];
  if (maskRelaxed) {
    console.log(`\n  Panel text (${locSkillMask} — location+skill relaxed):`);
    console.log(`    "${maskRelaxed.panel_text}"`);
  }

  // Tokens
  console.log("\n  Tokens:");
  const t = analysis.tokens;
  console.log(
    `    calls=${t.calls}  in=${t.input_tokens}  out=${t.output_tokens}  cache_hit=${t.cache_hit}  est_cost=${t.est_cost}`,
  );

  // 3. Post a decision
  hr("3. POST /api/decisions");
  const topOptionId = mask00000.top_option_id;
  const decisionBody = {
    req_id: analysis.parsed.req_id,
    option_id: topOptionId,
    verb: "Approve",
    decided_by: "Smoke Test",
    reason: "Automated smoke test — verifying decision endpoint returns 201.",
    relaxed_mask: "00000",
  };
  console.log("  Body:", JSON.stringify(decisionBody, null, 2));

  const { status: dStatus, body: dBody } = await post(
    "/api/decisions",
    decisionBody,
    201,
  );
  console.log("  HTTP", dStatus);
  console.log("  Response:", JSON.stringify(dBody, null, 2));
  console.log("  PASS ✓");

  hr("ALL SMOKE TESTS PASSED");
}

main().catch((err) => {
  console.error("\nFAIL:", err.message);
  process.exit(1);
});
