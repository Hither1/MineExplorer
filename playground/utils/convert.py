from __future__ import annotations
import base64
import io
import numpy as np
from PIL import Image
from loguru import logger


def convert_buffer_to_base64_images(frame_buffer: list[np.ndarray]) -> list[bytes]:
    base64_images = []
    for i, pov_image in enumerate(frame_buffer):
        try:
            img = Image.fromarray(pov_image)
            original_size = img.size
            # Downsample to save tokens and stay within context limits
            # MineRL usually has 64x64, let's keep it or slightly downsample if it was larger
            # For 64x64, no need to downsample further as it's already small.
            if original_size[0] > 256:
                new_width = original_size[0] // 2
                new_height = original_size[1] // 2
                new_size = (new_width, new_height)
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')
            base64_images.append(base64_image)
        except Exception as e:
            logger.error(f"Failed to encode frame {i} to base64: {e}")
            continue
    return base64_images
