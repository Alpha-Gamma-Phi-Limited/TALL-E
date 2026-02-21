from worker.fetchers.browser import _playwright_proxy


def test_playwright_proxy_parses_auth_and_port() -> None:
    proxy = _playwright_proxy("http://user:pass@proxy.example.com:8080")
    assert proxy["server"] == "http://proxy.example.com:8080"
    assert proxy["username"] == "user"
    assert proxy["password"] == "pass"

