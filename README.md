# PDF to HTML Presentation Converter

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
<!-- Add other badges as needed: build status, version, etc. -->

Convert your PDF presentations (exported from LibreOffice Impress, PowerPoint, etc.) into modern, interactive web slideshows based on [Swiper.js](https://swiperjs.com/). This tool extracts embedded videos, converts pages to SVG for high-quality vector rendering, and generates a standalone web application (HTML, CSS, JS).

![Demo Placeholder](placeholder.gif)
## Key Features

* **PDF to HTML Conversion:** Transforms a static PDF into a dynamic web presentation.
* **Swiper.js Integration:** Smooth navigation via keyboard, mouse, and touch (on mobile).
* **SVG Page Rendering:** Converts each PDF page into SVG for crisp vector display at any resolution (uses PyMuPDF or the `pdf2svg` executable).
* **Video Extraction:** Detects and extracts embedded video streams from the PDF.
* **Conditional Video Transcoding:**
  * Converts extracted videos into modern web formats (H.264/MP4, VP9/WebM, AV1/WebM using `ffmpeg`).
  * **Avoids unnecessary transcoding** if the video is already in a preferred format/codec (configurable).
  * Allows selection of the target codec (`--codec`).
* **Optional Video Scaling:**
  * Can scale videos to a given percentage (`--scale-videos`).
  * Automatically pre-scales ultra-high-resolution videos (> 4K by default) to avoid hardware encoding issues.
* **VAAPI Hardware Acceleration (Optional, Linux):**
  * Uses VAAPI hardware acceleration via `ffmpeg` for video encoding (if supported by hardware/drivers), reducing CPU usage.
  * **CPU Fallback:** If VAAPI encoding fails (incompatible hardware, driver error), the tool automatically falls back to CPU encoding.
* **Thumbnail Navigation:** A thumbnail menu (accessible with the 'M' key) allows quick slide navigation.
* **Fullscreen Mode:** A button and the 'F' key enable native browser fullscreen mode.
* **Laser Pointer (Fullscreen):** A red laser pointer is available in fullscreen mode. Its visibility is ensured on all backgrounds using CSS `mix-blend-mode: difference`, so it always stands out whether slides are light or dark. The pointer is small and discreet, optimized for presentations.
* **Standalone:** Copies necessary libraries (Swiper.js) into the output folder for easy deployment.
* **Configurable:** Many options (codecs, quality, paths) can be adjusted in `config.py`.

## Requirements

Before installing and using this tool, make sure your system includes:

1. **Python:** Version 3.8 or higher recommended.
2. **pip:** The Python package manager (usually comes with Python).
3. **FFmpeg and FFprobe:** **Essential** for all video operations (metadata extraction, scaling, transcoding). Must be installed and available in your system's `PATH`.
   * **Linux (Debian/Ubuntu):** `sudo apt update && sudo apt install ffmpeg`
   * **Linux (Fedora):** `sudo dnf install ffmpeg` (may require enabling RPM Fusion repos)
   * **macOS (Homebrew):** `brew install ffmpeg`
   * **Windows:** Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add the `bin` folder to your `PATH`.
4. **`libmagic` Library:** Required for the `python-magic` Python dependency (used for video file type detection).
   * **Linux (Debian/Ubuntu):** `sudo apt install libmagic1`
   * **Linux (Fedora):** `sudo dnf install file-libs`
   * **macOS (Homebrew):** `brew install libmagic`
   * **Windows:** More complex. `python-magic-bin` from PyPI *may* work, but using WSL (Windows Subsystem for Linux) is often simpler for Linux dependencies.
5. **Optional: `pdf2svg`:** Only needed if you plan to use the `--svg-method pdf2svg` option. Must be installed and in the `PATH`.
   * **Linux (Debian/Ubuntu):** `sudo apt install pdf2svg`
   * **Linux (Fedora):** `sudo dnf install pdf2svg`
   * **macOS (Homebrew):** `brew install pdf2svg`

## Installation

1. **Clone the Repository:**
    ```bash
    git clone https://github.com/YOUR_USER/YOUR_REPO.git
    cd YOUR_REPO
    ```
    (Replace `YOUR_USER/YOUR_REPO` with your actual repo URL)

2. **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    This installs `pikepdf`, `python-magic`, `Jinja2`, and `PyMuPDF` (if using the default SVG method `pymupdf`).

## Usage

The tool is used via the command line with the `main.py` script.

**Basic Syntax:**

```bash
python main.py [options] [path_to_pdf]
```

`[path_to_pdf]`: Path to your presentation PDF. If omitted, uses `presentation.pdf` in the current folder (set in `config.py`).

**Available Options:**

- `pdf_file` (positional, optional): Input PDF path. Default: `config.DEFAULT_PDF_FILE`.
- `-o OUTPUT_DIR`, `--output-dir OUTPUT_DIR`: Specify the output directory. If not provided, a folder named after the PDF (without extension) is created in the current directory.
- `--svg-method {pymupdf,pdf2svg}`: Method for converting PDF pages to SVG.
  - `pymupdf` (default): Uses the PyMuPDF Python library. Faster, fewer external dependencies.
  - `pdf2svg`: Uses the external `pdf2svg` executable. May offer better results for complex PDFs, but requires installation.
- `--scale-videos PERCENT`: Scales extracted video resolution to the specified percentage (1-100). Forces transcoding if needed. Example: `--scale-videos 50` to halve the size.
- `--codec {h264,vp9,av1}`: Target video codec for transcoding (if needed). Also determines output container (.mp4 for h264, .webm for vp9/av1). Default: `config.DEFAULT_VIDEO_CODEC` (usually h264).
- `--vaapi`: Attempts to use VAAPI hardware acceleration (Linux only) for video encoding. Requires compatible hardware, up-to-date drivers, and FFmpeg with VAAPI support. Automatically falls back to CPU encoding if VAAPI fails.

## Quick Start with Example

An example presentation is included in the `example` directory. To try it out:

### 1. Generate the HTML Presentation from the Example PDF

From the root of the repository, run:

```bash
python main.py example/presentation.pdf
```

This will generate a new folder called `presentation/` at the root of your project, containing all the HTML, CSS, JS, and media assets for your interactive presentation.

### 2. Open the Interactive Presentation

You can open the generated presentation directly in your browser:

```bash
firefox presentation/presentation_swiper.html  # or use your preferred browser
```

### 3. Try the HTML Integration Example

A ready-to-use HTML integration example is provided in [`example/integration_example.html`](example/integration_example.html). This page demonstrates how to embed your exported presentation into any website using an `<iframe>`.

To view the integration example:

```bash
firefox example/integration_example.html
```

#### What does the integration example show?
- **How to embed the generated presentation** into any web page using a simple `<iframe>`.
- The iframe will display your interactive slides with navigation, videos, and all features enabled.
- The layout is fully responsive: try resizing your browser window or viewing on mobile.

#### How to use in your own website?
You can copy the integration pattern from `example/integration_example.html` and adapt it for your own site. Simply ensure that the `presentation/` folder (containing `presentation_swiper.html` and all assets) is accessible to your web server, then use an iframe like:

```html
<iframe src="/presentation/presentation_swiper.html" style="width:100%;height:80vh;border:none;"></iframe>
```

For more advanced integration (custom navigation, multiple presentations, etc.), you can further adapt the example as needed.


This will demonstrate the key features including:
- Arrow keys for change of slides
- Smooth slide transitions
- Laser pointer in fullscreen mode
- Video playback
- Thumbnail navigation (press 'M')
- Specify output folder:
```bash
python main.py slides/my_presentation.pdf -o output/web_slides
```

Use `pdf2svg` for SVG conversion:
```bash
python main.py presentation.pdf --svg-method pdf2svg
```

Scale videos to 75%:
```bash
python main.py presentation.pdf --scale-videos 75
```

Transcode to VP9/WebM (if needed):
```bash
python main.py presentation.pdf --codec vp9
```

Use VAAPI acceleration (Linux):
```bash
python main.py presentation.pdf --vaapi
```

Combine multiple options:
```bash
python main.py docs/report.pdf -o web_report --codec vp9 --scale-videos 50 --vaapi
```

## Configuration (`config.py`)

The `config.py` file centralizes many parameters for customizing the process:

**Codecs & Formats:**

- `DEFAULT_VIDEO_CODEC`: Default codec for transcoding.
- `ALLOWED_VIDEO_CODECS`: List of codecs the user may request via `--codec`.
- `PREFERRED_FORMATS`: `{'.extension': ['codec1', 'codec2']}`. If an extracted video matches one of these format/codec pairs, transcoding is skipped (unless scaling or explicit change is requested). Useful to avoid reconverting optimized H264/MP4 videos.
- `CODEC_FORMAT_MAP`: Maps each codec to its file extension (.ext), MIME type, and FFmpeg container options.

**Resizing:**

- `MAX_PRE_RESIZE_WIDTH`, `MAX_PRE_RESIZE_HEIGHT`: Dimensions (in pixels) above which videos are pre-scaled (using CPU, fast) before main transcoding. Prevents errors with 8K+ videos and hardware encoders. Set to `None` or `0` to disable.
- `FFMPEG_PRE_RESIZE_OPTIONS`: FFmpeg options for the pre-scaling step.

**FFmpeg Options (Main Transcoding):**

- `FFMPEG_COMMON_OPTIONS`: Options applied to all transcoding runs (audio codec, etc.).
- `FFMPEG_CODEC_OPTIONS_CPU`: Codec-specific options for CPU encoding (preset, CRF).
- `FFMPEG_CODEC_OPTIONS_VAAPI`: Codec-specific options for VAAPI encoding (QP).

**VAAPI:**

- `VAAPI_DEVICE_PATH`: Path to VAAPI device (e.g. `/dev/dri/renderD128`). Leave empty ("") for auto-detection.

**Other:**

- `ENABLE_TRANSCODING`: Global switch to enable/disable transcoding (pre-scaling may still happen).
- Paths to HTML templates, default output folder names, etc.

## Output Folder Structure

After successful execution, the output folder (`-o` or PDF name) typically includes:

```
output_folder/
├── presentation_swiper.html  # <-- Main file to open in browser
├── presentation.js           # Custom JavaScript (navigation, video, etc.)
├── video_metadata.json       # Extracted media info (for debugging)
├── slides_svg/               # Contains SVG files for each page
│   ├── page_1.svg
│   ├── page_2.svg
│   └── ...
├── videos/                   # Contains extracted/transcoded videos
│   ├── slide_1_annot_1_...mp4
│   └── ...
└── libs/                     # Copied JS/CSS libraries
    └── swiper/
        ├── swiper-bundle.min.css
        └── swiper-bundle.min.js
```

---
