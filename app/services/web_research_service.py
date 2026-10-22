"""Web research service with strict SSRF protection and HTML text extraction."""

import ipaddress
import socket
from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.core.exceptions import SecurityPolicyError, ValidationError
from app.core.time import utc_now


def validate_public_url(url: str) -> str:
    """Validate that the URL resolves to a public, non-private IP address (SSRF Protection)."""
    parsed = urlparse(url)
    if parsed.scheme not in ["http", "https"]:
        raise SecurityPolicyError(
            f"Unsupported URL scheme '{parsed.scheme}'. Only HTTP and HTTPS are permitted."
        )

    hostname = parsed.hostname
    if not hostname:
        raise ValidationError("URL must contain a valid hostname.")

    # Block obvious local strings
    if hostname.lower() in ["localhost", "127.0.0.1", "0.0.0.0", "::1", "local"]:
        raise SecurityPolicyError(
            "Access to localhost or loopback destinations is strictly prohibited."
        )

    # Resolve IP address to check for private / link-local / loopback subnets
    try:
        ip_list = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise ValidationError(f"DNS resolution failed for hostname '{hostname}': {e}")

    for item in ip_list:
        ip_str = item[4][0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
            if (
                ip_obj.is_private
                or ip_obj.is_loopback
                or ip_obj.is_link_local
                or ip_obj.is_reserved
                or ip_obj.is_multicast
            ):
                raise SecurityPolicyError(
                    f"Destination IP address '{ip_str}' belongs to a private/reserved subnet. Access denied."
                )
        except ValueError:
            pass

    return url


class WebResearchService:
    """Service providing search queries, safe webpage retrieval, and HTML extraction."""

    @staticmethod
    async def fetch_webpage(
        url: str, timeout_seconds: int = 15, max_bytes: int = 2 * 1024 * 1024
    ) -> dict[str, Any]:
        """Safely fetch and parse a public webpage."""
        valid_url = validate_public_url(url)

        headers = {
            "User-Agent": "FridayAI-ResearchBot/1.0 (+http://localhost/bot)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=float(timeout_seconds),
            verify=True,
        ) as client:
            resp = await client.get(valid_url, headers=headers)

            # Re-verify final redirect destination for SSRF protection
            validate_public_url(str(resp.url))

            if resp.status_code >= 400:
                raise ValidationError(f"Webpage returned HTTP status {resp.status_code}.")

            content_bytes = resp.content[:max_bytes]
            html_text = content_bytes.decode(resp.encoding or "utf-8", errors="replace")

        # Parse HTML using BeautifulSoup
        soup = BeautifulSoup(html_text, "html.parser")

        # Strip script, style, and hidden elements
        for element in soup(["script", "style", "noscript", "svg", "header", "footer"]):
            element.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else "Untitled"
        body_text = soup.get_text(separator=" ", strip=True)

        # Collect outgoing links
        links = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            link_text = a_tag.get_text(strip=True)
            if href.startswith("http"):
                links.append({"href": href, "text": link_text[:100]})
            if len(links) >= 30:
                break

        return {
            "url": str(resp.url),
            "title": title,
            "text": body_text[:10000],  # Bound text length for prompt safety
            "links": links,
            "fetched_at": utc_now().isoformat(),
        }

    @staticmethod
    async def search(query: str, max_results: int = 5) -> list[dict[str, Any]]:
        """Perform web search using public DuckDuckGo HTML endpoint with safe parsing."""
        search_url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.post(search_url, data={"q": query}, headers=headers)
                if resp.status_code != 200:
                    return []

                soup = BeautifulSoup(resp.text, "html.parser")
                results = []
                for result in soup.find_all("div", class_="result"):
                    title_elem = result.find("a", class_="result__a")
                    snippet_elem = result.find("a", class_="result__snippet")
                    if title_elem and title_elem.get("href"):
                        href = title_elem["href"]
                        # Filter DuckDuckGo redirect link
                        if "uddg=" in href:
                            import urllib.parse

                            qs = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                            href = qs.get("uddg", [href])[0]
                        results.append(
                            {
                                "title": title_elem.get_text(strip=True),
                                "url": href,
                                "snippet": snippet_elem.get_text(strip=True)
                                if snippet_elem
                                else "",
                            }
                        )
                        if len(results) >= max_results:
                            break
                return results
        except Exception:
            # Return empty list gracefully if external search provider is unreachable
            return []
