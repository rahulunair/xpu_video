import logging
import queue as Queue
import threading
import traceback
from collections import deque
from datetime import datetime
from pathlib import Path

import requests

from config import VALID_TOKEN, config, logger, output_dir


class VideoGenerator:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}
        self.session = requests.Session()

    def generate_video(self, prompt: str, num_frames: int, fps: int):
        try:
            payload = {"prompt": prompt, "num_frames": num_frames, "fps": fps}
            response = self.session.post(
                self.base_url, json=payload, headers=self.headers, stream=True
            )

            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"Error response: {response.text}")
                return None

        except Exception as e:
            logger.error(f"Exception in generate_video: {str(e)}")
            logger.error(traceback.format_exc())
            return None


class AsyncVideoGenerator:
    def __init__(self):
        self.queue = Queue.Queue()
        self.results = {}
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()

    def _process_queue(self):
        while True:
            try:
                task_id, prompt, num_frames, fps = self.queue.get()
                generator = VideoGenerator(config.base_url, VALID_TOKEN)
                video_data = generator.generate_video(prompt, num_frames, fps)
                self.results[task_id] = video_data
            except Exception as e:
                logger.error(f"Error in worker thread: {str(e)}")
            finally:
                self.queue.task_done()

    def submit_task(self, task_id: str, prompt: str, num_frames: int, fps: int):
        self.queue.put((task_id, prompt, num_frames, fps))

    def get_result(self, task_id: str):
        return self.results.get(task_id)

    def clear_result(self, task_id: str):
        self.results.pop(task_id, None)


def get_video_size(path: Path) -> float:
    return path.stat().st_size / (1024 * 1024)


def cleanup_old_videos(max_size_mb: float = config.max_storage_mb):
    total_size = 0
    videos = sorted(output_dir.glob("*.mp4"), key=lambda x: x.stat().st_mtime)

    for video in videos:
        total_size += get_video_size(video)

    while total_size > max_size_mb and videos:
        oldest_video = videos.pop(0)
        total_size -= get_video_size(oldest_video)
        oldest_video.unlink()
        logger.info(f"Deleted old video: {oldest_video}")


def generate_unique_filename() -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"video_{timestamp}.mp4"
