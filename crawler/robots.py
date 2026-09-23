import urllib.parse
import re
from typing import List, Dict, Optional, Tuple
import httpx

class RobotsParser:
    def __init__(self, base_url: str, user_agent: str = "SEOJEV-Bot"):
        parsed = urllib.parse.urlparse(base_url)
        self.robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        self.user_agent = user_agent
        self.exists = False
        self.status_code = 0
        self.sitemaps: List[str] = []
        self.disallow_rules: List[str] = []
        self.allow_rules: List[str] = []
        self.user_agent_rules: Dict[str, Dict[str, List[str]]] = {}
        self.raw_text = ""

    async def fetch_and_parse(self, client: httpx.AsyncClient) -> bool:
        try:
            resp = await client.get(self.robots_url, timeout=10.0, follow_redirects=True)
            self.status_code = resp.status_code
            if resp.status_code == 200:
                self.exists = True
                self.raw_text = resp.text
                self._parse(resp.text)
                return True
            else:
                self.exists = False
                return False
        except Exception:
            self.exists = False
            self.status_code = 0
            return False

    def _parse(self, text: str):
        current_agents = []
        lines = text.splitlines()

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Strip inline comments
            if "#" in line:
                line = line.split("#", 1)[0].strip()

            if ":" not in line:
                continue

            key, value = line.split(":", 1)
            key = key.strip().lower()
            value = value.strip()

            if key == "sitemap":
                if value and value not in self.sitemaps:
                    self.sitemaps.append(value)
            elif key == "user-agent":
                agent = value.lower()
                current_agents = [agent]
            elif key == "disallow":
                if not value:
                    continue  # Disallow: (empty) means allow all
                for agent in current_agents:
                    if agent not in self.user_agent_rules:
                        self.user_agent_rules[agent] = {"allow": [], "disallow": []}
                    self.user_agent_rules[agent]["disallow"].append(value)
                if "*" in current_agents:
                    self.disallow_rules.append(value)
            elif key == "allow":
                if not value:
                    continue
                for agent in current_agents:
                    if agent not in self.user_agent_rules:
                        self.user_agent_rules[agent] = {"allow": [], "disallow": []}
                    self.user_agent_rules[agent]["allow"].append(value)
                if "*" in current_agents:
                    self.allow_rules.append(value)

    def is_allowed(self, url: str) -> bool:
        """
        Check if URL is allowed for current user agent or wildcard.
        Allow rule takes precedence if it matches a longer or equal prefix.
        """
        if not self.exists or not self.raw_text:
            return True

        parsed = urllib.parse.urlparse(url)
        path = parsed.path or "/"
        if parsed.query:
            path_with_query = f"{path}?{parsed.query}"
        else:
            path_with_query = path

        # Check specific agent first, then wildcard
        agent_key = self.user_agent.lower()
        rules = None
        if agent_key in self.user_agent_rules:
            rules = self.user_agent_rules[agent_key]
        elif "*" in self.user_agent_rules:
            rules = self.user_agent_rules["*"]

        if not rules:
            return True

        # Find best matching rule (longest matching prefix)
        best_allow_len = -1
        for rule in rules.get("allow", []):
            if self._path_matches(rule, path_with_query):
                best_allow_len = max(best_allow_len, len(rule))

        best_disallow_len = -1
        for rule in rules.get("disallow", []):
            if self._path_matches(rule, path_with_query):
                best_disallow_len = max(best_disallow_len, len(rule))

        if best_disallow_len >= 0 and best_disallow_len >= best_allow_len:
            return False

        return True

    def _path_matches(self, rule_pattern: str, path: str) -> bool:
        """Standard robots.txt wildcard matching."""
        if not rule_pattern:
            return False
        # Escape special regex chars except * and $
        regex = "^"
        i = 0
        while i < len(rule_pattern):
            c = rule_pattern[i]
            if c == "*":
                regex += ".*"
            elif c == "$":
                regex += "$"
            else:
                regex += re.escape(c)
            i += 1
        if not rule_pattern.endswith("$") and not rule_pattern.endswith("*"):
            # Prefix match
            pass
        try:
            return bool(re.match(regex, path))
        except Exception:
            return path.startswith(rule_pattern)
