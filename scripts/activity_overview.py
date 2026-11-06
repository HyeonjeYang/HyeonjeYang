"""Draw GitHub's "Activity overview" cross as an SVG for the profile README.

GitHub has no embeddable image for this chart, so we rebuild it from the same
contribution totals. Needs GITHUB_TOKEN. Covers the last 12 months.
"""

import json
import os
import urllib.request
from pathlib import Path

LOGIN = os.environ.get("GITHUB_REPOSITORY_OWNER", "HyeonjeYang")
OUTPUT = Path(__file__).resolve().parent.parent / "assets" / "activity-overview.svg"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
    }
  }
}
"""

WIDTH, HEIGHT = 460, 284
CX, CY = 230, 160
ARM = 70
GAP = 14  # space between the end of an arm and its label


def fetch_counts(token):
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "profile-activity-overview",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)

    # Fail the run instead of overwriting the chart with an empty one.
    if payload.get("errors") or not (payload.get("data") or {}).get("user"):
        raise RuntimeError(f"GitHub API returned no data: {payload}")

    totals = payload["data"]["user"]["contributionsCollection"]
    return {
        "commits": totals["totalCommitContributions"],
        "pull_requests": totals["totalPullRequestContributions"],
        "issues": totals["totalIssueContributions"],
        "reviews": totals["totalPullRequestReviewContributions"],
    }


def label(x, y, anchor, percent, name):
    return (
        f'<text class="pct" x="{x}" y="{y}" text-anchor="{anchor}">{percent}%</text>'
        f'<text class="name" x="{x}" y="{y + 15}" text-anchor="{anchor}">{name}</text>'
    )


def render(counts):
    total = sum(counts.values())
    share = {key: value / total if total else 0 for key, value in counts.items()}
    pct = {key: round(value * 100) for key, value in share.items()}

    # Same layout as GitHub: reviews up, issues right, PRs down, commits left.
    points = [
        (CX, CY - ARM * share["reviews"]),
        (CX + ARM * share["issues"], CY),
        (CX, CY + ARM * share["pull_requests"]),
        (CX - ARM * share["commits"], CY),
    ]
    polygon = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    summary = (
        f"Last 12 months: {pct['commits']}% commits, "
        f"{pct['pull_requests']}% pull requests, "
        f"{pct['issues']}% issues, {pct['reviews']}% code review"
    )
    ends = [(CX, CY - ARM), (CX + ARM, CY), (CX, CY + ARM), (CX - ARM, CY)]

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img">
<title>{summary}</title>
<style>
text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }}
.title {{ font-size: 15px; font-weight: 600; fill: #E0568B; }}
.range {{ font-size: 12px; fill: #A99BB0; }}
.pct {{ font-size: 15px; font-weight: 600; fill: #5C5470; }}
.name {{ font-size: 12px; fill: #5C5470; }}
</style>
<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="14" fill="#FFF6FB" stroke="#F2D6E6"/>
<path transform="translate(22 21) scale(0.8)" fill="#E0568B" d="M7 13S0 8.6 0 4a3.8 3.8 0 0 1 7-2 3.8 3.8 0 0 1 7 2c0 4.6-7 9-7 9z"/>
<text class="title" x="38" y="32">what I've been up to</text>
<text class="range" x="{WIDTH - 22}" y="32" text-anchor="end">last 12 months</text>
<g stroke="#E0568B" stroke-width="2" stroke-linecap="round">
<line x1="{CX - ARM}" y1="{CY}" x2="{CX + ARM}" y2="{CY}"/>
<line x1="{CX}" y1="{CY - ARM}" x2="{CX}" y2="{CY + ARM}"/>
</g>
<polygon points="{polygon}" fill="#E0568B" fill-opacity="0.45" stroke="#E0568B" stroke-width="3" stroke-linejoin="round"/>
<g fill="#FFF6FB" stroke="#E0568B" stroke-width="2">
{chr(10).join(f'<circle cx="{x}" cy="{y}" r="4"/>' for x, y in ends)}
</g>
{label(CX, CY - ARM - GAP - 15, "middle", pct["reviews"], "Code review")}
{label(CX + ARM + GAP, CY - 2, "start", pct["issues"], "Issues")}
{label(CX, CY + ARM + GAP + 6, "middle", pct["pull_requests"], "Pull requests")}
{label(CX - ARM - GAP, CY - 2, "end", pct["commits"], "Commits")}
</svg>
"""


def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is not set")

    svg = render(fetch_counts(token))
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(svg, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
