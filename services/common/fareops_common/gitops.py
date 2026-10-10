import base64

import requests

from .markers import get_marker, set_marker

API = "https://api.github.com"


class GitOpsClient:
    def __init__(self, repo: str, token: str, branch: str = "main"):
        if not repo or not token:
            raise ValueError("GITOPS_REPO and GITHUB_TOKEN must be set")
        self.repo, self.branch = repo, branch
        self.s = requests.Session()
        self.s.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

    def read(self, path: str) -> tuple[str, str]:
        r = self.s.get(f"{API}/repos/{self.repo}/contents/{path}", params={"ref": self.branch}, timeout=20)
        r.raise_for_status()
        body = r.json()
        return base64.b64decode(body["content"]).decode(), body["sha"]

    def get(self, path: str, key: str) -> str | None:
        return get_marker(self.read(path)[0], key)

    def set(self, path: str, key: str, value: str, message: str, quote: bool = False, retries: int = 3) -> bool:
        """Returns True if a commit was made, False if the value was already set."""
        for attempt in range(retries):
            text, sha = self.read(path)
            new, n = set_marker(text, key, value, quote)
            if n == 0:
                raise ValueError(f"marker fareops:{key} not found in {path}")
            if new == text:
                return False
            r = self.s.put(f"{API}/repos/{self.repo}/contents/{path}", timeout=20, json={
                "message": message, "branch": self.branch, "sha": sha,
                "content": base64.b64encode(new.encode()).decode(),
            })
            if r.status_code in (409, 422) and attempt < retries - 1:
                continue  # file changed under us: re-read and retry
            r.raise_for_status()
            return True
        return False
