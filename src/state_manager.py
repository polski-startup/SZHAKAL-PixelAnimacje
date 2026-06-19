import os
import tempfile
from pathlib import Path

from src.models import Project


class StateManager:
    def __init__(self, state_path: Path):
        self.state_path = state_path

    def save(self, project: Project) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = project.model_dump_json(indent=2)

        # Write to a sibling tempfile, then os.replace() atomically. A crash
        # mid-write never leaves a half-written state.json behind — otherwise
        # we'd lose the whole resumable state of a long pipeline run.
        fd, tmp = tempfile.mkstemp(
            dir=self.state_path.parent,
            prefix=f".{self.state_path.name}.",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
            os.replace(tmp, self.state_path)
        except Exception:
            Path(tmp).unlink(missing_ok=True)
            raise

    def load(self) -> Project | None:
        if not self.state_path.exists():
            return None
        return Project.model_validate_json(
            self.state_path.read_text(encoding="utf-8")
        )
