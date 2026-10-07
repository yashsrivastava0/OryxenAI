"""Claret Marquee in a real browser, served with the production preview headers (CSP included).

The matrix covers the finished page in both colour schemes at phone/tablet/desktop widths,
text contrast, both scene drivers (native timeline and the JS scrubber), reveals, reduced
motion, no script, keyboard use, routing and the toggle/pause controls. Chromium only: the
verifier in production also runs Chromium; Firefox/WebKit are an optional local run.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from urllib.parse import urlparse

import pytest
from tests.browser.helpers import sync_playwright
from tests.unit.themes.atlas_fixtures import FIXTURES

from oryxenai.agents.code_generator.bundle import build_bundle
from oryxenai.agents.code_generator.serving import preview_headers
from oryxenai.themes import get_theme

THEME = get_theme("claret-marquee/v1")
ORIGIN = "http://preview.test"
NAMES = sorted(FIXTURES)
WIDTHS = [360, 768, 1280]
SCHEMES = ["dark", "light"]

CONTRAST_SCRIPT = """() => {
  const parse = (value) => {
    let m = value.match(/^rgba?\\(([^)]+)\\)/);
    if (m) { const p = m[1].split(/[ ,\\/]+/).filter(Boolean).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; }
    m = value.match(/^color\\(srgb ([^)]+)\\)/);
    if (m) { const p = m[1].split(/[ \\/]+/).filter(Boolean).map(Number); return [p[0] * 255, p[1] * 255, p[2] * 255, p.length > 3 ? p[3] : 1]; }
    return null;
  };
  const lum = ([r, g, b]) => { const f = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
  const over = (top, under) => { const a = top[3]; return [top[0] * a + under[0] * (1 - a), top[1] * a + under[1] * (1 - a), top[2] * a + under[2] * (1 - a), 1]; };
  const root = document.documentElement;
  const claret = [59, 15, 30, 1];
  const background = (node) => {
    // The top bar is transparent while it floats over the claret hero: that is its backdrop.
    if (node.closest('.topbar') && root.dataset.top === 'claret') return claret;
    const layers = [];
    for (let n = node; n; n = n.parentElement) {
      const c = parse(getComputedStyle(n).backgroundColor);
      if (c && c[3] > 0) { layers.push(c); if (c[3] >= 1) break; }
    }
    let base = [255, 255, 255, 1];
    for (const layer of layers.reverse()) base = over(layer, base);
    return base;
  };
  const failures = [];
  let checked = 0;
  const selector = 'h1,h2,h3,p,li,dt,dd,blockquote,a,strong,span,small';
  for (const node of document.querySelectorAll(selector)) {
    const own = Array.from(node.childNodes).some((child) => child.nodeType === 3 && child.textContent.trim());
    if (!own) continue;
    const box = node.getBoundingClientRect();
    if (box.width < 1 || box.height < 1 || box.bottom < 0 || box.right < 0) continue;
    const style = getComputedStyle(node);
    if (style.visibility === 'hidden' || style.display === 'none' || Number(style.opacity) < 0.5) continue;
    const fg = parse(style.color);
    if (!fg) continue;
    const bg = background(node);
    const text = over(fg, bg);
    const a = lum(text), b = lum(bg);
    const ratio = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
    const size = parseFloat(style.fontSize);
    const bold = Number(style.fontWeight) >= 700;
    const large = size >= 24 || (bold && size >= 18.66);
    checked += 1;
    if (ratio < (large ? 3 : 4.5)) failures.push({ text: node.textContent.trim().slice(0, 40), cls: node.className, ratio: +ratio.toFixed(2), size });
  }
  return { checked, failures: failures.slice(0, 8) };
}"""


OVERFLOW_SCRIPT = """() => {
  // html clips horizontal overflow, so scrollWidth cannot see it: measure every element.
  const width = innerWidth;
  const bad = [];
  for (const node of document.querySelectorAll('main *, .topbar *, .site-footer *')) {
    if (node.closest('.hero-art, .ticker, .dust, .scrub, [hidden]')) continue;
    const box = node.getBoundingClientRect();
    if (box.width === 0 && box.height === 0) continue;
    if (box.right > width + 1 || box.left < -1) {
      bad.push(`${node.tagName.toLowerCase()}.${String(node.className).slice(0, 30)} ${Math.round(box.left)}..${Math.round(box.right)}`);
    }
  }
  return bad.slice(0, 6);
}"""


def _until(page: Any, predicate: str, timeout: float = 8.0) -> bool:
    """Poll with evaluate: wait_for_function evals a string, which the preview CSP forbids."""
    import time

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if page.evaluate(predicate):
            return True
        page.wait_for_timeout(80)
    return False


def _serve(bundles: dict[str, Any]) -> Any:
    def handle(route: Any) -> None:
        parts = urlparse(route.request.url).path.lstrip("/").split("/", 1)
        name = parts[0]
        path = parts[1] if len(parts) > 1 and parts[1] else "index.html"
        bundle = bundles.get(name)
        if bundle is None:
            route.fulfill(status=404, body="not found")
            return
        if path == "index.html":
            body = bundle.index_html.encode("utf-8")
            headers = {
                **preview_headers(html=True, scripts=True),
                "content-type": "text/html; charset=utf-8",
            }
        else:
            entry = THEME.file(path)
            if entry is None:
                route.fulfill(status=404, body="not found")
                return
            body = entry.data
            headers = {
                **preview_headers(html=False, etag=entry.sha256),
                "content-type": entry.media_type,
            }
        route.fulfill(status=200, body=body, headers=headers)

    return handle


@pytest.fixture(scope="module")
def bundles() -> dict[str, Any]:
    result = {}
    for name, build in FIXTURES.items():
        content = build()
        result[name] = build_bundle(
            content,
            THEME.contract.derive(content),
            THEME.contract.render_body(content),
            "en",
            THEME,
        )
    return result


@pytest.fixture(scope="module")
def browser(bundles: dict[str, Any]) -> Iterator[Any]:
    with sync_playwright() as playwright:
        try:
            instance = playwright.chromium.launch(headless=True)
        except Exception:
            try:
                instance = playwright.chromium.launch(headless=True, channel="chrome")
            except Exception:
                pytest.skip("no headless Chromium can be started on this machine")
        instance.bundles = bundles  # type: ignore[attr-defined]
        yield instance
        instance.close()


@contextmanager
def opened(
    browser: Any,
    name: str,
    *,
    width: int = 1280,
    height: int = 900,
    scheme: str = "dark",
    query: str = "",
    fragment: str = "",
    **options: Any,
) -> Iterator[tuple[Any, list[str]]]:
    context = browser.new_context(
        viewport={"width": width, "height": height}, color_scheme=scheme, **options
    )
    context.route(f"{ORIGIN}/**", _serve(browser.bundles))
    page = context.new_page()
    problems: list[str] = []
    page.on(
        "console",
        lambda m: (
            problems.append(f"console.{m.type}: {m.text}")
            if m.type in {"error", "warning"}
            else None
        ),
    )
    page.on("pageerror", lambda e: problems.append(f"pageerror: {e}"))
    page.on("requestfailed", lambda r: problems.append(f"requestfailed: {r.url}"))
    page.on(
        "response",
        lambda r: problems.append(f"http {r.status}: {r.url}") if r.status >= 400 else None,
    )
    url = f"{ORIGIN}/{name}/index.html{('?' + query) if query else ''}{('#' + fragment) if fragment else ''}"
    page.goto(url, wait_until="load")
    if options.get("java_script_enabled", True):
        page.evaluate("() => document.fonts.ready")
    page.wait_for_timeout(500)
    try:
        yield page, problems
    finally:
        context.close()


@pytest.mark.parametrize("scheme", SCHEMES)
@pytest.mark.parametrize("width", WIDTHS)
@pytest.mark.parametrize("name", NAMES)
def test_the_finished_page_is_clean_in_every_scheme_and_width(
    browser: Any, name: str, width: int, scheme: str
) -> None:
    with opened(browser, name, width=width, scheme=scheme) as (page, problems):
        state = page.evaluate(
            """() => ({
              motion: document.documentElement.dataset.motion,
              router: document.body.dataset.router,
              boot: document.documentElement.dataset.boot,
              api: typeof window.PortfolioTheme,
              audit: window.PortfolioTheme.audit(),
              overflow: document.documentElement.scrollWidth - window.innerWidth,
              fonts: Array.from(document.fonts).filter((f) => f.status === 'loaded').map((f) => f.family),
            })"""
        )
        assert problems == [], problems
        assert state["motion"] == "off" and state["router"] == "ready" and state["boot"] == "done"
        assert state["api"] == "object" and state["audit"] == []
        assert state["overflow"] <= 1, state
        assert {"Bodoni Moda", "Hanken Grotesk", "DM Mono"} <= set(state["fonts"])
        shift = page.evaluate(
            """() => new Promise((resolve) => {
              let total = 0;
              new PerformanceObserver((list) => {
                for (const entry of list.getEntries()) if (!entry.hadRecentInput) total += entry.value;
              }).observe({ type: 'layout-shift', buffered: true });
              setTimeout(() => resolve(total), 400);
            })"""
        )
        assert shift < 0.08, shift
        routes = page.evaluate(
            "() => Array.from(document.querySelectorAll('[data-view]')).map((v) => v.id)"
        )
        for route in routes:
            page.evaluate("(id) => window.PortfolioTheme.go(id)", route)
            visible = page.evaluate(
                "(id) => Array.from(document.querySelectorAll('[data-view]')).filter((v) => !v.hidden).map((v) => v.id)",
                route,
            )
            assert visible == [route]
            assert page.locator(f"#{route} h1").count() == 1
            assert page.evaluate(OVERFLOW_SCRIPT) == [], (name, route, width)
        assert problems == [], problems


@pytest.mark.parametrize("scheme", SCHEMES)
@pytest.mark.parametrize("width", [390, 1280])
@pytest.mark.parametrize("name", ["designer", "engineer", "chef", "stress"])
def test_text_meets_wcag_aa_contrast(browser: Any, name: str, width: int, scheme: str) -> None:
    with opened(browser, name, width=width, scheme=scheme) as (page, problems):
        for route in page.evaluate(
            "() => Array.from(document.querySelectorAll('[data-view]')).map((v) => v.id)"
        ):
            page.evaluate("(id) => window.PortfolioTheme.go(id)", route)
            page.wait_for_timeout(800)  # the top bar's colour transition is 0.4s
            result = page.evaluate(CONTRAST_SCRIPT)
            assert result["checked"] > 10, result
            assert result["failures"] == [], (route, result["failures"])
        assert problems == [], problems


@pytest.mark.parametrize("driver", ["native", "js"])
def test_the_hero_scene_follows_scroll_identically_under_both_drivers(
    browser: Any, driver: str
) -> None:
    with opened(browser, "designer", query=f"motion=1&intro=off&driver={driver}") as (
        page,
        problems,
    ):
        assert page.evaluate("() => document.documentElement.dataset.driver") == driver
        assert page.evaluate("() => document.documentElement.dataset.motion") == "full"
        for fraction in (0, 0.25, 0.5, 0.75, 1):
            page.evaluate(
                """(f) => {
                  const hero = document.querySelector('.hero');
                  const top = hero.getBoundingClientRect().top + scrollY;
                  window.scrollTo({ top: top + Math.max(1, hero.offsetHeight - innerHeight) * f, behavior: 'instant' });
                  return new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
                }""",
                fraction,
            )
            page.wait_for_timeout(160)
            scale = page.evaluate(
                "() => parseFloat(getComputedStyle(document.querySelector('.hero-ring')).scale)"
            )
            assert abs(scale - (1 + 4.2 * fraction)) < 0.06, (fraction, scale)
        assert problems == [], problems


def test_a_hero_too_tall_for_the_stage_flows_instead_of_clipping(browser: Any) -> None:
    with opened(browser, "stress", query="motion=1&intro=off") as (page, problems):
        flow = page.evaluate("() => document.querySelector('.hero').hasAttribute('data-flow')")
        position = page.evaluate(
            "() => getComputedStyle(document.querySelector('.hero-stage')).position"
        )
        assert flow and position == "relative", (flow, position)
        overflow = page.evaluate(
            "() => { const s = document.querySelector('.hero-stage'); return s.scrollHeight - s.clientHeight; }"
        )
        assert overflow <= 2
        assert problems == [], problems


def test_reveals_counters_ticker_and_controls_work_in_motion_mode(browser: Any) -> None:
    with opened(browser, "designer", query="motion=1&intro=off") as (page, problems):
        height = page.evaluate("() => document.documentElement.scrollHeight")
        for y in range(0, height, 400):
            page.evaluate("(y) => window.scrollTo({ top: y, behavior: 'instant' })", y)
            page.wait_for_timeout(90)
        assert _until(
            page,
            "() => document.querySelectorAll('#home .rv:not(.is-in),#home .rf:not(.is-in)').length === 0",
        )
        page.wait_for_timeout(1700)  # counters animate for 1.4s
        state = page.evaluate(
            """() => ({
              rv: document.querySelectorAll('#home .rv').length,
              rvIn: document.querySelectorAll('#home .rv.is-in').length,
              rf: document.querySelectorAll('#home .rf').length,
              rfIn: document.querySelectorAll('#home .rf.is-in').length,
              figures: Array.from(document.querySelectorAll('.figure-value')).map((n) => n.textContent),
              clones: document.querySelectorAll('.ticker-track [aria-hidden=true]').length,
              words: document.querySelectorAll('.thesis-statement .w').length,
              statement: document.querySelector('.thesis-statement').textContent,
              scrub: !!document.querySelector('.scrub'),
            })"""
        )
        assert state["rv"] > 10 and state["rvIn"] == state["rv"]
        assert state["rf"] > 2 and state["rfIn"] == state["rf"]
        assert state["figures"] == ["8+", "14", "-34%"]
        assert state["clones"] == 8 and state["words"] > 4 and state["scrub"]
        assert state["statement"] == "Clarity first, then craft — in that order."
        page.click(".tool-pause")
        assert page.evaluate("() => document.documentElement.hasAttribute('data-paused')")
        assert page.get_attribute(".tool-pause", "aria-pressed") == "true"
        before = page.evaluate("() => document.documentElement.dataset.theme || ''")
        page.click(".tool-theme")
        page.wait_for_timeout(900)
        after = page.evaluate("() => document.documentElement.dataset.theme")
        assert after in {"light", "dark"} and after != before
        assert problems == [], problems


def test_reduced_motion_gets_a_static_complete_page(browser: Any) -> None:
    with opened(browser, "designer", query="motion=1", reduced_motion="reduce") as (page, problems):
        state = page.evaluate(
            """() => ({
              motion: document.documentElement.dataset.motion,
              rv: document.querySelectorAll('.rv,.rf,.w').length,
              clones: document.querySelectorAll('.ticker-track [aria-hidden=true]').length,
              hero: document.querySelector('.hero').offsetHeight / innerHeight,
              pause: !!document.querySelector('.tool-pause'),
              scrub: !!document.querySelector('.scrub'),
              animations: document.getAnimations().filter((a) => a.playState === 'running').length,
            })"""
        )
        assert state["motion"] == "reduced"
        assert state["rv"] == 0 and state["clones"] == 0 and not state["scrub"]
        assert state["hero"] < 1.6 and state["animations"] == 0, state
        assert problems == [], problems


def test_the_page_is_complete_and_readable_without_script(browser: Any) -> None:
    with opened(browser, "designer", java_script_enabled=False) as (page, problems):
        assert page.evaluate("() => document.documentElement.classList.contains('js')") is False
        views = page.locator("article.route-view")
        assert views.count() == 5
        for index in range(views.count()):
            assert views.nth(index).is_visible()
            assert views.nth(index).locator("h1").count() == 1
        assert float(page.evaluate("() => getComputedStyle(document.body).opacity")) == 1
        assert page.locator(".hero-name").is_visible()
        assert problems == [], problems


def test_keyboard_users_can_skip_navigate_and_use_history(browser: Any) -> None:
    with opened(browser, "designer") as (page, problems):
        page.keyboard.press("Tab")
        assert "skip-link" in page.evaluate("() => document.activeElement.className")
        page.keyboard.press("Enter")
        assert page.evaluate("() => document.activeElement.id") == "main"
        page.click(".topnav a[href='#about']")
        page.wait_for_timeout(300)
        assert page.evaluate("() => !document.getElementById('about').hidden")
        assert page.evaluate("() => document.activeElement.tagName") == "H1"
        assert page.evaluate(
            "() => document.getElementById('route-announcer').textContent"
        ).startswith("About")
        page.go_back()
        page.wait_for_timeout(300)
        assert page.evaluate("() => !document.getElementById('home').hidden")
        page.go_forward()
        page.wait_for_timeout(300)
        assert page.evaluate("() => !document.getElementById('about').hidden")
        assert problems == [], problems


def test_deep_links_open_the_right_route_and_unknown_hashes_stay_on_home(browser: Any) -> None:
    with opened(browser, "designer", fragment="case-2") as (page, problems):
        assert page.evaluate("() => !document.getElementById('case-2').hidden")
        assert page.evaluate("() => document.title").startswith("Merchant onboarding")
        assert problems == [], problems
    with opened(browser, "designer", fragment="no-such-section") as (page, problems):
        assert page.evaluate("() => !document.getElementById('home').hidden")
        assert problems == [], problems


TOPBAR_SCRIPT = """() => {
  const box = (selector) => document.querySelector(selector).getBoundingClientRect();
  const cta = document.querySelector('.topnav-cta');
  const lines = document.createRange();
  lines.selectNodeContents(cta);
  return {
    brand: box('.brand-mark').right,
    navLeft: box('.topnav').left,
    navRight: box('.topnav').right,
    toolsLeft: box('.tools').left,
    toolsRight: box('.tools').right,
    ctaLines: lines.getClientRects().length,
    width: innerWidth,
  };
}"""


@pytest.mark.parametrize("width", [320, 360, 390, 430])
def test_the_phone_top_bar_stays_on_one_line_and_inside_the_screen(
    browser: Any, width: int
) -> None:
    for name in ("designer", "stress"):
        with opened(browser, name, width=width, height=740) as (page, problems):
            bar = page.evaluate(TOPBAR_SCRIPT)
            assert bar["ctaLines"] == 1, (name, bar)
            assert bar["brand"] <= bar["navLeft"] + 1, (name, bar)
            assert bar["navRight"] <= bar["toolsLeft"] + 1, (name, bar)
            assert bar["toolsRight"] <= width + 1, (name, bar)
            assert problems == [], problems


def test_the_phone_hero_name_fits_the_screen(browser: Any) -> None:
    for name in NAMES:
        with opened(browser, name, width=360, height=740) as (page, problems):
            right = page.evaluate(
                "() => { const n = document.querySelector('.hero-name'); const r = n.getBoundingClientRect(); return [r.right, innerWidth, n.scrollWidth - n.clientWidth]; }"
            )
            assert right[0] <= right[1] + 1 and right[2] <= 1, (name, right)
            assert problems == [], problems
