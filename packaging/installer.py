"""Per-user, offline Windows installer for AmigaNLoad."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

APP_TITLE = "AmigaNLoad"
APP_VERSION = "3.2"
APP_EXE = "AmigaNLoad.exe"
ASSETS = ["AmigaNLoad.ico", "AmigaNLoad_header_logo.png"]

# Reuse the old folder and uninstall key so Downloading 3.1 can be upgraded in place.
LEGACY_TITLE = "Downloading"
LEGACY_EXE = "Downloading.exe"
LEGACY_ASSETS = ["Downloading.ico", "Downloading_header_logo.png"]
REG_KEY = "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Downloading-OpenSource"
ROOT = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Programs" / LEGACY_TITLE


def payload_root():
    return Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "payload"


def payload_ready():
    return (payload_root() / APP_EXE).is_file()


def shortcut(folder: Path, executable: Path):
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / (APP_TITLE + ".lnk")

    def ps(value):
        return "'" + str(value).replace("'", "''") + "'"

    script = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut(" + ps(target) + ");"
        "$s.TargetPath=" + ps(executable) + ";"
        "$s.WorkingDirectory=" + ps(executable.parent) + ";"
        "$s.Save()"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        timeout=20,
    )
    if result.returncode:
        raise RuntimeError("Shortcut error: " + result.stderr[-400:])
    return target


def remove_old_shortcuts():
    program = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    desktop = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
    for path in (program / (LEGACY_TITLE + ".lnk"), desktop / (LEGACY_TITLE + ".lnk")):
        if path.exists():
            path.unlink()


def install(folder: Path, register=True):
    if not payload_ready():
        raise RuntimeError("App payload missing in setup.")
    folder.mkdir(parents=True, exist_ok=True)

    old_exe = folder / LEGACY_EXE
    if old_exe.exists():
        try:
            old_exe.unlink()
        except OSError as exc:
            raise RuntimeError(
                "Close the previous Downloading application, then run this installer again."
            ) from exc

    required_payload = [payload_root() / name for name in [APP_EXE] + ASSETS]
    for source in required_payload:
        if not source.is_file():
            raise FileNotFoundError(source)

    for source in required_payload:
        shutil.copy2(source, folder / source.name)

    for name in LEGACY_ASSETS:
        old_asset = folder / name
        if old_asset.is_file():
            old_asset.unlink()

    if register:
        shutil.copy2(sys.executable, folder / "Uninstall.exe")
        program = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        desktop = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
        remove_old_shortcuts()
        shortcut(program, folder / APP_EXE)
        shortcut(desktop, folder / APP_EXE)

        import winreg

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_KEY) as key:
            values = {
                "DisplayName": APP_TITLE,
                "DisplayVersion": APP_VERSION,
                "Publisher": "Open-source contributors",
                "InstallLocation": str(folder),
                "DisplayIcon": str(folder / APP_EXE),
                "UninstallString": '"' + str(folder / "Uninstall.exe") + '" --uninstall',
            }
            for name, value in values.items():
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)

    return folder / APP_EXE


def uninstall(folder: Path, register=True):
    if register:
        program = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        desktop = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
        for link in (
            program / (APP_TITLE + ".lnk"),
            desktop / (APP_TITLE + ".lnk"),
            program / (LEGACY_TITLE + ".lnk"),
            desktop / (LEGACY_TITLE + ".lnk"),
        ):
            if link.exists():
                link.unlink()

        import winreg

        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, REG_KEY)
        except FileNotFoundError:
            pass

    for name in [APP_EXE, LEGACY_EXE] + ASSETS + LEGACY_ASSETS:
        item = folder / name
        if item.is_file():
            item.unlink()

    if register and (folder / "Uninstall.exe").exists():
        script = (
            "Start-Sleep -Seconds 2;Remove-Item -LiteralPath "
            + repr(str(folder))
            + " -Recurse -Force -ErrorAction SilentlyContinue"
        )
        subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-Command", script],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

    try:
        folder.rmdir()
    except OSError:
        pass


def main():
    args = sys.argv[1:]
    if args == ["--inspect"]:
        print("SETUP_OK", APP_TITLE, APP_VERSION, "PAYLOAD", payload_ready())
        return 0 if payload_ready() else 2

    if len(args) == 2 and args[0] in ("--install-test", "--uninstall-test"):
        folder = Path(args[1]).resolve()
        temp = Path(os.environ.get("TEMP", str(Path.home()))).resolve()
        if not folder.is_relative_to(temp) or folder == temp:
            raise ValueError("Test install path must be a subdirectory of TEMP")
        if args[0] == "--install-test":
            print("TEST_INSTALLED", install(folder, False))
        else:
            uninstall(folder, False)
            print("TEST_UNINSTALLED", folder)
        return 0

    tk.Tk().withdraw()
    if args == ["--uninstall"]:
        if messagebox.askyesno(APP_TITLE, "Uninstall " + APP_TITLE + "?"):
            uninstall(ROOT)
            messagebox.showinfo(APP_TITLE, "Uninstalled. Your downloaded files are kept.")
        return 0

    if not payload_ready():
        messagebox.showerror(APP_TITLE, "Damaged setup: app payload missing.")
        return 2

    if not messagebox.askyesno(
        APP_TITLE,
        "Install " + APP_TITLE + " " + APP_VERSION
        + " for the current user? Desktop and Start Menu shortcuts will be created.",
    ):
        return 0

    try:
        exe = install(ROOT)
        messagebox.showinfo(APP_TITLE, "Installed successfully to:\n" + str(exe))
        return 0
    except Exception as exc:
        messagebox.showerror(APP_TITLE, "Install failed:\n" + str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
