import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { adapters } from "../src/PortfolioApp";
import type { Portfolio } from "../src/template-values";

const portfolio = JSON.parse(
  readFileSync(process.argv[2], "utf8"),
) as Portfolio;
const Adapter = adapters[portfolio.theme_id as keyof typeof adapters];
process.stdout.write(
  renderToStaticMarkup(<Adapter c={portfolio.c} d={portfolio.d} />),
);
