"""Clean generated noise and straighten long mask boundaries."""

from collections import Counter, defaultdict
import argparse
from pathlib import Path
from statistics import median

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MASK_FOLDER = (
    PROJECT_ROOT
    / "docs"
    / "archive"
    / "old_podium_iterations"
    / "02_3d_second_attempt"
)
OUTPUT_FOLDER = Path(__file__).with_name("cleaned_segmentation_mask_previews")
STRONG_ALPHA = 64
MIN_HORIZONTAL_LENGTH = 300
MAX_BOUNDARY_ADJUSTMENT = 8
CORNER_GUARD = 12

TRANSPARENT = -1
PALETTE = (
    (255, 255, 0),
    (255, 0, 0),
    (0, 0, 255),
    (0, 255, 255),
    (255, 0, 255),
)


def nearest_class(red: int, green: int, blue: int) -> int:
    return min(
        range(len(PALETTE)),
        key=lambda index: (
            (red - PALETTE[index][0]) ** 2
            + (green - PALETTE[index][1]) ** 2
            + (blue - PALETTE[index][2]) ** 2
        ),
    )


def group_nearby_rows(rows: list[int], maximum_gap: int = 4) -> list[tuple[int, int]]:
    groups: list[tuple[int, int]] = []
    start = previous = rows[0]
    for row in rows[1:]:
        if row - previous > maximum_gap:
            groups.append((start, previous))
            start = row
        previous = row
    groups.append((start, previous))
    return groups


def consecutive_runs(values: list[int], maximum_gap: int = 64) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    start = previous = values[0]
    for value in values[1:]:
        if value - previous > maximum_gap:
            runs.append((start, previous))
            start = value
        previous = value
    runs.append((start, previous))
    return runs


def fit_line(points: list[tuple[int, int]]) -> tuple[float, float]:
    mean_x = sum(x for x, _ in points) / len(points)
    mean_y = sum(y for _, y in points) / len(points)
    denominator = sum((x - mean_x) ** 2 for x, _ in points)
    slope = sum((x - mean_x) * (y - mean_y) for x, y in points) / denominator
    return slope, mean_y - slope * mean_x


def remove_interior_speckles(labels: list[list[int]], width: int, height: int) -> None:
    """Remove isolated class pixels without changing the exterior silhouette."""

    cleaned = [column[:] for column in labels]
    for x in range(1, width - 1):
        for y in range(1, height - 1):
            neighborhood = [
                labels[near_x][near_y]
                for near_x in range(x - 1, x + 2)
                for near_y in range(y - 1, y + 2)
            ]
            if TRANSPARENT in neighborhood:
                continue
            most_common, count = Counter(neighborhood).most_common(1)[0]
            if count >= 5:
                cleaned[x][y] = most_common

    for x in range(width):
        labels[x][:] = cleaned[x]


def flatten_transition_rows(labels: list[list[int]], width: int, height: int) -> None:
    """Resolve alternating pixels along otherwise continuous horizontal edges."""

    cleaned = [column[:] for column in labels]
    for y in range(1, height - 1):
        columns_by_transition: dict[tuple[int, int], list[int]] = defaultdict(list)
        for x in range(width):
            above, current, below = labels[x][y - 1], labels[x][y], labels[x][y + 1]
            if (
                above != below
                and TRANSPARENT not in (above, below)
                and current != TRANSPARENT
            ):
                columns_by_transition[(above, below)].append(x)

        for (above, below), columns in columns_by_transition.items():
            for run_start, run_end in consecutive_runs(columns, maximum_gap=1):
                if run_end - run_start < MIN_HORIZONTAL_LENGTH:
                    continue
                guarded_start = run_start + CORNER_GUARD
                guarded_end = run_end - CORNER_GUARD
                counts = Counter(
                    labels[x][y] for x in range(guarded_start, guarded_end + 1)
                )
                replacement = above if counts[above] >= counts[below] else below
                for x in range(guarded_start, guarded_end + 1):
                    cleaned[x][y] = replacement

    for x in range(width):
        labels[x][:] = cleaned[x]


def straighten_transition_segment(
    labels: list[list[int]],
    start_x: int,
    end_x: int,
    target_y: int,
    above: int,
    below: int,
) -> None:
    """Move a known nearly-level interior transition onto one exact row."""

    for x in range(start_x, end_x + 1):
        old_rows = [
            y
            for y in range(target_y - 2, target_y + 3)
            if labels[x][y - 1] == above and labels[x][y] == below
        ]
        if not old_rows:
            continue
        old_y = min(old_rows, key=lambda y: abs(y - target_y))
        if target_y > old_y:
            for y in range(old_y, target_y):
                labels[x][y] = above
        elif target_y < old_y:
            for y in range(target_y, old_y):
                labels[x][y] = below


def straighten_exterior_top_segment(
    labels: list[list[int]],
    start_x: int,
    end_x: int,
    target_y: int,
    fill_label: int,
) -> None:
    """Level a straight silhouette run without extending into its corners."""

    for x in range(start_x, end_x + 1):
        visible_rows = [
            y
            for y in range(target_y - 2, target_y + 3)
            if labels[x][y] != TRANSPARENT
        ]
        if not visible_rows:
            continue
        old_y = min(visible_rows)
        if target_y < old_y:
            for y in range(target_y, old_y):
                labels[x][y] = fill_label
        elif target_y > old_y:
            for y in range(old_y, target_y):
                labels[x][y] = TRANSPARENT


def straighten_vertical_transition_segment(
    labels: list[list[int]],
    start_y: int,
    end_y: int,
    target_x: int,
    left: int,
    right: int,
) -> None:
    """Move a nearly-level vertical transition onto one exact column."""

    for y in range(start_y, end_y + 1):
        old_columns = [
            x
            for x in range(target_x - 2, target_x + 3)
            if labels[x - 1][y] == left and labels[x][y] == right
        ]
        if not old_columns:
            continue
        old_x = min(old_columns, key=lambda x: abs(x - target_x))
        if target_x > old_x:
            for x in range(old_x, target_x):
                labels[x][y] = left
        elif target_x < old_x:
            for x in range(target_x, old_x):
                labels[x][y] = right


def repair_known_mask_artifacts(labels: list[list[int]], filename: str) -> None:
    """Apply narrow corrections where generated geometry defeats heuristics."""

    if filename == "01x_x_short_segmentation_mask.png":
        # The front inset's lower red edge alternates between rows 747 and 748.
        # Stop before both notch diagonals and the rounded outer corners.
        straighten_transition_segment(labels, 146, 361, 748, above=1, below=4)
        straighten_transition_segment(labels, 852, 1070, 748, above=1, below=4)

        # Lock every straight vertical boundary on the front face.  Each span
        # ends before its rounded top and bottom corner transitions.
        straighten_vertical_transition_segment(
            labels, 701, 747, 98, left=2, right=3
        )
        straighten_vertical_transition_segment(
            labels, 704, 737, 118, left=3, right=2
        )
        straighten_vertical_transition_segment(
            labels, 707, 742, 129, left=2, right=4
        )
        straighten_vertical_transition_segment(
            labels, 708, 741, 138, left=4, right=1
        )
        straighten_vertical_transition_segment(
            labels, 707, 742, 1075, left=1, right=4
        )
        straighten_vertical_transition_segment(
            labels, 708, 744, 1085, left=4, right=2
        )
        straighten_vertical_transition_segment(
            labels, 703, 747, 1095, left=2, right=3
        )
        straighten_vertical_transition_segment(
            labels, 703, 747, 1116, left=3, right=2
        )
    elif filename == "02x_short_segmentation_mask.png":
        # Level only the straight outer-top run; adjacent pixels belong to the
        # rounded corners and must retain their gradual vertical transition.
        straighten_exterior_top_segment(
            labels, 202, 1127, 473, fill_label=0
        )

        straighten_vertical_transition_segment(
            labels, 663, 776, 98, left=2, right=3
        )
        straighten_vertical_transition_segment(
            labels, 666, 770, 118, left=3, right=2
        )
        straighten_vertical_transition_segment(
            labels, 666, 765, 132, left=2, right=4
        )
        straighten_vertical_transition_segment(
            labels, 665, 764, 141, left=4, right=1
        )
        straighten_vertical_transition_segment(
            labels, 669, 761, 1064, left=1, right=4
        )
        straighten_vertical_transition_segment(
            labels, 664, 767, 1071, left=4, right=2
        )
        straighten_vertical_transition_segment(
            labels, 663, 775, 1084, left=2, right=3
        )
        straighten_vertical_transition_segment(
            labels, 662, 777, 1105, left=3, right=2
        )


def clean_mask(source_path: Path, output_path: Path) -> int:
    """Quantize a mask and straighten each long, nearly horizontal boundary."""

    with Image.open(source_path) as source:
        source = source.convert("RGBA")

    width, height = source.size
    source_pixels = source.load()
    labels = [[TRANSPARENT] * height for _ in range(width)]

    # Normalize the nearly transparent speckles and near-palette RGB values
    # found in the generated masks before analyzing their boundaries.
    for x in range(width):
        for y in range(height):
            red, green, blue, alpha = source_pixels[x, y]
            if alpha > STRONG_ALPHA:
                labels[x][y] = nearest_class(red, green, blue)

    remove_interior_speckles(labels, width, height)

    transitions: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
    for x in range(width):
        for y in range(1, height):
            above, below = labels[x][y - 1], labels[x][y]
            if above != below:
                transitions[(above, below)].append((x, y))

    straightened = 0
    for (above, below), points in transitions.items():
        # Never refit the exterior silhouette.  Its rounded corner transitions
        # must remain exactly where the source mask places them.
        if TRANSPARENT in (above, below):
            continue

        row_counts = Counter(y for _, y in points)
        dense_rows = sorted(y for y, count in row_counts.items() if count >= 40)
        if not dense_rows:
            continue

        for first_row, last_row in group_nearby_rows(dense_rows):
            candidates = [
                (x, y)
                for x, y in points
                if first_row - 3 <= y <= last_row + 3
            ]
            if not candidates:
                continue

            by_x: dict[int, list[int]] = defaultdict(list)
            for x, y in candidates:
                by_x[x].append(y)
            if max(by_x) - min(by_x) < MIN_HORIZONTAL_LENGTH:
                continue

            slope, intercept = fit_line(candidates)
            if abs(slope) > 0.02:
                continue

            # Select one transition per column and refit so nearby unrelated
            # edges cannot pull the final boundary away from its intended run.
            selected = [
                (x, min(ys, key=lambda y: abs(y - (slope * x + intercept))))
                for x, ys in by_x.items()
            ]
            clean_y = round(median(y for _, y in selected))
            stable_columns = sorted(
                x for x, old_y in selected if abs(old_y - clean_y) <= 2
            )

            for run_start, run_end in consecutive_runs(stable_columns):
                if run_end - run_start < MIN_HORIZONTAL_LENGTH:
                    continue
                guarded_start = run_start + CORNER_GUARD
                guarded_end = run_end - CORNER_GUARD

                for x in range(guarded_start, guarded_end + 1):
                    nearby_transitions = [
                        y
                        for y in range(
                            max(1, clean_y - MAX_BOUNDARY_ADJUSTMENT),
                            min(height, clean_y + MAX_BOUNDARY_ADJUSTMENT + 1),
                        )
                        if labels[x][y - 1] == above and labels[x][y] == below
                    ]
                    if not nearby_transitions:
                        continue
                    old_y = min(nearby_transitions, key=lambda y: abs(y - clean_y))
                    if clean_y > old_y:
                        for y in range(old_y, clean_y):
                            labels[x][y] = above
                    elif clean_y < old_y:
                        for y in range(clean_y, old_y):
                            labels[x][y] = below
            straightened += 1

    flatten_transition_rows(labels, width, height)
    repair_known_mask_artifacts(labels, source_path.name)

    result = Image.new("RGBA", source.size)
    result_pixels = result.load()
    for x in range(width):
        for y in range(height):
            label = labels[x][y]
            if label != TRANSPARENT:
                result_pixels[x, y] = (*PALETTE[label], 255)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(output_path)
    return straightened


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="replace the source masks after writing the preview copies",
    )
    parser.add_argument(
        "--only",
        help="clean only the segmentation mask with this exact filename",
    )
    args = parser.parse_args()

    source_paths = sorted(MASK_FOLDER.glob("*segmentation_mask.png"))
    if args.only:
        source_paths = [path for path in source_paths if path.name == args.only]
        if not source_paths:
            parser.error(f"mask not found: {args.only}")

    for source_path in source_paths:
        output_path = OUTPUT_FOLDER / source_path.name
        count = clean_mask(source_path, output_path)
        if args.apply:
            output_path.replace(source_path)
        print(f"Cleaned {source_path.name}: straightened {count} boundaries")


if __name__ == "__main__":
    main()
