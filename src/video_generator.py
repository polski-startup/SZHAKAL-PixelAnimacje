"""Factory — picks a video provider based on config.video_provider.

All providers share the same shape (describe / generate_scene_animation /
generate_transition / label) and validate their own keys in __init__.
Call sites depend on duck typing — if you add a 5th provider, register it
in build_video_generator() below and keep the method set intact.
"""
from src.config import Config


def build_video_generator(config: Config):
    provider = config.video_provider.lower()
    if provider == "veo":
        from src.providers.veo import VeoProvider

        return VeoProvider(config)
    if provider == "higgsfield":
        from src.providers.higgsfield import HiggsfieldProvider

        return HiggsfieldProvider(config)
    if provider == "fal":
        from src.providers.fal import FalProvider

        return FalProvider(config)
    if provider == "kling":
        from src.providers.kling import KlingProvider

        return KlingProvider(config)
    raise RuntimeError(
        f"Nieznany VIDEO_PROVIDER={config.video_provider!r}. "
        f"Wybierz 'veo', 'higgsfield', 'fal' albo 'kling'."
    )
