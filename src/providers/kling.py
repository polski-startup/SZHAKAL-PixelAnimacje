"""Official Kling AI image-to-video provider via api.klingai.com.

Uses JWT auth built from ACCESS_KEY + SECRET_KEY (issued in the Kling dev
console at app.klingai.com/global/dev). The model supports Kling V3 with
native audio AND first+last frame simultaneously — the main reason to pick
this provider over fal.ai's Kling V3 (cheaper per second).

Flow:
  1. POST /v1/videos/image2video  → returns task_id
  2. GET  /v1/videos/image2video/{task_id}  → poll task_status until "succeed"
  3. Download video URL and save

Schema (body):
  {
    "model_name": "kling-v3",
    "mode": "std" | "pro",
    "duration": "5" | "10",
    "image":       <base64 or https URL of first frame>,
    "image_tail":  <base64 or https URL of last frame (optional)>,
    "prompt": "...",
    "aspect_ratio": "9:16" | "16:9" | "1:1",
    "enable_audio": true   # alias: generate_audio
  }
"""
import time
from base64 import b64encode
from pathlib import Path

import httpx
import jwt

from src.config import Config
from src.models import Scene, Transition
from src.utils import retry


class KlingProvider:
    label = "kling"
    BASE_URL = "https://api-singapore.klingai.com"
    SUBMIT_PATH = "/v1/videos/image2video"

    def __init__(self, config: Config):
        if not (config.kling_access_key and config.kling_secret_key):
            raise RuntimeError(
                "Brak KLING_ACCESS_KEY / KLING_SECRET_KEY w .env"
            )
        self.access_key = config.kling_access_key
        self.secret_key = config.kling_secret_key
        self.model_name = config.kling_model
        self.mode = config.kling_mode
        self.duration = str(config.kling_duration)
        self.enable_audio = config.kling_enable_audio
        self.aspect_ratio = config.aspect_ratio

    def describe(self) -> str:
        audio = " + audio" if self.enable_audio else ""
        return (
            f"Kling {self.model_name} mode={self.mode} "
            f"({self.duration}s/klip{audio})"
        )

    def _token(self) -> str:
        now = int(time.time())
        payload = {"iss": self.access_key, "exp": now + 1800, "nbf": now - 5}
        return jwt.encode(
            payload,
            self.secret_key,
            algorithm="HS256",
            headers={"alg": "HS256", "typ": "JWT"},
        )

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token()}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _b64(path: Path) -> str:
        return b64encode(Path(path).read_bytes()).decode("utf-8")

    @retry(max_attempts=3, base_delay=30.0)
    def _submit(self, payload: dict) -> str:
        with httpx.Client(timeout=120) as client:
            response = client.post(
                f"{self.BASE_URL}{self.SUBMIT_PATH}",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
            if body.get("code") != 0:
                raise RuntimeError(f"Kling submit failed: {body}")
            return body["data"]["task_id"]

    def _poll(self, task_id: str, interval: int = 15, max_wait: int = 900) -> str:
        url = f"{self.BASE_URL}{self.SUBMIT_PATH}/{task_id}"
        deadline = time.time() + max_wait
        while time.time() < deadline:
            with httpx.Client(timeout=60) as client:
                response = client.get(url, headers=self._headers())
                response.raise_for_status()
                body = response.json()
            data = body.get("data", {})
            status = data.get("task_status")
            print(f"  [{task_id[:10]}] {status}")
            if status == "succeed":
                videos = data.get("task_result", {}).get("videos", [])
                if not videos:
                    raise RuntimeError(
                        f"Kling job succeeded but no video URL: {body}"
                    )
                return videos[0]["url"]
            if status == "failed":
                raise RuntimeError(f"Kling job failed: {body}")
            time.sleep(interval)
        raise TimeoutError(f"Kling job {task_id} did not finish in {max_wait}s")

    @retry(max_attempts=2, base_delay=20.0)
    def _download(self, url: str, output_path: Path) -> Path:
        with httpx.Client(timeout=300, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(response.content)
        return output_path

    def _run_job(
        self,
        first_frame: Path,
        last_frame: Path,
        prompt: str,
        output_path: Path,
    ) -> Path:
        payload = {
            "model_name": self.model_name,
            "mode": self.mode,
            "duration": self.duration,
            "image": self._b64(first_frame),
            "image_tail": self._b64(last_frame),
            "prompt": prompt[:2500],
            "aspect_ratio": self.aspect_ratio,
            "sound": "on" if self.enable_audio else "off",
        }
        task_id = self._submit(payload)
        print(f"  [kling] task={task_id}")
        video_url = self._poll(task_id)
        return self._download(video_url, output_path)

    def generate_scene_animation(self, scene: Scene, output_dir: Path) -> Scene:
        out_path = output_dir / f"scene_{scene.index:02d}_animation.mp4"
        self._run_job(
            Path(scene.first_frame_path),
            Path(scene.last_frame_path),
            scene.animation_prompt,
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
            out_path,
        )
        transition.video_path = str(out_path)
        return transition
