"""Higgsfield DoP image-to-video provider via higgsfield-client SDK."""
import json
import os
from pathlib import Path

import higgsfield_client as hf
import httpx

from src.config import Config
from src.models import Scene, Transition
from src.utils import retry


class HiggsfieldProvider:
    """Higgsfield DoP (Director of Photography) image-to-video.

    Uses the `first-last-frame` variant that interpolates motion between a
    start frame and an end frame. Fixed ~5s clip duration per generation.

    Tiers (from Higgsfield pricing):
        - lite      ~$0.125 / clip (cheapest, slow queue on free plan)
        - turbo     ~$0.406 / clip (2x faster)
        - standard  ~$0.563 / clip (best quality, priority queue)
    """

    label = "higgsfield"
    APP_TEMPLATE = "higgsfield-ai/dop/{tier}/first-last-frame"

    def __init__(self, config: Config):
        if not (config.higgsfield_api_key and config.higgsfield_api_secret):
            raise RuntimeError(
                "Brak HIGGSFIELD_API_KEY / HIGGSFIELD_API_SECRET w .env"
            )
        os.environ["HF_API_KEY"] = config.higgsfield_api_key
        os.environ["HF_API_SECRET"] = config.higgsfield_api_secret
        self.tier = config.higgsfield_tier
        self.app = self.APP_TEMPLATE.format(tier=self.tier)

    def describe(self) -> str:
        return f"Higgsfield DoP {self.tier} (first-last-frame, ~5s/klip)"

    @staticmethod
    def _extract_video_url(result) -> str:
        if isinstance(result, str) and result.startswith("http"):
            return result
        if isinstance(result, dict):
            candidates = [
                ("video", "url"),
                ("video_url",),
                ("output", "video", "url"),
                ("output", "url"),
                ("result", "video", "url"),
                ("assets", "video_url"),
            ]
            for path in candidates:
                node = result
                ok = True
                for key in path:
                    if isinstance(node, dict) and key in node:
                        node = node[key]
                    else:
                        ok = False
                        break
                if ok and isinstance(node, str) and node.startswith("http"):
                    return node
            for _, value in _iter_str_values(result):
                if isinstance(value, str) and (
                    value.endswith(".mp4") or ".mp4?" in value
                ):
                    return value
        raise RuntimeError(
            "Nie znaleziono URL video w odpowiedzi Higgsfield: "
            f"{json.dumps(result, default=str)[:500]}"
        )

    def _on_queue_update(self, status, label: str) -> None:
        kind = type(status).__name__
        position = getattr(status, "position", None)
        extra = f" pos={position}" if position is not None else ""
        print(f"  [{label}] {kind}{extra}")

    @retry(max_attempts=2, base_delay=20.0)
    def _run_job(
        self,
        first_frame: Path,
        last_frame: Path,
        prompt: str,
        label: str,
        output_path: Path,
    ) -> Path:
        first_url = hf.upload_file(first_frame)
        last_url = hf.upload_file(last_frame)

        result = hf.subscribe(
            self.app,
            {
                "prompt": prompt[:1500],
                "image_url": first_url,
                "end_image_url": last_url,
            },
            on_queue_update=lambda s: self._on_queue_update(s, label),
        )
        video_url = self._extract_video_url(result)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with httpx.Client(timeout=300, follow_redirects=True) as client:
            response = client.get(video_url)
            response.raise_for_status()
            output_path.write_bytes(response.content)
        return output_path

    def generate_scene_animation(self, scene: Scene, output_dir: Path) -> Scene:
        out_path = output_dir / f"scene_{scene.index:02d}_animation.mp4"
        self._run_job(
            Path(scene.first_frame_path),
            Path(scene.last_frame_path),
            scene.animation_prompt,
            f"scene {scene.index}",
            out_path,
        )
        scene.animation_video_path = str(out_path)
        return scene

    def generate_transition(
        self,
        transition: Transition,
        from_scene: Scene,
        to_scene: Scene,
        output_dir: Path,
    ) -> Transition:
        out_path = (
            output_dir
            / f"transition_{transition.from_scene:02d}_to_{transition.to_scene:02d}.mp4"
        )
        self._run_job(
            Path(from_scene.last_frame_path),
            Path(to_scene.first_frame_path),
            transition.prompt,
            f"trans {transition.from_scene}->{transition.to_scene}",
            out_path,
        )
        transition.video_path = str(out_path)
        return transition


def _iter_str_values(obj, path=()):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _iter_str_values(v, path + (k,))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _iter_str_values(v, path + (i,))
    else:
        yield path, obj
