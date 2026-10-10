import type { components } from "../api/types";
import analysisDemoRaw from "./analyze.demo.json";

// Validate the captured fixture against the generated types at compile time.
// If this fails, re-run: node scripts/capture-fixture.mjs
export const FIXTURE_ANALYSIS =
  analysisDemoRaw as unknown as components["schemas"]["AnalysisResult"];
