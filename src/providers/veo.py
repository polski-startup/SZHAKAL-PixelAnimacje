"""Google Veo 3.1 image-to-video provider via Gemini API."""
import time
from pathlib import Path

from google import genai
from google.genai import types

from src.config import Config
from src.models import Scene, Transition
from src.utils import retry


class VeoProvider:
    """Veo 3.1 Fast/Standard image-to-video via Gemini API.

    Uses first frame + last frame as keyframes. Same GEMINI_API_KEY as image gen.

    Constraints (Gemini API):
    - Duration: 4, 6 or 8 seconds only (not free-form).
    - 1080p requires duration=8.
    - Audio is always on; cannot be toggled.
    """

    label = "veo"

    def __init__(self, config: Config):
        if not config.gemini_api_key:
            raise RuntimeError("Brak GEMINI_API_KEY w .env (wymagane dla Veo)")
        self.client = genai.Client(api_key=config.gemini_api_key)
        self.model = config.veo_model
        self.resolution = config.veo_resolution
        self.scene_duration = config.veo_scene_duration
        self.transition_duration = config.veo_transition_duration
        self.aspect_ratio = config.aspect_ratio

    def describe(self) -> str:
        return (
            f"Veo {self.model} @ {self.resolution}, sceny={self.scene_duration}s, "
            f"przejscia={self.transition_duration}s"
        )

    @staticmethod
    def _load_image(path: Path) -> types.Image:
        return types.Image.from_file(location=str(path))

    def _poll(self, operation, interval: int = 10, max_wait: int = 900):
        deadline = time.time() + max_wait
        while not operation.done and time.time() < deadline:
            time.sleep(interval)
            operation = self.client.operations.get(operation)
        if not operation.done:
            raise TimeoutError(f"Veo operation did not finish in {max_wait}s")
        error = getattr(operation, "error", None)
        if error:
            raise RuntimeError(f"Veo operation failed: {error}")
        return operation

    @retry(max_attempts=6, base_delay=60.0)
    def _run_job(
        self,
        first_frame: Path,
        last_frame: Path,
        prompt: str,
        duration_seconds: int,
        output_path: Path,
    ) -> Path:
        first_image = self._load_image(first_frame)
        last_image = self._load_image(last_frame)

        config = types.GenerateVideosConfig(
            last_frame=last_image,
            duration_seconds=duration_seconds,
            resolution=self.resolution,
            aspect_ratio=self.aspect_ratio,
            number_of_videos=1,
        )

        operation = self.client.models.generate_videos(
            model=self.model,
            prompt=prompt[:2000],
            image=first_image,
            config=config,
        )
        operation = self._poll(operation)

        video = operation.response.generated_videos[0]
        self.client.files.download(file=video.video)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        video.video.save(str(output_path))

        # Throttle: Veo has a tight RPM quota. Pause to avoid 429 on the next call.
        time.sleep(15)
        return output_path

    def generate_scene_animation(self, scene: Scene, output_dir: Path) -> Scene:
        out_path = output_dir / f"scene_{scene.index:02d}_animation.mp4"
        self._run_job(
            Path(scene.first_frame_path),
            Path(scene.last_frame_path),
            scene.animation_prompt,
            self.scene_duration,
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
            self.transition_duration,
            out_path,
        )
        transition.video_path = str(out_path)
        return transition
