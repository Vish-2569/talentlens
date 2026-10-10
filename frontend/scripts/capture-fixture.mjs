#!/usr/bin/env node
/**
 * Capture real API responses from the running backend and write them as
 * committed fixture files.  Never hand-edit the output files; re-run this
 * script after backend changes.
 *
 * Usage:  node scripts/capture-fixture.mjs
 * Requires the backend running on http://127.0.0.1:8000
 */

import { mkdir, writeFile } from "node:fs/promises";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(__dirname, "..", "src", "fixtures");
const PEOPLE_DIR = join(FIXTURES, "people");
const BASE = "http://127.0.0.1:8000";

const DEMO_SENTENCE =
  "Senior Full Stack Developer, Bengaluru, on-site, 5+ years, must know React, Node.js and Kubernetes, budget ₹28L, need in 30 days.";

async function get(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
  return res.json();
}

async function post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`POST ${path} → ${res.status}: ${text}`);
  }
  return res.json();
}

async function write(filePath, data) {
  await mkdir(dirname(filePath), { recursive: true });
  await writeFile(filePath, JSON.stringify(data, null, 2) + "\n", "utf8");
  console.log(`  wrote ${filePath.replace(join(__dirname, ".."), ".")}`);
}

async function main() {
  console.log("Capturing fixtures from", BASE);

  // 1. Analyse demo sentence
  console.log("\n1. POST /api/analyze …");
  const analysis = await post("/api/analyze", { text: DEMO_SENTENCE });
  await write(join(FIXTURES, "analyze.demo.json"), analysis);

  // 2. Extract person IDs from the response
  const personIds = new Set();

  // Ripple candidates
  for (const c of analysis.ripple?.candidates ?? []) {
    if (c.person_id) personIds.add(c.person_id);
  }
  // Internal candidates
  for (const c of analysis.options?.internal_candidates ?? []) {
    if (c.person_id) personIds.add(c.person_id);
  }
  // Contractor cards
  for (const c of analysis.options?.contractor_cards ?? []) {
    if (c.person_id) personIds.add(c.person_id);
  }

  // Always ensure we capture the four demo story people by display name
  // Fall back to explicit IDs if not found in the response
  const namesNeeded = ["Karthik", "Priya", "Rahul", "Arjun"];
  const allPeople = [
    ...(analysis.ripple?.candidates ?? []),
    ...(analysis.options?.internal_candidates ?? []),
    ...(analysis.options?.contractor_cards ?? []),
  ];
  for (const name of namesNeeded) {
    const found = allPeople.find((p) => p.display_name === name);
    if (found?.person_id) personIds.add(found.person_id);
  }

  console.log("\n2. GET /api/people/{id}/skills for:", [...personIds].join(", "));
  for (const id of personIds) {
    const skills = await get(`/api/people/${encodeURIComponent(id)}/skills`);
    // Use id as filename, replacing / with _ for safety
    const safeName = id.replace(/\//g, "_");
    await write(join(PEOPLE_DIR, `${safeName}.json`), skills);
  }

  console.log("\nDone. Re-run after any backend change.");
}

main().catch((err) => {
  console.error(err.message);
  process.exit(1);
});
