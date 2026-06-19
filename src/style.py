"""Style guide — stylized pixel art game-cinematic aesthetic.

Used by Claude when filling prompts in state.json. Two aspect variants
supported: 9:16 default (vertical, shorts/reels) and 16:9 opt-in
(horizontal, YouTube).

VISUAL DIRECTION — single, non-negotiable:
- Beautiful modern stylized pixel art. Think Owlboy / Eastward /
  Hyper Light Drifter / Octopath Traveler (HD-2D) level of refinement
  — NOT blocky Minecraft, NOT generic 8-bit, NOT painterly illustration.
- Strong readable character silhouettes — figure pops from background.
- Rich but disciplined color palette — deep shadows, warm highlights,
  cool atmospheric midtones. No neon-vomit, no muddy browns.
- Game-ready cinematic lighting — subtle volumetric glow, rim light
  on characters, soft bloom on bright sources.
- Parallax-style atmospheric depth — crisp foreground, softer mid,
  hazy background.
- Premium game-cinematic mood — dramatic but controlled, never
  melodramatic.

NOT this style:
- photo-realistic / 3D-rendered
- painterly / watercolor / ink-wash
- chibi / kawaii / cute-cartoon
- voxel / Minecraft blocky
- black-and-white line art
"""

_STYLE_BASE = (
    "Beautiful modern stylized pixel art, premium game-cinematic "
    "aesthetic in the visual register of Owlboy, Eastward, Hyper Light "
    "Drifter, and Octopath Traveler (HD-2D). Crisp pixel grid with "
    "intentional chunky pixels, NOT blurry, NOT anti-aliased to "
    "smoothness. Strong readable character silhouette, rich disciplined "
    "color palette with deep shadows, warm highlights and cool "
    "atmospheric midtones. Cinematic game-ready lighting — subtle "
    "volumetric glow, rim light on character edges, soft bloom on "
    "bright light sources. Parallax-style depth: crisp foreground, "
    "softer mid-ground, hazy atmospheric background. Premium game "
    "mood — dramatic but controlled. STRICTLY NOT photo-realistic, "
    "NOT 3D-rendered, NOT painterly, NOT watercolor, NOT chibi, NOT "
    "voxel-blocky, NOT black-and-white line art."
)

STYLE_VERTICAL = f"{_STYLE_BASE} Vertical 9:16 aspect ratio composition."
STYLE_HORIZONTAL = f"{_STYLE_BASE} Horizontal 16:9 aspect ratio composition."

# Backwards-compat alias — default aspect is 9:16, so STYLE_DESCRIPTION
# continues to point at the vertical variant for any code importing it.
STYLE_DESCRIPTION = STYLE_VERTICAL


def style_description(aspect: str) -> str:
    """Return the style descriptor string for a given aspect ratio.

    Only '9:16' and '16:9' are supported. Anything else falls back to
    9:16 (defensive — CLI validates the choice up front)."""
    return STYLE_HORIZONTAL if aspect == "16:9" else STYLE_VERTICAL


_AUTHORING_COMMON = """
CHARACTER CONSISTENCY
  - Re-use each character's descriptor from the CHARACTERS block verbatim.
  - Silhouette, palette and key details (armor pieces, clothing accent
    colors, hair, weapon, scars, iconography) must stay identical across
    all scenes.
  - Pixel density must feel consistent — don't describe "tiny pixelated"
    in one scene and "detailed HD pixel art" in another.

CONTINUITY (first frame -> last frame)
  - Same location, same time of day, same lighting direction, same
    characters, same pixel density.
  - The last frame is a direct continuation of the first frame a few
    seconds later — a camera push, a pose shift, a lighting pulse, an
    element entering frame, a new environmental detail.
  - Write both frames so a reader with no context infers "same scene,
    progressing".

TRANSITIONS (between scenes N and N+1)
  - Concrete cinematic morph: a camera move (push-through door, whip-
    pan, elevator descent, portal walk, dive into water), a lighting
    sweep (sunset cut, flash-to-dark), or an element from scene N's
    last frame visually transforming into an element of scene N+1's
    first frame.
  - 2-3 seconds of motion.
  - Pixel art aesthetic maintained THROUGH the entire transition — no
    style drift into illustration or realism mid-morph.

ANIMATION PROMPT (within a single scene)
  - Describe the motion from first frame to last frame — 5, 8 or 10
    seconds depending on provider config.
  - Verbs for motion: camera push-in, parallax drift, character pose
    shift, cape flutter, particle shimmer, ember drift, water ripple,
    torch flicker, rim-light pulse, crowd murmur pan.
  - ALWAYS include the line: "Pixel art aesthetic maintained throughout,
    crisp pixel grid, NO style drift, NO smoothing, NO photo-realism."
  - If the selected provider supports audio (Veo, Kling with
    ENABLE_AUDIO=true, fal with GENERATE_AUDIO=true), append an
    ambient-audio directive at the end: foley, music cue, wordless
    character sound. If characters must vocalize, explicitly say
    WORDLESS (no intelligible speech) unless the script calls for a
    specific line.
"""

_AUTHORING_VERTICAL_TAIL = """
EVERY PROMPT
  - Written in English.
  - Starts with or clearly contains the STYLE_VERTICAL descriptor.
  - Vertical 9:16 (portrait). Favor tall compositions: towering
    structures, low-angle hero shots, vertical environmental
    storytelling (cliffs, waterfalls, castle spires), vertical
    parallax layers.
"""

_AUTHORING_HORIZONTAL_TAIL = """
EVERY PROMPT
  - Written in English.
  - Starts with or clearly contains the STYLE_HORIZONTAL descriptor.
  - Horizontal 16:9 (landscape). Favor wide cinematic compositions:
    establishing shots, side-scrolling framing, horizontal parallax
    layers, wide vistas.
"""


def authoring_rules(aspect: str) -> str:
    """Return the full authoring-rules block for a given aspect ratio."""
    tail = _AUTHORING_HORIZONTAL_TAIL if aspect == "16:9" else _AUTHORING_VERTICAL_TAIL
    return _AUTHORING_COMMON + tail


# Backwards-compat alias — 9:16 is the default, so AUTHORING_RULES
# resolves to the vertical block for any code importing it directly.
AUTHORING_RULES = authoring_rules("9:16")
