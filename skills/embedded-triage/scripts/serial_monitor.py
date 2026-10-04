#!/usr/bin/env python3
"""
serial_monitor.py - Serial monitor for the embedded-triage skill.

Opens a live serial monitor in its own terminal window for the user. The agent
reads the same output from a log file, so the two never fight over the port.

Commands
  launch   Open a terminal window running the monitor (user-facing).
  stop     Close the monitor window.
  pause    Release the port so the board can be flashed. The window stays open.
  resume   Reconnect after flashing.
  status   Exit 0 if a monitor is running for the port.
  tail     Print the last N logged lines (agent reads output this way).
  capture  Bounded headless read (N seconds). Reads the log when a monitor
           is already running, otherwise opens the port directly.
  run      Internal: the monitor loop that runs inside the terminal window.

The port defaults to "auto": the single USB serial port reported by
`arduino-cli board list` (built-in UARTs such as /dev/ttyS4 are ignored).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path


class PortError(RuntimeError):
    pass


class TerminalError(RuntimeError):
    pass


# --------------------------------------------------------------------- state
def state_dir() -> Path:
    base = os.environ.get("EMBEDDED_SERIAL_STATE_DIR") or os.environ.get("EMBEDDED_MICRO_STATE_DIR")
    if not base:
        runtime = os.environ.get("XDG_RUNTIME_DIR")
        base = os.path.join(runtime, "embedded-micro") if runtime else f"/tmp/embedded-micro-{os.getuid()}"
    path = Path(base)
    path.mkdir(parents=True, exist_ok=True)
    return path



class Paths:
    def __init__(self, port: str):
        slug = Path(port).name or "port"
        d = state_dir()
        self.pid = d / f"{slug}.pid"
        self.log = d / f"{slug}.log"
        self.pause = d / f"{slug}.pause"
        self.paused = d / f"{slug}.paused"


def running_pid(paths: Paths) -> int | None:
    try:
        pid = int(paths.pid.read_text().strip())
        os.kill(pid, 0)
        return pid
    except (FileNotFoundError, ValueError, ProcessLookupError):
        paths.pid.unlink(missing_ok=True)
        return None
    except PermissionError:
        return None


def _wait(cond, timeout: float, step: float = 0.1) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if cond():
            return True
        time.sleep(step)
    return cond()


# --------------------------------------------------------------- port picking
def pick_port(board_list) -> str | None:
    """Return the single USB serial port from `arduino-cli board list --format json`."""
    entries = board_list.get("detected_ports", []) if isinstance(board_list, dict) else board_list
    usb = []
    for entry in entries or []:
        port = entry.get("port", entry)
        props = port.get("properties") or {}
        if props.get("vid") and port.get("address"):
            usb.append(port["address"])
    if len(usb) > 1:
        raise PortError(f"Multiple USB serial ports found: {', '.join(usb)}. Pass --port explicitly.")
    return usb[0] if usb else None


def resolve_port(port: str) -> str:
    if port != "auto":
        return port
    found = None
    try:
        out = subprocess.run(
            ["arduino-cli", "board", "list", "--format", "json"],
            capture_output=True, text=True, timeout=15,
        ).stdout
        found = pick_port(json.loads(out or "{}"))
    except (FileNotFoundError, json.JSONDecodeError, subprocess.TimeoutExpired):
        candidates = sorted(glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*"))
        if len(candidates) > 1:
            raise PortError(f"Multiple serial ports found: {', '.join(candidates)}. Pass --port explicitly.")
        found = candidates[0] if candidates else None
    if not found:
        raise PortError("No USB serial board detected. Check the cable/port (see Board-Not-Found policy).")
    return found


# ------------------------------------------------------------------ terminals
TERMINALS = {
    "alacritty": lambda t, a: ["alacritty", "--title", t, "-e", *a],
    "foot": lambda t, a: ["foot", "--title", t, *a],
    "kitty": lambda t, a: ["kitty", "--title", t, *a],
    "ghostty": lambda t, a: ["ghostty", f"--title={t}", "-e", *a],
    "wezterm": lambda t, a: ["wezterm", "start", "--", *a],
    "gnome-terminal": lambda t, a: ["gnome-terminal", f"--title={t}", "--", *a],
    "konsole": lambda t, a: ["konsole", "-p", f"tabtitle={t}", "-e", *a],
    "xdg-terminal-exec": lambda t, a: ["xdg-terminal-exec", *a],
    "xterm": lambda t, a: ["xterm", "-T", t, "-e", *a],
}
PREFERENCE = ["alacritty", "foot", "kitty", "ghostty", "wezterm", "gnome-terminal",
              "konsole", "xdg-terminal-exec", "xterm"]


def terminal_command(term: str, title: str, argv: list[str]) -> list[str]:
    name = os.path.basename(term)
    if name not in TERMINALS:
        raise TerminalError(f"Unsupported terminal '{term}'. Supported: {', '.join(PREFERENCE)}")
    return TERMINALS[name](title, list(argv))


def choose_terminal(explicit: str | None) -> str:
    if explicit:
        return explicit
    env = os.environ.get("TERMINAL")
    order = ([os.path.basename(env)] if env else []) + PREFERENCE
    for name in order:
        if name in TERMINALS and shutil.which(name):
            return name
    raise TerminalError("No supported terminal emulator found. Install alacritty/foot/kitty or pass --terminal.")


# --------------------------------------------------------------------- logging
class LineLogger:
    """Writes complete lines, timestamped, to the log file. Partial chunks are buffered."""

    def __init__(self, path: Path):
        self._fh = open(path, "a", encoding="utf-8")
        self._buf = b""

    def feed(self, data: bytes) -> None:
        self._buf += data
        *lines, self._buf = self._buf.split(b"\n")
        for raw in lines:
            text = raw.rstrip(b"\r").decode("utf-8", errors="replace")
            stamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self._fh.write(f"[{stamp}] {text}\n")
        if lines:
            self._fh.flush()

    def note(self, text: str) -> None:
        self.feed(f"--- {text} ---\n".encode())

    def close(self) -> None:
        if self._buf:
            self.feed(b"\n")
        self._fh.close()


# --------------------------------------------------------------------- serial
def open_serial(port: str, baud: int, reset: bool = False):
    import serial  # pyserial

    ser = serial.Serial(port, baud, timeout=0.2)
    if reset:
        try:  # EN pulse via RTS on ESP32 auto-reset circuits
            ser.dtr = False
            ser.rts = True
            time.sleep(0.1)
            ser.rts = False
        except (OSError, serial.SerialException):
            pass
    return ser


def cmd_run(args) -> int:
    import serial

    port, paths = args.port, Paths(args.port)
    if running_pid(paths):
        print(f"A monitor is already running for {port}.")
        return 1
    paths.pid.write_text(str(os.getpid()))
    paths.paused.unlink(missing_ok=True)
    logger = LineLogger(paths.log)
    logger.note(f"monitor started {port} @ {args.baud}")
    lock = threading.Lock()
    state = {"ser": None}

    def cleanup(*_):
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGHUP, cleanup)

    def forward_input():
        for line in sys.stdin:
            with lock:
                if state["ser"]:
                    try:
                        state["ser"].write(line.encode())
                    except (OSError, serial.SerialException):
                        pass

    if sys.stdin and sys.stdin.isatty():
        threading.Thread(target=forward_input, daemon=True).start()

    out = sys.stdout
    out.write(f"\033]0;Serial {port}\007")
    out.write(f"== Serial monitor {port} @ {args.baud} baud | Ctrl+C to close ==\n")
    out.write(f"== Log: {paths.log} ==\n\n")
    out.flush()

    waiting_note = False
    try:
        while True:
            if paths.pause.exists():
                with lock:
                    if state["ser"]:
                        state["ser"].close()
                        state["ser"] = None
                if not paths.paused.exists():
                    paths.paused.touch()
                    out.write("\n[paused: port released for flashing]\n")
                    out.flush()
                    logger.note("paused for flashing")
                time.sleep(0.1)
                continue
            if paths.paused.exists():
                paths.paused.unlink(missing_ok=True)
                logger.note("resumed")

            if state["ser"] is None:
                try:
                    ser = open_serial(port, args.baud, args.reset)
                except (OSError, serial.SerialException):
                    if not waiting_note:
                        out.write(f"[waiting for {port}...]\n")
                        out.flush()
                        waiting_note = True
                    time.sleep(0.5)
                    continue
                with lock:
                    state["ser"] = ser
                waiting_note = False
                out.write(f"[connected {port}]\n")
                out.flush()

            try:
                data = state["ser"].read(4096)
            except (OSError, serial.SerialException):
                with lock:
                    try:
                        state["ser"].close()
                    except Exception:
                        pass
                    state["ser"] = None
                out.write("\n[disconnected]\n")
                out.flush()
                logger.note("disconnected")
                continue
            if data:
                out.write(data.decode("utf-8", errors="replace"))
                out.flush()
                logger.feed(data)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        with lock:
            if state["ser"]:
                state["ser"].close()
        logger.note("monitor stopped")
        logger.close()
        paths.pid.unlink(missing_ok=True)
        paths.paused.unlink(missing_ok=True)
        paths.pause.unlink(missing_ok=True)
    return 0


# ------------------------------------------------------------------- commands
def cmd_launch(args) -> int:
    try:
        port = resolve_port(args.port)
    except PortError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 2
    paths = Paths(port)
    if (pid := running_pid(paths)):
        print(f"Monitor already open for {port} (pid {pid}). Log: {paths.log}")
        return 0
    if not (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")):
        print("[ERROR] No graphical session (WAYLAND_DISPLAY/DISPLAY unset). Use `capture` instead.", file=sys.stderr)
        return 2
    try:
        term = choose_terminal(args.terminal)
        argv = [sys.executable, os.path.abspath(__file__), "run", "--port", port, "--baud", str(args.baud)]
        if args.reset:
            argv.append("--reset")
        cmd = terminal_command(term, f"Serial {port}", argv)
    except TerminalError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 2
    subprocess.Popen(cmd, start_new_session=True, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if _wait(lambda: running_pid(paths) is not None, 6):
        print(f"Serial monitor opened in {term}: {port} @ {args.baud} baud")
        print(f"Log for agent: {paths.log}")
        return 0
    print(f"[ERROR] Terminal '{term}' started but monitor did not come up within 6s.", file=sys.stderr)
    return 1


def cmd_stop(args) -> int:
    port = resolve_port_soft(args.port)
    paths = Paths(port)
    pid = running_pid(paths)
    if not pid:
        print(f"Monitor not running for {port}.")
        return 0
    os.kill(pid, signal.SIGTERM)
    if _wait(lambda: running_pid(paths) is None, 5):
        print(f"Monitor for {port} stopped.")
        return 0
    os.kill(pid, signal.SIGKILL)
    paths.pid.unlink(missing_ok=True)
    print(f"Monitor for {port} killed.")
    return 0


def cmd_pause(args) -> int:
    port = resolve_port_soft(args.port)
    paths = Paths(port)
    if not running_pid(paths):
        print(f"Monitor not running for {port}; nothing to pause.")
        return 0
    paths.pause.touch()
    if _wait(paths.paused.exists, 5):
        print(f"Paused: {port} released. Safe to flash.")
        return 0
    print(f"[ERROR] Monitor did not release {port} within 5s.", file=sys.stderr)
    return 1


def cmd_resume(args) -> int:
    port = resolve_port_soft(args.port)
    paths = Paths(port)
    paths.pause.unlink(missing_ok=True)
    if not running_pid(paths):
        print(f"Monitor not running for {port}.")
        return 0
    _wait(lambda: not paths.paused.exists(), 3)
    print(f"Resumed: monitor reconnecting to {port}.")
    return 0


def cmd_status(args) -> int:
    port = resolve_port_soft(args.port)
    paths = Paths(port)
    pid = running_pid(paths)
    if pid:
        state = "paused" if paths.paused.exists() else "live"
        print(f"running pid={pid} port={port} state={state} log={paths.log}")
        return 0
    print(f"not running port={port}")
    return 1


def cmd_tail(args) -> int:
    paths = Paths(resolve_port_soft(args.port))
    if not paths.log.exists():
        print(f"No log yet at {paths.log}", file=sys.stderr)
        return 1
    with open(paths.log, encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()
    sys.stdout.write("".join(lines[-args.n:]))
    return 0


def cmd_capture(args) -> int:
    import serial

    port = resolve_port(args.port)
    paths = Paths(port)
    deadline = time.time() + args.seconds

    if running_pid(paths) and not paths.paused.exists():
        # Monitor owns the port: follow its log instead of opening the port.
        start = paths.log.stat().st_size if paths.log.exists() else 0
        time.sleep(max(0.0, deadline - time.time()))
        with open(paths.log, encoding="utf-8", errors="replace") as fh:
            fh.seek(start)
            sys.stdout.write(fh.read())
        return 0

    ser = None
    while ser is None and time.time() < deadline:
        try:
            ser = open_serial(port, args.baud, args.reset)
        except (OSError, serial.SerialException):
            time.sleep(0.3)
    if ser is None:
        print(f"[ERROR] Could not open {port} within {args.seconds}s.", file=sys.stderr)
        return 2
    try:
        while time.time() < deadline:
            data = ser.read(4096)
            if data:
                sys.stdout.write(data.decode("utf-8", errors="replace"))
                sys.stdout.flush()
    except (OSError, serial.SerialException) as e:
        print(f"\n[disconnected: {e}]", file=sys.stderr)
    finally:
        ser.close()
    return 0


def resolve_port_soft(port: str) -> str:
    """Like resolve_port, but for state lookups: fall back to the only known monitor."""
    if port != "auto":
        return port
    pids = sorted(state_dir().glob("*.pid"))
    if len(pids) == 1:
        return f"/dev/{pids[0].stem}"
    return resolve_port(port)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Serial monitor for embedded-micro")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, fn, **extra):
        sp = sub.add_parser(name)
        sp.add_argument("--port", default="auto")
        sp.add_argument("--baud", type=int, default=115200)
        sp.set_defaults(fn=fn)
        for flag, kw in extra.items():
            sp.add_argument(flag, **kw)
        return sp

    add("launch", cmd_launch, **{"--terminal": {"default": None},
                                 "--reset": {"action": "store_true"}})
    add("run", cmd_run, **{"--reset": {"action": "store_true"}})
    add("stop", cmd_stop)
    add("pause", cmd_pause)
    add("resume", cmd_resume)
    add("status", cmd_status)
    add("tail", cmd_tail, **{"-n": {"type": int, "default": 40}})
    add("capture", cmd_capture, **{"--seconds": {"type": float, "default": 5.0},
                                   "--reset": {"action": "store_true"}})
    args = p.parse_args(argv)
    try:
        return args.fn(args)
    except PortError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
