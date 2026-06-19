import shutil
import subprocess
from pathlib import Path

from src.models import Project


class Assembler:
    """Concatenates scene animations and transitions in order using ffmpeg."""

    def _ensure_ffmpeg(self) -> None:
        if shutil.which("ffmpeg") is None:
            raise RuntimeError(
                "Nie znaleziono ffmpeg w PATH. Zainstaluj ffmpeg i dodaj do PATH."
            )

    def _collect_clips(self, project: Project) -> list[str]:
        clips: list[str] = []
        transitions_by_from = {t.from_scene: t for t in project.transitions}

        for scene in project.scenes:
            if scene.animation_video_path:
                clips.append(scene.animation_video_path)
            transition = transitions_by_from.get(scene.index)
            if transition and transition.video_path:
                clips.append(transition.video_path)
        return clips

    def assemble(self, project: Project, output_path: Path) -> Path:
        self._ensure_ffmpeg()
        clips = self._collect_clips(project)
        if not clips:
            raise RuntimeError("Brak klipow do zlozenia.")

        list_file = output_path.parent / "concat_list.txt"
        list_file.parent.mkdir(parents=True, exist_ok=True)
        list_file.write_text(
            "\n".join(f"file '{Path(c).resolve().as_posix()}'" for c in clips),
            encoding="utf-8",
        )

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-c",
                "copy",
                str(output_path),
            ],
            check=True,
        )
        return output_path
