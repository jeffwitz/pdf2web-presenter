# -*- coding: utf-8 -*-
"""
svg_converter.py

Handles the conversion of PDF pages to SVG files using either PyMuPDF (fitz)
or the external pdf2svg command-line tool.
"""

import os
import subprocess
import traceback
# Local import
import config

# Conditional import for PyMuPDF (fitz)
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    fitz = None  # Define fitz as None to avoid runtime errors if not imported
except Exception as import_error:
    PYMUPDF_AVAILABLE = False
    fitz = None
    print(f"ERROR: Unexpected error importing PyMuPDF (fitz): {import_error}")


class SvgConverter:
    """
    Converts PDF pages to SVG files via the selected method (PyMuPDF or pdf2svg).
    """

    def __init__(self, config_obj, svg_output_dir, method='pymupdf',
                 pdf2svg_path=None):
        """
        Initializes the SVG converter.

        Args:
            config_obj: The configuration object (from config.py).
            svg_output_dir (str): The absolute path to the output directory
                                  for SVG files.
            method (str): The conversion method ('pymupdf' or 'pdf2svg').
                          Defaults to 'pymupdf'.
            pdf2svg_path (str, optional): The path to the pdf2svg executable.
                                          Required if method is 'pdf2svg'.

        Raises:
            ImportError: If 'pymupdf' method is chosen but PyMuPDF (fitz)
                         is not installed or could not be imported.
            ValueError: If 'pdf2svg' method is chosen but pdf2svg_path is
                        not provided or is not a valid file path.
            NotImplementedError: If an unknown conversion method is requested.
        """
        self.config = config_obj
        self.svg_output_dir = svg_output_dir
        self.svg_extension = self.config.SVG_OUTPUT_EXTENSION or '.svg'
        self.method = method.lower()
        self.pdf2svg_path = pdf2svg_path

        if self.method == 'pymupdf':
            if not PYMUPDF_AVAILABLE:
                raise ImportError(
                    "Method 'pymupdf' chosen but PyMuPDF (fitz) is not "
                    "installed or could not be imported. "
                    "Please install it (`pip install PyMuPDF`)."
                )
            print("INFO: SvgConverter initialized using PyMuPDF (fitz).")
        elif self.method == 'pdf2svg':
            if not self.pdf2svg_path or not os.path.isfile(self.pdf2svg_path):
                raise ValueError(
                    f"Method 'pdf2svg' chosen but the provided path "
                    f"'{self.pdf2svg_path}' is invalid, not provided, "
                    f"or not a file."
                )
            print(f"INFO: SvgConverter initialized using pdf2svg "
                  f"({self.pdf2svg_path}).")
        else:
            raise NotImplementedError(
                f"Unknown SVG conversion method: '{self.method}'"
            )

    def convert_all(self, pdf_path, num_pages_expected):
        """
        Converts all expected pages of the PDF to SVG using the chosen method.

        Args:
            pdf_path (str): The path to the input PDF file.
            num_pages_expected (int): The number of pages expected to be
                                      converted (usually from PdfAnalyzer).

        Returns:
            bool: True if all expected pages were converted successfully,
                  False otherwise.
        """
        if not os.path.exists(pdf_path):
            print(f"ERROR: Input PDF file not found for SVG conversion: "
                  f"'{pdf_path}'")
            return False
        if num_pages_expected <= 0:
            print(f"ERROR: Invalid number of expected pages "
                  f"({num_pages_expected}) for SVG conversion.")
            return False

        try:
            os.makedirs(self.svg_output_dir, exist_ok=True)
            print(f"SVG conversion (method: {self.method}) outputting to: "
                  f"{self.svg_output_dir}")

            if self.method == 'pymupdf':
                return self._convert_with_pymupdf(pdf_path, num_pages_expected)
            elif self.method == 'pdf2svg':
                return self._convert_with_pdf2svg(pdf_path, num_pages_expected)
            else:
                # Should not happen due to __init__ check, but safeguard
                print(f"INTERNAL ERROR: Method {self.method} not supported "
                      "in convert_all.")
                return False
        except Exception as general_error:
            print(f"ERROR: Unexpected general error during SVG conversion "
                  f"({self.method}): {general_error}")
            traceback.print_exc()
            return False

    def _convert_with_pymupdf(self, pdf_path, num_pages_expected):
        """Internal logic for converting pages using PyMuPDF."""
        created_files_count = 0
        doc = None
        try:
            doc = fitz.open(pdf_path)
            num_pages_actual = doc.page_count

            if num_pages_actual != num_pages_expected:
                print(f"WARN (PyMuPDF): Actual page count ({num_pages_actual}) "
                      f"differs from expected ({num_pages_expected}). "
                      f"Attempting to convert {num_pages_expected} pages.")

            for page_index in range(num_pages_expected):
                if page_index >= num_pages_actual:
                    print(f"ERROR (PyMuPDF): Page index {page_index + 1} is "
                          f"out of bounds ({num_pages_actual} actual pages). "
                          "Cannot generate SVG.")
                    continue  # Skip this page, will result in overall failure

                page = doc.load_page(page_index)  # 0-based index
                svg_filename = f"page_{page_index + 1}{self.svg_extension}"
                output_path = os.path.join(self.svg_output_dir, svg_filename)

                try:
                    # text_as_path=True embeds fonts as paths (more robust rendering)
                    # but can increase file size.
                    svg_text = page.get_svg_image(text_as_path=True)
                    with open(output_path, "w", encoding="utf-8") as svg_file:
                        svg_file.write(svg_text)
                    created_files_count += 1
                except Exception as page_error:
                    print(f"ERROR (PyMuPDF): Failed to convert page "
                          f"{page_index + 1}: {page_error}")
                    # Attempt to clean up potentially corrupt output file
                    if os.path.exists(output_path):
                        try:
                            os.remove(output_path)
                        except OSError:
                            print(f"  WARN: Could not remove failed SVG file "
                                  f"{output_path}")

        except fitz.fitz.FileNotFoundError:
            print(f"ERROR (PyMuPDF): Input PDF file not found or inaccessible: "
                  f"'{pdf_path}'")
            return False
        except Exception as pymupdf_error:
            print(f"ERROR: Unexpected error during PyMuPDF conversion: "
                  f"{pymupdf_error}")
            traceback.print_exc()
            return False  # Ensure False is returned on unexpected errors
        finally:
            if doc:
                doc.close()
            print(f"SVG conversion (PyMuPDF) finished. "
                  f"{created_files_count}/{num_pages_expected} SVG file(s) "
                  f"generated successfully.")

        # Final success check
        if created_files_count == num_pages_expected:
            print("  Number of generated SVG files matches expected count.")
            return True
        else:
            print(f"  WARN: Number of generated SVG files ({created_files_count}) "
                  f"does not match expected count ({num_pages_expected}).")
            return False

    def _convert_with_pdf2svg(self, pdf_path, num_pages_expected):
        """Internal logic for converting pages using pdf2svg external tool."""
        try:
            # Output pattern for pdf2svg filenames
            output_pattern = os.path.join(
                self.svg_output_dir, f"page_%d{self.svg_extension}"
            )

            cmd = [self.pdf2svg_path, pdf_path, output_pattern, "all"]
            print(f"CMD pdf2svg: {' '.join(cmd)}")

            result = subprocess.run(
                cmd, capture_output=True, text=True, check=False,
                encoding='utf-8', errors='replace'
            )

            # Check if pdf2svg reported an error
            if result.returncode != 0:
                print(f"ERROR: pdf2svg failed (exit code: {result.returncode})")
                if result.stdout:
                    print(f"  pdf2svg stdout:\n{result.stdout.strip()}")
                if result.stderr:
                    print(f"  pdf2svg stderr:\n{result.stderr.strip()}")
                # Check if some files were created despite the error
                created_files = self._check_created_svg_files(num_pages_expected)
                print(f"  {len(created_files)} SVG file(s) found after error.")
                return False # Treat non-zero exit code as failure

            else:
                print("SVG conversion (pdf2svg) completed (exit code 0).")
                if result.stderr:
                    # stderr might contain warnings even on success
                    print(f"  pdf2svg messages (stderr):\n{result.stderr.strip()}")

                # Verify if the expected number of files was created
                created_files = self._check_created_svg_files(num_pages_expected)
                print(f"  {len(created_files)} SVG file(s) found in "
                      f"{self.svg_output_dir}.")
                if len(created_files) == num_pages_expected:
                    print("  Number of generated SVG files matches expected count.")
                    return True
                else:
                    print(f"  WARN: Number of SVG files ({len(created_files)}) "
                          f"does not match expected ({num_pages_expected}).")
                    # Consider it a failure if pages are missing
                    return False

        except FileNotFoundError:
            # Should not happen if path is checked in __init__, but safeguard
            print(f"ERROR: pdf2svg executable not found at "
                  f"'{self.pdf2svg_path}'.")
            return False
        except OSError as os_error:
            print(f"ERROR: OS error during pdf2svg execution: {os_error}")
            return False
        except Exception as pdf2svg_error:
            print(f"ERROR: Unexpected error during pdf2svg conversion: "
                  f"{pdf2svg_error}")
            traceback.print_exc()
            return False

    def _check_created_svg_files(self, expected_num_pages):
        """
        Checks how many 'page_N.svg' files exist in the output directory.

        Args:
            expected_num_pages (int): The number of pages originally expected.

        Returns:
            list: A list of filenames (str) of the found SVG files.
        """
        svg_files = []
        if not os.path.isdir(self.svg_output_dir):
            return svg_files # Return empty list if dir doesn't exist

        try:
            for i in range(1, expected_num_pages + 1):
                svg_filename = f"page_{i}{self.svg_extension}"
                if os.path.exists(os.path.join(self.svg_output_dir, svg_filename)):
                    svg_files.append(svg_filename)
        except Exception as list_error:
            print(f"Error while checking for created SVG files: {list_error}")
        return svg_files
