import assert from "node:assert/strict";
import test from "node:test";
import { consumePrivateDestination, privateDestination, rememberPrivateDestination } from "../../src/oryxenai/auth/static/return-route.mjs";

test("private return destinations allow only Home, Guide, and workflow stages", () => {
  assert.equal(privateDestination("?screen=guide&stage=studio"), "/app?screen=guide");
  assert.equal(privateDestination("?stage=content"), "/app?stage=content");
  assert.equal(privateDestination("?screen=outside&stage=outside"), "/app");
});

test("return destination survives auth once and cannot become an open redirect", () => {
  const items = new Map();
  const browser = { sessionStorage: {
    getItem: (key) => items.get(key) ?? null,
    setItem: (key, value) => items.set(key, value),
    removeItem: (key) => items.delete(key),
  } };
  rememberPrivateDestination({ pathname: "/app", search: "?screen=home" }, browser);
  assert.equal(consumePrivateDestination(browser), "/app?screen=home");
  assert.equal(consumePrivateDestination(browser), "/app");
  browser.sessionStorage.setItem("oryxenai.private_return_route", "https://other.example/steal");
  assert.equal(consumePrivateDestination(browser), "/app");
});
