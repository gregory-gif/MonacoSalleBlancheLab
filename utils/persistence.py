import json
import os
from typing import Dict, Any

# RAILWAY PERSISTENCE LOGIC
# On Railway, we will mount a volume to '/app/data'.
# If that directory exists, we save there. Otherwise, we use the local folder.
VOLUME_PATH = '/app/data'
PROFILE_FILENAME = 'profile.json'

def get_profile_path():
    if os.path.exists(VOLUME_PATH):
        return os.path.join(VOLUME_PATH, PROFILE_FILENAME)
    return PROFILE_FILENAME

def load_profile() -> Dict[str, Any]:
    path = get_profile_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

def save_profile(data: Dict[str, Any]):
    path = get_profile_path()
    try:
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving profile: {e}")