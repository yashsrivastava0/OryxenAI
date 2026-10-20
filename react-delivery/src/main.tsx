import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { PortfolioApp } from "./PortfolioApp";
import type { Portfolio } from "./template-values";
import data from "../portfolio.json";

const portfolio = data as Portfolio;
const stylesheet = document.createElement("link");
stylesheet.rel = "stylesheet";
stylesheet.href = portfolio.stylesheet;
document.head.append(stylesheet);
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <PortfolioApp portfolio={portfolio} />
  </StrictMode>,
);
