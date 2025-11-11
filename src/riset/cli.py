#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
import shutil
import subprocess
from pathlib import Path

from . import __version__

APP_NAME = "riset"
CONFIG_PATH = Path.home() / ".config" / APP_NAME / "config.toml"
DAY_ASSET = "morning.jpg"
NIGHT_ASSET = "evening.jpg"


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
    # src/riset/cli.py -> repo/
    return Path(__file__).resolve().parents[2]


def _find_dir(name: str) -> Path | None:
    """
    Find 'scripts' or 'assets' directory.
    Search order:
      1) Environment variable: RISET_SCRIPTS_DIR / RISET_ASSETS_DIR
      2) Repository checkout (../.. from this file) -> ./<name>
      3) Homebrew share locations (pkgshare)
    """
    # 1) ENV
    env_key = f"RISET_{name.upper()}_DIR"
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
            "Set ENV 'RISET_SCRIPTS_DIR' or install scripts via Homebrew pkgshare."
        )
    return p


def _assets_dir() -> Path | None:
    return _find_dir("assets")


def _launch_agent_paths() -> list[Path]:
    base = Path.home() / "Library" / "LaunchAgents"
    return [
        base / "com.riset.sunrise.plist",
        base / "com.riset.sunset.plist",
    ]


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
    lines = ["# riset config"]
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

def cmd_help(args: argparse.Namespace) -> int:
    parser = args._parser  # type: ignore[attr-defined]
    parser.print_help()
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


def cmd_morning(_: argparse.Namespace) -> int:
    sdir = _scripts_dir()
    script = sdir / "wallpaper_morning.sh"
    if not script.exists():
        print(f"Expected script not found: {script}", file=sys.stderr)
        return 2
    _run_or_die([str(script)])
    print("🌅 Morning wallpaper applied.")
    return 0


def cmd_evening(_: argparse.Namespace) -> int:
    sdir = _scripts_dir()
    script = sdir / "wallpaper_evening.sh"
    if not script.exists():
        print(f"Expected script not found: {script}", file=sys.stderr)
        return 2
    _run_or_die([str(script)])
    print("🌇 Evening wallpaper applied.")
    return 0


def _replace_wallpaper_image(src: str, dest_filename: str, label: str) -> int:
    assets_dir = _assets_dir()
    if assets_dir is None:
        print(
            "Could not find assets directory. "
            "Set RISET_ASSETS_DIR or ensure assets are installed.",
            file=sys.stderr,
        )
        return 2

    src_path = Path(src).expanduser()
    if not src_path.exists():
        print(f"Image not found: {src_path}", file=sys.stderr)
        return 2
    if not src_path.is_file():
        print(f"Expected a file but got: {src_path}", file=sys.stderr)
        return 2

    dest_path = assets_dir / dest_filename
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        shutil.copy2(src_path, dest_path)
    except OSError as exc:
        print(f"Failed to copy image: {exc}", file=sys.stderr)
        return 2

    print(f"✅ {label} wallpaper updated -> {dest_path}")
    return 0


def cmd_day_image(args: argparse.Namespace) -> int:
    return _replace_wallpaper_image(args.image, DAY_ASSET, "Day")


def cmd_night_image(args: argparse.Namespace) -> int:
    return _replace_wallpaper_image(args.image, NIGHT_ASSET, "Night")


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
    env.setdefault("RISET_PYTHON_BIN", sys.executable)
    cfg = _read_config()
    if "lat" in cfg:
        env.setdefault("RISET_LAT", cfg["lat"])
    if "lon" in cfg:
        env.setdefault("RISET_LON", cfg["lon"])

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


def cmd_cleanup(_: argparse.Namespace) -> int:
    """
    Unload launch agents and remove installed plist files.
    """
    plists = _launch_agent_paths()
    uid = os.getuid()
    errors: list[str] = []

    for plist in plists:
        res = _run(["launchctl", "bootout", f"gui/{uid}", str(plist)])
        if res.returncode not in (0, 36):  # 36 = "Operation now in progress" - harmless
            stderr = (res.stderr or "").strip()
            stdout = (res.stdout or "").strip()
            msg = stderr or stdout
            if msg and "No such process" not in msg and "No such file or directory" not in msg:
                errors.append(f"launchctl bootout {plist.name}: {msg}")

        try:
            plist.unlink()
        except FileNotFoundError:
            continue
        except OSError as exc:
            errors.append(f"Remove {plist.name}: {exc}")

    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 1

    print("🧹 Launch agents removed.")
    return 0


# ---------- Parser & entrypoint ----------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=APP_NAME,
        description="CLI wrapper for a sunrise/sunset-based wallpaper workflow."
    )
    # Default to showing help when no subcommand is supplied (mimics `brew` UX).
    p.set_defaults(func=cmd_help, _parser=p)
    p.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Print version and exit",
    )

    sub = p.add_subparsers(dest="cmd", metavar="<command>")

    help_p = sub.add_parser("help", help="Show quick help")
    help_p.set_defaults(func=cmd_help, _parser=p)

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

    cleanup_p = sub.add_parser(
        "cleanup",
        help="Unload launch agents and delete generated plist files."
    )
    cleanup_p.set_defaults(func=cmd_cleanup)

    morning_p = sub.add_parser("morning", help="Apply the morning wallpaper immediately.")
    morning_p.set_defaults(func=cmd_morning)

    evening_p = sub.add_parser("evening", help="Apply the evening wallpaper immediately.")
    evening_p.set_defaults(func=cmd_evening)

    day_p = sub.add_parser(
        "day",
        help="Replace the stored day wallpaper image (copies to assets/morning.jpg)."
    )
    day_p.add_argument("image", help="Path to the image file to use for day mode.")
    day_p.set_defaults(func=cmd_day_image)

    night_p = sub.add_parser(
        "night",
        help="Replace the stored night wallpaper image (copies to assets/evening.jpg)."
    )
    night_p.add_argument("image", help="Path to the image file to use for night mode.")
    night_p.set_defaults(func=cmd_night_image)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
        return int(args.func(args))
    except SystemExit as e:
        return int(e.code)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
