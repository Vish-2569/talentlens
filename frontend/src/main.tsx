import "./index.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { Gallery } from "./dev/Gallery";
import { AppProvider } from "./state/context";

const rootEl = document.getElementById("root");
if (!rootEl) throw new Error("Root element not found");

const showGallery = import.meta.env.DEV && new URLSearchParams(window.location.search).has("gallery");

createRoot(rootEl).render(
  <StrictMode>
    {showGallery ? (
      <Gallery />
    ) : (
      <AppProvider>
        <App />
      </AppProvider>
    )}
  </StrictMode>,
);
