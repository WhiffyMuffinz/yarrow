from abc import ABC, abstractmethod
from typing import List, Dict, Any

class LayoutResult:
    def __init__(self, regions: List[Dict[str, Any]]):
        self.regions = regions

class InferenceClient(ABC):
    @abstractmethod
    def parse_page_layout(self, image_bytes: bytes) -> LayoutResult:
        pass

class MockInferenceClient(InferenceClient):
    def parse_page_layout(self, image_bytes: bytes) -> LayoutResult:
        # Returning deterministic mock layout
        return LayoutResult(
            regions=[
                {"type": "header", "box": [0.1, 0.1, 0.9, 0.15], "text": "Mock Header"},
                {"type": "paragraph", "box": [0.1, 0.2, 0.9, 0.4], "text": "This is a mock paragraph."},
                {"type": "table", "box": [0.1, 0.5, 0.9, 0.8]}
            ]
        )

class VLLMInferenceClient(InferenceClient):
    def parse_page_layout(self, image_bytes: bytes) -> LayoutResult:
        # Stub for production inference
        return LayoutResult(regions=[])

