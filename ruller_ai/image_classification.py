"""Optional local-only image classification helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def classify_image(path: str | Path, model_path: str | Path, *, top_k: int = 5) -> list[dict[str, Any]]:
    """Classify an image with a Transformers model already present on disk.

    The helper never downloads a model. Both the image and model directory must
    be selected explicitly by the user; optional ML dependencies are only loaded
    when this function is called.
    """
    image_path = Path(path).expanduser()
    model_dir = Path(model_path).expanduser()
    if not image_path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")
    if not model_dir.is_dir():
        raise FileNotFoundError(f"Local model directory not found: {model_dir}")
    if image_path.stat().st_size > 20 * 1024 * 1024:
        raise ValueError("Image files larger than 20 MB are not accepted.")
    try:
        from PIL import Image
        from transformers import pipeline
    except ImportError as exc:
        raise RuntimeError(
            "Image classification requires the optional 'pillow', 'torch', and 'transformers' packages. "
            "Install them with: pip install 'ultron-1-0[image-classification]'"
        ) from exc
    try:
        with Image.open(image_path) as image:
            image = image.convert("RGB")
            classifier = pipeline(
                "image-classification", model=str(model_dir), local_files_only=True,
            )
            results = classifier(image, top_k=max(1, min(int(top_k), 10)))
    except Exception as exc:
        raise RuntimeError(f"Image classification failed: {exc}") from exc
    if not isinstance(results, list):
        raise RuntimeError("The local classifier returned an unexpected result.")
    return [
        {"label": str(item.get("label", "unknown")), "score": float(item.get("score", 0.0))}
        for item in results if isinstance(item, dict)
    ]


def format_classification(path: str | Path, results: list[dict[str, Any]]) -> str:
    lines = [f"Image classification for {Path(path)} (local model; prediction, not certainty):"]
    lines.extend(f"- {item['label']}: {item['score']:.3f}" for item in results)
    if not results:
        lines.append("- No labels returned.")
    return "\n".join(lines)
