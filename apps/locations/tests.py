from django.test import TestCase

from .services import bounding_box, haversine_km


class DistanceTests(TestCase):
    def test_haversine_zero_for_same_point(self):
        self.assertAlmostEqual(haversine_km(40.4, 49.8, 40.4, 49.8), 0.0, places=5)

    def test_haversine_known_distance(self):
        # Baku centre to ~ Sumqayit ≈ 25–35 km.
        d = haversine_km(40.4093, 49.8671, 40.5897, 49.6686)
        self.assertTrue(20 < d < 40, f"unexpected distance {d}")

    def test_bounding_box_contains_point(self):
        min_lat, max_lat, min_lng, max_lng = bounding_box(40.4093, 49.8671, 10)
        self.assertLess(min_lat, 40.4093)
        self.assertGreater(max_lat, 40.4093)
        self.assertLess(min_lng, 49.8671)
        self.assertGreater(max_lng, 49.8671)
