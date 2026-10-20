import { createRoot } from "react-dom/client";
import { PortfolioApp } from "../src/PortfolioApp";
import type { Portfolio } from "../src/template-values";

const portfolio = (await (
  await fetch("/fixture/portfolio.json")
).json()) as Portfolio;
const stylesheet = document.createElement("link");
stylesheet.rel = "stylesheet";
stylesheet.href = "/fixture/" + portfolio.stylesheet;
document.head.append(stylesheet);
createRoot(document.getElementById("root")!).render(
  <PortfolioApp portfolio={portfolio} />,
);
