import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class QualityChecker:
    BLUR_THRESHOLD = 100        # variance of the Laplacian
    DARK_THRESHOLD = 80         # median pixel intensity, i.e. the background
    BRIGHT_THRESHOLD = 150      # 0.1st-percentile pixel intensity, i.e. the darkest ink
    SKEW_THRESHOLD = 3.0        # degrees
    SKEW_MIN_LINES = 5          # text lines needed before the skew estimate is trusted
    SKEW_MIN_ASPECT = 3.0       # width / height of a text line whose edge angle is meaningful
    SKEW_MAX_LINE_ANGLE = 45.0  # degrees; steeper lines are vertical text, not skew
    TRUNCATION_MARGIN = 5       # pixels

    def __init__(self):
        pass

    def check_blur(self, frame: cv2.Mat, page_result: dict) -> list[str]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        return ["Image is blurry"] if laplacian_var < self.BLUR_THRESHOLD else []

    def check_skew(self, frame: cv2.Mat, page_result: dict) -> list[str]:
        # Get polygons from the OCR result
        ocr_result = page_result.get("overall_ocr_res", {})
        polygons = ocr_result.get("rec_polys") or ocr_result.get("dt_polys") or []
        angles = []

        for polygon in polygons:
            points = np.asarray(polygon, dtype=float)

            # Ensure the polygon has at least 4 points
            if points.ndim != 2 or points.shape[0] < 4 or points.shape[1] < 2:
                continue

            top_left, top_right, bottom_left = points[0][:2], points[1][:2], points[3][:2]
            width = np.linalg.norm(top_right - top_left)
            height = np.linalg.norm(bottom_left - top_left)

            # Short or square boxes (single characters, page numbers, cells) have no reliable direction
            if height == 0 or width / height < self.SKEW_MIN_ASPECT:
                continue

            # Signed angle of the top edge, so that small random tilts cancel out in the median
            dx, dy = top_right - top_left
            angle = float(np.degrees(np.arctan2(dy, dx)))
            if abs(angle) > self.SKEW_MAX_LINE_ANGLE:
                continue

            angles.append(angle)

        # Too few lines to tell a skewed page apart from a stray rotated stamp or label
        if len(angles) < self.SKEW_MIN_LINES:
            return []

        # A page is considered skewed if the median angle of its text lines exceeds the skew threshold
        median_angle = float(np.median(angles))
        if abs(median_angle) > self.SKEW_THRESHOLD:
            return [f"Image is skewed by {median_angle:.1f}°"]
        return []

    def check_truncation(self, frame: cv2.Mat, page_result: dict) -> list[str]:
        # Get polygons from the OCR result
        ocr_result = page_result.get("overall_ocr_res", {})
        polygons = ocr_result.get("rec_polys") or ocr_result.get("dt_polys") or []

        for polygon in polygons:
            points = np.asarray(polygon, dtype=float)

            # Ensure the polygon has at least 4 points
            if points.ndim != 2 or points.shape[0] < 4 or points.shape[1] < 2:
                continue

            # A polygon is considered truncated if any of its points are close to the image border
            h, w = frame.shape[:2]
            for point in points:
                x, y = point[:2]
                if x < self.TRUNCATION_MARGIN or \
                    x > w - self.TRUNCATION_MARGIN or \
                    y < self.TRUNCATION_MARGIN or \
                    y > h - self.TRUNCATION_MARGIN:
                    return ["Image is truncated"]

        return []

    def check_brightness(self, frame: cv2.Mat, page_result: dict) -> list[str]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if np.median(gray) < self.DARK_THRESHOLD:
            return ["Image is too dark"]
        elif np.percentile(gray, 0.1) > self.BRIGHT_THRESHOLD:
            return ["Image is too bright"]
        else:
            return []

    def check_quality(self, page_data: bytes, page_result: dict | None) -> list[str]:
        warnings: list[str] = []

        # A failed page has an empty or missing OCR result
        page_result = page_result or {}

        # Convert the page data to a numpy array
        nparr = np.frombuffer(page_data, np.uint8)

        # Decode the image
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            warnings.append("Failed to decode image")
            return warnings

        # A check that fails only loses its own warnings; it must never stop the page from being processed
        for check in (self.check_blur, self.check_skew, self.check_truncation, self.check_brightness):
            try:
                warnings.extend(check(img, page_result))
            except Exception:
                logger.exception(f"Quality check {check.__name__} failed")

        return warnings
