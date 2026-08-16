import base64
import io
import gymnasium as gym
import numpy as np
from PIL import Image
import os
import imageio
import imageio_ffmpeg
from loguru import logger

# One buffered frame == one agent step, so playback rate is steps-per-second, not
# wall-clock speed. At 10 a 13-step episode flashes by in 1.3s; 1 makes it watchable.
VIDEO_FPS = 1

class RenderWrapper(gym.Wrapper):
    """
    A Gym Wrapper to save observations as images and compile them into a video.

    This wrapper saves each frame from the environment's observation (`pov`)
    as a PNG image in a specified directory. When the environment is closed,
    it compiles these frames into an MP4 video.

    Args:
        env (gym.Env): The environment to wrap.
        save_path (str): The directory where frames and videos will be saved.
    """
    def __init__(self, env, save_messages=True, save_path="debug_frames"):
        super().__init__(env)
        self.save_path = str(save_path)
        self.frames_path = os.path.join(self.save_path, "frames")
        
        # Do not create frames directory; frames are kept in memory only for video compilation
        os.makedirs(self.save_path, exist_ok=True)
        logger.info(f"RenderWrapper: frames will be kept in memory only (frames/ directory disabled)")
        
        self.frames = []
        self.episode_count = 0
        self.frame_count = 0

    def reset(self, save_frame: bool = True, **kwargs):
        """
        Resets the environment, saves the video of the previous episode,
        and saves the first frame of the new episode.
        """
        # Save video of the previous episode if it has frames
        if self.frames:
            self.save_video()

        self.frames = []
        self.frame_count = 0
        self.episode_count += 1
        
        observation, info = self.env.reset(**kwargs)
        
        # Save the first frame
        if save_frame:
            self._save_frame(observation)
        
        return observation, info

    def step(self, action, save_frame: bool = True):
        """
        Steps the environment, saves the resulting frame, and collects it for video.
        """
        observation, reward, terminated, truncated, info = self.env.step(action)
        
        if save_frame:
            self._save_frame(observation)
        
        return observation, reward, terminated, truncated, info

    def _save_frame(self, observation):
        """Appends the 'pov' observation to the in-memory frame list (no disk write)."""
        try:
            if "pov" not in observation:
                logger.warning(f"_save_frame: 'pov' key missing in observation, keys={list(observation.keys())}")
                return
            pov = observation["pov"]
            if pov is None or pov.shape[0] == 0 or pov.shape[1] == 0:
                logger.warning(f"_save_frame: pov is empty (shape={pov.shape if pov is not None else None}), skipping.")
                return

            img = Image.fromarray(pov, 'RGB')

            # Resize image height to be divisible by 16 to avoid FFMPEG warning
            width, height = img.size
            target_height = (height // 16) * 16
            
            if height != target_height:
                # Use a high-quality resampling filter
                img = img.resize((width, target_height), Image.Resampling.LANCZOS)

            self.frames.append(np.array(img))
            self.frame_count += 1
            logger.debug(f"Frame buffered in memory (total frames={self.frame_count})")
        except Exception:
            logger.exception(f"_save_frame: failed to buffer frame {self.frame_count}:")

    def save_video_checkpoint(self):
        """Saves current frames as a checkpoint video, overwriting the same fixed file (episode.mp4).
        
        Call this periodically (e.g. every N steps) to preview the current run in real-time.
        """
        if not self.frames:
            return
        checkpoint_filename = os.path.join(self.save_path, "episode.mp4")
        logger.info(f"Saving checkpoint video ({len(self.frames)} frames) to {checkpoint_filename}...")
        try:
            imageio.mimsave(
                checkpoint_filename,
                self.frames,
                fps=VIDEO_FPS,
                codec="libx264",
                pixelformat="yuv420p",
            )
            logger.success(f"Checkpoint video saved ({len(self.frames)} frames) -> {checkpoint_filename}")
        except TypeError as error:
            if "audio_path" in str(error):
                logger.warning("imageio/imageio-ffmpeg version mismatch, falling back to imageio_ffmpeg writer.")
                self._save_video_with_imageio_ffmpeg(checkpoint_filename, fps=VIDEO_FPS)
            else:
                logger.exception("Error saving checkpoint video:")
        except Exception:
            logger.exception("Error saving checkpoint video:")

    def save_video(self):
        """Compiles collected frames into an MP4 video."""
        if not self.frames:
            return

        video_filename = os.path.join(self.save_path, "episode.mp4")
        logger.info(f"Saving video of episode {self.episode_count} to {video_filename}...")
        
        try:
            # Prefer an explicit codec to avoid PyAV "codec None" failures.
            imageio.mimsave(
                video_filename,
                self.frames,
                fps=VIDEO_FPS,
                codec="libx264",
                pixelformat="yuv420p",
            )
            logger.success("Video saved successfully.")
        except TypeError as error:
            if "audio_path" in str(error):
                logger.warning(
                    "imageio/imageio-ffmpeg version mismatch detected. "
                    "Falling back to direct imageio_ffmpeg writer."
                )
                self._save_video_with_imageio_ffmpeg(video_filename, fps=VIDEO_FPS)
            else:
                logger.exception("Error saving video:")
        except Exception:
            logger.exception(f"Error saving video:")

    def _save_video_with_imageio_ffmpeg(self, video_filename, fps=VIDEO_FPS):
        """Write video directly via imageio_ffmpeg for old plugin compatibility."""
        try:
            first_frame = np.asarray(self.frames[0])
            if first_frame.dtype != np.uint8:
                first_frame = np.clip(first_frame, 0, 255).astype(np.uint8)

            height, width = first_frame.shape[:2]
            writer = imageio_ffmpeg.write_frames(
                video_filename,
                (width, height),
                pix_fmt_in="rgb24",
                fps=fps,
                macro_block_size=1,
            )
            writer.send(None)

            for frame in self.frames:
                frame_array = np.asarray(frame)
                if frame_array.dtype != np.uint8:
                    frame_array = np.clip(frame_array, 0, 255).astype(np.uint8)

                if frame_array.shape[:2] != (height, width):
                    resized = Image.fromarray(frame_array, "RGB").resize((width, height), Image.Resampling.LANCZOS)
                    frame_array = np.asarray(resized)

                writer.send(frame_array)

            writer.close()
            logger.success("Video saved successfully via imageio_ffmpeg fallback.")
        except Exception:
            logger.exception("Error saving video via imageio_ffmpeg fallback:")

    def close(self):
        """Closes the environment and saves the final video."""
        self.save_video() # Save the last episode's video
        super().close()
