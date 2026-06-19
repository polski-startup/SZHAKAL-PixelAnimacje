from pathlib import Path

from src.models import Character, Project, Scene, Transition


def parse_script(script_path: Path) -> Project:
    """Reads a scenario text file split into CHARACTERS and SCENES sections.

    Format:
        # CHARACTERS
        Name: description
        Name: description

        # SCENES
        First narrative fragment (can span multiple lines).

        Second narrative fragment.

        ...

    Scenes are separated by blank lines.
    """
    content = script_path.read_text(encoding="utf-8")

    characters: list[Character] = []
    scene_texts: list[str] = []

    section: str | None = None
    current_scene_lines: list[str] = []

    def flush_scene() -> None:
        if current_scene_lines:
            scene_texts.append(" ".join(current_scene_lines).strip())
            current_scene_lines.clear()

    for raw_line in content.splitlines():
        stripped = raw_line.strip()

        if stripped.startswith("# CHARACTERS"):
            flush_scene()
            section = "characters"
            continue
        if stripped.startswith("# SCENES"):
            flush_scene()
            section = "scenes"
            continue

        if section == "characters":
            if not stripped or stripped.startswith("#"):
                continue
            if ":" in stripped:
                name, description = stripped.split(":", 1)
                characters.append(
                    Character(name=name.strip(), description=description.strip())
                )

        elif section == "scenes":
            if not stripped:
                flush_scene()
            else:
                current_scene_lines.append(stripped)

    flush_scene()

    scene_texts = [t for t in scene_texts if t]

    scenes = [Scene(index=i, text=text) for i, text in enumerate(scene_texts)]
    transitions = [
        Transition(from_scene=i, to_scene=i + 1) for i in range(len(scenes) - 1)
    ]

    return Project(
        name=script_path.stem,
        characters=characters,
        scenes=scenes,
        transitions=transitions,
    )
