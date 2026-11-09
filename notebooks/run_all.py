#!/usr/bin/env python
"""Run every numbered notebook in this folder, in order, saving outputs in place.

Intended for refreshing all results after a new imagery/climate pull. Run it
from anywhere with the project virtualenv active:

    python notebooks/run_all.py              # run everything, stop on first failure
    python notebooks/run_all.py --list       # show the run order without executing
    python notebooks/run_all.py --from 10    # start at the 10-series notebooks
    python notebooks/run_all.py --only 11 12 # run just these numeric prefixes
    python notebooks/run_all.py --skip 02 23 # run everything except these
    python notebooks/run_all.py --keep-going # continue past failures

Each notebook is executed with its working directory set to notebooks/, which
is what the notebooks themselves assume (ROOT = Path.cwd().parent). Executed
notebooks are written back in place so saved outputs stay current.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

NOTEBOOKS_DIR = Path(__file__).resolve().parent
DEFAULT_TIMEOUT = 60 * 60  # seconds per cell


def discover_notebooks() -> list[Path]:
    """Numbered notebooks in lexical (i.e. pipeline) order."""
    return sorted(
        p for p in NOTEBOOKS_DIR.glob("[0-9][0-9]_*.ipynb")
        if ".ipynb_checkpoints" not in p.parts
    )


def select(notebooks: list[Path], args: argparse.Namespace) -> list[Path]:
    selected = notebooks
    if args.only:
        wanted = set(args.only)
        selected = [p for p in selected if p.name[:2] in wanted]
    if args.skip:
        unwanted = set(args.skip)
        selected = [p for p in selected if p.name[:2] not in unwanted]
    if args.start_from:
        selected = [p for p in selected if p.name[:2] >= args.start_from]
    return selected


def run_notebook(path: Path, timeout: int) -> None:
    import nbformat
    from nbclient import NotebookClient

    nb = nbformat.read(path, as_version=4)
    client = NotebookClient(
        nb,
        timeout=timeout,
        kernel_name="python3",
        resources={"metadata": {"path": str(NOTEBOOKS_DIR)}},
    )
    try:
        client.execute()
    finally:
        # Write back even on failure so the error output is inspectable.
        nbformat.write(nb, path)


def fmt_duration(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--list", action="store_true", help="list run order and exit")
    parser.add_argument(
        "--from", dest="start_from", metavar="NN",
        help="start from this numeric prefix (e.g. 10)",
    )
    parser.add_argument(
        "--only", nargs="+", metavar="NN",
        help="run only these numeric prefixes (e.g. --only 11 12)",
    )
    parser.add_argument(
        "--skip", nargs="+", metavar="NN",
        help="skip these numeric prefixes (e.g. --skip 02 23)",
    )
    parser.add_argument(
        "--keep-going", action="store_true",
        help="continue with remaining notebooks after a failure",
    )
    parser.add_argument(
        "--timeout", type=int, default=DEFAULT_TIMEOUT,
        help=f"per-cell timeout in seconds (default {DEFAULT_TIMEOUT})",
    )
    args = parser.parse_args(argv)

    notebooks = select(discover_notebooks(), args)
    if not notebooks:
        print("No notebooks matched the given filters.")
        return 1

    if args.list:
        for i, path in enumerate(notebooks, 1):
            print(f"{i:2d}. {path.name}")
        return 0

    total = len(notebooks)
    results: list[tuple[Path, str, float]] = []
    overall_start = time.monotonic()
    print(f"Running {total} notebook(s) — started {datetime.now():%Y-%m-%d %H:%M:%S}")

    failed = False
    for i, path in enumerate(notebooks, 1):
        if failed and not args.keep_going:
            results.append((path, "skipped", 0.0))
            continue
        print(f"\n[{i}/{total}] {path.name} ... ", flush=True)
        start = time.monotonic()
        try:
            run_notebook(path, timeout=args.timeout)
        except Exception as exc:  # noqa: BLE001 — report any execution failure
            elapsed = time.monotonic() - start
            results.append((path, "FAILED", elapsed))
            failed = True
            print(f"[{i}/{total}] {path.name} FAILED after {fmt_duration(elapsed)}")
            print(f"    {type(exc).__name__}: {str(exc).strip().splitlines()[-1] if str(exc).strip() else ''}")
            print(f"    Full traceback saved in {path.name}")
            if not args.keep_going:
                print("    Stopping (use --keep-going to continue past failures).")
        else:
            elapsed = time.monotonic() - start
            results.append((path, "ok", elapsed))
            print(f"[{i}/{total}] {path.name} ok ({fmt_duration(elapsed)})")

    print(f"\n{'=' * 56}\nSummary ({fmt_duration(time.monotonic() - overall_start)} total):")
    for path, status, elapsed in results:
        marker = {"ok": "✓", "FAILED": "✗", "skipped": "-"}[status]
        timing = f" ({fmt_duration(elapsed)})" if status != "skipped" else ""
        print(f"  {marker} {path.name:<45} {status}{timing}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
