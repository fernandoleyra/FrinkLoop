import os, json, urllib.request, urllib.parse

TOOL_DEFINITION = {
    "name": "web_search",
    "description": "Search the web for technical documentation, market research, competitive analysis, best practices, or any current information needed for the project.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Specific search query"},
            "num_results": {"type": "integer", "default": 5}
        },
        "required": ["query"]
    }
}

def run(query: str, num_results: int = 5) -> str:
    api_key = os.environ.get("SERPAPI_KEY")
    if api_key:
        params = urllib.parse.urlencode({"q": query, "api_key": api_key, "num": num_results})
        url = f"https://serpapi.com/search.json?{params}"
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read())
            results = data.get("organic_results", [])[:num_results]
            return "\n".join(f"- {r['title']}: {r.get('snippet','')}" for r in results)
        except Exception as e:
            pass  # Fall through to DuckDuckGo

    # DuckDuckGo fallback
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_redirect=1"
        req = urllib.request.Request(url, headers={"User-Agent": "NEXUS-Agent/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        results = []
        if data.get("AbstractText"):
            results.append(data["AbstractText"])
        for t in data.get("RelatedTopics", [])[:num_results]:
            if "Text" in t:
                results.append(f"- {t['Text']}")
        return "\n".join(results) or "No results found."
    except Exception as e:
        return f"Search failed: {e}"
