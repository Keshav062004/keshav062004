import argparse
from collections import Counter
from html import escape
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen


USERNAME = "Keshav062004"
API_URL = f"https://api.github.com/users/{USERNAME}/repos"
PAGE_SIZE = 100
LANGUAGE_COLORS = {
    "JavaScript": "#E5B5C7",
    "HTML": "#C77B9B",
    "Jupyter Notebook": "#A84D75",
    "TypeScript": "#701A3D",
    "Python": "#B6A3AC",
    "Other": "#451126",
}
FALLBACK_COLORS = ("#C77B9B", "#A84D75", "#701A3D", "#E5B5C7", "#B6A3AC")


def fetch_language_counts(token: str | None) -> Counter[str]:
    counts: Counter[str] = Counter()
    page = 1
    while True:
        request = Request(
            f"{API_URL}?type=owner&per_page={PAGE_SIZE}&page={page}",
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "KeshavGupta-Profile-Language-Card",
                **({"Authorization": f"Bearer {token}"} if token else {}),
            },
        )
        with urlopen(request, timeout=30) as response:
            repositories = json.load(response)
        if not isinstance(repositories, list):
            raise RuntimeError("GitHub repository API returned an unexpected response")

        for repository in repositories:
            if not isinstance(repository, dict):
                raise RuntimeError("GitHub repository API returned an invalid repository")
            language = repository.get("language")
            if not repository.get("fork") and isinstance(language, str) and language:
                counts[language] += 1

        if len(repositories) < PAGE_SIZE:
            break
        page += 1

    if not counts:
        raise RuntimeError("No public repository language data was returned by GitHub")
    return counts


def language_color(language: str, index: int) -> str:
    return LANGUAGE_COLORS.get(language, FALLBACK_COLORS[index % len(FALLBACK_COLORS)])


def render_svg(language_counts: Counter[str]) -> str:
    total = sum(language_counts.values())
    if total < 1:
        raise ValueError("At least one language count is required")

    ranked = sorted(language_counts.items(), key=lambda item: (-item[1], item[0].casefold()))
    rows = ranked[:5]
    other_count = total - sum(count for _, count in rows)
    if other_count:
        rows.append(("Other", other_count))

    center_x, center_y, radius = 780, 166, 68
    circumference = 2 * 3.141592653589793 * radius
    segment_markup = []
    offset = 0.0
    for index, (language, count) in enumerate(rows):
        arc_length = circumference * count / total
        visible_length = max(0.0, arc_length - 2.5)
        color = language_color(language, index)
        segment_markup.append(
            f'<circle cx="{center_x}" cy="{center_y}" r="{radius}" fill="none" '
            f'stroke="{color}" stroke-width="22" stroke-linecap="round" '
            f'stroke-dasharray="{visible_length:.2f} {circumference - visible_length:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}">'
            f'<animate attributeName="stroke-opacity" values="0.72;1;0.72" '
            f'dur="{3.2 + index * 0.35:.2f}s" begin="{index * 0.16:.2f}s" '
            'repeatCount="indefinite"/></circle>'
        )
        offset += arc_length

    row_markup = []
    for index, (language, count) in enumerate(rows):
        y = 137 + index * 25
        share = count / total
        bar_width = 286 * share
        color = language_color(language, index)
        row_markup.append(
            f'<rect x="52" y="{y - 10}" width="9" height="9" rx="2" fill="{color}"/>'
            f'<text x="72" y="{y}" fill="#F8F0F3" font-family="Segoe UI, Arial, sans-serif" '
            f'font-size="13">{escape(language)}</text>'
            f'<rect x="210" y="{y - 8}" width="286" height="6" rx="3" fill="#27101C"/>'
            f'<rect x="210" y="{y - 8}" width="0" height="6" rx="3" fill="{color}">'
            f'<animate attributeName="width" from="0" to="{bar_width:.2f}" '
            f'dur="{1.4 + index * 0.12:.2f}s" begin="{index * 0.1:.2f}s" '
            'fill="freeze"/></rect>'
            f'<text x="514" y="{y}" fill="#E5B5C7" font-family="Consolas, monospace" '
            f'font-size="11" text-anchor="end">{count} repo{"s" if count != 1 else ""} '
            f'· {share * 100:.1f}%</text>'
        )

    description = "; ".join(
        f"{language}: {count} repositories" for language, count in rows
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="320" viewBox="0 0 1000 320" role="img" aria-labelledby="lang-title lang-desc">
  <title id="lang-title">Animated language mix across public repositories</title>
  <desc id="lang-desc">Primary repository languages for {total} public, non-fork repositories. {escape(description)}. Refreshed daily from GitHub.</desc>
  <defs>
    <linearGradient id="lang-bg" x1="0" y1="0" x2="1" y2="1">
      <stop stop-color="#10070C"/>
      <stop offset="0.62" stop-color="#190B12"/>
      <stop offset="1" stop-color="#27101C"/>
    </linearGradient>
    <radialGradient id="lang-glow" cx="70%" cy="35%" r="65%">
      <stop stop-color="#C77B9B" stop-opacity="0.18"/>
      <stop offset="1" stop-color="#701A3D" stop-opacity="0"/>
      <animate attributeName="cx" values="62%;80%;62%" dur="8s" repeatCount="indefinite"/>
    </radialGradient>
    <linearGradient id="lang-border" x1="0" y1="0" x2="1" y2="0">
      <stop stop-color="#701A3D"/>
      <stop offset="0.5" stop-color="#C77B9B"/>
      <stop offset="1" stop-color="#701A3D"/>
    </linearGradient>
    <pattern id="lang-grid" width="28" height="28" patternUnits="userSpaceOnUse">
      <path d="M28 0H0V28" fill="none" stroke="#E5B5C7" stroke-opacity="0.035"/>
    </pattern>
  </defs>
  <rect x="1" y="1" width="998" height="318" rx="18" fill="url(#lang-bg)" stroke="#451126"/>
  <rect x="2" y="2" width="996" height="316" rx="17" fill="url(#lang-grid)"/>
  <rect x="2" y="2" width="996" height="316" rx="17" fill="url(#lang-glow)"/>
  <path d="M48 112H568" stroke="url(#lang-border)" stroke-opacity="0.55"/>
  <text x="48" y="39" fill="#C77B9B" font-family="Consolas, monospace" font-size="10" letter-spacing="2">REPOSITORY LANGUAGE MIX</text>
  <text x="48" y="78" fill="#F8F0F3" font-family="Segoe UI, Arial, sans-serif" font-size="27" font-weight="700">A language for every idea.</text>
  <text x="48" y="99" fill="#B6A3AC" font-family="Segoe UI, Arial, sans-serif" font-size="12">Primary language per public repository · refreshed daily from GitHub</text>
  {''.join(row_markup)}
  <circle cx="{center_x}" cy="{center_y}" r="84" fill="none" stroke="#701A3D" stroke-opacity="0.3" stroke-width="1" stroke-dasharray="2 14">
    <animate attributeName="stroke-dashoffset" from="0" to="-80" dur="7s" repeatCount="indefinite"/>
  </circle>
  <g>
    <animateTransform attributeName="transform" type="rotate" values="-90 {center_x} {center_y};270 {center_x} {center_y}" dur="42s" repeatCount="indefinite"/>
    <circle cx="{center_x}" cy="{center_y}" r="{radius}" fill="none" stroke="#27101C" stroke-width="22"/>
    {''.join(segment_markup)}
  </g>
  <circle cx="{center_x}" cy="{center_y}" r="48" fill="#10070C" fill-opacity="0.9"/>
  <text x="{center_x}" y="{center_y - 2}" text-anchor="middle" fill="#F8F0F3" font-family="Segoe UI, Arial, sans-serif" font-size="23" font-weight="700">{total}</text>
  <text x="{center_x}" y="{center_y + 17}" text-anchor="middle" fill="#C77B9B" font-family="Consolas, monospace" font-size="8" letter-spacing="1">REPOS WITH CODE</text>
  <text x="48" y="295" fill="#C77B9B" font-family="Consolas, monospace" font-size="9" letter-spacing="1">PUBLIC REPOSITORY DATA  /  UPDATED DAILY</text>
</svg>
'''


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an animated repository-language SVG")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "dist/keshav-languages.svg",
    )
    args = parser.parse_args()

    svg = render_svg(fetch_language_counts(os.environ.get("GITHUB_TOKEN")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = args.output.with_name(f"{args.output.name}.tmp")
    temporary_path.write_text(svg, encoding="utf-8")
    temporary_path.replace(args.output)
    print(f"Generated {args.output}")


if __name__ == "__main__":
    main()
