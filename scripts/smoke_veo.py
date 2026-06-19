"""Smoke test: generate scene 0 animation with Veo.

Usage:
    python scripts/smoke_veo.py              # defaults to project 'redbull_sleep'
    python scripts/smoke_veo.py <project>    # uses output/<project>/state.json

Reads an existing state.json (so the project must already have scene 0's
first/last frames generated), forces the Veo provider regardless of
VIDEO_PROVIDER, and writes the clip to output/<project>/videos_smoke_veo/.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import Config  # noqa: E402
from src.models import Project  # noqa: E402
from src.providers.veo import VeoProvider  # noqa: E402


def main() -> None:
    project_name = sys.argv[1] if len(sys.argv) > 1 else "redbull_sleep"

    config = Config.from_env()
    state_path = config.output_dir / project_name / "state.json"
    if not state_path.exists():
        raise SystemExit(
            f"Brak {state_path}. Odpal najpierw main.py dla projektu '{project_name}' "
            f"(minimum do etapu klatek: --skip-video)."
        )
    project = Project.model_validate_json(state_path.read_text(encoding="utf-8"))
    scene = project.scenes[0]

    print(f"[Smoke] Projekt: {project_name}")
    print(f"[Smoke] Scena {scene.index}: {scene.text[:60]}...")
    print(f"[Smoke] Prompt: {scene.animation_prompt[:100]}...")
    print(f"[Smoke] first: {scene.first_frame_path}")
    print(f"[Smoke] last:  {scene.last_frame_path}")
    print()

    vg = VeoProvider(config)
    print(f"[Smoke] {vg.describe()}")
    out_dir = config.output_dir / project_name / "videos_smoke_veo"
    t0 = time.time()
    vg.generate_scene_animation(scene, out_dir)
    dt = time.time() - t0
    print(f"\n[OK] {scene.animation_video_path}  ({dt:.0f}s)")


if __name__ == "__main__":
    main()
