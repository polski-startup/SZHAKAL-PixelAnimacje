import shutil
from pathlib import Path

from src.assembler import Assembler
from src.config import Config
from src.image_generator import ImageGenerator
from src.models import Project
from src.script_parser import parse_script
from src.state_manager import StateManager
from src.video_generator import build_video_generator


class Pipeline:
    def __init__(self, config: Config):
        self.config = config

    def _validate_gemini(self) -> None:
        if not self.config.gemini_api_key:
            raise RuntimeError(
                "Brak GEMINI_API_KEY w .env (Nano Banana generuje klatki)"
            )

    def _preflight_video(self):
        """Instantiate the video provider and verify ffmpeg BEFORE image gen.

        Each provider validates its own keys in __init__ — so instantiation
        alone is a cheap key check. ffmpeg is required by Assembler at the
        very end; checking here avoids burning a 5-10 minute image run just
        to fail on the concat step.
        """
        if shutil.which("ffmpeg") is None:
            raise RuntimeError(
                "Nie znaleziono ffmpeg w PATH. Zainstaluj ffmpeg i dodaj do PATH "
                "(Assembler wymaga go na etapie koncowego concat)."
            )
        vg = build_video_generator(self.config)
        print(f"[Wideo] Provider: {vg.describe()}")
        return vg

    def _missing_prompts(self, project: Project) -> list[str]:
        missing: list[str] = []
        for s in project.scenes:
            if not s.first_frame_prompt:
                missing.append(f"scena {s.index}: first_frame_prompt")
            if not s.last_frame_prompt:
                missing.append(f"scena {s.index}: last_frame_prompt")
            if not s.animation_prompt:
                missing.append(f"scena {s.index}: animation_prompt")
        for t in project.transitions:
            if not t.prompt:
                missing.append(f"przejscie {t.from_scene} -> {t.to_scene}: prompt")
        return missing

    @staticmethod
    def _project_dir_name(project_name: str, aspect: str) -> str:
        """Output dir suffix keeps 9:16 backward-compatible (no suffix) and
        isolates 16:9 under a separate sibling dir so assets never mix."""
        if aspect == "9:16":
            return project_name
        return f"{project_name}_{aspect.replace(':', 'x')}"

    @staticmethod
    def _final_video_name(project_name: str, aspect: str) -> str:
        if aspect == "9:16":
            return f"{project_name}_final.mp4"
        return f"{project_name}_{aspect.replace(':', 'x')}_final.mp4"

    def run(self, script_path: Path, skip_video: bool = False) -> None:
        project = parse_script(script_path)
        project.aspect = self.config.aspect_ratio
        project_dir = self.config.output_dir / self._project_dir_name(
            project.name, project.aspect
        )
        state = StateManager(project_dir / "state.json")

        existing = state.load()
        if existing and existing.name == project.name:
            if existing.aspect != project.aspect:
                # Should be unreachable — each aspect has its own dir — but
                # guards against someone hand-copying state.json across dirs.
                raise RuntimeError(
                    f"Niezgodnosc aspect ratio: stan w {state.state_path} "
                    f"ma aspect={existing.aspect!r}, CLI prosi o "
                    f"{project.aspect!r}. Usun katalog {project_dir} albo "
                    f"uruchom z wlasciwa flaga --aspect."
                )
            print(f"[Wznawiam] Stan zaladowany z {state.state_path}")
            project = existing
        else:
            project_dir.mkdir(parents=True, exist_ok=True)
            state.save(project)
            print(f"[Init] Utworzono szkielet stanu: {state.state_path}")

        print(
            f"[Scenariusz] {len(project.scenes)} scen, "
            f"{len(project.transitions)} przejsc, "
            f"{len(project.characters)} postaci, aspect={project.aspect}"
        )

        missing = self._missing_prompts(project)
        if missing:
            print("\n[Blokada] Brakuje promptow:")
            for m in missing:
                print(f"  - {m}")
            print()
            print(f"Popros Claude Code zeby wypelnil: {state.state_path}")
            print("(patrz src/style.py po wytyczne stylu i spojnosci postaci)")
            # Include --aspect when non-default so the user re-runs against the
            # same state dir; otherwise a plain rerun would hit a different dir
            # (9:16 default) and silently start a second project.
            aspect_flag = (
                "" if project.aspect == "9:16" else f" --aspect {project.aspect}"
            )
            print(
                f"Potem odpal ponownie: python main.py {script_path}{aspect_flag}"
            )
            return

        self._validate_gemini()

        # Fail fast on provider keys + ffmpeg BEFORE burning image API quota.
        vg = None if skip_video else self._preflight_video()

        frames_dir = project_dir / "frames"
        videos_dir = project_dir / "videos"

        ig = ImageGenerator(self.config)

        print("[Obrazy] Arkusz postaci...")
        ig.generate_character_sheet(project, frames_dir)
        state.save(project)

        for scene in project.scenes:
            already = (
                scene.first_frame_path
                and scene.last_frame_path
                and Path(scene.first_frame_path).exists()
                and Path(scene.last_frame_path).exists()
            )
            if already:
                continue
            print(f"[Obrazy] Klatki sceny {scene.index}...")
            ig.generate_scene_frames(project, scene, frames_dir)
            state.save(project)

        if skip_video:
            print("[Info] Pomijam generowanie wideo (--skip-video).")
            return

        for scene in project.scenes:
            if scene.animation_video_path and Path(scene.animation_video_path).exists():
                continue
            print(f"[Wideo] Animacja sceny {scene.index}...")
            vg.generate_scene_animation(scene, videos_dir)
            state.save(project)

        for transition in project.transitions:
            if transition.video_path and Path(transition.video_path).exists():
                continue
            from_scene = project.scenes[transition.from_scene]
            to_scene = project.scenes[transition.to_scene]
            print(
                f"[Wideo] Przejscie {transition.from_scene} -> {transition.to_scene}..."
            )
            vg.generate_transition(transition, from_scene, to_scene, videos_dir)
            state.save(project)

        final_path = project_dir / self._final_video_name(project.name, project.aspect)
        print(f"[Montaz] Sklejam klipy -> {final_path}")
        Assembler().assemble(project, final_path)
        project.final_video_path = str(final_path)
        state.save(project)

        print(f"[Gotowe] Finalny film: {final_path}")
