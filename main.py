# -*- coding: utf-8 -*-
"""
main.py
Entry point and orchestrator for converting a PDF into a Swiper.js web presentation.

This script analyzes a PDF, extracts/processes media, converts pages to SVG
(using either PyMuPDF or pdf2svg), and generates an interactive HTML file.
It handles command-line options for the input file, SVG conversion method,
target video codec, optional video scaling, and VAAPI hardware acceleration (Linux).
"""

import argparse
import json
import os
import pathlib
import shutil
import sys
import traceback

# Import refactored modules
import config
import utils
from html_generator import HtmlBuilder
from media_extractor import MediaProcessor
from pdf_processor import PdfAnalyzer
from svg_converter import SvgConverter


def copy_libs(source_dir, target_dir):
    """
    Copies the necessary library files (swiper) to the output directory.

    Args:
        source_dir (str): Path to the directory containing the 'libs' subdir.
        target_dir (str): Path to the main output directory ('output').

    Returns:
        bool: True if copying succeeds or if the directory already exists
              after cleanup, False on error.
    """
    # Path to the source 'swiper' directory inside 'libs'
    source_swiper_path = os.path.join(source_dir, config.SOURCE_LIBS_DIR, 'swiper')
    # Path to the target 'libs' directory inside the output folder
    target_libs_path = os.path.join(target_dir, config.TARGET_LIBS_DIR_NAME)
    # Final path for the 'swiper' directory in the output folder
    target_swiper_path = os.path.join(target_libs_path, 'swiper')

    if not os.path.isdir(source_swiper_path):
        print(f"WARN: Swiper source directory not found: '{source_swiper_path}'. "
              "Libs will not be copied.")
        return False

    try:
        # Clean up destination before copying
        if os.path.isdir(target_swiper_path):
            print(f"Cleaning up old directory: {target_swiper_path}")
            shutil.rmtree(target_swiper_path)
        elif os.path.exists(target_swiper_path):
            # Just in case it's a file by mistake
            os.remove(target_swiper_path)

        # Ensure the parent 'libs' directory exists in output
        os.makedirs(target_libs_path, exist_ok=True)

        # Copy the directory tree
        print(f"Copying '{source_swiper_path}' to '{target_swiper_path}'...")
        shutil.copytree(source_swiper_path, target_swiper_path)
        print("Swiper libraries copied successfully.")
        return True
    except Exception as error:
        print(f"ERROR copying Swiper libraries: {error}")
        traceback.print_exc(limit=1)
        return False


def main():
    """Main function orchestrating the conversion process."""
    print(f"***** STARTING ORCHESTRATOR ({os.path.basename(__file__)}) *****")

    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(
        description="Converts PDF to a SwiperJS web presentation."
    )
    parser.add_argument(
        'pdf_file',
        nargs='?',  # Makes the positional argument optional
        default=config.DEFAULT_PDF_FILE,
        help=f"Path to the input PDF file (default: {config.DEFAULT_PDF_FILE})"
    )
    parser.add_argument(
        '-o', '--output-dir',
        default=None,  # Default is None, calculated later if not provided
        metavar='DIR',
        help=("Main output directory. If not provided, uses the input PDF "
              "filename (without extension) as the directory name.")
    )
    parser.add_argument(
        '--svg-method',
        choices=['pymupdf', 'pdf2svg'],
        default=config.SVG_CONVERSION_METHOD.lower(),
        help="SVG conversion method (default: %(default)s)."
    )
    parser.add_argument(
        '--scale-videos',
        type=int,
        metavar='PERCENT',
        default=None,
        help=("Optional: Scale video resolution to PERCENT%% of original "
              "(1-100). Forces transcoding.")
    )
    parser.add_argument(
        '--vaapi',
        action='store_true',
        help=('Attempt VA-API hardware acceleration (Linux, if codec '
              'supported).')
    )
    parser.add_argument(
        '--codec',
        choices=config.ALLOWED_VIDEO_CODECS,
        default=config.DEFAULT_VIDEO_CODEC,
        help=("Target video codec (default: %(default)s). Also determines "
              "the container (mp4/webm).")
    )
    args = parser.parse_args()

    # --- Determine Input and Output Paths ---
    pdf_input_path = os.path.abspath(args.pdf_file)

    # Determine output directory based on argument or PDF filename
    if args.output_dir:
        output_base_dir = os.path.abspath(args.output_dir)
    else:
        pdf_basename = os.path.basename(pdf_input_path)
        pdf_name_without_ext, _ = os.path.splitext(pdf_basename)
        # Default output dir is named after the PDF, in the current working dir
        output_base_dir = os.path.abspath(pdf_name_without_ext)

    # Store other arguments
    svg_method_to_use = args.svg_method
    use_vaapi_arg = args.vaapi
    codec_choice_arg = args.codec
    scaling_factor_arg = args.scale_videos  # Validation happens below

    print(f"Input PDF file: {pdf_input_path}")
    print(f"Output directory: {output_base_dir}")
    print(f"Chosen SVG method: '{svg_method_to_use}'")
    print(f"Chosen video codec: '{codec_choice_arg}'")

    # --- Validate and Log Optional Arguments ---
    if scaling_factor_arg is not None:
        if not (1 <= scaling_factor_arg <= 100):
            parser.error(
                f"--scale-videos: value {scaling_factor_arg} must be between 1 and 100."
            )
        print(f"INFO: Video scaling enabled: {scaling_factor_arg}%.")
    if use_vaapi_arg:
        print("VAAPI acceleration requested.")

    # --- Verify Input PDF Exists ---
    if not os.path.exists(pdf_input_path):
        print(f"ERROR: Input PDF file '{pdf_input_path}' not found!")
        sys.exit(1)

    # --- Create Output Directory and Define Paths ---
    try:
        os.makedirs(output_base_dir, exist_ok=True)
        print(f"Output directory ensured: {output_base_dir}")
    except OSError as error:
        print(f"ERROR: Could not create output directory "
              f"'{output_base_dir}': {error}")
        sys.exit(1)

    # Define absolute paths for subdirectories and output files
    media_dir_abs = os.path.join(output_base_dir, config.MEDIA_OUTPUT_DIR_NAME)
    svg_dir_abs = os.path.join(output_base_dir, config.SVG_OUTPUT_DIR_NAME)
    json_output_abs = os.path.join(
        output_base_dir, config.OUTPUT_JSON_FILE_NAME
    )
    html_output_abs = os.path.join(
        output_base_dir, config.OUTPUT_HTML_FILE_NAME
    )
    presentation_js_output_path = os.path.join(
        output_base_dir, os.path.basename(config.PRESENTATION_JS_PATH)
    )

    # Create media and SVG subdirectories
    os.makedirs(media_dir_abs, exist_ok=True)
    os.makedirs(svg_dir_abs, exist_ok=True)

    # --- Check Dependencies ---
    dependencies = utils.check_dependencies()
    print("--- External Dependency Check ---")
    print(f"  python-magic: {'Found' if dependencies['magic'] else 'Not Found'}")
    print(f"  pymupdf (fitz): {'Available' if dependencies['pymupdf'] else 'Unavailable'}")
    print(f"  pdf2svg: {'Found ('+str(dependencies['pdf2svg'])+')' if dependencies['pdf2svg'] else 'Not Found'}")
    print(f"  ffmpeg: {'Found ('+str(dependencies['ffmpeg'])+')' if dependencies['ffmpeg'] else 'Not Found'}")
    print(f"  ffprobe: {'Found ('+str(dependencies['ffprobe'])+')' if dependencies['ffprobe'] else 'Not Found (pre-resize unavailable)'}")

    # --- Check VAAPI Feasibility ---
    # Even if requested, check basic conditions
    if use_vaapi_arg:
        vaapi_possible = True # Assume possible initially
        if not dependencies['ffmpeg']:
            print("WARN: VAAPI requested but ffmpeg not found.")
            vaapi_possible = False
        elif not sys.platform.startswith('linux'):
            print("WARN: VAAPI requested but OS is not Linux.")
            vaapi_possible = False
        elif codec_choice_arg not in config.FFMPEG_CODEC_OPTIONS_VAAPI:
            print(f"WARN: VAAPI requested but not configured for codec '{codec_choice_arg}'.")
            vaapi_possible = False
        elif not dependencies['ffprobe']:
            print("WARN: VAAPI potentially usable but ffprobe not found "
                  "(cannot pre-check resolution).")
        else:
            # Basic check for VAAPI render nodes
            try:
                render_devices = [d for d in os.listdir('/dev/dri/') if d.startswith('renderD')]
                if not render_devices:
                    print("WARN: VAAPI requested but no /dev/dri/renderD* devices found.")
                # else: print(f"INFO: Potential VAAPI render devices found: {render_devices}")
            except FileNotFoundError:
                print("WARN: VAAPI requested but /dev/dri directory not found.")
                vaapi_possible = False
            except Exception as dri_error:
                print(f"WARN: Error checking /dev/dri: {dri_error}.")

        if not vaapi_possible:
            print("INFO: VAAPI usage disabled due to failed checks.")
            use_vaapi_arg = False # Update the flag passed to MediaProcessor

    # --- Check SVG Method Availability and Fallback ---
    can_use_pymupdf = dependencies['pymupdf']
    can_use_pdf2svg = bool(dependencies['pdf2svg'])
    original_svg_method_request = svg_method_to_use
    valid_svg_method_found = True

    # Check and potentially switch SVG method based on availability
    if svg_method_to_use == 'pymupdf':
        if not can_use_pymupdf:
            print("WARN: Method 'pymupdf' requested but PyMuPDF is unavailable.")
            valid_svg_method_found = False
            if can_use_pdf2svg:
                svg_method_to_use = 'pdf2svg'
                print("INFO: Attempting to use 'pdf2svg' as fallback.")
                valid_svg_method_found = True
            else:
                print("ERROR: No available SVG conversion method.")
                svg_method_to_use = None
    elif svg_method_to_use == 'pdf2svg':
        if not can_use_pdf2svg:
            print("WARN: Method 'pdf2svg' requested but pdf2svg not found.")
            valid_svg_method_found = False
            if can_use_pymupdf:
                svg_method_to_use = 'pymupdf'
                print("INFO: Attempting to use 'pymupdf' as fallback.")
                valid_svg_method_found = True
            else:
                print("ERROR: No available SVG conversion method.")
                svg_method_to_use = None
    # This else case should not be reached due to argparse choices
    # else:
    #     print(f"ERROR: Invalid SVG method '{svg_method_to_use}'.")
    #     svg_method_to_use = None
    #     valid_svg_method_found = False

    # Log final SVG method decision
    if valid_svg_method_found and svg_method_to_use != original_svg_method_request:
        print(f"INFO: Using fallback SVG method '{svg_method_to_use}'.")
    elif not valid_svg_method_found:
        print("INFO: SVG conversion will be skipped (no valid method available).")

    # --- Copy Libraries and Custom JS ---
    print("\n--- Copying JS/CSS libraries and custom script ---")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # copy_libs expects the parent directory containing 'libs'
    source_libs_dir_parent = script_dir
    libs_copied_ok = copy_libs(source_libs_dir_parent, output_base_dir)
    if not libs_copied_ok:
        print("WARN: Swiper libraries could not be copied.")

    # Copy custom JS
    js_filename = os.path.basename(config.PRESENTATION_JS_PATH)
    source_presentation_js = os.path.join(script_dir, js_filename)
    if os.path.exists(source_presentation_js):
        try:
            shutil.copy2(source_presentation_js, presentation_js_output_path)
            print(f"Copied '{js_filename}' successfully.")
        except Exception as copy_js_error:
            print(f"ERROR copying {js_filename}: {copy_js_error}")
    else:
        print(f"WARN: Custom script '{js_filename}' not found in "
              f"'{script_dir}'. Output HTML might lack functionality.")

    # --- Initializations before main processing block ---
    all_page_data = []
    num_pages = 0
    svg_success = False

    # --- Main Processing Block ---
    try:
        # --- Step 1: Analyze PDF and Process Media ---
        print("\n--- Step 1: Analyzing PDF and Processing Media ---")
        with PdfAnalyzer(pdf_input_path) as pdf_analyzer:
            num_pages = pdf_analyzer.get_num_pages()
            if num_pages <= 0:
                raise ValueError("PDF contains no pages or could not be read.")
            print(f"Detected {num_pages} total PDF pages.")
            page_dimensions_map = pdf_analyzer.get_all_page_dimensions()

            # Initialize MediaProcessor with all options
            media_processor = MediaProcessor(
                config_obj=config,
                media_output_dir=media_dir_abs,
                ffmpeg_path=dependencies['ffmpeg'],
                scaling_factor=scaling_factor_arg,
                use_vaapi=use_vaapi_arg, # Pass potentially adjusted flag
                codec_choice=codec_choice_arg,
                ffprobe_path=dependencies['ffprobe']
            )

            # Process each page
            for page_num in range(num_pages):
                print(f"\n--- Processing Page {page_num + 1}/{num_pages} ---")
                page_has_processed_video = False
                page_dims = page_dimensions_map.get(
                    page_num, config.FALLBACK_PAGE_DIMENSIONS
                )
                # Validate dimensions again before use
                if (not page_dims or not isinstance(page_dims, dict) or
                        page_dims.get('width_pt', 0) <= 0):
                    print(f"  WARN: Invalid/missing dimensions for page "
                          f"{page_num+1}. Using fallback.")
                    page_dims = config.FALLBACK_PAGE_DIMENSIONS

                media_annotations = pdf_analyzer.find_media_annotations(page_num)

                if not media_annotations:
                    print("  No media annotations found on this page.")
                else:
                    print(f"  Found {len(media_annotations)} media annotation(s).")
                    for annot_index, annot_info in enumerate(media_annotations):
                        print(f"    Processing media annotation {annot_index+1}...")
                        # Check for required annotation data
                        if annot_info.get('stream_ref') and annot_info.get('rect'):
                            processed_media_info = media_processor.process_annotation(
                                page_num, annot_index, annot_info['stream_ref'],
                                annot_info['rect'],
                                annot_info.get('content_type',
                                               'application/octet-stream')
                            )
                            if processed_media_info:
                                processed_media_info['pageDimensions'] = page_dims
                                processed_media_info['hasVideo'] = True
                                all_page_data.append(processed_media_info)
                                page_has_processed_video = True
                                print(f"    +++ Media processed successfully -> "
                                      f"{processed_media_info.get('outputPath')} "
                                      f"(Type: {processed_media_info.get('contentTypeDetected')})")
                            else:
                                print(f"    --- Failed to process media annotation "
                                      f"{annot_index+1}.")
                        else:
                            print(f"    WARN: Skipping annotation {annot_index+1} "
                                  "(missing stream or rect).")

                # Add a placeholder if no media was processed for this page
                if not page_has_processed_video:
                    print(f"  Adding placeholder for page {page_num + 1}.")
                    all_page_data.append({
                        "pageIndex": page_num,
                        "pageDimensions": page_dims,
                        "hasVideo": False
                    })

        print("\n--- Finished Step 1: PDF Analysis and Media Processing ---")
        # Sort final data by page index for consistency
        all_page_data.sort(key=lambda item: item.get('pageIndex', -1))

        # Save JSON metadata (useful for debugging)
        try:
            with open(json_output_abs, 'w', encoding='utf-8') as json_file:
                json.dump(all_page_data, json_file, indent=2, ensure_ascii=False)
            print(f"Media metadata saved to: '{json_output_abs}'")
        except Exception as json_error:
            print(f"WARN: Failed to save JSON metadata: {json_error}")

        # --- Step 2: Convert PDF to SVG ---
        print("\n--- Step 2: Converting PDF to SVG ---")
        svg_converter = None
        if svg_method_to_use: # Only proceed if a valid method was determined
            try:
                print(f"Initializing SVG converter using {svg_method_to_use}...")
                if svg_method_to_use == 'pymupdf':
                    svg_converter = SvgConverter(
                        config_obj=config,
                        svg_output_dir=svg_dir_abs,
                        method='pymupdf'
                    )
                elif svg_method_to_use == 'pdf2svg':
                    svg_converter = SvgConverter(
                        config_obj=config,
                        svg_output_dir=svg_dir_abs,
                        method='pdf2svg',
                        pdf2svg_path=dependencies['pdf2svg']
                    )

                # Execute conversion if converter was successfully initialized
                if svg_converter:
                    print(f"Starting SVG conversion via {svg_method_to_use}...")
                    svg_success = svg_converter.convert_all(
                        pdf_path=pdf_input_path,
                        num_pages_expected=num_pages
                    )
                    if not svg_success:
                        print(f"WARN: SVG conversion via '{svg_method_to_use}' "
                              "failed or was incomplete.")
                # else: Should not happen if logic is correct

            except (ImportError, ValueError, NotImplementedError) as init_error:
                print(f"ERROR initializing SVG converter ({svg_method_to_use}): "
                      f"{init_error}")
                svg_success = False # Ensure failure state
            except Exception as runtime_error:
                print(f"ERROR during SVG conversion ({svg_method_to_use}): "
                      f"{runtime_error}")
                traceback.print_exc(limit=1)
                svg_success = False # Ensure failure state
        else:
            print("SVG conversion skipped (no valid method available).")

        # --- Step 3: Generate HTML File ---
        print("\n--- Step 3: Generating Swiper.js HTML File ---")
        # Define relative paths for use within the generated HTML
        svg_dir_rel_for_html = config.SVG_OUTPUT_DIR_NAME
        media_dir_rel_for_html = config.MEDIA_OUTPUT_DIR_NAME
        html_builder = HtmlBuilder(config)
        html_success = html_builder.generate(
            all_page_data=all_page_data,
            num_total_pages=num_pages,
            output_html_path=html_output_abs,
            svg_dir_rel=svg_dir_rel_for_html,
            media_dir_rel=media_dir_rel_for_html
        )
        if not html_success:
            # Log error but potentially continue to show summary
            print("ERROR: Failed to generate the HTML file.")

    # --- Global Error Handling ---
    except Exception as error:
        print("\n!!! FATAL ERROR IN ORCHESTRATOR !!!")
        print(f"{type(error).__name__}: {error}")
        traceback.print_exc()
        sys.exit(1) # Exit with a non-zero code indicating failure

    # --- Final Summary ---
    print("\n--- Processing Finished ---")
    print(f"Presentation generated in directory: {output_base_dir}")
    print(f"  Main HTML file: {html_output_abs}")

    # Check existence of generated assets for summary
    media_files_exist = os.path.exists(media_dir_abs) and any(
        f.is_file() for f in os.scandir(media_dir_abs)
    )
    svg_files_exist = os.path.exists(svg_dir_abs) and any(
        f.is_file() for f in os.scandir(svg_dir_abs)
    )
    libs_copied = os.path.exists(
        os.path.join(output_base_dir, config.TARGET_LIBS_DIR_NAME, 'swiper')
    )
    custom_js_copied = os.path.exists(presentation_js_output_path)

    # Report status of generated assets
    if media_files_exist:
        print(f"  Media files present in: {media_dir_abs}")
    else:
        print(f"  No media files were extracted/processed in {media_dir_abs}")

    if svg_success and svg_files_exist:
        print(f"  SVG backgrounds (via {svg_method_to_use}) present in: {svg_dir_abs}")
    elif svg_method_to_use and not svg_success:
        print(f"  WARN: SVG generation failed (method tried: {svg_method_to_use}).")
    elif not svg_method_to_use:
        print("  SVG generation was not performed.")
    else: # Should not happen, indicates logic error
        print(f"  WARN: Inconsistent SVG status (success={svg_success}, "
              f"method={svg_method_to_use}).")

    if libs_copied:
        print(f"  Swiper libraries copied to: "
              f"{os.path.join(output_base_dir, config.TARGET_LIBS_DIR_NAME)}")
    else:
        print("  WARN: Swiper libraries were not copied.")

    if custom_js_copied:
        print(f"  Custom script copied: {presentation_js_output_path}")
    else:
        print("  WARN: Custom script was not copied.")

    if os.path.exists(json_output_abs):
        print(f"  Metadata JSON (for debugging): {json_output_abs}")

    # Display relative path if possible
    try:
        output_display = os.path.relpath(output_base_dir)
    except ValueError:
        # Fallback to absolute path if on different drives (Windows)
        output_display = output_base_dir

    print(f"\n>>> You can now copy the entire '{output_display}' directory.")
    print(f">>> Then open the '{config.OUTPUT_HTML_FILE_NAME}' file "
          "(inside that directory) in your web browser. <<<")

    # Summary of options used
    print("\n    Options Used:")
    print(f"      - Input PDF: {pdf_input_path}")
    print(f"      - SVG Method: {svg_method_to_use if svg_method_to_use else 'None'}")
    print(f"      - Target Video Codec: {codec_choice_arg}")
    print(f"      - Video Scaling: {str(scaling_factor_arg)+'%' if scaling_factor_arg else 'No'}")
    # Use original args.vaapi for final message as use_vaapi_arg might have been changed
    print(f"      - VAAPI: {'Requested (enabled if possible)' if args.vaapi else 'Not Requested'}")

    # Keyboard controls reminder
    print("\n    Keyboard Controls:")
    print("      - Arrows/PgUp/PgDn/Space: Navigate slides")
    print("      - Home/End: Go to first/last slide")
    print("      - F: Toggle fullscreen")
    print("      - M: Toggle thumbnail menu")
    print("      - Esc: Close thumbnail menu")

    print("\n***** ORCHESTRATOR FINISHED *****")
    sys.exit(0) # Exit with success code


if __name__ == "__main__":
    main()
