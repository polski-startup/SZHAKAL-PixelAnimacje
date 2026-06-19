"""fal.ai image-to-video provider via fal_client SDK.

fal.ai hosts many video models behind a unified API. This provider picks one
of the Kling first-last-frame variants by default because they natively
interpolate between a start and end keyframe — matching our pipeline shape.

Pricing (2026):
  - fal-ai/kling-video/o1/standard/image-to-video      $0.084/s, 720p, FLF
  - fal-ai/kling-video/o1/pro/image-to-video           ~$0.168/s, 1080p, FLF
  - fal-ai/wan-flf2v                                   $0.08/s (720p), FLF
"""
import os
import time
from pathlib import Path

import fal_client
import httpx

from src.config import Config
from src.models import Scene, Transition
from src.utils import retry


class FalProvider:
    label = "fal"

    # Fallback defaults in case config is missing the knob
    DEFAULT_APP = "fal-ai/kling-video/o1/standard/image-to-video"
    DEFAULT_DURATION = "5"  # Kling O1 supports 5 or 10 seconds

    def __init__(self, config: Config):
        if not config.fal_api_key:
            raise RuntimeError("Brak FAL_KEY w .env")
        os.environ["FAL_KEY"] = config.fal_api_key
        self.app = config.fal_app or self.DEFAULT_APP
        self.duration = str(config.fal_duration or self.DEFAULT_DURATION)
        # start/end parameter name varies per model — see _build_args
        self._first_param = config.fal_first_param or "start_image_url"
        self._last_param = config.fal_last_param or "end_image_url"
        # Audio flag: empty string = don't send (let model default); "true"/"false"
        # passes through as a boolean.
        self._audio_override = (config.fal_generate_audio or "").strip().lower()

    def describe(self) -> str:
        audio = ""
        if self._audio_override == "true":
            audio = " + audio"
        elif self._audio_override == "false":
            audio = " (mute)"
        return f"fal.ai {self.app} ({self.duration}s/klip{audio})"

    def _build_args(self, prompt: str, first_url: str, last_url: str) -> dict:
        args = {
            "prompt": prompt[:2000],
            self._first_param: first_url,
            self._last_param: last_url,
            "duration": self.duration,
        }
        if self._audio_override in ("true", "false"):
            args["generate_audio"] = self._audio_override == "true"
        return args

    def _on_queue_update(self, update, label: str) -> None:
        kind = type(update).__name__
        position = getattr(update, "position", None)
        extra = f" pos={position}" if position is not None else ""
        print(f"  [{label}] {kind}{extra}")

    @staticmethod
    def _extract_video_url(result) -> str:
        # fal.ai standard result shape: {"video": {"url": "..."}} — sometimes
        # {"output": {...}} or {"videos": [{"url": ...}]}. Walk the common
        # paths, then fall back to scanning for any .mp4 URL.
        if isinstance(result, dict):
            for path in [
                ("video", "url"),
                ("output", "url"),
                ("output", "video", "url"),
                ("videos", 0, "url"),
            ]:
                node = result
                ok = True
                for key in path:
                    if isinstance(node, list) and isinstance(key, int) and key < len(node):
                        node = node[key]
                    elif isinstance(node, dict) and key in node:
                        node = node[key]
                    else:
                        ok = False
                        break
                if ok and isinstance(node, str) and node.startswith("http"):
                    return node
            for _, value in _iter_values(result):
                if isinstance(value, str) and (
                    value.endswith(".mp4") or ".mp4?" in value
                ):
                    return value
        raise RuntimeError(f"Nie znaleziono URL video w odpowiedzi fal.ai: {result!s:.500}")

    @retry(max_attempts=3, base_delay=30.0)
    def _run_job(
        self,
        first_frame: Path,
        last_frame: Path,
        prompt: str,
        label: str,
        output_path: Path,
    ) -> Path:
        first_url = fal_client.upload_file(str(first_frame))
        last_url = fal_client.upload_file(str(last_frame))

        result = fal_client.subscribe(
            self.app,
            arguments=self._build_args(prompt, first_url, last_url),
            with_logs=False,
            on_queue_update=lambda s: self._on_queue_update(s, label),
        )
        video_url = self._extract_video_url(result)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with httpx.Client(timeout=300, follow_redirects=True) as client:
            response = client.get(video_url)
            response.raise_for_status()
            output_path.write_bytes(response.content)

        # Light throttle between jobs (defensive — fal has generous limits but
        # this keeps us safe under concurrent runs).
        time.sleep(2)
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


def _iter_values(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _iter_values(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_values(v)
    else:
        yield None, obj
