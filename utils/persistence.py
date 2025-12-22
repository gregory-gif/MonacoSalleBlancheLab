import json
import os
from datetime import datetime
from typing import Dict, Any, List

# RAILWAY PERSISTENCE CONFIGURATION
# We mount the volume to '/app/data'.
# If it exists, we read/write there. If not, we use the local folder.
VOLUME_PATH = '/app/data'
PROFILE_FILENAME = 'profile.json'
LOGS_FILENAME = 'session_logs.json'

def get_file_path(filename: str) -> str:
    """Returns the volume path if available, else local path."""
    if os.path.exists(VOLUME_PATH):
        return os.path.join(VOLUME_PATH, filename)
    return filename

# --- PROFILE MANAGEMENT (Strategies & Bankroll) ---

def load_profile() -> Dict[str, Any]:
    path = get_file_path(PROFILE_FILENAME)
    if not os.path.exists(path):
        return {'saved_strategies': {}, 'ga': 2000.0} # Default basics
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading profile: {e}")
        return {}

def save_profile(data: Dict[str, Any]):
    path = get_file_path(PROFILE_FILENAME)
    try:
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving profile: {e}")

# --- CAPTAIN'S LOG (Session History) ---

def log_session_result(start_ga: float, end_ga: float, shoes_played: int, mode: str = "Unknown"):
    """Logs a completed session to the permanent drive."""
    log_entry = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": mode,
        "start_ga": start_ga,
        "end_ga": end_ga,
        "pnl": end_ga - start_ga,
        "shoes": shoes_played
    }
    
    path = get_file_path(LOGS_FILENAME)
    history = []
    
    # Load existing history
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                history = json.load(f)
        except:
            history = []
            
    # Append new log
    history.append(log_entry)
    
    # Save back to drive
    try:
        with open(path, 'w') as f:
            json.dump(history, f, indent=4)
    except Exception as e:
        print(f"Error saving logs: {e}")

def get_session_logs() -> List[Dict]:
    """Retrieves history from the permanent drive."""
    path = get_file_path(LOGS_FILENAME)
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r') as f:
            data = json.load(f)
            # Return reversed so newest is first
            return data[::-1]
    except:
        return []

def delete_session_log(log_date: str) -> bool:
    """Deletes a specific log entry."""
    path = get_file_path(LOGS_FILENAME)
    if not os.path.exists(path):
        return False
        
    try:
        with open(path, 'r') as f:
            history = json.load(f)
        
        # Filter out the item with the matching date
        new_history = [h for h in history if h.get('date') != log_date]
        
        with open(path, 'w') as f:
            json.dump(new_history, f, indent=4)
        return True
    except:
        return False