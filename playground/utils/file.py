from __future__ import annotations
import json
from loguru import logger
from pathlib import Path

def save_messages(
    message_history: list[dict],
    env_id: int, 
    run_start_timestamp: str,
    file_path: Path, 
    is_error: bool = False, 
    error_message: str | None =None
) -> bool:
    """
    Save message history to JSON file.
    
    Args:
        message_history: List of interaction records
        env_id: Environment ID
        run_start_timestamp: Run start timestamp
        file_path: Path to save file
        is_error: Whether this is an error save
        error_message: Error message if is_error=True
    """
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "environment": env_id,
            "run_start_time": run_start_timestamp,
            "total_steps": len(message_history),
            "interactions": message_history
        }
        
        if is_error and error_message:
            data["error"] = error_message
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
        
    except Exception as e:
        logger.error(f"Failed to save messages: {e}")
        return False