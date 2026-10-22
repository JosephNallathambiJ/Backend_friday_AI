# Browser Automation & Web Research

## 1. Web Research Service (`app/services/web_research_service.py`)

FRIDAY AI provides safe internet search and webpage extraction:
- **Search Provider**: Public DuckDuckGo HTML endpoint with safe HTML parsing.
- **HTML Extraction**: BeautifulSoup-powered text and outgoing link extraction with script/style stripping.
- **Length Bounding**: Output text is bounded to 10,000 characters for prompt context efficiency.

### SSRF Protection
The `validate_public_url()` function validates every destination:
- Prohibits non-HTTP/HTTPS schemes (`file://`, `ftp://`).
- Blocks loopback strings (`localhost`, `127.0.0.1`, `0.0.0.0`).
- Performs DNS resolution and verifies destination IP addresses against private (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local (`169.254.0.0/16`), loopback (`::1`), and reserved subnets.
- Re-verifies final destinations after HTTP redirects.

---

## 2. Browser Automation (`app/services/browser_service.py`)

Browser automation is built on an isolated Playwright adapter:
- **Incognito Sessions**: Every session operates in an ephemeral browser context without shared cookies or host browser profiles.
- **Supported Actions**:
  - `browser_navigate`: Opens public URLs.
  - `browser_read`: Extracts visible innerText and anchors.
  - `browser_interact`: Clicks buttons, fills form fields, and selects options.
  - `browser_close`: Closes pages and reclaims memory.

### Prompt-Injection Defense
Webpage text, scraped HTML, and extracted links are treated as untrusted data, never as system instructions. Text containing instructions like "ignore previous instructions" or "run this command" cannot bypass system policies or grant permissions.
