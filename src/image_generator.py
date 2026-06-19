import io
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image

from src.config import Config
from src.models import Character, Project, Scene
from src.style import style_description
from src.utils import retry


class ImageGenerator:
    def __init__(self, config: Config):
        self.client = genai.Client(api_key=config.gemini_api_key)
        self.model = config.image_model
        self.aspect_ratio = config.aspect_ratio
        self._gen_config = types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio=self.aspect_ratio),
        )

    def _save_image(self, response, output_path: Path) -> Path:
        for part in response.candidates[0].content.parts:
            inline = getattr(part, "inline_data", None)
            if inline is not None and inline.data:
                image = Image.open(io.BytesIO(inline.data))
                output_path.parent.mkdir(parents=True, exist_ok=True)
                image.save(output_path)
                return output_path
        raise RuntimeError(
            "Brak obrazu w odpowiedzi modelu (prompt moze byc zablokowany przez safety)."
        )

    @retry(max_attempts=3, base_delay=10.0)
    def _generate(self, contents: list, output_path: Path) -> Path:
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=self._gen_config,
        )
        return self._save_image(response, output_path)

    def generate_character_sheet(
        self, project: Project, output_dir: Path
    ) -> list[Character]:
        """Generate one reference image per character. Updates characters in place."""
        style = style_description(self.aspect_ratio)
        framing = (
            "wide horizontal frame" if self.aspect_ratio == "16:9"
            else "tall vertical frame"
        )
        for char in project.characters:
            if char.reference_image_path and Path(char.reference_image_path).exists():
                continue

            prompt = (
                f"{style} "
                f"Character reference of {char.name}. {char.description}. "
                f"Full body front view, neutral standing pose, centered in a "
                f"{framing}. Clean white background. Single character only, "
                f"no props, no background details. ABSOLUTELY NO TEXT, NO LABELS, "
                f"NO CAPTIONS anywhere in the image."
            )

            out_path = (
                output_dir
                / f"character_{char.name.lower().replace(' ', '_')}.png"
            )
            self._generate([prompt], out_path)
            char.reference_image_path = str(out_path)

        return project.characters

    def _character_refs(self, project: Project) -> list[Image.Image]:
        imgs: list[Image.Image] = []
        for char in project.characters:
            if char.reference_image_path:
                imgs.append(Image.open(char.reference_image_path))
        return imgs

    def generate_scene_frames(
        self,
        project: Project,
        scene: Scene,
        output_dir: Path,
    ) -> Scene:
        """Generate first + last frame for a scene, using character refs for consistency.

        Last frame additionally uses the freshly generated first frame as a
        continuity reference so the two images share setting, composition, and
        character appearance.
        """
        character_refs = self._character_refs(project)

        if not (scene.first_frame_path and Path(scene.first_frame_path).exists()):
            first_path = output_dir / f"scene_{scene.index:02d}_first.png"
            guidance = (
                "Generate the FIRST FRAME described below. Match the character "
                "appearance and style from the reference images exactly."
            )
            contents = [guidance, scene.first_frame_prompt, *character_refs]
            self._generate(contents, first_path)
            scene.first_frame_path = str(first_path)

        if not (scene.last_frame_path and Path(scene.last_frame_path).exists()):
            last_path = output_dir / f"scene_{scene.index:02d}_last.png"
            first_img = Image.open(scene.first_frame_path)
            guidance = (
                "Generate the LAST FRAME described below. It MUST be a direct "
                "continuation of the attached first frame — same characters, same "
                "setting, same style — showing the progression described in the prompt. "
                "Use the character reference sheet(s) to keep identities consistent."
            )
            contents = [
                guidance,
                scene.last_frame_prompt,
                first_img,
                *character_refs,
            ]
            self._generate(contents, last_path)
            scene.last_frame_path = str(last_path)

        return scene
