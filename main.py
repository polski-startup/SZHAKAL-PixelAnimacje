import argparse
import sys
from pathlib import Path

# Line-buffered output so progress is visible when stdout is piped/redirected.
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except AttributeError:
    pass

from src.config import Config
from src.pipeline import Pipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "SZHAKAL Animacje - scenariusz PL -> film. "
            "Default: pionowy 9:16 (shorts/reels). "
            "Opt-in: poziomy 16:9 (YouTube) przez --aspect 16:9."
        ),
    )
    parser.add_argument(
        "scenario",
        type=Path,
        help="sciezka do pliku scenariusza (np. scenarios/moj.txt)",
    )
    parser.add_argument(
        "--skip-video",
        action="store_true",
        help="zatrzymaj po generowaniu klatek (przed platnym wideo)",
    )
    parser.add_argument(
        "--aspect",
        choices=["9:16", "16:9"],
        default=None,
        help="format wideo: 9:16 (default, vertical) lub 16:9 (horizontal)",
    )
    args = parser.parse_args()

    if not args.scenario.exists():
        print(f"Nie znaleziono pliku: {args.scenario}")
        sys.exit(1)

    config = Config.from_env(aspect_ratio=args.aspect)
    print(f"[Config] aspect_ratio={config.aspect_ratio}")
    pipeline = Pipeline(config)
    pipeline.run(args.scenario, skip_video=args.skip_video)


if __name__ == "__main__":
    main()
