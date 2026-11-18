from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


PROFILE_CONTRIBUTIONS_URL = "https://github.com/users/Keshav062004/contributions"
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "dist/github-contribution-calendar.svg"
CELL_SIZE = 12
CELL_GAP = 4
GRID_LEFT = 38
GRID_TOP = 25
MONTHS = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)
LEVEL_COLORS = ("#21121A", "#451126", "#701A3D", "#A84D75", "#E5B5C7")


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
        if not 0 <= level < len(LEVEL_COLORS):
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


def render_calendar(levels: dict[date, int]) -> str:
    first_day = min(levels)
    first_sunday = first_day - timedelta(days=(first_day.weekday() + 1) % 7)
    last_day = max(levels)
    weeks = (last_day - first_sunday).days // 7 + 1
    step = CELL_SIZE + CELL_GAP
    width = GRID_LEFT + weeks * step + 8
    height = GRID_TOP + 7 * step + 10

    route_points = []
    for week in range(weeks):
        weekdays = range(7) if week % 2 == 0 else range(6, -1, -1)
        for weekday in weekdays:
            x = GRID_LEFT + week * step + CELL_SIZE // 2
            y = GRID_TOP + weekday * step + CELL_SIZE // 2
            route_points.append((x, y))
    route = f"M {route_points[0][0]} {route_points[0][1]} " + " ".join(
        f"L {x} {y}" for x, y in route_points[1:]
    )

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {width} {height}" '
        f'width="100%" role="img" aria-labelledby="title description">',
        "<title id=\"title\">GitHub contribution calendar</title>",
        "<desc id=\"description\">Daily contributions over the past year, with a moving snake. "
        "Months are labeled above and Monday, Wednesday, and Friday at the left.</desc>",
        '<rect width="100%" height="100%" rx="10" fill="#10070C"/>',
        f'<defs><path id="snake-route" d="{route}"/></defs>',
    ]

    seen_months: set[tuple[int, int]] = set()
    for day in sorted(levels):
        month = (day.year, day.month)
        if month not in seen_months:
            week = (day - first_sunday).days // 7
            x = GRID_LEFT + week * step
            elements.append(
                f'<text x="{x}" y="16" fill="#E5B5C7" font-family="Segoe UI, Arial, sans-serif" '
                f'font-size="11">{MONTHS[day.month - 1]}</text>'
            )
            seen_months.add(month)

    for weekday, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        y = GRID_TOP + weekday * step + CELL_SIZE / 2
        elements.append(
            f'<text x="{GRID_LEFT - 8}" y="{y:g}" fill="#E5B5C7" '
            f'font-family="Segoe UI, Arial, sans-serif" font-size="10" '
            f'text-anchor="end" dominant-baseline="middle">{label}</text>'
        )

    for day, level in sorted(levels.items()):
        week = (day - first_sunday).days // 7
        weekday = (day.weekday() + 1) % 7
        x = GRID_LEFT + week * step
        y = GRID_TOP + weekday * step
        elements.append(
            f'<rect x="{x}" y="{y}" width="{CELL_SIZE}" height="{CELL_SIZE}" rx="2" '
            f'fill="{LEVEL_COLORS[level]}"><title>{day.isoformat()}: '
            f'contribution level {level} of 4</title></rect>'
        )

    duration = 42
    step_duration = duration / (len(route_points) - 1)
    segments = (
        (4.5, "#C77B9B", 0.82),
        (4.2, "#C77B9B", 0.68),
        (3.9, "#C77B9B", 0.54),
        (3.6, "#C77B9B", 0.4),
        (3.3, "#C77B9B", 0.28),
        (5, "#F8F0F3", 1),
    )
    for index, (radius, color, opacity) in enumerate(segments):
        begin = -index * step_duration
        elements.append(
            f'<circle r="{radius:g}" fill="{color}" fill-opacity="{opacity:g}" '
            'stroke="#451126" stroke-width="1">'
            f'<animateMotion dur="{duration}s" begin="{begin:.3f}s" '
            'repeatCount="indefinite"><mpath xlink:href="#snake-route"/>'
            '</animateMotion></circle>'
        )

    elements.append("</svg>")
    return "\n".join(elements) + "\n"


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(render_calendar(fetch_contributions()), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
