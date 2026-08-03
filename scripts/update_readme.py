from __future__ import annotations

import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests


README_PATH = Path("README.md")

START_MARKER = "<!-- AUTO-GENERATED:START -->"
END_MARKER = "<!-- AUTO-GENERATED:END -->"

API_URL = "https://api.github.com"
API_VERSION = "2026-03-10"


def github_get(
    endpoint: str,
    params: dict[str, Any] | None = None,
) -> Any:
    """Make an authenticated or unauthenticated GitHub API request."""

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
        "User-Agent": "self-updating-github-profile",
    }

    token = os.getenv("GITHUB_TOKEN")

    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.get(
        f"{API_URL}{endpoint}",
        headers=headers,
        params=params,
        timeout=30,
    )

    response.raise_for_status()
    return response.json()


def clean_description(description: str | None) -> str:
    """Prepare a repository description for Markdown output."""

    if not description:
        return "No description provided yet."

    return " ".join(description.split()).replace("|", "\\|")


def get_public_repositories(username: str) -> list[dict[str, Any]]:
    """Retrieve public repositories owned by the user."""

    repositories = github_get(
        f"/users/{username}/repos",
        params={
            "type": "owner",
            "sort": "pushed",
            "direction": "desc",
            "per_page": 100,
        },
    )

    return [
        repository
        for repository in repositories
        if not repository.get("fork", False)
        and not repository.get("archived", False)
        and repository["name"].lower() != username.lower()
    ]


def generate_dynamic_section(
    username: str,
    repositories: list[dict[str, Any]],
) -> str:
    """Generate the Markdown that will be inserted into the README."""

    total_stars = sum(
        repository.get("stargazers_count", 0)
        for repository in repositories
    )

    language_counts = Counter(
        repository["language"]
        for repository in repositories
        if repository.get("language")
    )

    top_languages = ", ".join(
        f"`{language}`"
        for language, _ in language_counts.most_common(6)
    )

    if not top_languages:
        top_languages = "No language information available."

    lines = [
        "### GitHub snapshot",
        "",
        f"- **Active public repositories:** {len(repositories)}",
        f"- **Stars across active repositories:** {total_stars}",
        f"- **Most-used repository languages:** {top_languages}",
        "",
        "### Recently updated projects",
        "",
    ]

    recent_repositories = repositories[:6]

    if not recent_repositories:
        lines.append("No public projects are currently available.")
    else:
        for repository in recent_repositories:
            language = repository.get("language") or "Mixed"
            stars = repository.get("stargazers_count", 0)
            pushed_date = repository["pushed_at"][:10]
            description = clean_description(repository.get("description"))

            lines.extend(
                [
                    (
                        f"- **[{repository['name']}]"
                        f"({repository['html_url']})** — {description}"
                    ),
                    (
                        f"  - `{language}` · ⭐ {stars} · "
                        f"Updated `{pushed_date}`"
                    ),
                ]
            )

    updated_at = datetime.now(
        ZoneInfo("America/Guayaquil")
    ).strftime("%Y-%m-%d %H:%M")

    lines.extend(
        [
            "",
            f"_Automatically updated on {updated_at} — Ecuador time._",
        ]
    )

    return "\n".join(lines)


def update_readme(dynamic_section: str) -> bool:
    """Replace the generated section and return whether the file changed."""

    if not README_PATH.exists():
        raise FileNotFoundError("README.md was not found.")

    current_content = README_PATH.read_text(encoding="utf-8")

    pattern = re.compile(
        rf"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}",
        flags=re.DOTALL,
    )

    if not pattern.search(current_content):
        raise ValueError(
            "The README does not contain the required generated-section markers."
        )

    replacement = (
        f"{START_MARKER}\n"
        f"{dynamic_section}\n"
        f"{END_MARKER}"
    )

    new_content = pattern.sub(replacement, current_content)

    if new_content == current_content:
        print("README.md is already up to date.")
        return False

    README_PATH.write_text(new_content, encoding="utf-8")
    print("README.md updated successfully.")
    return True


def main() -> None:
    username = (
        os.getenv("GITHUB_USERNAME")
        or os.getenv("GITHUB_REPOSITORY_OWNER")
    )

    if not username:
        raise RuntimeError(
            "Set GITHUB_USERNAME locally or run this script in GitHub Actions."
        )

    print(f"Generating profile information for @{username}...")

    repositories = get_public_repositories(username)
    dynamic_section = generate_dynamic_section(username, repositories)
    update_readme(dynamic_section)


if __name__ == "__main__":
    main()