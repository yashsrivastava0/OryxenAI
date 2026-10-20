"""Deterministic theme parity, artifact projection, capability and storage gates."""

from __future__ import annotations

import io
import json
import shutil
import subprocess
from collections import Counter
from datetime import UTC, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from uuid import uuid4

import pytest

from oryxenai.delivery.contracts import DeliveryError, ShareSigner, safe_path, sha256
from oryxenai.delivery.project import SUPPORTED_THEMES, TEMPLATES, assemble_project
from oryxenai.jobs.policy import policy_for
from oryxenai.storage.artifacts import (
    ArtifactReference,
    ArtifactStorageError,
    MemoryArtifactStore,
    S3ArtifactStore,
)
from oryxenai.themes import get_theme
from tests.unit.agents.code_generator.helpers import minimal_content, sample_content
from tests.unit.themes.atlas_fixtures import designer, engineer, sparse_samples, stress

ROOT = Path(__file__).resolve().parents[2]


def long_content():
    content = stress()
    # Atlas v2's immutable fixed-copy gate accepts only single-digit stat
    # indices. Keep the largest source fixture eligible for Studio itself.
    content["atlas"]["experience"] = content["atlas"]["experience"][:9]
    return content


class Markup(HTMLParser):
    def __init__(self, value: str):
        super().__init__(convert_charrefs=True)
        self.tags: Counter[str] = Counter()
        self.links: list[str] = []
        self.fields: list[str] = []
        self.text: list[str] = []
        self.feed(value)

    def handle_starttag(self, tag, attrs):
        if tag == "link":  # React may emit image preload hints.
            return
        self.tags[tag] += 1
        values = dict(attrs)
        if tag == "a":
            self.links.append(values.get("href", ""))
        if "data-field" in values:
            self.fields.append(values["data-field"])

    def handle_data(self, data):
        self.text.append(data)


@pytest.mark.parametrize("theme_id", sorted(SUPPORTED_THEMES))
@pytest.mark.parametrize(
    "fixture", [minimal_content, designer, engineer, sparse_samples, long_content]
)
def test_native_react_markup_matches_pinned_host(theme_id, fixture, tmp_path):
    node = shutil.which("node")
    renderer = ROOT / ".workspace/react-tests/render.cjs"
    assert node and renderer.exists(), (
        "Run npm ci and npm run build:viewer in react-delivery first."
    )
    content = fixture()
    theme = get_theme(theme_id)
    project = assemble_project(content, theme_id, theme.css_sha256, "a" * 64, max_bytes=10485760)
    portfolio_path = tmp_path / "portfolio.json"
    portfolio_path.write_bytes(project.files["portfolio.json"])
    output = subprocess.run(  # noqa: S603 - checked-in renderer and fixture-only input
        [node, str(renderer), str(portfolio_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        timeout=20,
    )
    original = Markup(theme.contract.render_body(project.portfolio["c"], project.portfolio["d"]))
    react = Markup(output.stdout)
    assert react.tags == original.tags
    assert react.links == original.links
    assert react.fields == original.fields
    assert "".join("".join(react.text).split()) == "".join("".join(original.text).split())
    assert project.receipt["model_calls"] == 0
    assert project.receipt["browser_verification"] == "not_run_for_this_portfolio"
    assert "theme.js" not in "\n".join(project.files)
    manifest = json.loads(project.files["project-manifest.json"])
    for item in manifest["files"]:
        assert sha256(project.files[item["path"]]) == item["sha256"]
        assert len(project.files[item["path"]]) == item["bytes"]


def test_projection_does_not_export_internal_session_fields():
    content = sample_content("01_strong_profile")
    content.update({"evidence": "private-evidence-canary", "chat_history": "private-chat-canary"})
    theme = get_theme("editorial-forest/v1")
    project = assemble_project(
        content, theme.theme_id, theme.css_sha256, "a" * 64, max_bytes=10485760
    )
    assert b"private-evidence-canary" not in project.files["portfolio.json"]
    assert b"private-chat-canary" not in project.files["portfolio.json"]


def test_adapter_and_size_fail_closed(monkeypatch, tmp_path):
    theme = get_theme("cobalt-atlas/v2")
    with pytest.raises(DeliveryError, match="theme"):
        assemble_project(designer(), "unknown/v9", "a" * 64, "b" * 64, max_bytes=10485760)
    with pytest.raises(DeliveryError) as exc:
        assemble_project(designer(), theme.theme_id, theme.css_sha256, "b" * 64, max_bytes=65536)
    assert exc.value.code == "PROJECT_TOO_LARGE"
    monkeypatch.setattr("oryxenai.delivery.project.TEMPLATES", tmp_path)
    with pytest.raises(DeliveryError) as exc:
        assemble_project(designer(), theme.theme_id, theme.css_sha256, "b" * 64, max_bytes=10485760)
    assert exc.value.code == "ADAPTER_BUILD_UNAVAILABLE"


def test_stable_purpose_separated_share_signing():
    identifier, expiry = uuid4(), datetime.now(UTC) + timedelta(hours=24)
    signer = ShareSigner("test-secret-" * 4)
    token = signer.token(identifier, expiry)
    assert ShareSigner("test-secret-" * 4).token(identifier, expiry) == token
    assert signer.parse("https://example.com/share/" + token) == (
        identifier,
        int(expiry.timestamp()),
    )
    for invalid in [
        token + "x",
        token.replace(identifier.hex, uuid4().hex),
        "garbage",
        "a.999999999999999999999.b",
    ]:
        with pytest.raises(DeliveryError):
            signer.parse(invalid)
    with pytest.raises(DeliveryError):
        ShareSigner("short")


@pytest.mark.parametrize(
    "path", ["../secret", "/secret", "a\\b", "a//b", "a/./b", ".env", "a:C", ""]
)
def test_paths_cannot_escape_manifest(path):
    with pytest.raises(DeliveryError):
        safe_path(path)


@pytest.mark.asyncio
async def test_bounded_binary_storage_and_idempotent_prefix_cleanup():
    store = MemoryArtifactStore()
    data = bytes(range(256)) * 300
    expiry = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    first = await store.put_verified(
        key="handoffs/a/attempt/font.woff2", data=data, sha256=sha256(data), expires_at=expiry
    )
    other = await store.put_verified(
        key="handoffs/ab/attempt/font.woff2",
        data=b"other",
        sha256=sha256(b"other"),
        expires_at=expiry,
    )
    assert await store.get_range(first, 32768, 32768) == data[32768:65536]
    await store.delete_prefix("handoffs/a")
    await store.delete_prefix("handoffs/a")
    assert await store.head(first) is None
    assert await store.get_verified(other) == b"other"


def test_preparation_is_portfolio_bound_without_model_credits():
    policy = policy_for("react_delivery.prepare")
    assert policy.portfolio_bound
    assert not policy.consumes_model_credit
    manifest = json.loads((TEMPLATES / "template-manifest.json").read_text())
    assert manifest["checks"]["typescript"] == "passed"


@pytest.mark.asyncio
async def test_s3_range_reads_check_etag_hash_and_close_body():
    from types import SimpleNamespace

    body = io.BytesIO(b"cdef")
    reference = ArtifactReference(
        provider="r2_s3",
        bucket="private",
        key="handoffs/a/font",
        sha256="a" * 64,
        size_bytes=8,
        expires_at="2030-01-01",
        etag="etag",
    )
    calls = []

    def get(**args):
        calls.append(args)
        return {"Body": body, "Metadata": {"sha256": reference.sha256}}

    store = object.__new__(S3ArtifactStore)
    store._bucket, store._client = "private", SimpleNamespace(get_object=get)
    assert await store.get_range(reference, 2, 4) == b"cdef"
    assert body.closed and calls == [
        {"Bucket": "private", "Key": "handoffs/a/font", "Range": "bytes=2-5", "IfMatch": '"etag"'}
    ]
    body = io.BytesIO(b"too long")
    with pytest.raises(ArtifactStorageError, match="changed"):
        await store.get_range(reference, 2, 4)
    assert body.closed


@pytest.mark.asyncio
async def test_s3_lifecycle_rejects_tag_filtered_rule_and_cleanup_retries():
    from types import SimpleNamespace

    rules = [
        {
            "Status": "Enabled",
            "Filter": {"And": {"Prefix": "handoffs/", "Tags": [{"Key": "other", "Value": "true"}]}},
            "Expiration": {"Days": 2},
        }
    ]
    objects = {"handoffs/a/file", "handoffs/ab/file"}
    fail = True

    def listing(**args):
        assert args["Prefix"] == "handoffs/a/"
        return {"Contents": [{"Key": key} for key in objects if key.startswith(args["Prefix"])]}

    def delete(**args):
        nonlocal fail
        if fail:
            fail = False
            raise OSError("storage outage")
        objects.remove(args["Key"])

    store = object.__new__(S3ArtifactStore)
    store._bucket, store._client = (
        "private",
        SimpleNamespace(
            get_bucket_lifecycle_configuration=lambda **_: {"Rules": rules},
            list_objects_v2=listing,
            delete_object=delete,
        ),
    )
    with pytest.raises(ArtifactStorageError) as exc:
        await store.require_lifecycle("handoffs")
    assert exc.value.code == "ARTIFACT_LIFECYCLE_MISSING"
    rules[0]["Filter"] = {"Prefix": "handoffs/"}
    await store.require_lifecycle("handoffs/")
    with pytest.raises(ArtifactStorageError):
        await store.delete_prefix("handoffs/a")
    await store.delete_prefix("handoffs/a")
    await store.delete_prefix("handoffs/a")
    assert objects == {"handoffs/ab/file"}
