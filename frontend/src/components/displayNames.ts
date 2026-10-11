let apiSkillNames: Record<string, string> = {};

export function setApiSkillNames(names: Record<string, string>) {
  apiSkillNames = names;
}

const LOCATION_NAMES: Record<string, string> = {
  bengaluru: "Bengaluru",
  hyderabad: "Hyderabad",
  pune: "Pune",
  remote_india: "Remote-India",
};

const LEVEL_NAMES: Record<string, string> = {
  junior: "Junior",
  mid: "Mid",
  senior: "Senior",
  lead: "Lead",
};

const WORK_MODE_NAMES: Record<string, string> = {
  onsite: "On-site",
  remote: "Remote",
  hybrid: "Hybrid",
};

export function skillName(id: string): string {
  return apiSkillNames[id] ?? id;
}

export function locationName(id: string): string {
  return LOCATION_NAMES[id] ?? id;
}

export function levelName(id: string): string {
  return LEVEL_NAMES[id] ?? id;
}

export function workModeName(id: string): string {
  return WORK_MODE_NAMES[id] ?? id;
}

export function displayValue(key: string, value: string | number): string {
  const s = String(value);
  if (key === "location") return locationName(s);
  if (key === "level") return levelName(s);
  if (key === "work_mode") return workModeName(s);
  if (key === "budget_lpa") return `₹${value}L`;
  if (key === "need_by_days") return `${value} days`;
  if (key === "min_years") return `${value}+ years`;
  if (key === "duration_months") return `${value} months`;
  return s;
}

export function displayRelaxedValue(kind: string, raw: string): string {
  if (kind === "location") return locationName(raw);
  return raw;
}

export function displayOptionText(text: string): string {
  return text
    .replace(/\bremote_india\b/g, "Remote-India")
    .replace(/\bbengaluru\b/g, "Bengaluru")
    .replace(/\bhyderabad\b/g, "Hyderabad")
    .replace(/\bpune\b/g, "Pune");
}
