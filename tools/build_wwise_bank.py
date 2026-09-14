import argparse
from pathlib import Path

from clone_reference_bank import build


def main():
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=project_root / "reference" / "Reference")
    parser.add_argument("--output-root", type=Path, default=project_root / "src" / "audioww")
    args = parser.parse_args()
    summary = build(
        args.source_root / "wpn.bnk",
        args.source_root / "wpn.pck",
        args.output_root / "oldshoot.bnk",
        None,
        "wpn",
        True,
    )
    for key, value in summary.items():
        print("{}: {}".format(key, value))


if __name__ == "__main__":
    main()
