from __future__ import annotations

import hashlib

import pytest

from scripts.acquire_official_sources import download_pdf, sha256


def test_sha256_is_stable():
    assert sha256(b"legal") == hashlib.sha256(b"legal").hexdigest()


def test_download_rejects_non_pdf(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return b"<html>portal error</html>"

    monkeypatch.setattr("scripts.acquire_official_sources.urlopen", lambda *_args, **_kwargs: Response())
    with pytest.raises(ValueError, match="did not return a PDF"):
        download_pdf("https://official.example/document")
