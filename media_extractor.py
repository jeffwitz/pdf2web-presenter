# -*- coding: utf-8 -*-
"""
media_extractor.py

Handles media extraction and processing using a two-step strategy:
1. Optional HIGH-QUALITY Scaling (CPU) to an intermediate H.264 file.
2. Optional Final Transcoding (VAAPI attempt with CPU fallback) to target format.
Includes an intermediate H.264 transcoding step for sources incompatible
with VAAPI decoding, prioritizing quality preservation.
Applies specific, tested FFmpeg command structures and pixel formats,
and corrects handling of failed transcodes. Adheres to PEP 8.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import traceback

# Third-party imports
try:
    import magic
    MAGIC_IMPORTED_SUCCESSFULLY = True
except ImportError:
    MAGIC_IMPORTED_SUCCESSFULLY = False
    magic = None
except Exception as import_error:
    MAGIC_IMPORTED_SUCCESSFULLY = False
    magic = None
    print(f"WARN: Failed to import or initialize python-magic: {import_error}")
    print("      MIME type detection will rely solely on PDF metadata.")

# Local import
import config


class MediaProcessor:
    """
    Processes media using a multi-step approach:
    1. Optional pre-resizing for very large videos.
    2. Optional HIGH-QUALITY Scaling (CPU) to a specified percentage.
    3. Optional Final Transcoding (VAAPI attempt + CPU fallback).
    4. Includes intermediate H.264 step for VAAPI decode incompatibilities.
    """
    # Codecs known to be decodable by common VAAPI drivers.
    # MPEG-4 Part 2 ('mpeg4') is intentionally omitted as it often fails VAAPI init.
    VAAPI_DECODABLE_CODECS = [
        'h264', 'hevc', 'vp9', 'av1', 'mpeg2video', 'vc1'
    ]
    PREFERRED_FORMATS = config.PREFERRED_FORMATS

    def __init__(self, config_obj, media_output_dir, ffmpeg_path=None,
                 ffprobe_path=None, scaling_factor=None, use_vaapi=False,
                 codec_choice=None):
        """Initializes the media processor."""
        self.config = config_obj
        self.media_output_dir = media_output_dir
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path

        self.enable_transcoding = (
            self.config.ENABLE_TRANSCODING and bool(self.ffmpeg_path)
        )
        if self.config.ENABLE_TRANSCODING and not self.ffmpeg_path:
            print("WARN: Transcoding enabled but ffmpeg not found. Disabling.")

        self.user_codec_choice = codec_choice
        self._validate_and_set_scaling(scaling_factor)
        self._determine_target_format(codec_choice)
        self._validate_vaapi_request(use_vaapi)
        self._initialize_magic()

    def _validate_and_set_scaling(self, scaling_factor_input):
        """Validates and stores the requested scaling factor."""
        self.scaling_factor = None
        if scaling_factor_input is not None:
            try:
                factor = int(scaling_factor_input)
                if 1 <= factor <= 100:
                    self.scaling_factor = factor
                    print(f"INFO: Video scaling requested: {self.scaling_factor}%.")
                else:
                    print(
                        f"WARN: Scaling factor ({scaling_factor_input}) "
                        f"out of range (1-100). Ignored."
                    )
            except (ValueError, TypeError):
                print(
                    f"WARN: Invalid scaling factor ({scaling_factor_input}). "
                    f"Ignored."
                )

    def _determine_target_format(self, codec_choice_input):
        """Determines the effective target format based on input and defaults."""
        if (codec_choice_input is not None and
                codec_choice_input in self.config.ALLOWED_VIDEO_CODECS):
            self.target_codec = codec_choice_input
            print(f"INFO: User requested target video codec: {self.target_codec}")
        else:
            self.target_codec = self.config.DEFAULT_VIDEO_CODEC
            if codec_choice_input is not None:
                print(
                    f"WARN: Invalid codec '{codec_choice_input}'. "
                    f"Using default: {self.target_codec}"
                )
            else:
                print(f"INFO: Using default target video codec: {self.target_codec}")

        format_info = self.config.CODEC_FORMAT_MAP.get(self.target_codec)
        if not format_info:
            print(
                f"ERROR: Config error! Codec '{self.target_codec}' "
                f"not in CODEC_FORMAT_MAP."
            )
            print("       Falling back to H.264/MP4.")
            self.target_codec = 'h264'
            format_info = self.config.CODEC_FORMAT_MAP['h264']

        self.target_extension = format_info.get('ext', '.mp4')
        self.target_mime_type = format_info.get('mime', 'video/mp4')
        self.target_container_opts = format_info.get('container_opts', [])

        print(
            f"INFO: Effective target format details: "
            f"Codec={self.target_codec}, Extension={self.target_extension}, "
            f"MIME={self.target_mime_type}"
        )

    def _validate_vaapi_request(self, use_vaapi_input):
        """Checks prerequisites for attempting VAAPI."""
        self.use_vaapi = False
        if not use_vaapi_input:
            return
        if not self.ffmpeg_path:
            print("WARN: VAAPI requested, but ffmpeg missing.")
            return
        if not sys.platform.startswith('linux'):
            print("WARN: VAAPI requested, but not Linux.")
            return
        if not any(codec in self.config.FFMPEG_CODEC_OPTIONS_VAAPI
                   for codec in self.config.ALLOWED_VIDEO_CODECS):
            print("WARN: VAAPI requested, but no VAAPI encoders configured.")
            return
        if not self.ffprobe_path:
            print("WARN: VAAPI requested, but ffprobe missing "
                  "(decode capability check limited).")
        try:
            has_render_node = any(
                d.startswith('renderD') for d in os.listdir('/dev/dri/')
            )
            if not has_render_node and not self.config.VAAPI_DEVICE_PATH:
                print("WARN: No VAAPI render devices found in /dev/dri/ "
                      "and no VAAPI_DEVICE_PATH set in config.")
        except FileNotFoundError:
            print("INFO: /dev/dri directory not found.")
        except Exception as e:
            print(f"WARN: Error checking /dev/dri: {e}")

        print("INFO: VAAPI acceleration enabled. Will attempt usage.")
        self.use_vaapi = True

    def _initialize_magic(self):
        """Initializes python-magic if available."""
        self.magic_available = False
        self.mime_checker = None
        if MAGIC_IMPORTED_SUCCESSFULLY and magic:
            try:
                self.mime_checker = magic.Magic(mime=True)
                self.magic_available = True
                print("INFO: python-magic initialized.")
            except magic.MagicException as e:
                print(f"ERROR: python-magic init failed: {e}. Check libmagic.")
                self.magic_available = False
            except Exception as e:
                print(f"WARN: Unexpected error initializing python-magic: {e}")
                self.magic_available = False
        else:
             print("INFO: python-magic not available or import failed.")

    def _get_file_extension_from_mime(self, mime_type):
        """Determines file extension from MIME type."""
        if not isinstance(mime_type, str) or '/' not in mime_type:
            return ".bin"

        main_type, sub_type_full = mime_type.split('/', 1)
        sub_type = sub_type_full.split(';')[0].lower().strip()

        for details in self.config.CODEC_FORMAT_MAP.values():
            if details.get('mime') == mime_type:
                return details.get('ext', '.bin')

        common_mime_map = {
            'video/mp4': '.mp4', 'video/quicktime': '.mov', 'video/webm': '.webm',
            'video/x-matroska': '.mkv', 'video/x-msvideo': '.avi',
            'video/mpeg': '.mpg', 'audio/mpeg': '.mp3', 'audio/aac': '.aac',
            'audio/ogg': '.ogg', 'audio/wav': '.wav', 'audio/flac': '.flac',
            'image/jpeg': '.jpg', 'image/png': '.png', 'image/gif': '.gif',
            'image/webp': '.webp', 'image/svg+xml': '.svg',
            'application/octet-stream': '.bin',
        }
        if mime_type in common_mime_map:
            return common_mime_map[mime_type]

        safe_subtype = ''.join(
            c for c in sub_type if c.isalnum() or c in ['-', '+']
        )
        if safe_subtype:
            return f".{safe_subtype}"

        return ".bin"

    def _get_video_info(self, input_path):
        """Gets video width, height, codec using ffprobe."""
        if not self.ffprobe_path or not os.path.exists(input_path):
            return None
        try:
            command = [
                self.ffprobe_path, '-v', 'error', '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height,codec_name',
                '-of', 'json', input_path
            ]
            result = subprocess.run(
                command, capture_output=True, text=True, check=True,
                encoding='utf-8', errors='replace'
            )
            data = json.loads(result.stdout)
            if not data.get('streams'):
                return None
            stream = data['streams'][0]
            width = stream.get('width')
            height = stream.get('height')
            codec = stream.get('codec_name')
            if width and height and codec:
                info = {
                    'width': int(width),
                    'height': int(height),
                    'codec_name': str(codec)
                }
                print(
                    f"    Video info: {info['width']}x{info['height']}, "
                    f"Codec: {info['codec_name']}"
                )
                return info
            else:
                return None
        except (subprocess.CalledProcessError, json.JSONDecodeError) as probe_err:
            print(f"    WARN: ffprobe failed for {os.path.basename(input_path)}: {probe_err}")
            return None
        except Exception as e:
            print(f"    ERROR: Unexpected error getting video info: {e}")
            return None

    def _perform_pre_resize(self, input_path, video_info):
        """Performs fast CPU pre-resize if video exceeds MAX limits."""
        if not self.ffmpeg_path or not video_info:
            return False, input_path

        width = video_info['width']
        height = video_info['height']
        max_w = self.config.MAX_PRE_RESIZE_WIDTH
        max_h = self.config.MAX_PRE_RESIZE_HEIGHT

        if not max_w or not max_h or (width <= max_w and height <= max_h):
            return False, input_path # No pre-resize needed

        print(
            f"    INFO: Video dims ({width}x{height}) > limit ({max_w}x{max_h}). "
            f"Pre-resizing..."
        )
        temp_path = None
        success = False
        original_input_path = input_path # Keep track of the original path
        try:
            input_dir = os.path.dirname(input_path)
            input_base = os.path.splitext(os.path.basename(input_path))[0]
            temp_suffix = '.preresize.mp4'
            with tempfile.NamedTemporaryFile(
                    mode='wb', delete=False, dir=input_dir,
                    prefix=f"{input_base}_", suffix=temp_suffix) as temp_file:
                temp_path = temp_file.name

            scale_filter = (
                f"scale=w='min(iw,trunc({max_w}/2)*2)':"
                f"h='min(ih,trunc({max_h}/2)*2)':"
                f"force_original_aspect_ratio=decrease:flags=bicubic"
            )

            command = [self.ffmpeg_path, '-y', '-i', input_path]
            command.extend(['-vf', scale_filter])
            command.extend(self.config.FFMPEG_PRE_RESIZE_OPTIONS)
            command.append(temp_path)

            print(f"       CMD PRE-RESIZE: {' '.join(command)}")
            result = subprocess.run(
                command, capture_output=True, text=True, check=False,
                encoding='utf-8', errors='replace'
            )

            if (result.returncode == 0 and os.path.exists(temp_path)
                    and os.path.getsize(temp_path) > 0):
                print(f"       Pre-resize OK: {os.path.basename(temp_path)}")
                shutil.move(temp_path, input_path)
                print("       Original file overwritten by pre-resized version.")
                success = True
            else:
                print(f"    ERROR: Pre-resize failed (code: {result.returncode}).")
                print(f"      Stderr: ...{result.stderr[-500:]}")
                success = False
                input_path = original_input_path

        except Exception as e:
            print(f"    ERROR: Unexpected exception during pre-resize: {e}")
            success = False
            input_path = original_input_path
        finally:
            if not success and temp_path and os.path.exists(temp_path):
                print("       Cleaning failed temp pre-resize file.")
                try:
                    os.remove(temp_path)
                except OSError as del_err:
                    print(f"       WARN: Failed cleaning temp file: {del_err}")

        return success, input_path

    def _perform_intermediate_h264_encode(self, input_path, intermediate_h264_output_path):
        """
        Performs a fast, high-quality CPU transcode to an intermediate
        H.264/MP4 file. Designed for sources incompatible with VAAPI decoding,
        prioritizing quality preservation over size for this temporary file.
        """
        if not self.ffmpeg_path:
            print("    ERROR: Cannot perform intermediate encode - ffmpeg path not set.")
            return False

        print(
            f"    Creating intermediate H.264 (near-lossless) for VAAPI compatibility: "
            f"{os.path.basename(intermediate_h264_output_path)}"
        )

        intermediate_cmd = [
            self.ffmpeg_path, '-y',
            '-i', input_path,
            '-c:v', 'libx264',
            '-preset', 'ultrafast', # Fastest preset
            '-crf', '17',          # Near-lossless quality
            '-c:a', 'copy',        # Copy audio stream without re-encoding
            '-movflags', '+faststart', # Standard for MP4 web playback
            intermediate_h264_output_path
        ]

        print(f"      CMD INTERMEDIATE H264 (Near-Lossless): {' '.join(intermediate_cmd)}")
        try:
            result = subprocess.run(
                intermediate_cmd, capture_output=True, text=True, check=False,
                encoding='utf-8', errors='replace'
            )
            if (result.returncode == 0 and os.path.exists(intermediate_h264_output_path)
                    and os.path.getsize(intermediate_h264_output_path) > 0):
                print("      Intermediate H.264 step successful.")
                return True
            else:
                print(f"    ERROR: Intermediate H.264 step failed! (code: {result.returncode})")
                stderr_head = result.stderr[:500]
                stderr_tail = result.stderr[-500:]
                print(f"      Stderr (beginning): {stderr_head}...")
                print(f"      Stderr (end): ...{stderr_tail}")
                if os.path.exists(intermediate_h264_output_path):
                     try: os.remove(intermediate_h264_output_path)
                     except OSError: pass
                return False
        except Exception as e:
            print(f"    ERROR: Exception during intermediate H.264 step: {e}")
            traceback.print_exc(limit=1)
            if os.path.exists(intermediate_h264_output_path):
                 try: os.remove(intermediate_h264_output_path)
                 except OSError: pass
            return False

    # --- Main Processing Workflow ---

    def process_annotation(self, page_num, annot_index, stream_ref, pdf_rect,
                           content_type_pdf):
        """Main workflow using multi-step scaling/transcoding."""
        print(
            f"--- Processing Annotation: Page {page_num + 1}, "
            f"Index {annot_index + 1} ---"
        )

        # --- 1. Extraction ---
        # ... (Extraction code as before) ...
        try:
            stream_bytes = stream_ref.read_bytes()
            if not stream_bytes:
                print("    ERROR: Extracted stream is empty.")
                return None
        except Exception as e:
            print(f"    ERROR: Reading stream failed: {e}")
            return None
        stream_id_part = (f"{stream_ref.objgen[0]}_{stream_ref.objgen[1]}"
                          if hasattr(stream_ref, 'objgen')
                          else f'p{page_num+1}a{annot_index+1}s')
        base_filename_raw = (
            f"slide_{page_num+1}_annot_{annot_index+1}_{stream_id_part}"
        )
        safe_base = "".join(
            c if c.isalnum() or c in ['_', '-'] else '_'
            for c in base_filename_raw
        )
        temp_ext = ".tmp.bin"
        temp_fname = safe_base + temp_ext
        initial_absolute_temp_path = os.path.join(
            self.media_output_dir, temp_fname
        )
        try:
            os.makedirs(self.media_output_dir, exist_ok=True)
            with open(initial_absolute_temp_path, "wb") as f:
                f.write(stream_bytes)
            print(f"    Extracted to temporary file: {temp_fname}")
        except OSError as e:
            print(f"    ERROR: Saving extracted media failed: {e}")
            return None

        # --- 2. Pre-resize (>4K) and Identify ---
        current_path = initial_absolute_temp_path
        video_info = self._get_video_info(current_path)
        source_codec = video_info.get('codec_name') if video_info else None
        resized, current_path = self._perform_pre_resize(current_path, video_info)
        if resized:
            video_info = self._get_video_info(current_path)
            source_codec = video_info.get('codec_name') if video_info else None
        # ... (MIME detection as before) ...
        detected_mime = "application/octet-stream"
        if self.magic_available and self.mime_checker:
            try:
                magic_mime = self.mime_checker.from_file(current_path)
                if magic_mime and magic_mime != "application/octet-stream":
                    detected_mime = magic_mime
                    print(f"    MIME detected by magic: '{detected_mime}'")
                elif content_type_pdf and content_type_pdf != "application/octet-stream":
                    detected_mime = content_type_pdf
                    print(f"    Magic inconclusive, using MIME from PDF: '{content_type_pdf}'")
            except Exception as e:
                print(f"    WARN: Magic failed: {e}")
                if content_type_pdf and content_type_pdf != "application/octet-stream":
                    detected_mime = content_type_pdf
                    print(f"    Using MIME from PDF due to magic error: '{content_type_pdf}'")
        elif content_type_pdf and content_type_pdf != "application/octet-stream":
             detected_mime = content_type_pdf
             print(f"    Using MIME from PDF (magic unavailable): '{content_type_pdf}'")
        final_extension = self._get_file_extension_from_mime(detected_mime)
        final_filename_initial_guess = safe_base + final_extension
        final_path_initial_guess = os.path.join(
            self.media_output_dir, final_filename_initial_guess
        )
        if current_path != final_path_initial_guess:
            try:
                print(f"    Renaming '{os.path.basename(current_path)}' to '{final_filename_initial_guess}'")
                if os.path.exists(final_path_initial_guess):
                    print(f"    WARN: Target file '{final_filename_initial_guess}' exists, removing.")
                    os.remove(final_path_initial_guess)
                shutil.move(current_path, final_path_initial_guess)
                current_path = final_path_initial_guess
            except OSError as e:
                print(f"    ERROR: Rename failed: {e}")
                print(f"    WARN: Proceeding with current filename: {os.path.basename(current_path)}")
        if not video_info or resized:
            video_info = self._get_video_info(current_path)
            source_codec = video_info.get('codec_name') if video_info else None
        is_video = detected_mime.startswith("video/")
        if not is_video:
             print(f"    INFO: Content '{detected_mime}' not video. Processing complete.")
             if initial_absolute_temp_path != current_path and os.path.exists(initial_absolute_temp_path):
                  try: os.remove(initial_absolute_temp_path)
                  except OSError: pass
             return None

        # --- 3. Step 1 (Optional): Scaling ---
        # ... (Scaling logic as before, updating path_for_final_encode etc.) ...
        scaled_intermediate_path = None
        path_for_final_encode = current_path
        codec_for_final_encode = source_codec
        ext_for_final_encode = os.path.splitext(current_path)[1].lower()
        mime_for_final_encode = detected_mime
        needs_scaling = self.scaling_factor is not None and self.scaling_factor != 100
        if needs_scaling and is_video and self.enable_transcoding:
            print("--- Step 1: Scaling (High Quality Intermediate) ---")
            scaled_intermediate_suffix = ".scale_hq_inter.mp4"
            scaled_intermediate_path = os.path.join(
                self.media_output_dir, safe_base + scaled_intermediate_suffix
            )
            scale_ok = self._perform_scaling_step(current_path, scaled_intermediate_path)
            if scale_ok:
                print("    Scaling to intermediate file successful.")
                path_for_final_encode = scaled_intermediate_path
                codec_for_final_encode = 'h264'
                ext_for_final_encode = '.mp4'
                mime_for_final_encode = 'video/mp4'
                if current_path != initial_absolute_temp_path and os.path.exists(current_path):
                    try:
                        os.remove(current_path)
                        print(f"    Deleted pre-scaled file: {os.path.basename(current_path)}")
                    except OSError as e:
                        print(f"    WARN: Failed deleting pre-scaled file: {e}")
            else:
                print("    WARN: Scaling step failed. Using previous file for final encode.")
                if scaled_intermediate_path and os.path.exists(scaled_intermediate_path):
                    try: os.remove(scaled_intermediate_path)
                    except OSError: pass
                scaled_intermediate_path = None

        # --- 4. Step 2: Final Transcoding Logic (REVISED) ---
        print("--- Step 2: Final Transcoding Check ---")
        final_transcode_needed, reasons = False, []
        # ... (logic to determine final_transcode_needed and reasons as before) ...
        is_preferred_format = False
        preferred_codecs = self.PREFERRED_FORMATS.get(ext_for_final_encode)
        if preferred_codecs and codec_for_final_encode in preferred_codecs:
            is_preferred_format = True
        if not is_preferred_format:
             final_transcode_needed = True
             reasons.append("Format not preferred")
        if self.user_codec_choice:
            requested_info = self.config.CODEC_FORMAT_MAP.get(self.user_codec_choice)
            requested_ext = requested_info.get('ext', '.err').lower() if requested_info else '.err'
            if (self.user_codec_choice != codec_for_final_encode or
                    requested_ext != ext_for_final_encode):
                final_transcode_needed = True
                reasons.append(f"Explicit change to {self.user_codec_choice}")

        # --- Variables for tracking results ---
        final_output_path = os.path.join(
            self.media_output_dir, safe_base + self.target_extension
        )
        final_output_filename = os.path.basename(final_output_path)
        resulting_path = path_for_final_encode # Start with the input to this stage
        resulting_filename = os.path.basename(resulting_path)
        resulting_mime = mime_for_final_encode
        intermediate_h264_file = None # Track the H.264 intermediate
        final_encode_success = False # Overall success flag

        if final_transcode_needed and self.enable_transcoding:
            print(
                f"    Decision: Final transcode required. Reasons: "
                f"[{', '.join(sorted(list(set(reasons))))}]"
            )

            # Check VAAPI capabilities based on CURRENT input and TARGET output
            decode_vaapi_possible = (
                self.use_vaapi and codec_for_final_encode and
                codec_for_final_encode in self.VAAPI_DECODABLE_CODECS
            )
            encode_vaapi_possible = (
                self.use_vaapi and
                self.target_codec in self.config.FFMPEG_CODEC_OPTIONS_VAAPI
            )

            # --- Revised Transcoding Strategy ---
            input_for_next_step = path_for_final_encode
            source_codec_for_next_step = codec_for_final_encode
            attempt_decode_vaapi_next_step = decode_vaapi_possible

            # Phase 1: Can we encode the target with VAAPI?
            if encode_vaapi_possible:
                # Phase 1a: Is direct VAAPI pipeline possible? (Source decodable)
                if decode_vaapi_possible:
                    print("    Attempt 1: Direct VAAPI Pipeline...")
                    success_direct_vaapi = self._perform_final_encode_step(
                        input_path=input_for_next_step,
                        final_output_path=final_output_path,
                        target_codec=self.target_codec,
                        source_codec_name=source_codec_for_next_step,
                        attempt_vaapi_decode=True,
                        use_vaapi_for_encode_attempt=True
                    )
                    if success_direct_vaapi:
                        final_encode_success = True
                    else:
                        print("    WARN: Direct VAAPI pipeline failed.")
                        # Continue to check if intermediate step is needed

                # Phase 1b: If direct VAAPI failed OR wasn't possible, try intermediate H.264
                if not final_encode_success:
                    # Create intermediate H.264 if source wasn't decodable or direct VAAPI failed
                    if not decode_vaapi_possible:
                         print("    INFO: Source codec not VAAPI decodable, attempting intermediate H.264.")
                    #else: # Means direct VAAPI failed, also try intermediate
                    #     print("    INFO: Direct VAAPI failed, attempting intermediate H.264.")

                    intermediate_h264_suffix = ".inter_h264.mp4"
                    intermediate_h264_file = os.path.join(
                        self.media_output_dir, safe_base + intermediate_h264_suffix
                    )
                    intermediate_ok = self._perform_intermediate_h264_encode(
                        input_path=path_for_final_encode, # Start from original/scaled input
                        intermediate_h264_output_path=intermediate_h264_file
                    )

                    if intermediate_ok:
                        # Update input for the next VAAPI attempt
                        input_for_next_step = intermediate_h264_file
                        source_codec_for_next_step = 'h264'
                        attempt_decode_vaapi_next_step = True # H.264 is decodable

                        # Phase 1c: Try VAAPI again, now from H.264 intermediate
                        print("    Attempt 2: VAAPI Pipeline from Intermediate H.264...")
                        success_vaapi_from_h264 = self._perform_final_encode_step(
                            input_path=input_for_next_step,
                            final_output_path=final_output_path,
                            target_codec=self.target_codec,
                            source_codec_name=source_codec_for_next_step,
                            attempt_vaapi_decode=attempt_decode_vaapi_next_step,
                            use_vaapi_for_encode_attempt=True # Still target VAAPI encode
                        )
                        if success_vaapi_from_h264:
                            final_encode_success = True
                        else:
                             print("    WARN: VAAPI pipeline from H.264 intermediate failed.")
                             # Proceed to CPU fallback using the intermediate file
                    else:
                         print("    WARN: Intermediate H.264 step failed. Will proceed to CPU fallback from original source.")
                         # Keep input_for_next_step as the original/scaled path
                         input_for_next_step = path_for_final_encode
                         source_codec_for_next_step = codec_for_final_encode
                         attempt_decode_vaapi_next_step = decode_vaapi_possible

            # Phase 2: If VAAPI encode isn't possible, or all VAAPI attempts failed
            if not final_encode_success:
                 # Determine the correct input for the CPU fallback
                 cpu_input_path = intermediate_h264_file if intermediate_h264_file and os.path.exists(intermediate_h264_file) else path_for_final_encode
                 cpu_source_codec = 'h264' if cpu_input_path == intermediate_h264_file else codec_for_final_encode
                 cpu_attempt_decode = True if cpu_source_codec == 'h264' else decode_vaapi_possible # Can still try VAAPI decode for H.264

                 print(
                     f"    Attempt 3: CPU Fallback Encode from "
                     f"'{os.path.basename(cpu_input_path)}'..."
                 )
                 success_cpu = self._perform_final_encode_step(
                     input_path=cpu_input_path,
                     final_output_path=final_output_path,
                     target_codec=self.target_codec,
                     source_codec_name=cpu_source_codec,
                     attempt_vaapi_decode=cpu_attempt_decode, # Allow VAAPI decode if possible
                     use_vaapi_for_encode_attempt=False # Force CPU encode
                 )
                 if success_cpu:
                     final_encode_success = True
                 else:
                     print("    ERROR: Final CPU fallback encode failed.")

            # --- Update Results Based on Overall Success ---
            if final_encode_success:
                print(f"    Final transcode OK. Using: {final_output_filename}")
                resulting_path = final_output_path
                resulting_filename = final_output_filename
                resulting_mime = self.target_mime_type
            else:
                # All attempts failed, keep the input file from before this stage
                print(
                    f"    WARN: All transcode attempts FAILED. Using input file "
                    f"'{os.path.basename(path_for_final_encode)}' as is."
                )
                resulting_path = path_for_final_encode
                resulting_filename = os.path.basename(resulting_path)
                resulting_mime = mime_for_final_encode
                # Try to rename to target filename if extension differs
                if resulting_path != final_output_path:
                    try:
                        print(
                            f"    Attempting to rename '{resulting_filename}' to "
                            f"target name '{final_output_filename}' after failed transcode."
                        )
                        if os.path.exists(final_output_path):
                            os.remove(final_output_path)
                        shutil.move(resulting_path, final_output_path)
                        resulting_path = final_output_path
                        resulting_filename = os.path.basename(resulting_path)
                    except OSError as e:
                        print(f"    ERROR: Renaming failed input file: {e}")
                        resulting_filename = os.path.basename(resulting_path)

        elif is_video: # Transcode not needed
            print("    Decision: Final transcode not required or skipped.")
            resulting_path = path_for_final_encode
            resulting_filename = os.path.basename(resulting_path)
            resulting_mime = mime_for_final_encode
            if resulting_path != final_output_path:
                 try:
                    print(f"    Renaming '{resulting_filename}' to final target name '{final_output_filename}' (no transcode).")
                    if os.path.exists(final_output_path): os.remove(final_output_path)
                    shutil.move(resulting_path, final_output_path)
                    resulting_path = final_output_path
                    resulting_filename = os.path.basename(resulting_path)
                 except OSError as e:
                    print(f"    ERROR: Renaming to final name failed: {e}")
                    resulting_filename = os.path.basename(resulting_path)


        # --- 5. Cleanup and Return ---
        # ... (Cleanup logic for intermediate_h264_file, initial_absolute_temp_path, scaled_intermediate_path as before) ...
        if intermediate_h264_file and os.path.exists(intermediate_h264_file):
             try:
                 os.remove(intermediate_h264_file)
                 print(f"    Cleaned up intermediate H.264 file: {os.path.basename(intermediate_h264_file)}")
             except OSError as e:
                 print(f"    WARN: Failed cleanup of intermediate H.264 file: {e}")
        if (initial_absolute_temp_path != resulting_path and
                os.path.exists(initial_absolute_temp_path)):
            try: os.remove(initial_absolute_temp_path)
            except OSError: pass
        if (scaled_intermediate_path and
                scaled_intermediate_path != resulting_path and
                os.path.exists(scaled_intermediate_path)):
            try:
                os.remove(scaled_intermediate_path)
                print("    Cleaned up unused intermediate scaled file.")
            except OSError as e:
                print(f"    WARN: Failed final cleanup of intermediate scaled file: {e}")

        if not os.path.exists(resulting_path):
             print(f"    CRITICAL ERROR: Final file missing after processing: {resulting_path}")
             return None

        relative_path = os.path.join(
            self.config.MEDIA_OUTPUT_DIR_NAME, resulting_filename
        ).replace("\\", "/")

        print(f"--- Finished Annotation. Final relative path: {relative_path} ---")
        return {
            "pageIndex": page_num, "annotIndex": annot_index,
            "outputPath": relative_path, "absolutePath": resulting_path,
            "contentTypeDetected": resulting_mime, "pdfRect": pdf_rect
        }


    def _perform_scaling_step(self, input_path, intermediate_output_path):
        """
        Performs CPU scaling to a temporary intermediate H.264/MP4 file
        using high quality settings to preserve detail.
        """
        if not self.ffmpeg_path or self.scaling_factor is None:
            return False

        print(f"    Scaling '{os.path.basename(input_path)}' to HQ intermediate MP4...")
        scale_ratio = self.scaling_factor / 100.0
        scale_filter = (
            f"scale=w='trunc(iw*{scale_ratio}/2)*2':"
            f"h='trunc(ih*{scale_ratio}/2)*2':flags=lanczos"
        )

        scale_cmd = [
            self.ffmpeg_path, '-y',
            '-i', input_path,
            '-vf', scale_filter,
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '18',
            '-c:a', 'copy',
            '-movflags', '+faststart',
            intermediate_output_path
        ]

        print(f"      CMD SCALE STEP (HQ): {' '.join(scale_cmd)}")
        try:
            result = subprocess.run(
                scale_cmd, capture_output=True, text=True, check=False,
                encoding='utf-8', errors='replace'
            )
            if (result.returncode == 0 and os.path.exists(intermediate_output_path)
                    and os.path.getsize(intermediate_output_path) > 0):
                print("      Scaling step successful.")
                return True
            else:
                print(f"    ERROR: Scaling step failed! (code: {result.returncode})")
                stderr_head = result.stderr[:500]
                stderr_tail = result.stderr[-500:]
                print(f"      Stderr (beginning): {stderr_head}...")
                print(f"      Stderr (end): ...{stderr_tail}")
                if os.path.exists(intermediate_output_path):
                     try: os.remove(intermediate_output_path)
                     except OSError: pass
                return False
        except Exception as e:
            print(f"    ERROR: Exception during scaling step: {e}")
            traceback.print_exc(limit=1)
            if os.path.exists(intermediate_output_path):
                 try: os.remove(intermediate_output_path)
                 except OSError: pass
            return False


    def _perform_final_encode_step(self, input_path, final_output_path, target_codec,
                                   source_codec_name, attempt_vaapi_decode,
                                   use_vaapi_for_encode_attempt):
        """
        Performs the final transcode step (VAAPI attempt or CPU),
        using specific command structures based on working tests.
        Returns True on success, False on failure.
        """
        if not self.ffmpeg_path:
            print("    ERROR: Cannot perform final encode - ffmpeg path not set.")
            return False

        temp_output_path = None
        final_encode_ok = False
        try:
            final_dir = os.path.dirname(final_output_path)
            final_base, final_ext = os.path.splitext(os.path.basename(final_output_path))
            attempt_type = 'vaapi' if use_vaapi_for_encode_attempt else 'cpu'
            temp_prefix = f"{final_base}_final_{attempt_type}_"
            with tempfile.NamedTemporaryFile(
                    mode='wb', delete=False, dir=final_dir,
                    prefix=temp_prefix, suffix=final_ext) as tf:
                temp_output_path = tf.name
        except Exception as e:
            print(f"    ERROR: Creating temporary final encode file failed: {e}")
            return False

        ffmpeg_cmd = [self.ffmpeg_path, '-y']
        log_parts = []
        vaapi_needed_overall = attempt_vaapi_decode or use_vaapi_for_encode_attempt
        vaapi_instance_name = "va"

        if vaapi_needed_overall:
            init_device_str = f"vaapi={vaapi_instance_name}"
            if self.config.VAAPI_DEVICE_PATH:
                init_device_str += f":{self.config.VAAPI_DEVICE_PATH}"
                log_parts.append(f"init_hw({self.config.VAAPI_DEVICE_PATH})")
            else:
                log_parts.append("init_hw(default)")
            ffmpeg_cmd.extend(['-init_hw_device', init_device_str])
            if use_vaapi_for_encode_attempt or attempt_vaapi_decode: # Filter device needed for VAAPI filters OR decode
                 ffmpeg_cmd.extend(['-filter_hw_device', vaapi_instance_name])
                 log_parts.append("filter_hw_dev")

        hw_decode_active = False
        decode_opts = []
        # Only attempt HW decode if requested AND source codec is known compatible
        if attempt_vaapi_decode and source_codec_name in self.VAAPI_DECODABLE_CODECS:
            decode_opts.extend(['-hwaccel', 'vaapi'])
            decode_opts.extend(['-hwaccel_device', vaapi_instance_name])
            decode_opts.extend(['-hwaccel_output_format', 'vaapi'])
            hw_decode_active = True
            log_parts.append(f"VAAPI_Decode({source_codec_name})")
        else:
            log_parts.append(f"SW_Decode({source_codec_name})")

        ffmpeg_cmd.extend(decode_opts)
        ffmpeg_cmd.extend(['-i', input_path])
        ffmpeg_cmd.extend(['-map', '0:v:0', '-map', '0:a:0?'])
        log_parts.append("map(0:v:0,0:a:0?)")

        vf_parts = []
        extra_output_opts = []
        if use_vaapi_for_encode_attempt:
            if not hw_decode_active:
                # This might happen if the intermediate step failed, but we still try VAAPI encode
                print("    WARN: Attempting VAAPI encode filter chain without active VAAPI decode input. May fail.")
                # Let FFmpeg try, it might handle internal conversion or fail predictably
                vf_parts.append("format=pix_fmts=nv12") # Ensure format for encoder anyway? Risky.
                log_parts.append("vf(format=nv12_for_vaapi)")
                # Or maybe just skip filters? Let's skip filters if decode failed.
                # vf_parts = [] # Safer?
            else:
                # Normal VAAPI encode path from VAAPI decode
                vf_parts.append("hwupload") # May be redundant, but safe
                vf_parts.append("scale_vaapi=w=iw:h=ih:format=nv12")
                log_parts.append("vf(hwupload,scale_vaapi(format=nv12))")
        else: # CPU Encode path
            if hw_decode_active:
                vf_parts.append("hwdownload")
                vf_parts.append("format=pix_fmts=yuv420p")
                log_parts.append("vf(hwdownload,format=yuv420p)")
            elif target_codec == 'av1':
                vf_parts.append("format=pix_fmts=yuv420p")
                log_parts.append("vf(format=yuv420p)")

        if vf_parts:
            ffmpeg_cmd.extend(['-vf', ",".join(vf_parts)])

        codec_options = None
        encoder_log = ""
        if use_vaapi_for_encode_attempt:
            codec_options = self.config.FFMPEG_CODEC_OPTIONS_VAAPI.get(target_codec)
            if codec_options:
                encoder_log = f"Encode({target_codec}_vaapi)"
                log_parts.append("VAAPI_Encode")
            else:
                raise ValueError(f"Missing VAAPI config for {target_codec}")
        else:
            codec_options = self.config.FFMPEG_CODEC_OPTIONS_CPU.get(target_codec)
            if codec_options:
                encoder_log = f"Encode({target_codec}_cpu)"
                if hw_decode_active: log_parts.append("(VAAPI Decode->CPU Encode)")
            else:
                raise ValueError(f"Missing CPU config for {target_codec}")

        ffmpeg_cmd.extend(codec_options)
        log_parts.append(encoder_log)

        audio_opts = []
        target_ext_lower = os.path.splitext(final_output_path)[1].lower()
        if target_ext_lower == '.webm':
            audio_opts = ['-c:a', 'libopus', '-b:a', '96k']
            log_parts.append("Audio(Opus)")
        else:
            audio_opts = ['-c:a', 'aac', '-b:a', '128k']
            log_parts.append("Audio(AAC)")
        ffmpeg_cmd.extend(audio_opts)

        ffmpeg_cmd.extend(self.config.FFMPEG_COMMON_OPTIONS)
        target_format_info = self.config.CODEC_FORMAT_MAP.get(target_codec)
        container_opts = target_format_info.get('container_opts', []) if target_format_info else []
        if container_opts: ffmpeg_cmd.extend(container_opts)
        if extra_output_opts: ffmpeg_cmd.extend(extra_output_opts)
        ffmpeg_cmd.append(temp_output_path)

        print(f"    CMD FINAL ENCODE ({', '.join(log_parts)}): {' '.join(ffmpeg_cmd)}")

        try:
            result = subprocess.run(
                ffmpeg_cmd, capture_output=True, text=True, check=False,
                encoding='utf-8', errors='replace'
            )
            if (result.returncode == 0 and os.path.exists(temp_output_path)
                    and os.path.getsize(temp_output_path) > 0):
                print("    Final encode attempt successful.")
                shutil.move(temp_output_path, final_output_path)
                print(f"    Moved result to: '{os.path.basename(final_output_path)}'")
                final_encode_ok = True
                temp_output_path = None
            else:
                print(f"    ERROR: Final encode FFmpeg failed! (code: {result.returncode})")
                if os.path.exists(temp_output_path) and os.path.getsize(temp_output_path) == 0:
                    print("      Reason: Output file is 0 bytes.")
                stderr_head = result.stderr[:1000]; stderr_tail = result.stderr[-1000:]
                print(f"      Stderr (beginning): {stderr_head}...")
                print(f"      Stderr (end): ...{stderr_tail}")
                final_encode_ok = False
        except FileNotFoundError:
            print(f"    ERROR: ffmpeg not found at '{self.ffmpeg_path}'.")
            final_encode_ok = False
        except Exception as e:
            print(f"    ERROR: Unexpected error during final encode ffmpeg: {e}")
            traceback.print_exc(limit=1)
            final_encode_ok = False
        finally:
            if temp_output_path and os.path.exists(temp_output_path):
                print(f"    Cleaning failed/unused final encode temp file: {os.path.basename(temp_output_path)}")
                try: os.remove(temp_output_path)
                except OSError as delete_error: print(f"      WARN: Failed cleaning temp file: {delete_error}")

        return final_encode_ok
