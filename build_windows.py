"""Reproducible Windows build for AmigaNLoad."""
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
NAME = "AmigaNLoad"
SOURCE = "downloading.py"
ASSETS = ["AmigaNLoad.ico", "AmigaNLoad_header_logo.png"]
ICON = "AmigaNLoad.ico"


def run(args):
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--windowed"] + args,
        check=True,
        cwd=ROOT,
    )


def main():
    for folder in (ROOT / "build", ROOT / "dist"):
        if folder.exists():
            shutil.rmtree(folder)

    basic = ["--name", NAME]
    if ICON:
        basic += ["--icon", ICON]
    run(basic + [SOURCE])

    app = ROOT / "dist" / (NAME + ".exe")
    if not app.is_file():
        raise FileNotFoundError(app)

    # The Portable archive contains only the executable and required runtime images.
    archive = ROOT / "dist" / (NAME + "-Portable.zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as out:
        for filename in [app.name] + ASSETS:
            path = ROOT / "dist" / filename if filename == app.name else ROOT / filename
            if not path.is_file():
                raise FileNotFoundError(path)
            out.write(path, arcname=filename)

    args = ["--name", NAME + "-Setup", "--add-data", str(app) + ";payload"]
    for asset in ASSETS:
        args += ["--add-data", str(ROOT / asset) + ";payload"]
    if ICON:
        args += ["--icon", ICON]
    run(args + ["packaging/installer.py"])

    setup = ROOT / "dist" / (NAME + "-Setup.exe")
    if not setup.is_file():
        raise FileNotFoundError(setup)

    print("BUILT", app, archive, setup)


if __name__ == "__main__":
    main()
