from typing import List, Tuple


class DataManager:
    def __init__(self):
        self.file_registry = {}  # {file_path: {"points": [], "bounds": {}}}

    def add_file(self, file_path: str, points: list):
        """Store points using your legacy format"""
        if not points:
            raise ValueError("No valid points found")

        self.file_registry[file_path] = {
            "points": points,
            "bounds": self._calculate_bounds(points),
        }

    def remove_file(self, file_path: str) -> None:
        """Completely purge a file's data"""
        if file_path in self.file_registry:
            del self.file_registry[file_path]

    def get_points_in_bounds(
        self, selection_bounds: dict
    ) -> List[Tuple[float, float]]:
        """Return all points from relevant files within current selection"""
        relevant_points = []

        for file_data in self.file_registry.values():
            if self._bounds_overlap(file_data["bounds"], selection_bounds):
                relevant_points.extend(
                    [
                        (lat, lon)
                        for lat, lon in file_data["points"]
                        if self._point_in_bounds((lat, lon), selection_bounds)
                    ]
                )

        return relevant_points

    def _calculate_bounds(self, points):
        """Your original bounds calculation"""
        lats = [p[0] for p in points]
        lons = [p[1] for p in points]
        return {
            "min_lat": min(lats),
            "max_lat": max(lats),
            "min_lon": min(lons),
            "max_lon": max(lons),
        }

    def _bounds_overlap(
        self, file_bounds: dict, selection_bounds: dict
    ) -> bool:
        """Fast preliminary check using precomputed bounds"""
        return not (
            file_bounds["max_lat"] < selection_bounds["sw"][0]
            or file_bounds["min_lat"] > selection_bounds["nw"][0]
            or file_bounds["max_lon"] < selection_bounds["nw"][1]
            or file_bounds["min_lon"] > selection_bounds["ne"][1]
        )

    def _point_in_bounds(self, point: tuple, selection_bounds: dict) -> bool:
        """Precise point-in-polygon check"""
        # Implementation depends on your bounds format
        # Simplified example using rectangular bounds:
        lat, lon = point
        return (
            selection_bounds["sw"][0] <= lat <= selection_bounds["nw"][0]
            and selection_bounds["nw"][1] <= lon <= selection_bounds["ne"][1]
        )
