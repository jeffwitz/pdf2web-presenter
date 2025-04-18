# -*- coding: utf-8 -*-
"""
pdf_processor.py
Handles PDF analysis (dimensions, media annotations).
"""

import traceback
import os  # For example usage

import pikepdf

import config  # For fallback dimensions


class PdfAnalyzer:
    """Analyzes a PDF file to extract page dimensions and media annotations."""

    def __init__(self, pdf_path):
        """
        Initializes the PdfAnalyzer.

        Args:
            pdf_path (str): The path to the input PDF file.
        """
        self.pdf_path = pdf_path
        self.pdf = None
        self.num_pages = 0
        self._open_pdf()

    def _open_pdf(self):
        """Opens the PDF file."""
        try:
            self.pdf = pikepdf.Pdf.open(self.pdf_path)
            self.num_pages = len(self.pdf.pages)
            print(f"PDF '{self.pdf_path}' opened, {self.num_pages} pages.")
        except pikepdf.PdfError as e_pike:
            print(f"Pikepdf ERROR opening '{self.pdf_path}': {e_pike}")
            raise  # Re-raise to indicate failure
        except Exception as e:
            print(f"Unknown ERROR opening '{self.pdf_path}': {e}")
            traceback.print_exc()
            raise  # Re-raise to indicate failure

    def get_num_pages(self):
        """Returns the number of pages in the PDF."""
        return self.num_pages

    def get_page_dimensions(self, page_num):
        """
        Calculates the dimensions (in points) of a given page (0-based index).

        Args:
            page_num (int): The 0-based index of the page.

        Returns:
            dict or None: A dictionary {'width_pt': float, 'height_pt': float}
                          or None if dimensions cannot be determined.
        """
        if not self.pdf or not (0 <= page_num < self.num_pages):
            return None

        page = self.pdf.pages[page_num]
        page_dimensions = None
        try:
            # Attempt to retrieve CropBox, otherwise MediaBox
            page_box_array = page.get('/CropBox', page.get('/MediaBox'))
            if page_box_array:
                try:
                    # Convert coordinates to float
                    coords = [float(coord) for coord in page_box_array]
                    if len(coords) == 4:
                        llx, lly, urx, ury = coords
                        page_width_pt = urx - llx
                        page_height_pt = ury - lly

                        # Consider page rotation
                        rotation = int(page.get('/Rotate', 0))
                        if rotation in [90, 270]:
                            # Swap width and height for rotated pages
                            page_width_pt, page_height_pt = page_height_pt, page_width_pt

                        if page_width_pt > 0 and page_height_pt > 0:
                            page_dimensions = {
                                "width_pt": page_width_pt,
                                "height_pt": page_height_pt
                            }
                        else:
                            print(
                                f"WARN Page {page_num+1}: Calculated dimensions "
                                f"invalid (<=0) {page_width_pt}x{page_height_pt}pt."
                            )
                    else:
                        print(
                            f"WARN Page {page_num+1}: Invalid Box format (not 4 "
                            f"coordinates): {page_box_array}"
                        )
                except (ValueError, TypeError) as e_coord:
                    print(
                        f"WARN Page {page_num+1} dims: Invalid coordinates "
                        f"in Box {page_box_array} - {e_coord}"
                    )
            else:
                print(f"WARN Page {page_num+1}: Missing /CropBox or /MediaBox.")
        except Exception as e_page_size:
            print(f"WARN Page {page_num+1} dims (Read Error): {e_page_size}")
            traceback.print_exc(limit=1) # Print limited traceback for context

        return page_dimensions

    def get_all_page_dimensions(self):
        """
        Returns a dictionary of dimensions for all pages, applying fallbacks.

        Returns:
            dict: A dictionary where keys are 0-based page indices and values
                  are dimension dictionaries {'width_pt': float, 'height_pt': float}.
                  Guaranteed to have an entry for every page.
        """
        all_dims = {}
        default_dims = None
        for i in range(self.num_pages):
            dims = self.get_page_dimensions(i)
            all_dims[i] = dims
            # Use the first valid page as a potential reference
            if default_dims is None and dims:
                default_dims = dims

        # If no page provided valid dimensions, use the fallback from config
        if default_dims is None:
            default_dims = config.FALLBACK_PAGE_DIMENSIONS
            print(
                f"CRITICAL ERROR: PDF dimensions undetermined. Using default: "
                f"{default_dims}"
            )
        else:
            print(f"INFO: Reference dimensions for fallback: {default_dims}")

        # Apply the determined default/fallback to pages without dimensions
        for i in range(self.num_pages):
            if all_dims[i] is None:
                print(f"INFO: Page {i+1} using default/fallback dimensions.")
                all_dims[i] = default_dims

        return all_dims

    def find_media_annotations(self, page_num):
        """
        Finds media annotations on a specific page and returns their basic info.

        Args:
            page_num (int): The 0-based index of the page.

        Returns:
            list: A list of dictionaries, each representing a found media
                  annotation with keys like 'pageIndex', 'annotIndex',
                  'subtype', 'rect', 'stream_ref', 'content_type'.
                  Returns an empty list if no relevant annotations are found.
        """
        if not self.pdf or not (0 <= page_num < self.num_pages):
            return []

        page = self.pdf.pages[page_num]
        media_annotations_info = []

        if not page.get('/Annots'):
            return []  # No annotations on this page

        try:
            for annot_index, annot in enumerate(page.Annots):
                annot_info = {'pageIndex': page_num, 'annotIndex': annot_index}
                try:
                    annot_type = annot.get('/Subtype')
                    # Check for media-related annotation types
                    if annot_type in [
                        pikepdf.Name.Screen,
                        pikepdf.Name.Movie,
                        pikepdf.Name.RichMedia
                    ]:
                        annot_info['subtype'] = str(annot_type).lstrip('/')
                        rect = annot.get('/Rect')
                        if not rect:
                            print(
                                f"    WARN Annot {annot_index} "
                                f"(Page {page_num+1}): Type {annot_type} "
                                f"but missing /Rect."
                            )
                            continue  # Skip useless annotation

                        # Validate and store Rect
                        try:
                            coords = [float(c) for c in rect]
                            # Basic validation: 4 coords, non-zero width/height
                            if (len(coords) == 4 and
                                    coords[0] < coords[2] and
                                    coords[1] < coords[3]):
                                annot_info['rect'] = {
                                    "llx": coords[0], "lly": coords[1],
                                    "urx": coords[2], "ury": coords[3]
                                }
                            else:
                                print(
                                    f"    ERR Rect (Page {page_num+1}, "
                                    f"Annot {annot_index}): Invalid "
                                    f"coords {rect}"
                                )
                                continue  # Skip useless annotation
                        except (ValueError, TypeError) as e_rect:
                            print(
                                f"    ERR Rect (Page {page_num+1}, "
                                f"Annot {annot_index}): Conversion "
                                f"{rect} - {e_rect}"
                            )
                            continue  # Skip useless annotation

                        # Search for the associated media stream
                        stream_ref = None
                        # Default content type hint
                        content_type_pdf = "application/octet-stream"
                        action = annot.get('/A')
                        rendition = None
                        movie_dict = None

                        # Look for Rendition or Movie actions/dictionaries
                        if action:
                            if action.get('/S') == pikepdf.Name.Rendition:
                                rendition = action.get('/R')
                            elif action.get('/S') == pikepdf.Name.Movie:
                                movie_dict = action.get('/Movie')
                        # Fallback checks if not in Action dictionary
                        if not rendition and annot.get('/R'):
                            rendition = annot.get('/R')  # Common in Screen annots
                        if not movie_dict and annot.get('/Movie'):
                            movie_dict = annot.get('/Movie')
                        # Simplification for RichMedia /MA, assuming it contains
                        # a valid reference if other methods fail.
                        # More complex logic could be added here if needed.

                        # Process Rendition if found
                        if rendition:
                            # Check for Media Rendition type
                            if rendition.get('/S') == pikepdf.Name.MR:
                                media_clip = rendition.get('/C')
                                # Check for Media Clip Data
                                if media_clip and media_clip.get('/S') == pikepdf.Name.MCD:
                                    if media_clip.get('/CT'):
                                        content_type_pdf = str(media_clip.CT)
                                    data_spec = media_clip.get('/D')
                                    # Check for embedded file specification
                                    if (data_spec and
                                            data_spec.get('/Type') == pikepdf.Name.Filespec):
                                        embedded_file = data_spec.get('/EF')
                                        file_stream_ref = embedded_file.get('/F') if embedded_file else None
                                        if (file_stream_ref and
                                                isinstance(file_stream_ref, pikepdf.Stream)):
                                            stream_ref = file_stream_ref
                        # Process Movie dictionary if found (and no rendition stream)
                        elif movie_dict:
                            data_spec = movie_dict.get('/F')
                            if (data_spec and
                                    data_spec.get('/Type') == pikepdf.Name.Filespec):
                                embedded_file = data_spec.get('/EF')
                                file_stream_ref = embedded_file.get('/F') if embedded_file else None
                                # Check if it's an embedded stream
                                if (file_stream_ref and
                                        isinstance(file_stream_ref, pikepdf.Stream)):
                                    stream_ref = file_stream_ref
                                    # Try to get description as content type hint
                                    if data_spec.get('/Desc'):
                                        content_type_pdf = str(data_spec.Desc)
                                # Check if it references an external file (unsupported)
                                elif (data_spec.get('/F') and
                                      isinstance(data_spec.get('/F'), pikepdf.String)):
                                    print(
                                        f"    WARN (Page {page_num+1}, "
                                        f"Annot {annot_index}): Movie "
                                        f"references external path "
                                        f"('{data_spec.F}'), not supported "
                                        f"for extraction."
                                    )

                        # Store info if a stream was successfully found
                        if stream_ref:
                            annot_info['stream_ref'] = stream_ref
                            annot_info['content_type'] = content_type_pdf
                            media_annotations_info.append(annot_info)
                        else:
                            # Log if annotation looks like media but no stream found
                            print(
                                f"    WARN: (Page {page_num+1}, "
                                f"Annot {annot_index}) Type {annot_type} found "
                                f"but no associated/embedded data stream."
                            )

                except Exception as e_annot_item:
                    # Catch errors processing a single annotation
                    print(
                        f"  !!! ERR processing annotation {annot_index} "
                        f"(Page {page_num + 1}): {e_annot_item}"
                    )
                    traceback.print_exc(limit=1)
        except Exception as e_page_process:
            # Catch errors processing the annotations array for the page
            print(
                f"!!! ERR processing annotations page {page_num + 1}: "
                f"{e_page_process}"
            )
            traceback.print_exc(limit=1)

        return media_annotations_info

    def close(self):
        """Closes the PDF file if it is open."""
        if self.pdf:
            try:
                self.pdf.close()
                self.pdf = None
                print(f"PDF '{self.pdf_path}' closed.")
            except Exception as e_close:
                print(f"WARN: Error during PDF close: {e_close}")

    def __enter__(self):
        """Enter the runtime context related to this object."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the runtime context related to this object."""
        self.close()


# Example usage (if executed directly)
if __name__ == '__main__':
    # Use the default PDF specified in config for testing
    test_pdf = config.DEFAULT_PDF_FILE
    if not os.path.exists(test_pdf):
        print(f"Test file '{test_pdf}' not found in the current directory.")
    else:
        # Usage with a context manager ensures the file is closed
        try:
            with PdfAnalyzer(test_pdf) as analyzer:
                dimensions_map = analyzer.get_all_page_dimensions()
                print("\nDimensions of all pages:")
                # Nicer printout for dimensions map
                for page_idx, dims in dimensions_map.items():
                     print(f"  Page {page_idx+1}: {dims}")

                for i in range(analyzer.get_num_pages()):
                    print(f"\nMedia Annotations Page {i+1}:")
                    annotations = analyzer.find_media_annotations(i)
                    if not annotations:
                        print("  None")
                    else:
                        for annot_data in annotations:
                            stream_found = 'Yes' if annot_data.get('stream_ref') else 'No'
                            print(
                                f"  - Index: {annot_data['annotIndex']}, "
                                f"Type: {annot_data['subtype']}, "
                                f"Rect: {annot_data.get('rect')}, "
                                f"Stream: {stream_found}, "
                                f"PDF Type: {annot_data.get('content_type')}"
                            )
        except Exception as e_main:
            print(f"\nError in example usage: {e_main}")
            traceback.print_exc(limit=2)
