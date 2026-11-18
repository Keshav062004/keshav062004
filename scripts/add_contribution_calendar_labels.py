from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.request import Request, urlopen


PROFILE_CONTRIBUTIONS_URL = "https://github.com/users/Keshav062004/contributions"
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "dist/github-contribution-calendar.svg"
MONTHS = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)


class ContributionParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.levels: dict[date, int] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "td":
            return

        attributes = dict(attrs)
        date_text = attributes.get("data-date")
        level_text = attributes.get("data-level")
        if date_text is None or level_text is None:
            return

        day = date.fromisoformat(date_text)
        level = int(level_text)
        if not 0 <= level <= 4:
            raise ValueError(f"Unexpected contribution level {level} for {day}")
        if day in self.levels:
            raise ValueError(f"Duplicate contribution date: {day}")
        self.levels[day] = level


def fetch_contributions() -> dict[date, int]:
    request = Request(
        PROFILE_CONTRIBUTIONS_URL,
        headers={"User-Agent": "KeshavGupta-Profile-Contribution-Calendar"},
    )
    with urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8")

    parser = ContributionParser()
    parser.feed(html)
    if not parser.levels:
        raise RuntimeError("GitHub's contribution calendar contained no daily data")
    return parser.levels


def main() -> None:
    levels = fetch_contributions()
    svg = OUTPUT_PATH.read_text(encoding="utf-8")
    viewbox_match = re.search(
        r'(<svg\b[^>]*\bviewBox=")(-?\d+(?:\.\d+)?)[,\s]+'
        r'(-?\d+(?:\.\d+)?)[,\s]+(\d+(?:\.\d+)?)[,\s]+(\d+(?:\.\d+)?)(")',
        svg,
    )
    if viewbox_match is None:
        raise RuntimeError("Generated snake SVG has no supported viewBox")

    x_min, y_min, view_width, view_height = map(float, viewbox_match.groups()[1:5])
    cell_x = min(
        int(re.search(r'\bx="(-?\d+)"', tag).group(1))
        for tag in re.findall(r"<rect\b[^>]*>", svg)
        if re.search(r'\bclass="c(?:\s+[^"]*)?"', tag)
    )
    new_x_min = min(x_min, cell_x - 30)
    new_view_width = x_min + view_width - new_x_min
    viewbox = (
        f"{new_x_min:g} {y_min:g} {new_view_width:g} {view_height:g}"
    )
    svg = svg[:viewbox_match.start(2)] + viewbox + svg[viewbox_match.end(5):]
    labels = add_calendar_labels(levels)
    svg = svg.replace("</svg>", f"{labels}</svg>", 1)
    svg = re.sub(r'<rect class="u(?:\s+[^"]*)?"[^>]*/>', "", svg)
    temporary_path = OUTPUT_PATH.with_name(f"{OUTPUT_PATH.name}.tmp")
    temporary_path.write_text(svg, encoding="utf-8")
    temporary_path.replace(OUTPUT_PATH)
    print(f"Added calendar labels to {OUTPUT_PATH}")


def add_calendar_labels(levels: dict[date, int]) -> str:
    svg = OUTPUT_PATH.read_text(encoding="utf-8")
    if "calendar-month-label" in svg:
        raise ValueError("Calendar labels are already present")

    cell_rects = [
        tag
        for tag in re.findall(r"<rect\b[^>]*>", svg)
        if re.search(r'\bclass="c(?:\s+[^"]*)?"', tag)
    ]
    x_positions = sorted({
        int(re.search(r'\bx="(-?\d+)"', tag).group(1))
        for tag in cell_rects
    })
    y_positions = sorted({
        int(re.search(r'\by="(-?\d+)"', tag).group(1))
        for tag in cell_rects
    })
    if len(x_positions) < 52 or len(y_positions) != 7:
        raise RuntimeError(
            f"Expected a weekly contribution grid; found {len(x_positions)} columns "
            f"and {len(y_positions)} rows"
        )

    first_day = min(levels)
    first_sunday = first_day - timedelta(days=(first_day.weekday() + 1) % 7)
    labels = []
    seen_months: set[tuple[int, int]] = set()
    for day in sorted(levels):
        month = (day.year, day.month)
        if month not in seen_months:
            week = (day - first_sunday).days // 7
            if week >= len(x_positions):
                raise RuntimeError(f"No contribution column found for {day}")
            labels.append(
                f'<text class="calendar-month-label" x="{x_positions[week]}" '
                f'y="{y_positions[0] - 14}" fill="#E5B5C7" '
                'font-family="Segoe UI, Arial, sans-serif" font-size="11">'
                f'{MONTHS[day.month - 1]}</text>'
            )
            seen_months.add(month)

    for weekday, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        y = y_positions[weekday] + 6
        labels.append(
            f'<text class="calendar-weekday-label" x="{x_positions[0] - 8}" y="{y}" '
            'fill="#E5B5C7" font-family="Segoe UI, Arial, sans-serif" '
            f'font-size="10" text-anchor="end" dominant-baseline="middle">{label}</text>'
        )
    return "\n".join(labels)


if __name__ == "__main__":
    main()
