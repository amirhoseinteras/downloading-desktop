# Downloading (Windows)

A free graphical Windows downloader for supported media links. Select video/audio quality, inspect metadata and save to disk.

Version 3.1.

## Download / دانلود

Download the latest Setup.exe from GitHub Releases for installation with shortcuts and uninstall; or download Portable ZIP for extraction and direct use of Downloading.exe.

## Source installation

Windows and Python 3.10+ with Tkinter required. Install dependencies with: python -m pip install -r requirements.txt

Then run: python downloading.py

## Notes / نکات

Some sites require login. For video/audio stream merging and conversion, install FFmpeg separately alongside the EXE.

Use for lawful downloads only. Never share browser cookies or login details.

## Security and license

See SECURITY.md, THIRD_PARTY.md and LICENSE. License: GPL-3.0-or-later. Contributions and responsible issue reports welcome.

## Reproducible Windows builds

Install Python 3.10+, run 'python -m pip install -r requirements.txt pyinstaller' then 'python build_windows.py'. Outputs are under dist/. The installer provides per-user installation and uninstall; it never requires administrator access.
