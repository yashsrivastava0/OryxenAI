import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import ts from "typescript";

const projectRoot = process.cwd();
const sourceRoot = path.resolve(projectRoot, "src");
const sourceFiles = [];
const sourceTrees = new Map();
const diagnostics = [];

function collect(directory) {
  if (!fs.existsSync(directory)) return;
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) collect(absolute);
    else if (/\.(?:ts|tsx)$/.test(entry.name)) sourceFiles.push(absolute);
  }
}

function relative(fileName) {
  return path.relative(projectRoot, fileName).split(path.sep).join("/");
}

function report(fileName, node, message) {
  const source = sourceTrees.get(fileName);
  const position = source && node?.getStart
    ? `:${source.getLineAndCharacterOfPosition(node.getStart(source)).line + 1}`
    : "";
  diagnostics.push(`${relative(fileName)}${position}: ${message}`);
}

function unwrap(node) {
  let current = node;
  while (
    current &&
    (ts.isAsExpression(current) ||
      ts.isTypeAssertionExpression(current) ||
      ts.isSatisfiesExpression(current) ||
      ts.isParenthesizedExpression(current) ||
      ts.isNonNullExpression(current))
  ) {
    current = current.expression;
  }
  return current;
}

function propertyName(node) {
  if (!node) return "";
  if (ts.isIdentifier(node) || ts.isStringLiteral(node) || ts.isNumericLiteral(node)) {
    return node.text;
  }
  return "";
}

function literalValue(node) {
  const value = unwrap(node);
  if (!value) return undefined;
  if (ts.isStringLiteral(value) || ts.isNoSubstitutionTemplateLiteral(value)) return value.text;
  if (ts.isNumericLiteral(value)) return Number(value.text);
  if (value.kind === ts.SyntaxKind.TrueKeyword) return true;
  if (value.kind === ts.SyntaxKind.FalseKeyword) return false;
  if (value.kind === ts.SyntaxKind.NullKeyword) return null;
  if (ts.isArrayLiteralExpression(value)) {
    return value.elements.map((element) => literalValue(element));
  }
  if (ts.isObjectLiteralExpression(value)) {
    const result = {};
    for (const member of value.properties) {
      if (!ts.isPropertyAssignment(member)) continue;
      const name = propertyName(member.name);
      if (name) result[name] = literalValue(member.initializer);
    }
    return result;
  }
  return undefined;
}

function exportedInitializer(source, exportName) {
  if (!source) return undefined;
  for (const statement of source.statements) {
    if (!ts.isVariableStatement(statement)) continue;
    for (const declaration of statement.declarationList.declarations) {
      if (ts.isIdentifier(declaration.name) && declaration.name.text === exportName) {
        return declaration.initializer;
      }
    }
  }
  return undefined;
}

function exportedValue(fileName, exportName) {
  return literalValue(exportedInitializer(sourceTrees.get(fileName), exportName));
}

function localTarget(importer, moduleName) {
  let base;
  if (moduleName.startsWith("@/")) base = path.join(sourceRoot, moduleName.slice(2));
  else if (moduleName.startsWith(".")) base = path.resolve(path.dirname(importer), moduleName);
  else if (moduleName.startsWith("/")) base = path.resolve(projectRoot, moduleName.slice(1));
  else return null;
  const candidates = [
    base,
    `${base}.ts`,
    `${base}.tsx`,
    `${base}.js`,
    `${base}.jsx`,
    `${base}.css`,
    `${base}.json`,
    path.join(base, "index.ts"),
    path.join(base, "index.tsx"),
  ];
  for (const candidate of candidates) {
    if (!fs.existsSync(candidate) || !fs.statSync(candidate).isFile()) continue;
    const resolved = path.resolve(candidate);
    if (resolved === sourceRoot || !resolved.startsWith(`${sourceRoot}${path.sep}`)) return null;
    return resolved;
  }
  return null;
}

function moduleName(importDeclaration) {
  return ts.isStringLiteral(importDeclaration.moduleSpecifier)
    ? importDeclaration.moduleSpecifier.text
    : "";
}

function exportNames(source) {
  const result = new Set();
  if (!source) return result;
  for (const statement of source.statements) {
    const exported = statement.modifiers?.some(
      (modifier) => modifier.kind === ts.SyntaxKind.ExportKeyword,
    );
    const defaulted = statement.modifiers?.some(
      (modifier) => modifier.kind === ts.SyntaxKind.DefaultKeyword,
    );
    if (defaulted) result.add("default");
    if (exported && ts.isVariableStatement(statement)) {
      for (const declaration of statement.declarationList.declarations) {
        if (ts.isIdentifier(declaration.name)) result.add(declaration.name.text);
      }
    }
    if (exported && (ts.isFunctionDeclaration(statement) || ts.isClassDeclaration(statement))) {
      if (statement.name) result.add(statement.name.text);
    }
    if (
      exported &&
      (ts.isInterfaceDeclaration(statement) ||
        ts.isTypeAliasDeclaration(statement) ||
        ts.isEnumDeclaration(statement) ||
        ts.isModuleDeclaration(statement)) &&
      statement.name
    ) {
      result.add(statement.name.text);
    }
    if (ts.isExportDeclaration(statement) && statement.exportClause) {
      if (ts.isNamedExports(statement.exportClause)) {
        for (const element of statement.exportClause.elements) {
          result.add((element.name || element.propertyName).text);
        }
      }
    }
    if (ts.isExportAssignment(statement) && !statement.isExportEquals) result.add("default");
  }
  return result;
}

function jsxTagName(node) {
  const tag = ts.isJsxElement(node) ? node.openingElement.tagName : node.tagName;
  if (!tag) return "";
  if (ts.isIdentifier(tag)) return tag.text;
  if (ts.isPropertyAccessExpression(tag)) {
    return `${ts.isIdentifier(tag.expression) ? tag.expression.text : ""}.${tag.name.text}`;
  }
  return "";
}

function jsxAttributes(node) {
  const attributes = new Map();
  const attributeList = ts.isJsxElement(node) ? node.openingElement.attributes : node.attributes;
  for (const attribute of attributeList.properties) {
    if (!ts.isJsxAttribute(attribute)) continue;
    const name = attribute.name.text;
    const value = attribute.initializer && literalValue(attribute.initializer);
    attributes.set(name, value);
  }
  return attributes;
}

function jsxNodes(source) {
  const values = [];
  function visit(node) {
    if (ts.isJsxElement(node) || ts.isJsxSelfClosingElement(node)) values.push(node);
    ts.forEachChild(node, visit);
  }
  visit(source);
  return values;
}

function callNodes(source) {
  const values = [];
  function visit(node) {
    if (ts.isCallExpression(node)) values.push(node);
    ts.forEachChild(node, visit);
  }
  visit(source);
  return values;
}

function allStringLiterals(source) {
  const values = new Set();
  function visit(node) {
    if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) values.add(node.text);
    ts.forEachChild(node, visit);
  }
  visit(source);
  return values;
}

function importedNames(source, expectedModule) {
  const names = new Set();
  let found = false;
  for (const statement of source?.statements || []) {
    if (!ts.isImportDeclaration(statement) || moduleName(statement) !== expectedModule) continue;
    found = true;
    const bindings = statement.importClause?.namedBindings;
    if (!bindings || !ts.isNamedImports(bindings)) continue;
    for (const element of bindings.elements) names.add(element.propertyName?.text || element.name.text);
  }
  return { found, names };
}

function readRoutes() {
  const registryFile = path.join(sourceRoot, "generated", "route-registry.ts");
  const registry = sourceTrees.get(registryFile);
  if (!registry) return [];
  const imports = new Map();
  for (const statement of registry.statements) {
    if (!ts.isImportDeclaration(statement)) continue;
    const module = moduleName(statement);
    const target = localTarget(registryFile, module);
    const defaultName = statement.importClause?.name?.text;
    if (defaultName && target) imports.set(defaultName, target);
  }
  const initializer = exportedInitializer(registry, "ROUTES");
  const routes = literalValue(initializer);
  if (!Array.isArray(routes)) return [];
  const arrayNode = unwrap(initializer);
  if (!ts.isArrayLiteralExpression(arrayNode)) return [];
  return routes.map((route, index) => {
    const objectNode = unwrap(arrayNode.elements[index]);
    let componentName = "";
    if (ts.isObjectLiteralExpression(objectNode)) {
      for (const member of objectNode.properties) {
        if (!ts.isPropertyAssignment(member) || propertyName(member.name) !== "component") continue;
        const component = unwrap(member.initializer);
        if (ts.isIdentifier(component)) componentName = component.text;
      }
    }
    return {
      routeId: String(route?.routeId || ""),
      path: String(route?.path || ""),
      fileName: imports.get(componentName) || "",
    };
  });
}

function routeSections() {
  const fileName = path.join(sourceRoot, "generated", "content-manifest.ts");
  const value = exportedValue(fileName, "CONTENT_MANIFEST");
  const result = new Map();
  for (const route of value?.public_content || []) {
    if (!route || typeof route.route_id !== "string") continue;
    const sections = Array.isArray(route.sections)
      ? route.sections.map((section) => String(section?.section_id || "")).filter(Boolean)
      : [];
    result.set(route.route_id, sections);
  }
  return result;
}

function routeScopedFiles(routeFile) {
  if (!routeFile) return [];
  const directory = path.dirname(routeFile);
  return [...sourceTrees.keys()].filter(
    (fileName) => fileName === routeFile || fileName.startsWith(`${directory}${path.sep}`),
  );
}

function sectionRenderPositions(routeSource, sectionIds, files) {
  const anchors = new Map();
  for (const fileName of files) {
    const source = sourceTrees.get(fileName);
    for (const node of jsxNodes(source)) {
      const sectionId = jsxAttributes(node).get("data-content-id");
      if (typeof sectionId !== "string" || !sectionIds.includes(sectionId)) continue;
      const entries = anchors.get(sectionId) || [];
      entries.push({ fileName, node, source });
      anchors.set(sectionId, entries);
    }
  }
  const importedNamesByFile = new Map();
  for (const statement of routeSource.statements) {
    if (!ts.isImportDeclaration(statement)) continue;
    const target = localTarget(routeSource.fileName, moduleName(statement));
    if (!target || target === routeSource.fileName) continue;
    const names = importedNamesByFile.get(target) || new Set();
    if (statement.importClause?.name) names.add(statement.importClause.name.text);
    const bindings = statement.importClause?.namedBindings;
    if (bindings && ts.isNamedImports(bindings)) {
      for (const element of bindings.elements) names.add(element.name.text);
    }
    importedNamesByFile.set(target, names);
  }
  const routeJsx = jsxNodes(routeSource);
  return sectionIds.map((sectionId) => {
    const entries = anchors.get(sectionId) || [];
    const direct = entries.find((entry) => entry.fileName === routeSource.fileName);
    if (direct) return direct.node.getStart(routeSource);
    const names = new Set();
    for (const entry of entries) {
      for (const name of importedNamesByFile.get(entry.fileName) || []) names.add(name);
    }
    const rendered = routeJsx.find((node) => names.has(jsxTagName(node)));
    return rendered ? rendered.getStart(routeSource) : -1;
  });
}

function routeContractData(routes) {
  const contentFile = path.join(sourceRoot, "content", "generated-content.ts");
  const content = exportedValue(contentFile, "CONTENT_INDEX");
  const contentByRoute = new Map();
  const routeIds = routes
    .map((route) => String(route.routeId || ""))
    .filter(Boolean)
    .sort((left, right) => right.length - left.length);
  for (const entry of Array.isArray(content) ? content : []) {
    if (!entry || typeof entry.content_id !== "string") continue;
    const routeId = routeIds.find((candidate) => entry.content_id.startsWith(`content:${candidate}:`));
    if (!routeId) continue;
    const values = contentByRoute.get(routeId) || [];
    values.push(entry.content_id);
    contentByRoute.set(routeId, values);
  }
  const interactionFile = path.join(sourceRoot, "generated", "interaction-map.ts");
  const interactions = exportedValue(interactionFile, "INTERACTION_MAP");
  const interactionsByRoute = new Map();
  for (const interaction of interactions?.interactions || []) {
    if (!interaction || typeof interaction.route_id !== "string") continue;
    const values = interactionsByRoute.get(interaction.route_id) || [];
    values.push(interaction);
    interactionsByRoute.set(interaction.route_id, values);
  }
  return { contentByRoute, interactionsByRoute };
}

function auditLocalImports() {
  for (const [fileName, source] of sourceTrees) {
    for (const statement of source.statements) {
      if (!ts.isImportDeclaration(statement)) continue;
      const module = moduleName(statement);
      if (!module.startsWith(".") && !module.startsWith("@/") && !module.startsWith("/")) continue;
      const target = localTarget(fileName, module);
      if (!target) {
        report(fileName, statement, `local import does not resolve: ${module}`);
        continue;
      }
      const targetSource = sourceTrees.get(target);
      if (!targetSource || !statement.importClause) continue;
      const exports = exportNames(targetSource);
      const clause = statement.importClause;
      if (clause.name && !exports.has("default")) report(fileName, clause.name, `local module has no default export: ${module}`);
      if (clause.namedBindings && ts.isNamedImports(clause.namedBindings)) {
        for (const element of clause.namedBindings.elements) {
          const imported = element.propertyName?.text || element.name.text;
          if (!exports.has(imported)) report(fileName, element, `local module does not export ${imported}: ${module}`);
        }
      }
    }
  }
}

function auditUnsafeCalls() {
  const forbidden = new Set(["fetch", "WebSocket", "EventSource", "XMLHttpRequest", "sendBeacon"]);
  for (const [fileName, source] of sourceTrees) {
    for (const call of callNodes(source)) {
      const expression = unwrap(call.expression);
      const name = ts.isIdentifier(expression)
        ? expression.text
        : ts.isPropertyAccessExpression(expression)
          ? expression.name.text
          : "";
      if (forbidden.has(name)) report(fileName, call, `runtime network API ${name} is forbidden`);
    }
    function visit(node) {
      if (ts.isNewExpression(node) && ts.isIdentifier(node.expression) && forbidden.has(node.expression.text)) {
        report(fileName, node, `runtime network API ${node.expression.text} is forbidden`);
      }
      ts.forEachChild(node, visit);
    }
    visit(source);
  }
}

function auditV4Routes() {
  const metaFile = path.join(sourceRoot, "generated", "contract-meta.ts");
  const meta = exportedValue(metaFile, "CONTRACT_META");
  if (meta?.pipeline_contract_version !== "code-generator-v4") return;
  const routes = readRoutes();
  const sectionsByRoute = routeSections();
  const { contentByRoute, interactionsByRoute } = routeContractData(routes);
  if (!routes.length) {
    report(metaFile, sourceTrees.get(metaFile), "V4 source audit found no generated routes");
    return;
  }
  for (const route of routes) {
    const routeSource = sourceTrees.get(route.fileName);
    if (!routeSource) {
      report(path.join(sourceRoot, "generated", "route-registry.ts"), undefined, `route ${route.routeId} has no resolvable source module`);
      continue;
    }
    const files = routeScopedFiles(route.fileName);
    const trees = files.map((fileName) => sourceTrees.get(fileName)).filter(Boolean);
    const jsx = trees.flatMap((tree) => jsxNodes(tree));
    const routeJsx = jsxNodes(routeSource);
    const routeImports = importedNames(routeSource, "../../components/generated/SharedSystems");
    if (!routeImports.found || !routeImports.names.has("RouteShell")) {
      report(route.fileName, routeSource, "V4 route must import RouteShell from the trusted SharedSystems module");
    }
    if (!routeJsx.some((node) => jsxTagName(node) === "RouteShell")) {
      report(route.fileName, routeSource, "V4 route must render the trusted RouteShell");
    }
    const h1Count = routeJsx.filter((node) => jsxTagName(node) === "h1").length;
    if (h1Count !== 1) report(route.fileName, routeSource, `V4 route must contain exactly one h1 (found ${h1Count})`);
    const routeIdLiterals = new Set(
      routeJsx.flatMap((node) => [...jsxAttributes(node).entries()])
        .filter(([name]) => name === "data-route-id" || name === "routeId")
        .map(([, value]) => value)
        .filter((value) => typeof value === "string"),
    );
    if (!routeIdLiterals.has(route.routeId)) report(route.fileName, routeSource, `route ID is not a literal JSX contract value: ${route.routeId}`);

    const sectionIds = sectionsByRoute.get(route.routeId) || [];
    for (const sectionId of sectionIds) {
      const contentAnchors = jsx.filter((node) => jsxAttributes(node).get("data-content-id") === sectionId);
      const domIds = jsx.filter((node) => jsxAttributes(node).get("id") === sectionId);
      if (contentAnchors.length !== 1) report(route.fileName, routeSource, `section ${sectionId} needs exactly one literal data-content-id anchor`);
      if (domIds.length !== 1) report(route.fileName, routeSource, `section ${sectionId} needs exactly one literal DOM id`);
    }
    const sectionPositions = sectionRenderPositions(routeSource, sectionIds, files);
    if (sectionPositions.some((position) => position < 0)) {
      report(route.fileName, routeSource, "V4 route does not render every approved section through its route composition");
    } else if (sectionPositions.some((position, index) => index > 0 && position <= sectionPositions[index - 1])) {
      report(route.fileName, routeSource, "V4 route section rendering order does not match the approved content order");
    }
    const ids = new Map();
    const interactionMarkers = new Map();
    for (const node of jsx) {
      const attributes = jsxAttributes(node);
      for (const [name, value] of attributes) {
        if (name !== "id" && name !== "data-interaction-id") continue;
        if (typeof value !== "string") continue;
        const target = name === "id" ? ids : interactionMarkers;
        target.set(value, (target.get(value) || 0) + 1);
      }
    }
    for (const [value, count] of ids) if (count > 1) report(route.fileName, routeSource, `duplicate DOM id: ${value}`);
    for (const [value, count] of interactionMarkers) if (count > 1) report(route.fileName, routeSource, `duplicate interaction marker: ${value}`);

    const contentCalls = new Set();
    const contentFile = path.join(sourceRoot, "content", "generated-content.ts");
    const trustedContentNames = new Set();
    for (const fileName of files) {
      const source = sourceTrees.get(fileName);
      for (const statement of source?.statements || []) {
        if (!ts.isImportDeclaration(statement)) continue;
        if (localTarget(fileName, moduleName(statement)) !== contentFile) continue;
        const bindings = statement.importClause?.namedBindings;
        if (!bindings || !ts.isNamedImports(bindings)) continue;
        for (const element of bindings.elements) {
          if ((element.propertyName?.text || element.name.text) === "contentValue") {
            trustedContentNames.add(element.name.text);
          }
        }
      }
    }
    if (!trustedContentNames.size && (contentByRoute.get(route.routeId) || []).length) {
      report(route.fileName, routeSource, "V4 route must import contentValue from the trusted generated-content module");
    }
    for (const tree of trees) {
      for (const call of callNodes(tree)) {
        if (!ts.isIdentifier(call.expression) || !trustedContentNames.has(call.expression.text)) continue;
        const argument = call.arguments[0] && literalValue(call.arguments[0]);
        if (typeof argument === "string") contentCalls.add(argument);
      }
    }
    for (const contentId of contentByRoute.get(route.routeId) || []) {
      if (!contentCalls.has(contentId)) report(route.fileName, routeSource, `approved content key is not rendered through contentValue: ${contentId}`);
    }

    for (const interaction of interactionsByRoute.get(route.routeId) || []) {
      const marker = String(interaction.interaction_id || "");
      if (!interactionMarkers.has(marker)) {
        report(route.fileName, routeSource, `interaction marker is missing: ${marker}`);
        continue;
      }
      const markerNodes = jsx.filter((node) => jsxAttributes(node).get("data-interaction-id") === marker);
      const hasHandler = markerNodes.some((node) => {
        const attributes = jsxAttributes(node);
        return [...attributes.keys()].some((name) => name === "href" || name === "onClick" || name === "onKeyDown" || name === "onChange");
      });
      if (!hasHandler) report(route.fileName, routeSource, `interaction has no JSX handler or navigation outcome: ${marker}`);
    }

    const allLiterals = new Set(trees.flatMap((tree) => [...allStringLiterals(tree)]));
    for (const contentId of contentByRoute.get(route.routeId) || []) {
      if (!allLiterals.has(contentId)) report(route.fileName, routeSource, `content key is not present as an executable literal: ${contentId}`);
    }
  }
}

collect(sourceRoot);
for (const fileName of sourceFiles.sort()) {
  const source = fs.readFileSync(fileName, "utf8");
  const kind = fileName.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS;
  const tree = ts.createSourceFile(fileName, source, ts.ScriptTarget.Latest, true, kind);
  sourceTrees.set(fileName, tree);
  for (const diagnostic of tree.parseDiagnostics) {
    const position = diagnostic.start == null
      ? ""
      : `:${tree.getLineAndCharacterOfPosition(diagnostic.start).line + 1}`;
    diagnostics.push(`${relative(fileName)}${position}: ${ts.flattenDiagnosticMessageText(diagnostic.messageText, " ")}`);
  }
}

auditLocalImports();
auditUnsafeCalls();
auditV4Routes();

if (diagnostics.length) {
  console.error(diagnostics.join("\n"));
  process.exitCode = 1;
}
