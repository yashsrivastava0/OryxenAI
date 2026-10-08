"""Rebuild fixed fictional demos; no database, provider, or startup generation.

uv run python scripts/prepare_showcase.py --seed-fixture
uv run python scripts/prepare_showcase.py --capture
Portraits are committed WebP assets, prepared once with the image tool.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import mimetypes
import runpy
import threading
import tomllib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader

from oryxenai.agents.code_generator.bundle import compose_document
from oryxenai.agents.code_generator.serving import preview_headers
from oryxenai.themes import get_theme

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "src/oryxenai/auth"
OUTPUT = AUTH / "showcase"


def prepare(*, seed: bool, capture: bool) -> None:
    config = tomllib.loads((ROOT / "config/showcase.toml").read_text())
    OUTPUT.mkdir(exist_ok=True)
    content_path = OUTPUT / "content.json"
    if seed:
        designer = runpy.run_path(str(ROOT / "tests/unit/themes/atlas_fixtures.py"))["designer"]
        content_path.write_text(json.dumps(designer(), indent=2), encoding="utf-8", newline="\n")
    base = json.loads(content_path.read_text(encoding="utf-8"))
    env = Environment(loader=FileSystemLoader(AUTH / "templates"), autoescape=True)
    manifest = {"presentation": config["presentation"], "samples": []}
    for sample in config["samples"]:
        content = json.loads(
            json.dumps(copy.deepcopy(base))
            .replace("Maya Kapoor", sample["profile"])
            .replace("Maya", sample["profile"].split()[0])
        )
        content["hero"]["location"] = "Bengaluru, India"
        theme = get_theme(sample["theme_id"])
        derived = theme.contract.derive(content)
        body = theme.contract.render_body(content, derived)  # type: ignore[attr-defined]
        soup = BeautifulSoup(compose_document(content, derived, body, "en", theme), "html.parser")
        assert soup.html is not None and soup.head is not None and soup.body is not None
        soup.html["data-demo"] = sample["id"]
        link = soup.new_tag("link", rel="stylesheet", href="./demo.css")
        soup.head.append(link)
        script = soup.new_tag("script", src="./ready.mjs", type="module")
        soup.head.append(script)
        cover = env.get_template("showcase_cover.html").render(
            sample=sample,
            content=content,
            monogram="".join(word[0] for word in sample["profile"].split()),
            work_id="practice" if sample["id"] == "nightshift" else "work",
        )
        soup.body.insert(0, BeautifulSoup(cover, "html.parser"))
        folder = OUTPUT / sample["id"]
        folder.mkdir(exist_ok=True)
        (folder / "index.html").write_text(str(soup), encoding="utf-8", newline="\n")
        (folder / "demo.css").write_bytes(
            (AUTH / "showcase-demo.css").read_text(encoding="utf-8").encode("utf-8")
        )
        (folder / "ready.mjs").write_bytes(
            (AUTH / "showcase-ready.mjs").read_text(encoding="utf-8").encode("utf-8")
        )
        for entry in theme.files.values():
            target = folder / entry.path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(entry.data)
        source_package = ROOT / "src/oryxenai/themes" / sample["theme_id"].replace("-", "_")
        for license_file in source_package.glob("LICENSE*.txt"):
            (folder / license_file.name).write_bytes(license_file.read_bytes())
        manifest["samples"].append({**sample, "files": {}})
    if capture:
        capture_posters(config["samples"])
    for entry in manifest["samples"]:
        folder = OUTPUT / entry["id"]
        entry["files"] = {
            file.relative_to(folder).as_posix(): hashlib.sha256(file.read_bytes()).hexdigest()
            for file in sorted(folder.rglob("*"))
            if file.is_file()
        }
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Prepared fictional showcase bundles.")


def capture_posters(samples: list[dict[str, str]]) -> None:
    from PIL import Image
    from playwright.sync_api import sync_playwright

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            path = (OUTPUT / urlsplit(self.path).path.lstrip("/")).resolve()
            if not path.is_relative_to(OUTPUT.resolve()) or not path.is_file():
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header(
                "Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            )
            for key, value in preview_headers(html=path.suffix == ".html", scripts=True).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(path.read_bytes())

        def log_message(self, *_args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch()
            except Exception:
                browser = playwright.chromium.launch(channel="chrome")
            page = browser.new_page(
                viewport={"width": 1100, "height": 740}, reduced_motion="reduce"
            )
            for sample in samples:
                page.goto(f"http://127.0.0.1:{server.server_port}/{sample['id']}/index.html")
                page.evaluate("document.fonts.ready")
                page.locator(".demo-profile img").evaluate("img => img.decode()")
                image = Image.open(io.BytesIO(page.locator(".demo-overview").screenshot()))
                folder = OUTPUT / sample["id"]
                image.convert("RGB").save(folder / "poster.webp", quality=85, method=6)
                image.thumbnail((400, 300))
                image.convert("RGB").save(folder / "thumb.webp", quality=82, method=6)
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-fixture", action="store_true")
    parser.add_argument("--capture", action="store_true")
    args = parser.parse_args()
    prepare(seed=args.seed_fixture, capture=args.capture)
