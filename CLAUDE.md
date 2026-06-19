# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

End-to-end pipeline that turns a Polish narration script into a narrated video **in a stylized pixel-art game-cinematic aesthetic** (Owlboy / Eastward / Hyper Light Drifter / Octopath Traveler HD-2D register). **Default: vertical 9:16 (shorts/reels/TikTok — the main mode).** **Opt-in: horizontal 16:9 (YouTube) via `--aspect 16:9`.** Only those two aspects are supported. Flow: scenario text → per-scene prompts (filled by Claude directly into `state.json`) → Nano Banana (`gemini-2.5-flash-image`) frames → provider-agnostic image-to-video clip per scene + transition → ffmpeg concat.

**This is a sibling project to `SZHAKAL Animacje` (black-and-white comic pipeline).** The technical core is identical — only the visual layer (`src/style.py`, README, BRIEF, scenario demos) is different. If you're changing pipeline mechanics (state format, provider contract, parser), consider whether the sibling repo should get the same change.

## Commands

```bash
# Main entry point (Windows: run.bat wraps the same invocation)
python main.py scenarios/<name>.txt                       # 9:16 default
python main.py scenarios/<name>.txt --aspect 16:9         # horizontal (YouTube)
python main.py scenarios/<name>.txt --skip-video          # stop after frame generation
run.bat scenarios\<name>.txt                              # Windows shortcut (flags pass through)

# Single-clip smoke tests (read existing state.json, force provider)
python scripts/smoke_veo.py [project_name]
python scripts/smoke_higgsfield.py [project_name]

# Install deps
pip install -r requirements.txt
```

No test suite, no linter, no build step. Python ≥ 3.10 required (`pyproject.toml` declares it). `ffmpeg` must be on `PATH` — `Pipeline._preflight_video()` checks this **before** image generation so a missing ffmpeg fails fast instead of after a 10-minute paid run.

## Architecture

### Pipeline is state-driven and resumable

[src/pipeline.py](src/pipeline.py) orchestrates everything. On every run it loads the right state.json (see aspect-aware paths below), matching by `project.name` (scenario filename stem), and resumes from the first missing artifact. `StateManager.save()` is called after **every** generated asset so a crash loses at most one step. The save itself is **atomic** (tempfile + `os.replace()` in [src/state_manager.py](src/state_manager.py)) so a crash mid-write cannot corrupt `state.json` and wipe the whole resumable state. Do not break either invariant when editing the pipeline.

Artifacts live under `output/<project>/` (9:16) or `output/<project>_16x9/` (16:9), all gitignored:
- `state.json` — serialized `Project` (pydantic model in [src/models.py](src/models.py)); includes an `aspect` field.
- `frames/` — character refs + scene first/last frames (PNG). Nano Banana produces `768×1344` for 9:16 and `1344×768` for 16:9 (ratio ~1.75, close to exact 16:9).
- `videos/` — scene animations + transitions (MP4)
- `<project>_final.mp4` (9:16) or `<project>_16x9_final.mp4` (16:9) — ffmpeg concat output

### Aspect isolation and mismatch fail-fast

`Pipeline._project_dir_name()` and `Pipeline._final_video_name()` encode the aspect into paths so 9:16 and 16:9 never share state or assets. The `Project.aspect` field is persisted into `state.json`; on resume, if the stored aspect differs from the CLI-requested aspect, the pipeline raises **before** any API call. Belt-and-suspenders on top of per-aspect directory isolation — do not collapse these two layers into one.

### Prompts are written by Claude into state.json, not by Python

**The central design choice.** Easy to miss if you're new to the codebase:

1. First run of `main.py` on a new scenario parses the script, creates an empty `Project` skeleton with blank prompts, writes `state.json`, and **exits with a "Blokada: brakuje promptow" message** — see `Pipeline.run()`.
2. Claude Code then edits `state.json` directly, filling `first_frame_prompt`, `last_frame_prompt`, `animation_prompt` for each scene and `prompt` for each transition.
3. User re-runs `main.py` — now prompts exist, so the pipeline proceeds to image + video generation.

Authoring rules live in [src/style.py](src/style.py). Call `style_description(aspect)` and `authoring_rules(aspect)` to get the right variant. **Every prompt is English, pixel-art game-cinematic** — deep shadows, rim light, parallax depth, crisp pixel grid, NO style drift. The aspect-ratio line inside each prompt MUST match the project's aspect.

Per-scenario helper scripts under `output/<name>/fill_prompts.py` are one-off Python programs that bulk-write prompts into that scenario's `state.json`. They live under `output/` which is gitignored — never enter version control. Use them as examples when authoring new prompts.

### Scenario format ([src/script_parser.py](src/script_parser.py))

```
# CHARACTERS
Name: description (used verbatim in image prompts — include palette,
      silhouette, key armor/clothing details, weapon, distinguishing
      marks)

# SCENES
First scene text (can span multiple lines).

Second scene text. Blank lines separate scenes.
```

Transitions are auto-created between every consecutive scene pair. `project.name` = `script_path.stem`.

**Pro tip from sibling repo:** grouping 2-3 narration lines per scene (separated by blank lines) produces fewer, richer scenes with longer animations — dramatically better for 10-second Kling/Veo clips than one-line-per-scene. See "Narration grouping" below.

### Narration grouping (content-layer convention, no code change)

The parser treats blank-line-separated blocks as scenes — it's indifferent to how many narration lines you pack into one block. This is a pure workflow knob:

- **1 line per scene** — many short scenes, lots of transitions. Cheapest per total video duration ONLY if per-clip duration is equal. Can feel chopped-up at 10s/clip.
- **2 lines per scene** — natural beat pairs (hook+setup, problem+solution). Sweet spot for most narrative scripts.
- **3 lines per scene** — fewer, richer scenes; demands more thought on first→last continuity (3 beats in one visual arc). Great for 10-second clips.

Pick per-scenario. Document the choice in the helper `fill_prompts.py` docstring.

### Video provider abstraction

[src/video_generator.py](src/video_generator.py) is a factory that dispatches on `VIDEO_PROVIDER` env var. Each provider under [src/providers/](src/providers/) implements `describe()`, `generate_scene_animation()`, `generate_transition()`:

- **veo** — Google Veo 3.1 via Gemini API; `GEMINI_API_KEY`; 4/6/8s only, 1080p requires 8s; `time.sleep(15)` throttle for RPM quota. Honors `aspect_ratio` explicitly.
- **fal** — fal.ai unified API; `FAL_KEY=key_id:secret`; keyframe param names vary per model (`FAL_FIRST_PARAM`, `FAL_LAST_PARAM`). Output aspect inherited from keyframes.
- **higgsfield** — Higgsfield DoP; tier `lite|turbo|standard`; fixed ~5s clips. Output aspect inherited from keyframes.
- **kling** — Official Kling API with JWT auth; only route that gives Kling V3 + audio + first/last-frame simultaneously. Honors `aspect_ratio` explicitly.

All providers use the first+last frame keyframe model. Scenes animate between `scene.first_frame_path` and `scene.last_frame_path`; transitions animate from `from_scene.last_frame_path` to `to_scene.first_frame_path`. Keep this shape when adding providers.

### Pixel art + video providers — what actually works

Pixel-art first/last keyframes go into the video providers the same way any image does. Two things to watch:

1. **Style drift mid-clip** — some video models "evolve" pixel art toward smooth illustration across the clip. Counter by adding to every `animation_prompt`:
   > *Pixel art aesthetic maintained throughout, crisp pixel grid, NO style drift, NO smoothing, NO photo-realism.*
2. **Motion feel** — pixel art traditionally has stepped, discrete motion (low-fps sprite animation look). Modern image-to-video models interpolate smoothly, which can fight the aesthetic. If you want stepped motion, add *"stepped low-framerate sprite-animation motion feel"* — or accept smooth interpolation as a modern game-cinematic look (recommended default).

**Provider ranking for this project** (observed + priced):
- **fal / wan-flf2v** — $0.08/s 720p, no audio. Cheapest, least style drift. **Recommended default for testing.**
- **fal / kling-video/v3/pro** — $0.168/s 1080p, audio OK. Premium option. Heavier style drift if animation_prompt is vague.
- **kling (native API)** — same model as fal Kling V3, slightly different pricing via credits. Good when you already have Kling wallet.
- **veo** — best at cinematic motion but 10 RPD Tier-1 limit kills throughput. Use for hero shots, not batch.
- **higgsfield** — `lite` tier $0.125/clip (~$0.025/s), 5s fixed. Queue latency unpredictable on free plan.

### Image generation continuity ([src/image_generator.py](src/image_generator.py))

Every character gets a one-time reference sheet (front view, neutral pose, white background). When generating scene frames, all character reference images are passed as additional `contents` to Nano Banana so identities stay consistent. The **last frame** call additionally passes the freshly generated **first frame** as a reference so the two stills share setting and composition — don't remove this coupling in `generate_scene_frames`.

For pixel art: character descriptors in `# CHARACTERS` should include **palette accents** ("rust-red cape", "bronze pauldron", "glowing teal rune on chest") — these give Nano Banana anchors to preserve across scenes far more reliably than "wearing a cape" alone.

### Retry + throttling

[src/utils.py](src/utils.py) exposes `@retry(max_attempts, base_delay)` with exponential backoff. Image gen uses `3×10s`, video providers vary (Veo 6×60s, fal 3×30s, etc.). When editing providers, keep retries around the network call only, not around the whole pipeline step (double-retry wastes quota).

### Final concat invariant

`Assembler.assemble()` concats with `-c copy` (stream copy, no re-encode). **Consequence:** all scene + transition clips in one run must share codec, resolution and fps. Switching `VIDEO_PROVIDER` mid-project after some clips exist can silently break the concat step. Fix = delete `output/<project>/videos/` before swapping providers.

**Clip ordering** (from `Assembler._collect_clips`): `scene_0 → transition_0→1 → scene_1 → transition_1→2 → … → scene_N`. A transition with `from_scene=i` is emitted right after `scene_i`.

## Configuration

All knobs in `.env` — see [.env.example](.env.example). `Config.from_env()` in [src/config.py](src/config.py) is the single place env is read; pass `Config` objects around rather than re-reading env. `from_env()` accepts an optional `aspect_ratio` kwarg that overrides the env value; `main.py` wires it from the `--aspect` CLI flag.

`GEMINI_API_KEY` is always required (image generation). Video provider keys are validated early — `Pipeline._preflight_video()` instantiates the configured provider (which raises on missing keys in its own `__init__`) and checks `ffmpeg` presence **before** the image-generation phase, so key/ffmpeg mistakes fail fast and do not waste paid image quota.

### Per-provider aspect-ratio handling

- **Veo** / **Kling** — explicit `aspect_ratio` in the API call; honored.
- **fal** / **Higgsfield** — no explicit aspect parameter. Output aspect inherited from input keyframes (Nano Banana generates at the right aspect).

## Keeping the architecture diagram in sync

[README.md](README.md) contains a Mermaid flowchart of the pipeline. Update it whenever:
- a provider is added, removed or renamed in [src/providers/](src/providers/)
- a step is added, removed or reordered in `Pipeline.run()` ([src/pipeline.py](src/pipeline.py))
- the scenario format changes in [src/script_parser.py](src/script_parser.py)
- where state is saved or where artifacts land changes
- the blocking-loop for missing prompts changes shape

Minor changes — refactors inside a single provider, new `.env` knobs, tweaks to prompt authoring rules in [src/style.py](src/style.py), retry tuning — do not require diagram updates.
