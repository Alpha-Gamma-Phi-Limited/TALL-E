import httpx
import pytest

from worker.adapters.harvey_norman import HarveyNormanLiveAdapter


def test_harvey_fetch_uses_browser_fallback_when_http_fetch_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = HarveyNormanLiveAdapter(max_fetch_retries=0, use_fixture_fallback=False, browser_fallback=True)

    def fail_http(*_args, **_kwargs):
        raise httpx.NetworkError("blocked")

    monkeypatch.setattr(adapter.client, "get", fail_http)
    monkeypatch.setattr(adapter, "_fetch_text_with_browser", lambda _url: "<html><body>ok</body></html>")

    html = adapter._fetch_text("https://example.com/product")
    assert "ok" in html


def test_harvey_fetch_raises_when_browser_fallback_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = HarveyNormanLiveAdapter(max_fetch_retries=0, use_fixture_fallback=False, browser_fallback=False)

    def fail_http(*_args, **_kwargs):
        raise httpx.NetworkError("blocked")

    monkeypatch.setattr(adapter.client, "get", fail_http)

    with pytest.raises(Exception):
        adapter._fetch_text("https://example.com/product")


def test_harvey_fetch_raises_when_browser_result_is_still_challenge(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = HarveyNormanLiveAdapter(max_fetch_retries=0, use_fixture_fallback=False, browser_fallback=True)

    def fail_http(*_args, **_kwargs):
        raise httpx.NetworkError("blocked")

    challenge = "<html><body>Request unsuccessful. Incapsula incident ID: 1</body></html>"
    monkeypatch.setattr(adapter.client, "get", fail_http)
    monkeypatch.setattr(adapter, "_fetch_text_with_browser", lambda _url: challenge)

    with pytest.raises(Exception):
        adapter._fetch_text("https://example.com/product")
