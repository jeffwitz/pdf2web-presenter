# -*- coding: utf-8 -*-
"""
utils.py
Utility functions and dependency checking for the PDF to SwiperJS converter.
"""

import shutil
import sys
import os  # Needed for os.path below if you re-add functions using it

try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    magic = None # Define as None to avoid NameErrors later
except Exception as import_error:
    # Catch other potential import errors (e.g., library installed but broken)
    MAGIC_AVAILABLE = False
    magic = None
    print(f"WARN: Failed to import or initialize python-magic: {import_error}")

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    fitz = None
except Exception as import_error:
    PYMUPDF_AVAILABLE = False
    fitz = None
    print(f"WARN: Failed to import PyMuPDF (fitz): {import_error}")


def check_dependencies():
    """
    Checks for the presence of external command-line tools (ffmpeg, ffprobe,
    pdf2svg) and key Python libraries (PyMuPDF, python-magic).

    Returns:
        dict: A dictionary containing the check results. Keys are dependency
              names ('ffmpeg', 'ffprobe', 'pdf2svg', 'pymupdf', 'magic').
              Values are either the path (str) to the executable if found
              (for command-line tools) or a boolean indicating availability
              (for Python libraries).
    """
    print("Checking dependencies...")
    dependencies = {
        'ffmpeg': shutil.which("ffmpeg"),
        'ffprobe': shutil.which("ffprobe"),
        'pdf2svg': shutil.which("pdf2svg"),
        'pymupdf': PYMUPDF_AVAILABLE,  # Uses the result from the module-level import
        'magic': False  # Default to False, check below
    }

    # Check python-magic initialization (more robust than just import)
    if MAGIC_AVAILABLE:
        try:
            # Attempt to instantiate the Magic class
            _ = magic.Magic(mime=True)
            dependencies['magic'] = True
            print("  python-magic: Found and initialized.")
        except magic.MagicException as magic_runtime_error:
            # Specific error if libmagic files are missing/corrupt
            print("ERROR: Failed to initialize python-magic "
                  f"({magic_runtime_error}).\n"
                  "  Check system's libmagic installation and paths.")
            dependencies['magic'] = False # Mark as unavailable
        except Exception as magic_error:
            # Catch other potential initialization errors
            print(f"WARN: Error initializing python-magic: {magic_error}")
            dependencies['magic'] = False # Mark as unavailable
    else:
        print("  python-magic: Library not found or import failed.")

    # Log findings for command-line tools
    for tool in ['ffmpeg', 'ffprobe', 'pdf2svg']:
        if dependencies[tool]:
            print(f"  {tool}: Found at {dependencies[tool]}")
        else:
            print(f"  {tool}: Not found in PATH.")
    # Log findings for Python libs (already logged during import/init check)
    print(f"  pymupdf (fitz): {'Available' if dependencies['pymupdf'] else 'Unavailable'}")

    return dependencies
