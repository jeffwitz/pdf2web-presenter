# -*- coding: utf-8 -*-
"""
html_generator.py
Generates the final HTML presentation file using Jinja2 templates.
"""

import html
import os
import traceback

import jinja2

# Local import
import config


class HtmlBuilder:
    """Builds the Swiper.js HTML presentation file."""

    def __init__(self, config_obj):
        """
        Initializes the HtmlBuilder.

        Args:
            config_obj: The configuration object (from config.py).
        """
        self.config = config_obj
        self.template_dir = self.config.HTML_TEMPLATE_DIR
        self.template_name = self.config.HTML_TEMPLATE_NAME
        self.jinja_env = None
        try:
            # Configure the Jinja2 environment
            self.jinja_env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(self.template_dir),
                autoescape=jinja2.select_autoescape(['html', 'xml']),
                # Trim blocks to clean up whitespace around Jinja blocks
                trim_blocks=True,
                lstrip_blocks=True
            )
            # Add 'round' as a global filter if needed (for data attributes)
            self.jinja_env.filters['round'] = round
            print(f"Jinja2 environment loaded from '{self.template_dir}'")
        except Exception as jinja_init_error:
            print(
                f"ERROR: Failed to initialize Jinja2 (check path "
                f"'{self.template_dir}'): {jinja_init_error}"
            )
            # self.jinja_env remains None

    def _prepare_context(self, all_page_data, num_total_pages, svg_dir_rel,
                         media_dir_rel, output_html_path):
        """Prepares the context dictionary for the Jinja2 template."""
        context = {
            'html_title': "Swiper.js Presentation",
            'slides': [],
            'num_total_pages': num_total_pages,
            'svg_dir': svg_dir_rel,
            'media_dir': media_dir_rel,
            'swiper_css_path': self.config.SWIPER_CSS_PATH,
            'swiper_js_path': self.config.SWIPER_JS_PATH,
            'presentation_js_path': self.config.PRESENTATION_JS_PATH,
            'fallback_slide_width': self.config.FALLBACK_PAGE_DIMENSIONS['width_pt'],
            'fallback_slide_height': self.config.FALLBACK_PAGE_DIMENSIONS['height_pt'],
            # --- NEW: Default aspect ratio as a safe fallback ---
            'ref_aspect_ratio': 16 / 9
            # ---------------------------------------------------
        }

        # Find dimensions of the first valid page to use as CSS reference
        first_valid_dims = None
        for item in all_page_data:
            page_dims = item.get('pageDimensions')
            if (page_dims and isinstance(page_dims, dict) and
                    page_dims.get('width_pt', 0) > 0 and
                    page_dims.get('height_pt', 0) > 0):
                first_valid_dims = page_dims
                break  # Found the first valid one

        # If no valid dimension found, use fallback from config
        if not first_valid_dims:
            print("WARN: No valid page dimensions found in metadata. "
                  "Using fallback dimensions for reference.")
            first_valid_dims = self.config.FALLBACK_PAGE_DIMENSIONS

        ref_width = first_valid_dims.get(
            'width_pt', self.config.FALLBACK_PAGE_DIMENSIONS['width_pt']
        )
        ref_height = first_valid_dims.get(
            'height_pt', self.config.FALLBACK_PAGE_DIMENSIONS['height_pt']
        )

        # Ensure they are valid numbers before calculation
        ref_width_num = ref_width if (
            isinstance(ref_width, (int, float)) and ref_width > 0
        ) else self.config.FALLBACK_PAGE_DIMENSIONS['width_pt']

        ref_height_num = ref_height if (
            isinstance(ref_height, (int, float)) and ref_height > 0
        ) else self.config.FALLBACK_PAGE_DIMENSIONS['height_pt']

        # --- MODIFIED: Calculate and store aspect ratio ---
        # Check for division by zero
        if ref_height_num > 0:
            calculated_ratio = ref_width_num / ref_height_num
            context['ref_aspect_ratio'] = calculated_ratio
        else:
            # Use the default ratio already set if height is invalid
            print(
                f"WARN: Reference height ({ref_height_num}) is invalid, "
                f"using default aspect ratio {context['ref_aspect_ratio']}."
            )

        # Store rounded dimensions (less critical now for layout)
        context['ref_slide_width'] = round(ref_width_num)
        context['ref_slide_height'] = round(ref_height_num)
        # -------------------------------------------------

        print(
            f"Reference size for CSS/JS: "
            f"{context['ref_slide_width']}x{context['ref_slide_height']}px "
            f"(Aspect Ratio: {context['ref_aspect_ratio']:.4f})"
        )

        # --- Organize data per slide for the template ---
        # Create an entry for each page, even if it has no extracted media
        slides_dict = {
            i: {'pageIndex': i, 'videos': [], 'dimensions': None, 'svg_exists': False}
            for i in range(num_total_pages)
        }
        # Get the directory where the HTML will be written
        html_output_dir = os.path.dirname(output_html_path) or '.'

        for item in all_page_data:
            idx = item.get('pageIndex')
            if idx is not None and 0 <= idx < num_total_pages:
                page_entry = slides_dict[idx]

                # Store page dimensions (use the first valid one found)
                if not page_entry['dimensions'] and item.get('pageDimensions'):
                    dims = item['pageDimensions']
                    # Validate dimensions before storing
                    if (isinstance(dims, dict) and
                            dims.get('width_pt', 0) > 0 and
                            dims.get('height_pt', 0) > 0):
                        page_entry['dimensions'] = dims
                    else:
                        print(
                            f"WARN Slide {idx + 1}: Received invalid dimensions: "
                            f"{dims}. Fallback will be used in template."
                        )

                # If this item represents a successfully processed video
                if (item.get('hasVideo') and item.get('outputPath') and
                        item.get('pdfRect')):
                    # 'outputPath' should already be the correct relative path
                    # (e.g., 'videos/file.mp4')
                    video_data_for_template = {
                        'videoPath': item['outputPath'],  # Path used in src=""
                        'videoMime': item.get('contentTypeDetected', 'video/unknown'),
                        'pdfRect': item['pdfRect']  # Contains llx, lly, urx, ury
                    }
                    page_entry['videos'].append(video_data_for_template)

        # --- Check SVG existence and ensure dimensions for all slides ---
        for i in range(num_total_pages):
            page_entry = slides_dict[i]
            svg_file_name = f"page_{i + 1}{self.config.SVG_OUTPUT_EXTENSION}"

            # Check existence using absolute path relative to HTML output dir
            svg_abs_path = os.path.abspath(
                os.path.join(html_output_dir, svg_dir_rel, svg_file_name)
            )
            page_entry['svg_exists'] = os.path.exists(svg_abs_path)

            # Relative path for the src attribute in HTML
            # Ensure forward slashes for web compatibility
            page_entry['svg_path'] = f"{svg_dir_rel}/{svg_file_name}".replace("\\", "/")

            # Assign fallback dimensions if none were found for this page
            if not page_entry['dimensions']:
                page_entry['dimensions'] = self.config.FALLBACK_PAGE_DIMENSIONS
                print(
                    f"INFO Slide {i + 1}: Using fallback dimensions "
                    f"(not found in metadata)."
                )
            # Final check: ensure dimensions are a dict (should be by now)
            elif not isinstance(page_entry['dimensions'], dict):
                print(
                    f"ERROR Slide {i + 1}: Incorrect dimensions format "
                    f"({type(page_entry['dimensions'])}). Using fallback."
                )
                page_entry['dimensions'] = self.config.FALLBACK_PAGE_DIMENSIONS

        # Add the processed list of slide data to the context
        context['slides'] = list(slides_dict.values())
        # --- DEBUGGING ---
        print(f"DEBUG: Number of slides being passed to template: {len(context['slides'])}")
        # --- END DEBUGGING ---
        return context

    def generate(self, all_page_data, num_total_pages, output_html_path,
                 svg_dir_rel, media_dir_rel):
        """
        Generates the HTML file from the provided data and template.

        Args:
            all_page_data (list): List of dictionaries, each containing data
                                  for a page or a media item on a page.
            num_total_pages (int): The total number of pages in the PDF.
            output_html_path (str): The absolute path where the HTML file
                                    should be saved.
            svg_dir_rel (str): The relative path to the SVG directory from the
                               HTML file's location (e.g., 'slides_svg').
            media_dir_rel (str): The relative path to the media directory from
                                 the HTML file's location (e.g., 'videos').

        Returns:
            bool: True if HTML generation was successful, False otherwise.
        """
        if not self.jinja_env:
            print(
                "ERROR: Jinja2 environment not initialized. "
                "HTML generation cancelled."
            )
            return False

        print(f"\nGenerating Swiper.js HTML to: {output_html_path}")
        print(
            f"  Using Template: {os.path.join(self.template_dir, self.template_name)}"
        )
        print(f"  Relative SVG path for HTML: {svg_dir_rel}/")
        print(f"  Relative Videos path for HTML: {media_dir_rel}/")

        # --- Prepare Context ---
        try:
            context = self._prepare_context(
                all_page_data, num_total_pages, svg_dir_rel, media_dir_rel,
                output_html_path
            )
        except Exception as context_error:
            print(f"ERROR: Failed to prepare context for HTML generation: {context_error}")
            traceback.print_exc()
            return False

        # --- Render and Write File ---
        try:
            template = self.jinja_env.get_template(self.template_name)
            html_content = template.render(context)

            # Ensure output directory exists
            output_dir = os.path.dirname(output_html_path) or '.'
            os.makedirs(output_dir, exist_ok=True)

            with open(output_html_path, "w", encoding="utf-8") as file_handle:
                file_handle.write(html_content)

            print(f"Successfully generated Swiper.js HTML file: {output_html_path}")
            return True

        except jinja2.exceptions.TemplateNotFound:
            print(
                f"ERROR: Jinja2 template '{self.template_name}' not found "
                f"in '{self.template_dir}'. Please check the path."
            )
            return False
        except jinja2.exceptions.TemplateError as template_error:
            print(f"ERROR: Jinja2 template error during rendering: {template_error}")
            traceback.print_exc(limit=2)
            return False
        except Exception as render_error:
            print(
                f"ERROR: Unexpected error during HTML rendering/writing: "
                f"{render_error}"
            )
            traceback.print_exc()
            return False
