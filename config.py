# -*- coding: utf-8 -*-
"""
config.py
Centralized configuration file for the PDF to SwiperJS converter.
"""

import os

# --- Paths and Filenames ---
DEFAULT_PDF_FILE = "presentation.pdf"
OUTPUT_JSON_FILE_NAME = "video_metadata.json"
MEDIA_OUTPUT_DIR_NAME = "videos"
SVG_OUTPUT_DIR_NAME = "slides_svg"
OUTPUT_HTML_FILE_NAME = "presentation_swiper.html"
SVG_OUTPUT_EXTENSION = ".svg"

# --- SVG Conversion Configuration ---
SVG_CONVERSION_METHOD = 'pymupdf' # 'pymupdf' or 'pdf2svg'

# --- Library Copying Configuration ---
SOURCE_LIBS_DIR = "libs"
TARGET_LIBS_DIR_NAME = "libs"

# --- Video Transcoding Configuration ---

# -- Codec Selection --
DEFAULT_VIDEO_CODEC = 'h264'
ALLOWED_VIDEO_CODECS = ['h264', 'vp9', 'av1']

# -- Preferred Formats (for skipping unnecessary transcoding) --
PREFERRED_FORMATS = {
    '.mp4': ['h264'],
    '.webm': ['vp9', 'av1'],
}

# -- Format Mapping (Codec -> Extension, MIME Type, Container Opts) --
CODEC_FORMAT_MAP = {
    'h264': {
        'ext': '.mp4', 'mime': 'video/mp4',
        'container_opts': ['-movflags', '+faststart']
    },
    'vp9':  {
        'ext': '.webm', 'mime': 'video/webm',
        'container_opts': []
    },
    'av1':  {
        'ext': '.webm', 'mime': 'video/webm',
        'container_opts': []
    },
}

# -- Pre-Resizing for Oversized Videos --
MAX_PRE_RESIZE_WIDTH = 3840
MAX_PRE_RESIZE_HEIGHT = 2160
FFMPEG_PRE_RESIZE_OPTIONS = [
    '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '8',
    '-c:a', 'copy', '-sn',
]

# -- FFMPEG Options for Main Transcoding --
# Common options (Audio handled conditionally)
FFMPEG_COMMON_OPTIONS = [
    '-map_metadata', '0', '-map_chapters', '0', '-threads', '0',
]

# CPU Encoding Options
FFMPEG_CODEC_OPTIONS_CPU = {
    'h264': [
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
        '-profile:v', 'high', '-level:v', '4.1'
    ],
    'vp9':  [
        '-c:v', 'libvpx-vp9', '-crf', '31', '-b:v', '0',
        '-deadline', 'good', '-row-mt', '1'
    ],
    'av1':  [
        '-c:v', 'libaom-av1', '-crf', '35', '-b:v', '0',
        '-cpu-used', '6', '-row-mt', '1',
        '-tile-columns', '2', '-tile-rows', '2'
    ]
}

# VAAPI Hardware Encoding Options
FFMPEG_CODEC_OPTIONS_VAAPI = {
    'h264': [
        '-c:v', 'h264_vaapi', '-qp', '23', '-profile:v', 'high'
    ],
    'vp9':  [
        '-c:v', 'vp9_vaapi',  '-qp', '31'
    ],
    # --- MODIFIED based on working command ---
    # Using bitrate control as required by rc_mode 2 on user's system
    'av1':  [
        '-c:v', 'av1_vaapi', '-rc_mode', '2', '-b:v', '1M' # Example bitrate
    ]
    # -----------------------------------------
}

ENABLE_TRANSCODING = True
VAAPI_DEVICE_PATH = "" # e.g., '/dev/dri/renderD128'

# --- HTML Generation Configuration ---
HTML_TEMPLATE_DIR = "templates"
HTML_TEMPLATE_NAME = "template.html.j2"
FALLBACK_PAGE_DIMENSIONS = {"width_pt": 960.0, "height_pt": 540.0}

# --- JS/CSS Library Paths ---
SWIPER_CSS_PATH = f"{TARGET_LIBS_DIR_NAME}/swiper/swiper-bundle.min.css"
SWIPER_JS_PATH = f"{TARGET_LIBS_DIR_NAME}/swiper/swiper-bundle.min.js"
PRESENTATION_JS_PATH = "presentation.js"
