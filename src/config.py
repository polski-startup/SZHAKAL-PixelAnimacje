import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# The only aspect ratios the pipeline supports. Validated at config-load so
# bad values in .env fail immediately, not after burning API quota. argparse
# enforces the same set at the CLI layer; this is belt-and-suspenders.
SUPPORTED_ASPECTS = frozenset({"9:16", "16:9"})


@dataclass
class Config:
    # Shared
    gemini_api_key: str
    output_dir: Path
    scenarios_dir: Path
    image_model: str
    aspect_ratio: str

    # Video provider selection
    video_provider: str  # "veo" | "higgsfield" | "fal"

    # Veo (via Gemini API)
    veo_model: str
    veo_resolution: str
    veo_scene_duration: int
    veo_transition_duration: int

    # Higgsfield
    higgsfield_api_key: str
    higgsfield_api_secret: str
    higgsfield_tier: str  # "lite" | "turbo" | "standard"

    # fal.ai
    fal_api_key: str
    fal_app: str
    fal_duration: str
    fal_first_param: str
    fal_last_param: str
    fal_generate_audio: str  # "true" | "false" | "" (omit parameter)

    # Kling official API (api.klingai.com)
    kling_access_key: str
    kling_secret_key: str
    kling_model: str  # kling-v1, kling-v1-6, kling-v2-master, kling-v3
    kling_mode: str  # "std" | "pro"
    kling_duration: str  # "5" | "10"
    kling_enable_audio: bool

    @classmethod
    def from_env(
        cls,
        project_root: Path | None = None,
        aspect_ratio: str | None = None,
    ) -> "Config":
        """Load config from .env. A CLI-supplied `aspect_ratio` overrides the
        env value so runs can pick between "9:16" (default) and "16:9" without
        editing .env.

        The resolved aspect is validated against SUPPORTED_ASPECTS. An invalid
        value from .env raises here (before any API call) — we do NOT silently
        fall back to 9:16, because a silent fallback would create output dirs
        for a ratio the user explicitly requested, then produce content at a
        different ratio.
        """
        load_dotenv()
        if project_root is None:
            project_root = Path(__file__).parent.parent

        resolved_aspect = aspect_ratio or os.getenv("ASPECT_RATIO", "9:16")
        if resolved_aspect not in SUPPORTED_ASPECTS:
            raise RuntimeError(
                f"Niewspierany aspect_ratio={resolved_aspect!r}. "
                f"Dozwolone tylko: {sorted(SUPPORTED_ASPECTS)}. "
                f"Popraw ASPECT_RATIO w .env albo uzyj --aspect 9:16 / --aspect 16:9."
            )

        return cls(
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            output_dir=project_root / "output",
            scenarios_dir=project_root / "scenarios",
            image_model=os.getenv("IMAGE_MODEL", "gemini-2.5-flash-image"),
            aspect_ratio=resolved_aspect,
            video_provider=os.getenv("VIDEO_PROVIDER", "veo"),
            veo_model=os.getenv("VEO_MODEL", "veo-3.1-fast-generate-preview"),
            veo_resolution=os.getenv("VEO_RESOLUTION", "1080p"),
            veo_scene_duration=int(os.getenv("VEO_SCENE_DURATION", "8")),
            veo_transition_duration=int(os.getenv("VEO_TRANSITION_DURATION", "8")),
            higgsfield_api_key=os.getenv("HIGGSFIELD_API_KEY", ""),
            higgsfield_api_secret=os.getenv("HIGGSFIELD_API_SECRET", ""),
            higgsfield_tier=os.getenv("HIGGSFIELD_TIER", "lite"),
            fal_api_key=os.getenv("FAL_KEY", ""),
            fal_app=os.getenv("FAL_APP", "fal-ai/kling-video/o1/standard/image-to-video"),
            fal_duration=os.getenv("FAL_DURATION", "5"),
            fal_first_param=os.getenv("FAL_FIRST_PARAM", "start_image_url"),
            fal_last_param=os.getenv("FAL_LAST_PARAM", "end_image_url"),
            fal_generate_audio=os.getenv("FAL_GENERATE_AUDIO", ""),
            kling_access_key=os.getenv("KLING_ACCESS_KEY", ""),
            kling_secret_key=os.getenv("KLING_SECRET_KEY", ""),
            kling_model=os.getenv("KLING_MODEL", "kling-v3"),
            kling_mode=os.getenv("KLING_MODE", "pro"),
            kling_duration=os.getenv("KLING_DURATION", "5"),
            kling_enable_audio=os.getenv("KLING_ENABLE_AUDIO", "true").lower() == "true",
        )
