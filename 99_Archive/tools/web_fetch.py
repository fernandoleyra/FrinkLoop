import urllib.request, urllib.error, re

TOOL_DEFINITION = {
    "name": "web_fetch",
    "description": "Fetch and read the full text content of any URL — docs, articles, APIs, frameworks.",
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "max_chars": {"type": "integer", "default": 10000}
        },
        "required": ["url"]
    }
}

def run(url: str, max_chars: int = 10000) -> str:
    if not url.startswith("http"):
        return "Error: URL must start with http/https"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (NEXUS-Agent)"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars] + ("..." if len(text) > max_chars else "")
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return f"Fetch failed: {e}"
