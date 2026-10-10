import type { components } from "./types";

type AnalysisResult = components["schemas"]["AnalysisResult"];
type AnalyzeRequest = components["schemas"]["AnalyzeRequest"];
type DecisionRequest = components["schemas"]["DecisionRequest"];
type SkillScore = components["schemas"]["SkillScore"];
type Health = components["schemas"]["Health"];

// ── Typed error ───────────────────────────────────────────────────────────────

export interface FieldError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export class ApiError extends Error {
  readonly status: number;
  readonly fieldErrors: FieldError[] | undefined;

  constructor(status: number, message: string, fieldErrors?: FieldError[]) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

// FastAPI 422 body: { detail: [{loc, msg, type}] }
// FastAPI 400 body: { detail: string }
async function parseError(res: Response): Promise<ApiError> {
  let body: unknown;
  try {
    body = await res.json();
  } catch {
    return new ApiError(res.status, res.statusText);
  }

  if (
    typeof body === "object" &&
    body !== null &&
    "detail" in body
  ) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") {
      return new ApiError(res.status, detail);
    }
    if (Array.isArray(detail)) {
      const fieldErrors = detail as FieldError[];
      const message = fieldErrors.map((e) => `${e.loc.join(".")}: ${e.msg}`).join("; ");
      return new ApiError(res.status, message || "Validation error", fieldErrors);
    }
  }
  return new ApiError(res.status, res.statusText);
}

// ── Fetch helper ──────────────────────────────────────────────────────────────

async function request<T>(input: RequestInfo, init?: RequestInit): Promise<T> {
  const res = await fetch(input, init);
  if (!res.ok) throw await parseError(res);
  return res.json() as Promise<T>;
}

// ── Public API ────────────────────────────────────────────────────────────────

const BASE = "/api";

export async function analyze(
  body: AnalyzeRequest,
  stub = false,
): Promise<AnalysisResult> {
  const url = stub ? `${BASE}/analyze?stub=true` : `${BASE}/analyze`;
  return request<AnalysisResult>(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function getPersonSkills(personId: string): Promise<SkillScore[]> {
  return request<SkillScore[]>(`${BASE}/people/${encodeURIComponent(personId)}/skills`);
}

export async function postDecision(body: DecisionRequest): Promise<void> {
  // No retry: a double-submit would record two decisions in the append-only log.
  await request<unknown>(`${BASE}/decisions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function getHealth(): Promise<Health> {
  return request<Health>(`${BASE}/health`);
}
