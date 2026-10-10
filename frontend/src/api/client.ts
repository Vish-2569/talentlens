import type { components } from "./types";

type AnalysisResult = components["schemas"]["AnalysisResult"];
type AnalyzeRequest = components["schemas"]["AnalyzeRequest"];
type DecisionRequest = components["schemas"]["DecisionRequest"];
type SkillScore = components["schemas"]["SkillScore"];
type Health = components["schemas"]["Health"];

const BASE = "/api";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export async function analyze(
  body: AnalyzeRequest,
  stub = false,
): Promise<AnalysisResult> {
  const url = stub ? `${BASE}/analyze?stub=true` : `${BASE}/analyze`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return json<AnalysisResult>(res);
}

export async function getPersonSkills(personId: string): Promise<SkillScore[]> {
  const res = await fetch(`${BASE}/people/${encodeURIComponent(personId)}/skills`);
  return json<SkillScore[]>(res);
}

export async function postDecision(body: DecisionRequest): Promise<void> {
  const res = await fetch(`${BASE}/decisions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  await json<unknown>(res);
}

export async function getHealth(): Promise<Health> {
  const res = await fetch(`${BASE}/health`);
  return json<Health>(res);
}
