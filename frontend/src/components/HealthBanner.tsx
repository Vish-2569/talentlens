import { useEffect, useState } from "react";
import { getHealth } from "../api/client";

export function HealthBanner() {
  const [down, setDown] = useState(false);

  useEffect(() => {
    getHealth().then(
      () => setDown(false),
      () => setDown(true),
    );
  }, []);

  if (!down) return null;

  return (
    <div
      role="alert"
      aria-live="assertive"
      className="bg-redline px-4 py-2 font-sans text-sm text-white"
    >
      Backend is unreachable. Start it with:{" "}
      <code className="font-mono">
        uvicorn backend.api.main:app --reload
      </code>
    </div>
  );
}
