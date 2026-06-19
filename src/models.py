from typing import Optional

from pydantic import BaseModel, Field


class Character(BaseModel):
    name: str
    description: str
    reference_image_path: Optional[str] = None


class Scene(BaseModel):
    index: int
    text: str
    first_frame_prompt: str = ""
    last_frame_prompt: str = ""
    animation_prompt: str = ""
    first_frame_path: Optional[str] = None
    last_frame_path: Optional[str] = None
    animation_video_path: Optional[str] = None


class Transition(BaseModel):
    from_scene: int
    to_scene: int
    prompt: str = ""
    video_path: Optional[str] = None


class Project(BaseModel):
    name: str
    # Default keeps backward compat: existing state.json files without this
    # field load as 9:16 projects. New 16:9 projects set it explicitly via CLI.
    aspect: str = "9:16"
    characters: list[Character] = Field(default_factory=list)
    scenes: list[Scene] = Field(default_factory=list)
    transitions: list[Transition] = Field(default_factory=list)
    final_video_path: Optional[str] = None
