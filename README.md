# Downloading — Free and Open-Source Windows Software

Graphical Windows media downloader for supported websites, with video/audio quality selection and local saving.

[![Automated tests](https://github.com/amirhoseinteras/downloading-desktop/actions/workflows/tests.yml/badge.svg)](https://github.com/amirhoseinteras/downloading-desktop/actions/workflows/tests.yml)
[Download for Windows](https://github.com/amirhoseinteras/downloading-desktop/releases/latest) · [Source code](https://github.com/amirhoseinteras/downloading-desktop) · [Report a problem](https://github.com/amirhoseinteras/downloading-desktop/issues)

**Version:** 3.1 · **Platform:** Windows · **License:** GPL-3.0-or-later

## Features
- Preview available media information and select a download format or quality.
- Download supported online video and audio using yt-dlp.
- Choose a regular installer or extract a portable Windows ZIP.

## Download and install

| Version | Direct download | How to use |
| --- | --- | --- |
| Installer | [Downloading-Setup.exe](https://github.com/amirhoseinteras/downloading-desktop/releases/latest/download/Downloading-Setup.exe) | Launch setup; installs shortcuts and an uninstaller for the current user |
| Portable | [Downloading-Portable.zip](https://github.com/amirhoseinteras/downloading-desktop/releases/latest/download/Downloading-Portable.zip) | Unzip first; launch Downloading.exe; no installation required |
| Checksum | [SHA256SUMS.txt](https://github.com/amirhoseinteras/downloading-desktop/releases/latest/download/SHA256SUMS.txt) | Verify downloads using SHA-256 |

### Verify your download

~~~powershell
Get-FileHash .\Downloading-Setup.exe -Algorithm SHA256
~~~
Compare the calculated hash with the entry for the same filename in SHA256SUMS.txt.

**Security note:** The Windows EXE files are unsigned. Windows SmartScreen may warn you. Verify files and source code; do not disable security protections just to install an unfamiliar program.

## Requirements and limitations

- Some websites require legitimate login. Support varies by website and yt-dlp version. Some conversions or merges require an independently installed FFmpeg.
- yt-dlp and its dependencies have their own license terms. See THIRD_PARTY.md.
- Use only with content and files you are legally permitted to download or handle.

## Run and test from source

- Windows with Python 3.10+ and Tkinter.
- Clone this repository and open a terminal inside it.
~~~powershell
python -m pip install -r requirements.txt
python downloading.py
python -m unittest discover -s tests -v
~~~

For a Windows executable, install PyInstaller and run the included build script. Installer packaging sources are under packaging/.

## Open-source development

- [License](LICENSE) · [Security guidance](SECURITY.md) · [Third-party notices](https://github.com/amirhoseinteras/downloading-desktop/blob/main/THIRD_PARTY.md)
- [Contributing](CONTRIBUTING.md) · [Version history](CHANGELOG.md) · [Issues](https://github.com/amirhoseinteras/downloading-desktop/issues)
- The published source is intended to be readable by developers, search engines and AI assistants. Check the code for definitive technical behavior.

## فارسی — راهنمای کوتاه

**Downloading** یک نرم‌افزار رایگان و متن‌باز برای ویندوز است. برای نصب، فایل Setup و برای اجرای بدون نصب، فایل Portable ZIP را از بخش Releases دریافت کنید.
برای اطمینان از سالم بودن فایل دانلودشده، مقدار SHA-256 را با فایل SHA256SUMS.txt همان نسخه مقایسه کنید.

---
**Official repository:** https://github.com/amirhoseinteras/downloading-desktop · **Downloads:** https://github.com/amirhoseinteras/downloading-desktop/releases