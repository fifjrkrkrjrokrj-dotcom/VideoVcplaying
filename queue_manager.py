import os
import asyncio
from typing import Dict, List, Optional

class PlaybackState:
    def __init__(self, chat_id: int, user_id: int):
        self.chat_id: int = chat_id
        self.user_id: int = user_id
        self.queue: List[dict] = []
        self.current_index: int = 0
        self.is_playing: bool = False
        self.is_paused: bool = False
        self.loop_mode: str = "off"  # "off" | "queue" | "single"
        self.volume: int = 100       # 0 to 200
        self.autoplay: bool = False  # Keep playing all videos continuously when queue ends
        self.active_msg_id: Optional[int] = None  # Message ID of the DM dashboard
        self.local_file_path: Optional[str] = None
        self.download_task: Optional[asyncio.Task] = None
        self.skip_lock = asyncio.Lock()  # Prevent double skipping issues

    def get_current_video(self) -> Optional[dict]:
        """Gets the video metadata dictionary currently playing."""
        if 0 <= self.current_index < len(self.queue):
            return self.queue[self.current_index]
        return None

    def add_to_queue(self, videos: List[dict]):
        """Adds a list of videos to the queue."""
        self.queue.extend(videos)

    def next_index(self) -> bool:
        """
        Advances the current index based on the loop mode.
        Returns True if there is a next video to play, False otherwise.
        """
        if not self.queue:
            return False
            
        if self.loop_mode == "single":
            # Keep playing the same video
            return True
            
        elif self.loop_mode == "queue":
            # Loop around to the start if we reach the end
            self.current_index = (self.current_index + 1) % len(self.queue)
            return True
            
        else: # "off"
            if self.current_index + 1 < len(self.queue):
                self.current_index += 1
                return True
            return False

    def prev_index(self) -> bool:
        """Goes back to the previous video. Returns True if successful."""
        if not self.queue:
            return False
            
        if self.loop_mode == "single":
            return True
            
        elif self.loop_mode == "queue":
            self.current_index = (self.current_index - 1) % len(self.queue)
            return True
            
        else: # "off"
            if self.current_index > 0:
                self.current_index -= 1
                return True
            return False

    def clear(self):
        """Clears the playback state queue and stops playback markers."""
        self.queue = []
        self.current_index = 0
        self.is_playing = False
        self.is_paused = False
        self.cleanup_local_file()
        if self.download_task and not self.download_task.done():
            self.download_task.cancel()

    def cleanup_local_file(self):
        """Safely deletes the local downloaded video file from the server."""
        if self.local_file_path:
            try:
                if os.path.exists(self.local_file_path):
                    os.remove(self.local_file_path)
            except Exception as e:
                print(f"Error cleaning up local file {self.local_file_path}: {e}")
            finally:
                self.local_file_path = None


# Global active playbacks lookup: chat_id -> PlaybackState
_active_playbacks: Dict[int, PlaybackState] = {}

def get_playback(chat_id: int) -> Optional[PlaybackState]:
    """Retrieves the active playback state for a given group chat."""
    return _active_playbacks.get(chat_id)

def create_playback(chat_id: int, user_id: int) -> PlaybackState:
    """Creates (or resets) and returns a playback state for a group chat."""
    state = PlaybackState(chat_id, user_id)
    _active_playbacks[chat_id] = state
    return state

def delete_playback(chat_id: int):
    """Deletes and cleans up the playback state for a group chat."""
    if chat_id in _active_playbacks:
        _active_playbacks[chat_id].clear()
        del _active_playbacks[chat_id]
