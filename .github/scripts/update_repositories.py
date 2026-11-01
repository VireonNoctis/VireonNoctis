#!/usr/bin/env python3
"""Refresh the expandable repository index in the profile README."""
import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request

OWNER = os.environ.get("GITHUB_OWNER", "VireonNoctis")
README_PATH = os.environ.get("README_PATH", "README.md")
START = "<!-- AUTO-REPOSITORIES:START -->"
END = "<!-- AUTO-REPOSITORIES:END -->"
API = "https://api.github.com"
FRAMEWORK_PACKAGES = {
    "next": "Next.js", "react": "React", "svelte": "Svelte",
    "vue": "Vue", "@angular/core": "Angular", "astro": "Astro", "three": "Three.js",
}


def request_json(url, token):
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "vireon-repository-readme-updater",
    })
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.load(response)


def short_description(value, limit=180):
    description = " ".join(str(value or "").split())
    if len(description) <= limit:
        return description
    return description[:limit - 1].rsplit(" ", 1)[0].rstrip() + "…"


def detect_frameworks(repo, token):
    """Read a root package manifest; framework labels are not language labels."""
    full_name = repo.get("full_name", "")
    branch = repo.get("default_branch", "main")
    if not full_name:
        return []
    url = (
        f"{API}/repos/{full_name}/contents/package.json?"
        + urllib.parse.urlencode({"ref": branch})
    )
    try:
        payload = request_json(url, token)
        encoded = payload.get("content", "")
        if payload.get("encoding") != "base64" or not encoded:
            return []
        manifest = json.loads(base64.b64decode(encoded).decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, KeyError, UnicodeDecodeError):
        return []
    if not isinstance(manifest, dict):
        return []
    dependencies = {}
    for section in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
        values = manifest.get(section, {})
        if isinstance(values, dict):
            dependencies.update(values)
    return sorted(label for package, label in FRAMEWORK_PACKAGES.items() if package in dependencies)


def main():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GH_TOKEN or GITHUB_TOKEN is required")
    repos = []
    page = 1
    has_private_access = bool(os.environ.get("GH_REPOS_TOKEN"))
    endpoint = "/user/repos" if has_private_access else "/users/" + urllib.parse.quote(OWNER) + "/repos"
    while page <= 10:
        params = {"per_page": 100, "sort": "updated", "page": page}
        if has_private_access:
            params.update({"visibility": "all", "affiliation": "owner"})
        else:
            params.update({"type": "owner"})
        batch = request_json(API + endpoint + "?" + urllib.parse.urlencode(params), token)
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    candidates = []
    for repo in repos:
        if repo.get("owner", {}).get("login", "").lower() != OWNER.lower():
            continue
        if repo.get("name", "").lower() == OWNER.lower():
            continue
        if repo.get("fork") or repo.get("archived") or not repo.get("description"):
            continue
        candidates.append(repo)
    candidates.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
    candidates = candidates[:10]

    rows = []
    for index, repo in enumerate(candidates, 1):
        name = str(repo.get("name", "Repository"))
        url = str(repo.get("html_url", ""))
        description = short_description(repo.get("description"))
        updated_at = (repo.get("updated_at") or "")[:10] or "Unknown"
        try:
            languages = request_json(repo["languages_url"], token)
            source_stack = ", ".join(sorted(languages, key=languages.get, reverse=True)) or "Not detected"
        except (urllib.error.HTTPError, urllib.error.URLError, KeyError, TimeoutError):
            source_stack = "Unavailable"
        frameworks = detect_frameworks(repo, token)
        rows.extend([
            "<details>",
            f"<summary><strong>{index:02d} · {name}</strong> <code>UPDATED {updated_at}</code></summary>",
            "",
            description,
            "",
            f"**Repository:** [Open on GitHub]({url})",
            f"**Source languages:** {source_stack}",
        ])
        if frameworks:
            rows.append("**Detected frameworks:** " + " · ".join(frameworks))
        rows.extend(["", "</details>", ""])

    if not candidates:
        rows = ["No described public repositories found yet. Add a description in GitHub repository settings to list a project here."]
    generated = "\n".join(rows).rstrip()
    with open(README_PATH, "r", encoding="utf-8") as handle:
        readme = handle.read()
    if START not in readme or END not in readme:
        raise SystemExit("README markers are missing; refusing to overwrite unrelated content")
    before, remainder = readme.split(START, 1)
    _, after = remainder.split(END, 1)
    updated = before + START + "\n" + generated + "\n" + END + after
    with open(README_PATH, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)


if __name__ == "__main__":
    main()
