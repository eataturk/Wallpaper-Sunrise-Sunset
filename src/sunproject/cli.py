#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
import subprocess
from pathlib import Path

from . import __version__

APP_NAME = "sunproject"
CONFIG_PATH = Path.home() / ".config" / APP_NAME / "config.toml"


# ---------- Paths & discovery helpers ----------

def _homebrew_share_candidates() -> list[Path]:
    """
    Candidate locations where Homebrew may place shared data.
    Your formula can do: pkgshare.install "scripts", "assets"
    """
    cands: list[Path] = []
    hb_prefix = os.environ.get("HOMEBREW_PREFIX")
    if hb_prefix:
        cands.append(Path(hb_prefix) / "share" / APP_NAME)
    # common defaults
    cands += [
        Path("/opt/homebrew/share") / APP_NAME,  # Apple Silicon
        Path("/usr/local/share") / APP_NAME,     # Intel
    ]
    return cands


def _repo_root_from_this_file() -> Path:
    # When running from source, this points to the repository root:
    # src/sunproject/cli.py -> repo/
    return Path(__file__).resolve().parents[2]


def _find_dir(name: str) -> Path | None:
    """
    Find 'scripts' or 'assets' directory.
    Search order:
      1) Environment variable: SUNPROJECT_SCRIPTS_DIR / SUNPROJECT_ASSETS_DIR
      2) Repository checkout (../.. from this file) -> ./<name>
      3) Homebrew share locations (pkgshare)
    """
    # 1) ENV
    env_key = f"SUNPROJECT_{name.upper()}_DIR"
    env_val = os.environ.get(env_key)
    if env_val:
        p = Path(env_val).expanduser()
        if p.exists():
            return p

    # 2) Source tree (developer runs)
    repo = _repo_root_from_this_file()
    p = repo / name
    if p.exists():
        return p

    # 3) Homebrew shared locations
    for base in _homebrew_share_candidates():
        p = base / name
        if p.exists():
            return p

    return None


def _scripts_dir() -> Path:
    p = _find_dir("scripts")
    if p is None:
        raise FileNotFoundError(
            "Could not find 'scripts' directory. "
            "Set ENV 'SUNPROJECT_SCRIPTS_DIR' or install scripts via Homebrew pkgshare."
        )
    return p


def _assets_dir() -> Path | None:
    return _find_dir("assets")


# ---------- Simple config (key=value lines) ----------

def _ensure_config_dir() -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)


def _read_config() -> dict[str, str]:
    if not CONFIG_PATH.exists():
        return {}
    data: dict[str, str] = {}
    for line in CONFIG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip()
    return data


def _write_config(cfg: dict[str, str]) -> None:
    _ensure_config_dir()
    lines = ["# sunproject config"]
    for k, v in cfg.items():
        lines.append(f"{k}={v}")
    CONFIG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------- Subprocess helpers ----------

def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True)


def _run_or_die(cmd: list[str]) -> str:
    res = _run(cmd)
    if res.returncode != 0:
        msg = res.stderr.strip() or res.stdout.strip() or f"Command failed: {' '.join(cmd)}"
        print(msg, file=sys.stderr)
        raise SystemExit(res.returncode or 1)
    return res.stdout.strip()


# ---------- Command handlers ----------

def cmd_help(_: argparse.Namespace) -> int:
    print("For usage, run:  sunproject -h   or   sunproject <command> -h")
    return 0


def cmd_location_change(args: argparse.Namespace) -> int:
    cfg = _read_config()
    cfg["lat"] = str(args.lat)
    cfg["lon"] = str(args.lon)
    _write_config(cfg)
    print(f"✅ Location updated: lat={args.lat} lon={args.lon}")
    print(f"🗂  Config file: {CONFIG_PATH}")
    return 0


def cmd_background_change(args: argparse.Namespace) -> int:
    sdir = _scripts_dir()

    if args.mode == "auto":
        # Preferred: a single script that decides and applies (your existing scheduler/logic)
        times_script = sdir / "wallpaper_times.sh"
        if times_script.exists():
            _run_or_die([str(times_script)])
            print("🖼️  Wallpaper set automatically (day/night).")
            return 0

        # Fallback: compute_mode.sh prints 'day' or 'night'; we then call the specific script
        compute_script = sdir / "compute_mode.sh"
        if compute_script.exists():
            mode = _run_or_die([str(compute_script)]).strip().lower()
            if mode not in {"day", "night"}:
                print(f"Invalid mode from compute_mode.sh: {mode}", file=sys.stderr)
                return 2
            args.mode = mode
        else:
            print("For --mode auto, expected 'wallpaper_times.sh' or 'compute_mode.sh' not found.", file=sys.stderr)
            return 2

    # Explicit day/night: call dedicated scripts
    if args.mode == "day":
        script = sdir / "wallpaper_morning.sh"
    elif args.mode == "night":
        script = sdir / "wallpaper_evening.sh"
    else:
        print("Invalid --mode. Must be one of: day | night | auto", file=sys.stderr)
        return 2

    if not script.exists():
        print(f"Expected script not found: {script}", file=sys.stderr)
        return 2

    _run_or_die([str(script)])
    print(f"🖼️  Wallpaper set: {args.mode}")
    return 0


def cmd_post_install(_: argparse.Namespace) -> int:
    """
    Homebrew can invoke this after installation to bootstrap launch agents.
    """
    sdir = _scripts_dir()
    times_script = sdir / "wallpaper_times.sh"
    if not times_script.exists():
        print(f"Expected script not found: {times_script}", file=sys.stderr)
        return 2

    env = os.environ.copy()
    cfg = _read_config()
    if "lat" in cfg:
        env.setdefault("SUNPROJECT_LAT", cfg["lat"])
    if "lon" in cfg:
        env.setdefault("SUNPROJECT_LON", cfg["lon"])

    res = subprocess.run(["bash", str(times_script)], text=True, capture_output=True, env=env)
    if res.returncode != 0:
        err = res.stderr.strip() or res.stdout.strip() or "wallpaper_times.sh failed"
        print(err, file=sys.stderr)
        return res.returncode

    if res.stdout.strip():
        print(res.stdout.strip())
    if res.stderr.strip():
        print(res.stderr.strip(), file=sys.stderr)

    print("✅ wallpaper_times.sh executed (launch agents updated).")
    return 0


# ---------- Parser & entrypoint ----------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=APP_NAME,
        description="CLI wrapper for a sunrise/sunset-based wallpaper workflow."
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Print version and exit",
    )

    sub = p.add_subparsers(dest="cmd", metavar="<command>", required=True)

    help_p = sub.add_parser("help", help="Show quick help")
    help_p.set_defaults(func=cmd_help)

    loc_p = sub.add_parser("location_change", help="Update location (lat/lon)")
    loc_p.add_argument("--lat", type=float, required=True, help="Latitude (e.g., 41.0082)")
    loc_p.add_argument("--lon", type=float, required=True, help="Longitude (e.g., 28.9784)")
    loc_p.set_defaults(func=cmd_location_change)

    bg_p = sub.add_parser("background_change", help="Change wallpaper")
    bg_p.add_argument("--mode", choices=["day", "night", "auto"], required=True, help="day | night | auto")
    bg_p.set_defaults(func=cmd_background_change)

    post_p = sub.add_parser(
        "post_install",
        help="Run wallpaper_times.sh (for Homebrew post_install hook)."
    )
    post_p.set_defaults(func=cmd_post_install)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except SystemExit as e:
        return int(e.code)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
