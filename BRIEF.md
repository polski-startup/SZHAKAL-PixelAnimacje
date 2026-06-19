# Visual Brief — SZHAKAL PixelAnimacje

Single source of truth for the visual direction. Claude Code should read this **before** writing prompts for a new scenario. Pair it with [src/style.py](src/style.py) (the in-code implementation).

## One-line direction

> Beautiful modern stylized pixel art, premium game-cinematic mood, in the visual register of **Owlboy / Eastward / Hyper Light Drifter / Octopath Traveler (HD-2D)**.

## What this means

| Dimension | Target |
|---|---|
| **Pixel grid** | Crisp, intentional chunky pixels. Not blurry, not anti-aliased to smoothness, not hyper-detailed modern-indie style that loses the pixel feel. |
| **Silhouette** | Character reads instantly even at small size. Strong outline, distinct pose, recognizable colors/shapes. |
| **Palette** | Rich but disciplined — deep shadows, warm highlights, cool atmospheric midtones. Colors chosen for mood, not saturation competition. No neon-vomit, no muddy browns. |
| **Lighting** | Cinematic game-ready. Subtle volumetric glow. Rim light on characters. Soft bloom on bright sources (torches, runes, lanterns, windows). Shadows are colored (cool blue-violet), never pure black. |
| **Depth** | Parallax layering. Crisp sharp foreground → slightly softer mid-ground → hazy atmospheric background. Depth-of-field via fog/mist, not via actual blur of pixels. |
| **Mood** | Dramatic but controlled. Premium feel. Never melodramatic, never Disney-cute, never grimdark-edgy for its own sake. |
| **Motion (for video providers)** | Can be either (a) traditional stepped sprite-animation feel (low-fps blocky motion) or (b) modern smooth interpolation (Kling/Veo default). **Default for this project: modern smooth interpolation** — feels more cinematic for social content. Only switch to stepped if script calls for nostalgic retro beat. |

## Hard NOs

- **Photo-realism** or 3D-rendered look
- **Painterly / watercolor / ink-wash** illustration
- **Chibi / kawaii / cute-cartoon** proportions
- **Voxel / Minecraft blocky** geometry
- **Black-and-white line art** (that's the sibling repo `SZHAKAL Animacje`)
- **Neon cyberpunk cliché** unless script explicitly asks for it
- **8-bit generic retro** — we're aiming for modern pixel art, not NES nostalgia

## Character descriptor cheatsheet (for `# CHARACTERS` block)

A good character descriptor for this pipeline includes:

1. **Silhouette anchor** — build, posture, headgear presence, cape/robe presence
2. **Palette accents** — 2-3 distinctive color notes ("rust-red cape", "bronze pauldron with teal rune", "silver filigree on dark leather")
3. **Key props** — weapon, staff, lantern, tome — described by shape and color
4. **Distinguishing marks** — scar, glowing eye, tattoo, missing limb
5. **Pixel density hint** (optional) — "rendered at ~96px tall character scale" keeps Nano Banana from oscillating between tiny sprite and massive HD sprite across scenes

Example (good):

> **Ash**: slender rogue figure with a hooded dark-green cloak, rust-red scarf wrapped at the neck, bronze-plated bracer on the right forearm, matte black leather leggings, twin curved daggers sheathed at the hips with faint teal rune-glow on the pommels, single faint scar across the left cheek, 96px-tall pixel-art sprite silhouette.

Example (bad — too vague):

> Ash: a warrior with a sword.

## Scene prompt cheatsheet

**First frame (0s):**
1. Style preamble (pulled from `style_description(aspect)`)
2. Setting — physical location, time of day, key environmental props
3. Lighting — direction, warmth, notable light sources
4. Character pose + position in frame
5. Foreground / mid / background layering
6. Polish on-screen text (if any) — specify exact Polish text in quotes

**Last frame (10s):**
Mostly identical to first frame, except the explicit element that has changed (pose, prop state, camera framing, new arrival). Include the continuity hook for the next scene ("… the open portal in the wall now glowing brighter, ready to swallow the camera in the next shot").

**Animation prompt (motion plan):**
- 3 time-stamped beats matching clip length (0-3s / 3-6s / 6-10s for a 10-second clip)
- Explicit verbs only (push-in, pan, parallax drift, pose shift, rune pulse, ember rise, cape flutter)
- **Mandatory sign-off line**: *"Pixel art aesthetic maintained throughout, crisp pixel grid, NO style drift, NO smoothing, NO photo-realism."*
- Audio directive if the provider supports it: ambient, foley, wordless character vocalizations (no intelligible speech unless scripted).

**Transition prompt (between scenes):**
- One concrete morph — an element transforming, a camera move, a lighting sweep
- 2-3 seconds
- Pixel art preserved through the morph

## Polish on-screen text

Polish is the narration language — so any diegetic on-screen text (signs, titles, banners, UI elements, comment icons) must be Polish. Collect labels as module-level constants in the scenario's `fill_prompts.py` helper so you don't drift across prompts. Nano Banana handles Polish diacritics inconsistently — prefer simple ASCII-safe forms when possible ("WKROTCE" over "WKRÓTCE" if the font rendering is unreliable).

## Audio

For providers with audio (Veo / Kling `ENABLE_AUDIO=true` / fal `GENERATE_AUDIO=true`):

- **Characters**: unless the script demands a specific line, use *wordless* vocalizations (hm, gasp, sigh, grunt, short surprise breath). Explicit `AUDIO DIRECTIVE: NO spoken words in any language, NO intelligible speech` block in every animation_prompt.
- **Ambient**: scene-appropriate foley (footsteps on stone, wind in trees, distant crowd murmur, torch crackle, UI chimes for phone scenes).
- **Music cue**: optional per-scene hint ("soft orchestral swell as the portal opens", "low drone fading to silence") — providers interpret loosely but it nudges the score.

## Iterating

If a scene's output feels off:

1. **Style drift** → strengthen the mandatory sign-off line, add one or two hard NOs directly to the animation_prompt.
2. **Character inconsistency** → beef up the `# CHARACTERS` descriptor with more palette accents + props, regenerate the character sheet.
3. **Composition wrong** → rewrite just first/last frame, keep animation_prompt, re-run `--skip-video` (only regenerates the affected scene's frames).
4. **Bad motion** → rewrite animation_prompt only, then delete the scene's video file and re-run (pipeline skips existing files, so just the one clip regenerates).

State is resumable — partial rewrites cost only the re-generated step, not the whole run.
