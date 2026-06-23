"""The pure inline-SVG sparkline helper (developer-dashboard §5.2, DD-DESIGN-5).

Pure unit tests (no DB): coordinate math, the empty/all-zero → None guard, and the
single-bucket degenerate-axis guard. Asserts the module pulls in no app dependency.
"""

import ast
import inspect
from dataclasses import dataclass

from django.test import SimpleTestCase

from apps.dashboard import charts


@dataclass(frozen=True)
class _Bucket:
    """A minimal TrendBucket-shaped stand-in (charts duck-types ``.total`` / ``.curated``)."""

    total: int
    curated: int


class BuildSparklineTests(SimpleTestCase):
    def test_one_point_per_bucket_on_both_lines(self):
        buckets = [_Bucket(10, 4), _Bucket(20, 5), _Bucket(0, 0), _Bucket(15, 15)]
        svg = charts.build_sparkline(buckets)

        self.assertIsNotNone(svg)
        self.assertEqual(len(svg.total_points.split()), 4)
        self.assertEqual(len(svg.curated_points.split()), 4)

    def test_curated_line_differs_from_total_line(self):
        buckets = [_Bucket(10, 1), _Bucket(20, 2)]
        svg = charts.build_sparkline(buckets)
        self.assertNotEqual(svg.total_points, svg.curated_points)

    def test_max_value_maps_to_the_top_of_the_chart(self):
        # The largest total sits at y == 0 (top); a zero value sits at y == height (bottom).
        buckets = [_Bucket(0, 0), _Bucket(50, 10)]
        svg = charts.build_sparkline(buckets)
        ys = [float(point.split(",")[1]) for point in svg.total_points.split()]
        self.assertEqual(ys[1], 0.0)
        self.assertEqual(ys[0], svg.height)

    def test_empty_series_returns_none(self):
        self.assertIsNone(charts.build_sparkline([]))

    def test_all_zero_series_returns_none(self):
        self.assertIsNone(charts.build_sparkline([_Bucket(0, 0), _Bucket(0, 0)]))

    def test_single_bucket_has_no_divide_by_zero(self):
        svg = charts.build_sparkline([_Bucket(7, 3)])
        self.assertIsNotNone(svg)
        self.assertEqual(len(svg.total_points.split()), 1)


class ChartsIsolationTests(SimpleTestCase):
    def test_imports_nothing_from_apps(self):
        tree = ast.parse(inspect.getsource(charts))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
        self.assertEqual(
            {name for name in imported if name.startswith("apps")},
            set(),
            "charts.py must stay free of app dependencies (DESIGN §5.2)",
        )
