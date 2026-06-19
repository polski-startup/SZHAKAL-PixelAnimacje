# SZHAKAL PixelAnimacje

Pipeline, który zamienia **tekstowy scenariusz po polsku w gotowy, narrowany film w stylu premium pixel-art game-cinematic** 

Domyślnie **pionowy 9:16** (TikTok / Reels / Shorts). Opcjonalnie **poziomy 16:9** (YouTube) przez flagę `--aspect 16:9`.

> Autor: [@dekoder12345](https://github.com/dekoder12345)

---

## Kluczowa idea

**Prompty wizualne pisze człowiek (lub Claude Code) ręcznie do `state.json`, nie generuje ich kod.**

Pierwsze uruchomienie na nowym scenariuszu parsuje tekst, tworzy szkielet `state.json` z pustymi promptami i **zatrzymuje się z blokadą**. Wtedy wypełniasz pola (`first_frame_prompt`, `last_frame_prompt`, `animation_prompt`, `transition.prompt`) wg wytycznych stylu, a ponowne uruchomienie kontynuuje od miejsca przerwania. Dzięki temu najtrudniejsza, kreatywna część — spójne, stylowe prompty — zostaje pod pełną kontrolą, a Python jest tylko orkiestratorem.

Wytyczne stylu i reguły pisania promptów: [`src/style.py`](src/style.py) + [`BRIEF.md`](BRIEF.md).

---

## Jak to działa

```
scenariusz .txt  ──►  parser (CHARACTERS + SCENES)  ──►  state.json (puste prompty) ──► BLOKADA
                                                                                          │
                          wypełniasz prompty w state.json  ◄────────────────────────────┘
                                          │
                                          ▼
        Nano Banana (gemini-2.5-flash-image)  ──►  arkusze postaci + klatki first/last każdej sceny
                                          │
                                          ▼
        provider image-to-video (Veo / Kling / fal.ai / Higgsfield)  ──►  animacje scen + przejścia
                                          │
                                          ▼
                       ffmpeg concat  ──►  <projekt>_final.mp4
```

Pełny diagram (Mermaid) i opis każdego kroku: [`CLAUDE.md`](CLAUDE.md).

**Ważne właściwości:**
- **Wznawialność** — stan zapisywany po *każdym* wygenerowanym asecie; crash gubi maksymalnie jeden krok.
- **Atomowy zapis** — `state.json` zapisywany przez tempfile + `os.replace()`, więc crash w trakcie zapisu nie uszkodzi stanu.
- **Fail-fast na kosztach** — klucze providera wideo i obecność `ffmpeg` sprawdzane *zanim* ruszy płatne generowanie obrazów.
- **Spójność postaci** — każda postać ma jednorazowy arkusz referencyjny, dołączany do każdej klatki; klatka „last" dostaje dodatkowo świeżo wygenerowaną klatkę „first" jako referencję kompozycji.

---

## Czego potrzebujesz

| Wymaganie | Po co |
|---|---|
| **Python ≥ 3.10** | kod używa składni `X \| None`, `list[str]` |
| **ffmpeg** w `PATH` | końcowe sklejanie klipów ([pobierz](https://ffmpeg.org/download.html)) |
| **`GEMINI_API_KEY`** | zawsze wymagany — Nano Banana generuje klatki |
| **klucz jednego providera wideo** | animacja scen i przejść (patrz tabela niżej) |

> ⚠️ Projekt korzysta z **płatnych API** (generowanie klatek + wideo). Trzymaj rękę na pulsie kosztów.

---

## Instalacja

```bash
git clone https://github.com/polski-startup/SZHAKAL-PixelAnimacje.git
cd SZHAKAL-PixelAnimacje

python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env     # Windows: copy .env.example .env
# uzupełnij GEMINI_API_KEY i klucze wybranego providera wideo
```

Weryfikacja środowiska:

```bash
python -c "import fal_client, higgsfield_client, google.genai, jwt, PIL, httpx, pydantic; print('deps OK')"
ffmpeg -version
```

---

## Uruchomienie

```bash
python main.py scenarios/<nazwa>.txt                 # domyślnie 9:16
python main.py scenarios/<nazwa>.txt --aspect 16:9   # poziomy (YouTube)
python main.py scenarios/<nazwa>.txt --skip-video    # stop po klatkach (przed płatnym wideo)
```

Na Windowsie `run.bat scenarios\<nazwa>.txt` opakowuje to samo wywołanie (flagi przechodzą dalej).

**Typowy przebieg:**
1. Pierwsze uruchomienie → tworzy `state.json` i wychodzi z blokadą „brakuje promptów".
2. Wypełniasz prompty w `output/<nazwa>/state.json` wg [`src/style.py`](src/style.py) i [`BRIEF.md`](BRIEF.md).
3. Ponowne uruchomienie → generuje klatki, wideo i finalny film.

Demo do szybkiej weryfikacji: [`scenarios/demo_pixel_hero.txt`](scenarios/demo_pixel_hero.txt).

---

## Providery wideo

Wybierasz przez `VIDEO_PROVIDER` w `.env`. Wszystkie używają modelu „pierwsza + ostatnia klatka" (first/last frame).

| Provider | Klucze | Cena (orientacyjnie) | Uwagi |
|---|---|---|---|
| **fal.ai** *(zalecany)* | `FAL_KEY` | `wan-flf2v` ~$0.08/s 720p (bez audio); `kling-v3/pro` ~$0.168/s 1080p (audio) | pay-as-you-go, brak limitów dziennych, najmniejszy dryf stylu |
| **Veo 3.1** | `GEMINI_API_KEY` | w ramach Gemini API | najlepszy ruch kinowy, ale ~10 generacji/dzień na Tier 1 — do hero shotów, nie batchy |
| **Kling** (oficjalne API) | `KLING_ACCESS_KEY` + `KLING_SECRET_KEY` | wg kredytów | jedyna trasa z Kling V3 + audio + first/last naraz; wymaga depozytu (~$10–20) |
| **Higgsfield** | `HIGGSFIELD_API_KEY` + `HIGGSFIELD_API_SECRET` | `lite` ~$0.125/klip | stałe ~5 s/klip, nieprzewidywalna kolejka na free planie |

Wszystkie pokrętła w [`.env.example`](.env.example). Pełne porównanie i wskazówki anty-dryfu stylu: [`CLAUDE.md`](CLAUDE.md).

---

## Format scenariusza

```
# CHARACTERS
Imię: opis używany dosłownie w promptach — paleta, sylwetka, kluczowe detale
      (zbroja, akcenty kolorystyczne, broń, blizny). Akcenty palety
      ("rdzawoczerwona peleryna", "turkusowa runa na piersi") trzymają
      spójność postaci między scenami dużo lepiej niż samo "peleryna".

# SCENES
Pierwszy fragment narracji (może zajmować kilka linii).

Drugi fragment. Puste linie rozdzielają sceny.
```

Przejścia tworzą się automatycznie między każdą parą kolejnych scen. `project.name` = nazwa pliku scenariusza (bez rozszerzenia).

**Wskazówka:** grupowanie 2–3 linii narracji na scenę (oddzielonych pustą linią) daje mniej, ale bogatszych scen z dłuższymi animacjami — wyraźnie lepsze dla 10-sekundowych klipów Kling/Veo niż jedna linia na scenę.

---

## Output i wznawialność

Artefakty lądują w `output/<projekt>/` (9:16) lub `output/<projekt>_16x9/` (16:9) — wszystko w `.gitignore`:

- `state.json` — zserializowany stan projektu (z polem `aspect`).
- `frames/` — arkusze postaci + klatki first/last scen (PNG).
- `videos/` — animacje scen + przejścia (MP4).
- `<projekt>_final.mp4` — finalny film po sklejeniu.

Format 9:16 i 16:9 mają osobne katalogi i nigdy nie mieszają assetów. Niezgodność `aspect` między `state.json` a flagą CLI wywala pipeline **przed** jakimkolwiek wywołaniem API.

---

## Smoke testy pojedynczego klipu

```bash
python scripts/smoke_veo.py [nazwa_projektu]
python scripts/smoke_higgsfield.py [nazwa_projektu]
```

Wymagają istniejącego `output/<nazwa>/state.json` z wygenerowanymi klatkami sceny 0.

---

## Dokumentacja

- [`CLAUDE.md`](CLAUDE.md) — architektura, kontrakt providerów, zasady pracy z kodem.
- [`BRIEF.md`](BRIEF.md) — kierunek wizualny i ściąga do pisania promptów.
