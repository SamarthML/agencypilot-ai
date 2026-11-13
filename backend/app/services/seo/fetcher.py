"""Safe page fetching for the SEO audit.

Users submit arbitrary URLs, so this is an SSRF boundary:
- only http/https on the default ports, no credentials in the URL;
- every hostname is resolved and rejected if ANY address is non-public (private, loopback,
  link-local, reserved, CGNAT, multicast, unspecified; IPv4-mapped IPv6 unwrapped);
- the connection is pinned to the validated IP (Host header + TLS SNI keep the real hostname),
  so a second DNS lookup can't be rebound to an internal address;
- redirects are followed manually and every hop is re-validated;
- 10 s total time limit and a 2 MB body cap.
"""

import asyncio
import ipaddress
import re
import socket
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass

import httpx

TIMEOUT_SECONDS = 10.0
MAX_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 5
DEFAULT_PORTS = {"http": 80, "https": 443}
SCHEME_PREFIX = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.-]*):")
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
BOT_BLOCK_STATUSES = frozenset({401, 403, 429})
HTML_CONTENT_TYPES = ("text/html", "application/xhtml+xml")
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

Resolver = Callable[[str, int], Awaitable[list[str]]]


class SeoFetchError(Exception):
    """Base class; every message is safe to show to the user."""


class InvalidUrlError(SeoFetchError):
    pass


class BlockedAddressError(SeoFetchError):
    pass


class FetchTimeoutError(SeoFetchError):
    pass


class NotHtmlError(SeoFetchError):
    pass


class PageTooLargeError(SeoFetchError):
    pass


class SiteBlocksBotsError(SeoFetchError):
    pass


class SiteUnreachableError(SeoFetchError):
    pass


@dataclass(frozen=True)
class FetchResult:
    final_url: str
    status_code: int
    load_ms: int
    html_bytes: int
    content: bytes
    charset: str | None


# ---------------------------------------------------------------------------
# URL validation
# ---------------------------------------------------------------------------


def _with_scheme(text: str, allow_bare_domain: bool) -> str:
    """Add https:// to a bare domain; refuse other scheme-like input (javascript:, file:/)."""
    if "://" in text:
        return text
    scheme_like = SCHEME_PREFIX.match(text)
    if not allow_bare_domain or (scheme_like and "." not in scheme_like.group(1)):
        raise InvalidUrlError("Only http:// and https:// URLs can be audited.")
    return f"https://{text}"


def parse_url(raw: str, *, allow_bare_domain: bool = True) -> httpx.URL:
    """Validate and normalise a URL: lower-case scheme/host, no default port, no fragment."""
    text = raw.strip()
    if not text:
        raise InvalidUrlError("Enter a URL to audit.")
    try:
        url = httpx.URL(_with_scheme(text, allow_bare_domain))
    except httpx.InvalidURL as exc:
        raise InvalidUrlError(f"That doesn't look like a valid URL ({exc}).") from exc
    scheme = url.scheme.lower()
    if scheme not in DEFAULT_PORTS:
        raise InvalidUrlError("Only http:// and https:// URLs can be audited.")
    if not url.host:
        raise InvalidUrlError("The URL has no host name.")
    if url.userinfo:
        raise InvalidUrlError("URLs containing a username or password can't be audited.")
    if url.port not in (None, DEFAULT_PORTS[scheme]):
        raise InvalidUrlError("Only standard ports (80 for http, 443 for https) are allowed.")
    host = f"[{url.host}]" if ":" in url.host else url.host
    return httpx.URL(f"{scheme}://{host}{url.raw_path.decode('ascii') or '/'}")


def normalize_url(raw: str) -> str:
    return str(parse_url(raw))


# ---------------------------------------------------------------------------
# SSRF guard
# ---------------------------------------------------------------------------


def is_public_ip(address: str) -> bool:
    ip = ipaddress.ip_address(address.split("%", 1)[0])  # drop an IPv6 zone id
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


async def resolve_host(host: str, port: int) -> list[str]:
    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise SiteUnreachableError(f"Couldn't find {host}. Check the domain name.") from exc
    return sorted({str(info[4][0]) for info in infos})


def _ip_literal(host: str) -> str | None:
    try:
        return str(ipaddress.ip_address(host))
    except ValueError:
        return None


async def safe_address(url: httpx.URL, resolve: Resolver) -> str:
    """The IP to connect to, after checking that every address the host resolves to is public."""
    host = url.host
    literal = _ip_literal(host)
    addresses = [literal] if literal else await resolve(host, 443 if url.scheme == "https" else 80)
    if not addresses:
        raise SiteUnreachableError(f"Couldn't find {host}. Check the domain name.")
    blocked = [a for a in addresses if not is_public_ip(a)]
    if blocked:
        raise BlockedAddressError(
            f"{host} points to a private or reserved address ({blocked[0]}), "
            "so it can't be audited."
        )
    return addresses[0]


def pinned_request(client: httpx.AsyncClient, url: httpx.URL, ip: str) -> httpx.Request:
    """A request to `ip` that still presents the real hostname (Host header + TLS SNI)."""
    extensions = {"sni_hostname": url.host} if url.scheme == "https" else {}
    return client.build_request(
        "GET",
        url.copy_with(host=ip),
        headers={**BROWSER_HEADERS, "Host": url.netloc.decode("ascii")},
        extensions=extensions,
    )


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _client_scope(client: httpx.AsyncClient | None) -> AsyncIterator[httpx.AsyncClient]:
    if client is not None:
        yield client
        return
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS, follow_redirects=False) as owned:
        yield owned


def _check_status(response: httpx.Response, host: str) -> None:
    code = response.status_code
    if code in BOT_BLOCK_STATUSES:
        raise SiteBlocksBotsError(
            f"{host} refused the request (HTTP {code}). The site blocks automated audits."
        )
    if code >= 400:
        raise SiteUnreachableError(f"{host} returned HTTP {code}.")


def _check_content_type(response: httpx.Response) -> None:
    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type and content_type not in HTML_CONTENT_TYPES:
        raise NotHtmlError(f"That URL returns {content_type}, not an HTML page.")


async def _read_limited(response: httpx.Response) -> bytes:
    declared = response.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_BYTES:
        raise PageTooLargeError("The page is larger than 2 MB, the audit limit.")
    chunks: list[bytes] = []
    size = 0
    async for chunk in response.aiter_bytes():
        size += len(chunk)
        if size > MAX_BYTES:
            raise PageTooLargeError("The page is larger than 2 MB, the audit limit.")
        chunks.append(chunk)
    return b"".join(chunks)


def _redirect_target(current: httpx.URL, location: str) -> httpx.URL:
    try:
        return parse_url(str(current.join(location)), allow_bare_domain=False)
    except InvalidUrlError as exc:
        raise BlockedAddressError(
            f"The page redirects to a URL that can't be audited: {exc}"
        ) from exc


async def _follow(
    http: httpx.AsyncClient, url: httpx.URL, resolve: Resolver
) -> tuple[httpx.URL, int, bytes, str | None]:
    for _ in range(MAX_REDIRECTS + 1):
        ip = await safe_address(url, resolve)
        response = await http.send(
            pinned_request(http, url, ip), stream=True, follow_redirects=False
        )
        try:
            location = response.headers.get("location")
            if response.status_code in REDIRECT_STATUSES and location:
                url = _redirect_target(url, location)
                continue
            _check_status(response, url.host)
            _check_content_type(response)
            content = await _read_limited(response)
            return url, response.status_code, content, response.charset_encoding
        finally:
            await response.aclose()
    raise SiteUnreachableError(f"The page redirected more than {MAX_REDIRECTS} times.")


async def fetch_page(
    url: httpx.URL, *, client: httpx.AsyncClient | None = None, resolve: Resolver = resolve_host
) -> FetchResult:
    """Fetch a validated URL (see `parse_url`) within the SSRF, size and time limits."""
    started = time.perf_counter()
    try:
        async with asyncio.timeout(TIMEOUT_SECONDS), _client_scope(client) as http:
            final_url, status, content, charset = await _follow(http, url, resolve)
    except (TimeoutError, httpx.TimeoutException) as exc:
        raise FetchTimeoutError(
            f"{url.host} took longer than {TIMEOUT_SECONDS:g} seconds to respond."
        ) from exc
    except httpx.TransportError as exc:
        raise SiteUnreachableError(
            f"Couldn't connect to {url.host} ({type(exc).__name__})."
        ) from exc
    return FetchResult(
        final_url=str(final_url),
        status_code=status,
        load_ms=int((time.perf_counter() - started) * 1000),
        html_bytes=len(content),
        content=content,
        charset=charset,
    )
