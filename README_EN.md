# WenQi · 文齐

<p align="center"><img src="assets/icon.png" alt="WenQi icon" width="128"></p>
<p align="center"><strong>Keep your document formatting consistent.</strong></p>

[中文说明](README.md) · [Developer notes](README_DEV.md) · [Issues](https://github.com/Weisiren-liu/wenqi/issues)

WenQi is a local utility for formatting Word documents. Its new Liquid Glass desktop interface separates documents from format editing. Start from a custom format or a built-in preset, edit parameters inline, then apply them to one or multiple documents.

![WenQi main window](assets/screenshot.png)

## Features and limitations

- Edit fonts, sizes, bold, alignment, indentation, line and paragraph spacing per document element.
- Choose official-document, academic or legal starting presets; save your own formats. Overrides remain separate from defaults and can be reset by row or in full.
- Edit paragraph, page, table and cleanup parameters in separate tabs, with automatic saving and a format preview.
- Batch-process files or folders, or create a `.docx` from pasted text.
- Choose automatic formatting, a diagnostic report, or punctuation repair alone.
- Apply Chinese typography rules while preserving embedded images and attachment media.
- Optionally produce tracked formatting changes for review in Word.

Processing runs locally without document uploads, telemetry or background network requests. The UI is primarily Chinese. Paragraph classification still follows Chinese official-document conventions; academic and legal presets are formatting starting points. Diagnostics do **not yet validate every setting against the selected custom format**. Review the output manually, especially for complex documents or missing fonts.

## Run from source

Prebuilt packages have not been published here yet. Future packages will be available from [Releases](https://github.com/Weisiren-liu/wenqi/releases).

Python 3.11 or newer is recommended:

```bash
git clone https://github.com/Weisiren-liu/wenqi.git
cd wenqi
python -m venv .venv
```

Activate with `.venv\Scripts\Activate.ps1` in Windows PowerShell, or `source .venv/bin/activate` on macOS / Linux. Then run:

```bash
python -m pip install -r requirements.txt
python docformat_gui.py
```

The new interface uses Edge WebView2 on Windows and the system WKWebView on macOS. Linux needs Tk, GTK / WebKitGTK and PyGObject; install the appropriate system packages and `pywebview[gtk]`. Alternatively, use `bash install.sh` to set up an environment and launch the application.

All platforms support `.docx` without Microsoft Word. Windows can additionally convert `.doc` / `.wps` through locally installed Microsoft Office or WPS Office. On macOS / Linux, convert those formats first. Install the selected fonts for consistent results. The new interface uses native browser file drops. Python 3.8 / Windows 7 builds retain the Tk interface and `tkinterdnd2` support.

## Workflow

1. Select files and an output location.
2. Choose a starting format and edit parameters in the Format workspace.
3. Select a processing mode and start.
4. Review and open the output from the result panel. Default output is a sibling file with a `_processed` suffix; existing outputs receive a numeric suffix.

Saved formats and overrides persist between launches. The historical `DocFormatter` configuration directory is retained for compatibility; see [developer notes](README_DEV.md).

## Development

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m pip install pyinstaller
python build.py windows   # windows / linux / macos, on the matching host
```

Outputs use `wenqi_`, such as `wenqi_windows.exe`. GitHub Actions supports manual builds and releases from `v*` tags. Windows 7 builds use Python 3.8 and `requirements-win7.txt`; macOS signing and notarization require repository secrets.

## Attribution and license

WenQi derives from KaguraNanaga's **MIT-licensed docformat-gui v1.8.8.2**. This branch unifies configuration paths and preset management, introduces inline formatting controls and narrow-window support, and adds the WenQi identity and icon. Original author: **KaguraNanaga**. Fork maintained by **Weisiren-liu**.

The [MIT license](LICENSE) permits use, modification and distribution, including commercial use, with the original copyright and license notice retained. See [third-party licenses](THIRD_PARTY_LICENSES.md), [privacy and disclaimer](DISCLAIMER.md) and [brand asset notes](docs/BRANDING.md).
