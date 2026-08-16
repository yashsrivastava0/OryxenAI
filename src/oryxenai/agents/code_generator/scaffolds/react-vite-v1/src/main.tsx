import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { AppRouter } from "./app/AppRouter";
import { ErrorBoundary } from "./app/ErrorBoundary";
import { installPreviewBridge } from "./app/PreviewBridge";
import "./design/global.css";

installPreviewBridge();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary>
      <AppRouter />
    </ErrorBoundary>
  </StrictMode>,
);
