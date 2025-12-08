import json
import os
from datetime import datetime

# File where we store the Director's data AND Strategy Library
DATA_FILE = 'lab_data.json'

DEFAULT_PROFILE = {
    # --- LIVE TRACKER DATA ---
    "ga": 1700.0,          # Game Account (Real Money)
    "ytd_pnl": 0.0,        # Year-to-Date Profit/Loss
    "contributions": 0.0,  # Total Monthly Contributions
    "luxury_tax_paid": 0.0,
    "sessions_played": 0,
    "current_tier": 1,
    "history": [],         # Log of all real sessions
    
    # --- SIMULATOR LIBRARY ---
    "saved_strategies": {} # Presets for the Simulator
}

def load_profile():
    """
    Loads the profile from disk. If missing or corrupt, returns default.
    Ensures 'saved_strategies' key always exists.
    """
    if not os.path.exists(DATA_FILE):
        save_profile(DEFAULT_PROFILE)
        return DEFAULT_PROFILE.copy()
    
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            
        # Migration: Ensure new keys exist if loading an old file
        if "saved_strategies" not in data:
            data["saved_strategies"] = {}
        if "history" not in data:
            data["history"] = []
            
        return data
        
    except (json.JSONDecodeError, IOError):
        print(f"⚠️ Warning: Could not read {DATA_FILE}. Returning defaults.")
        return DEFAULT_PROFILE.copy()

def save_profile(data):
    """Writes the profile to disk."""
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except IOError as e:
        print(f"❌ Error saving profile: {e}")

def log_session_result(start_ga: float, end_ga: float, shoes_played: int):
    """
    Updates the Live Profile after a REAL session ends.
    (Used by dashboard.py, not the simulator)
    """
    profile = load_profile()
    
    session_pnl = end_ga - start_ga
    
    # Update Totals
    profile["ga"] = end_ga
    profile["ytd_pnl"] += session_pnl
    profile["sessions_played"] += 1
    
    # Log Entry
    entry = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "start_ga": start_ga,
        "end_ga": end_ga,
        "pnl": session_pnl,
        "shoes": shoes_played
    }
    profile["history"].append(entry)
    
    save_profile(profile)
    return profile
