"""URL validation, SSRF guard and fetch limits, via httpx.MockTransport and a fake resolver."""

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable

import httpx
import pytest

from app.services.seo import fetcher

PUBLIC_IP = "93.184.215.14"
HTML = {"content-type": "text/html; charset=utf-8"}
PAGE = b"<html><head><title>Hi</title></head><body>Hello</body></html>"

Handler = Callable[[httpx.Request], Awaitable[httpx.Response]]


def resolver(table: dict[str, list[str]]) -> fetcher.Resolver:
    async def resolve(host: str, port: int) -> list[str]:
        if host not in table:
            raise fetcher.SiteUnreachableError(f"Couldn't find {host}.")
        return table[host]

    return resolve


def client(handler: Handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def fetch(
    url: str, handler: Handler, dns: dict[str, list[str]] | None = None
) -> fetcher.FetchResult:
    table = dns if dns is not None else {"site.example": [PUBLIC_IP]}
    async with client(handler) as http:
        return await fetcher.fetch_page(
            fetcher.parse_url(url), client=http, resolve=resolver(table)
        )


async def ok_page(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, headers=HTML, content=PAGE)


# --- URL validation --------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ("", "Enter a URL"),
        ("ftp://site.example/file", "Only http:// and https://"),
        ("javascript:alert(1)", "Only http:// and https://"),
        ("https://user:pass@site.example/", "username or password"),
        ("https://site.example:8443/", "standard ports"),
        ("http://site.example:22/", "standard ports"),
        ("https://", "valid URL|no host"),
    ],
)
def test_invalid_urls_are_rejected(raw: str, message: str) -> None:
    with pytest.raises(fetcher.InvalidUrlError, match=message):
        fetcher.parse_url(raw)


@pytest.mark.parametrize(
    ("raw", "normalized"),
    [
        ("Site.Example", "https://site.example/"),
        ("HTTPS://SITE.example:443/Path?q=1#frag", "https://site.example/Path?q=1"),
        ("http://site.example:80", "http://site.example/"),
        ("  https://site.example/a  ", "https://site.example/a"),
    ],
)
def test_urls_are_normalised(raw: str, normalized: str) -> None:
    assert fetcher.normalize_url(raw) == normalized


# --- SSRF guard --------------------------------------------------------------------


@pytest.mark.parametrize(
    "address",
    [
        "10.0.0.1",
        "172.16.5.4",
        "192.168.1.1",
        "127.0.0.1",
        "169.254.169.254",  # cloud metadata
        "100.64.0.1",  # CGNAT
        "0.0.0.0",
        "224.0.0.1",
        "240.0.0.1",
        "::1",
        "fe80::1%eth0",
        "fc00::1",
        "::ffff:127.0.0.1",
        "::ffff:10.0.0.1",
        "64:ff9b::7f00:1",  # NAT64 -> 127.0.0.1
        "64:ff9b::a9fe:a9fe",  # NAT64 -> 169.254.169.254
        "2002:7f00:1::1",  # 6to4
        "2001:0:4136:e378:8000:63bf:80ff:fffe",  # Teredo
    ],
)
def test_non_public_addresses_are_not_public(address: str) -> None:
    assert fetcher.is_public_ip(address) is False


@pytest.mark.parametrize(
    "address", [PUBLIC_IP, "8.8.8.8", "2606:4700:4700::1111", "64:ff9b::808:808"]
)
def test_public_addresses_are_public(address: str) -> None:
    assert fetcher.is_public_ip(address) is True


@pytest.mark.parametrize(
    "url", ["http://127.0.0.1/", "http://169.254.169.254/latest/meta-data", "http://[::1]/"]
)
async def test_private_ip_literals_are_blocked(url: str) -> None:
    with pytest.raises(fetcher.BlockedAddressError, match="private or reserved"):
        await fetch(url, ok_page, dns={})


async def test_hostname_resolving_to_private_ip_is_blocked() -> None:
    with pytest.raises(fetcher.BlockedAddressError, match="10.1.2.3"):
        await fetch("https://intranet.example/", ok_page, dns={"intranet.example": ["10.1.2.3"]})


async def test_any_private_address_in_the_answer_blocks_the_host() -> None:
    dns = {"mixed.example": [PUBLIC_IP, "127.0.0.1"]}

    with pytest.raises(fetcher.BlockedAddressError):
        await fetch("https://mixed.example/", ok_page, dns=dns)


async def test_unknown_host_is_unreachable() -> None:
    with pytest.raises(fetcher.SiteUnreachableError, match="Couldn't find"):
        await fetch("https://nowhere.example/", ok_page)


async def test_connection_is_pinned_to_the_validated_ip() -> None:
    seen: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return await ok_page(request)

    result = await fetch("https://site.example/page", handler)

    [request] = seen
    assert request.url.host == PUBLIC_IP
    assert request.headers["host"] == "site.example"
    assert request.extensions["sni_hostname"] == "site.example"
    assert "Chrome/" in request.headers["user-agent"]
    assert result.final_url == "https://site.example/page"
    assert (result.status_code, result.html_bytes, result.content) == (200, len(PAGE), PAGE)
    assert result.charset == "utf-8"


async def test_plain_http_has_no_sni() -> None:
    seen: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return await ok_page(request)

    await fetch("http://site.example/", handler)

    assert "sni_hostname" not in seen[0].extensions


# --- Redirects ---------------------------------------------------------------------


def redirecting(locations: dict[str, str]) -> Handler:
    """Redirect while the requested path is in `locations`, then serve the page."""

    async def handler(request: httpx.Request) -> httpx.Response:
        target = locations.get(request.url.path)
        if target is not None:
            return httpx.Response(301, headers={"location": target})
        return await ok_page(request)

    return handler


async def test_relative_redirect_is_followed() -> None:
    result = await fetch("https://site.example/old", redirecting({"/old": "/new"}))

    assert result.final_url == "https://site.example/new"


async def test_redirect_to_private_host_is_blocked() -> None:
    dns = {"site.example": [PUBLIC_IP], "internal.example": ["192.168.0.10"]}
    handler = redirecting({"/": "http://internal.example/admin"})

    with pytest.raises(fetcher.BlockedAddressError, match="internal.example"):
        await fetch("https://site.example/", handler, dns=dns)


async def test_redirect_to_metadata_ip_is_blocked() -> None:
    handler = redirecting({"/": "http://169.254.169.254/latest/meta-data/"})

    with pytest.raises(fetcher.BlockedAddressError):
        await fetch("https://site.example/", handler)


async def test_redirect_to_non_http_scheme_is_blocked() -> None:
    handler = redirecting({"/": "file:///etc/passwd"})

    with pytest.raises(fetcher.BlockedAddressError, match="can't be audited"):
        await fetch("https://site.example/", handler)


async def test_five_redirects_are_allowed() -> None:
    chain = {f"/{i}": f"/{i + 1}" for i in range(5)}  # /0 -> ... -> /5

    result = await fetch("https://site.example/0", redirecting(chain))

    assert result.final_url == "https://site.example/5"


async def test_more_than_five_redirects_fail() -> None:
    chain = {f"/{i}": f"/{i + 1}" for i in range(6)}

    with pytest.raises(fetcher.SiteUnreachableError, match="more than 5"):
        await fetch("https://site.example/0", redirecting(chain))


# --- Responses -----------------------------------------------------------------------


@pytest.mark.parametrize("code", [401, 403, 429])
async def test_bot_blocking_statuses(code: int) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(code, headers=HTML, content=b"blocked")

    with pytest.raises(fetcher.SiteBlocksBotsError, match=f"HTTP {code}"):
        await fetch("https://site.example/", handler)


@pytest.mark.parametrize("code", [404, 500, 503])
async def test_error_statuses(code: int) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(code, headers=HTML)

    with pytest.raises(fetcher.SiteUnreachableError, match=f"HTTP {code}"):
        await fetch("https://site.example/", handler)


@pytest.mark.parametrize("content_type", ["application/pdf", "image/png", "application/json"])
async def test_non_html_is_rejected(content_type: str) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": content_type}, content=b"%PDF")

    with pytest.raises(fetcher.NotHtmlError, match=content_type):
        await fetch("https://site.example/file", handler)


async def test_missing_content_type_is_allowed() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=PAGE)

    assert (await fetch("https://site.example/", handler)).content == PAGE


async def test_declared_oversize_body_is_rejected() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers=HTML, content=b"x" * (fetcher.MAX_BYTES + 1))

    with pytest.raises(fetcher.PageTooLargeError):
        await fetch("https://site.example/", handler)


async def test_streamed_oversize_body_is_cut_off() -> None:
    async def chunks() -> AsyncIterator[bytes]:
        for _ in range(3):
            yield b"x" * (1024 * 1024)

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers=HTML, content=chunks())  # no content-length

    with pytest.raises(fetcher.PageTooLargeError):
        await fetch("https://site.example/", handler)


async def test_httpx_timeout_is_friendly() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(fetcher.FetchTimeoutError, match="site.example took longer than 10"):
        await fetch("https://site.example/", handler)


async def test_overall_time_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fetcher, "TIMEOUT_SECONDS", 0.05)

    async def slow(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(1)
        return await ok_page(request)

    with pytest.raises(fetcher.FetchTimeoutError):
        await fetch("https://site.example/", slow)


async def test_connection_error_is_unreachable() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(fetcher.SiteUnreachableError, match="Couldn't connect to site.example"):
        await fetch("https://site.example/", handler)
