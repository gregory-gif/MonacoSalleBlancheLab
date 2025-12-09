import os
import json
from datetime import datetime
try:
    from pymongo import MongoClient
    from pymongo.server_api import ServerApi
    from pymongo.errors import ConnectionFailure
except ImportError:
    MongoClient = None

# --- CONFIGURATION ---
MONGO_URL = os.environ.get('MONGO_URL')

# GLOBAL DB CLIENT
mongo_client = None
db = None

def get_db():
    global mongo_client, db
    if MONGO_URL and not mongo_client:
        try:
            mongo_client = MongoClient(
                MONGO_URL, 
                server_api=ServerApi('1'), 
                serverSelectionTimeoutMS=5000
            )
            # Test connection
            mongo_client.admin.command('ping')
            db = mongo_client['salle_blanche_db']
            print("✅ CONNECTED TO MONGODB ATLAS")
        except Exception as e:
            print(f"⚠️ MONGODB CONNECTION FAILED: {e}")
            mongo_client = None
    
    return db

# --- PROFILE MANAGEMENT ---

def load_profile():
    """Loads profile from MongoDB or local JSON."""
    database = get_db()
    
    # CLOUD MODE
    if database is not None:
        try:
            profile_coll = database['profile']
            data = profile_coll.find_one({'_id': 'user_profile'})
            if not data:
                default_profile = {
                    '_id': 'user_profile',
                    'ga': 1700.0,
                    'saved_strategies': {}
                }
                profile_coll.insert_one(default_profile)
                return default_profile
            return data
        except Exception as e:
            print(f"Error reading profile from DB: {e}")

    # LOCAL FILE MODE (Fallback)
    if not os.path.exists('profile.json'):
        return {'ga': 1700.0, 'saved_strategies': {}}
    
    try:
        with open('profile.json', 'r') as f:
            return json.load(f)
    except:
        return {'ga': 1700.0, 'saved_strategies': {}}

def save_profile(data):
    """Saves profile to MongoDB or local JSON."""
    database = get_db()
    
    # CLOUD MODE
    if database is not None:
        try:
            profile_coll = database['profile']
            # Ensure _id exists
            if '_id' not in data:
                data['_id'] = 'user_profile'
            profile_coll.replace_one({'_id': 'user_profile'}, data, upsert=True)
            return
        except Exception as e:
            print(f"Error saving profile to DB: {e}")

    # LOCAL FILE MODE
    with open('profile.json', 'w') as f:
        json.dump(data, f, indent=4)

# --- SESSION LOGGING ---

def log_session_result(start_ga, end_ga, shoes_played):
    """Logs a completed session."""
    log_entry = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "start_ga": start_ga,
        "end_ga": end_ga,
        "pnl": end_ga - start_ga,
        "shoes": shoes_played
    }
    
    database = get_db()
    
    # CLOUD MODE
    if database is not None:
        try:
            logs_coll = database['session_logs']
            logs_coll.insert_one(log_entry)
            return
        except Exception as e:
            print(f"Error logging session to DB: {e}")

    # LOCAL FILE MODE
    history = []
    if os.path.exists('session_logs.json'):
        try:
            with open('session_logs.json', 'r') as f:
                history = json.load(f)
        except:
            pass
    
    history.append(log_entry)
    
    with open('session_logs.json', 'w') as f:
        json.dump(history, f, indent=4)

def get_session_logs():
    """Retrieves history."""
    database = get_db()
    
    # CLOUD MODE
    if database is not None:
        try:
            logs_coll = database['session_logs']
            cursor = logs_coll.find().sort('_id', -1)
            return list(cursor)
        except Exception as e:
            print(f"Error fetching logs from DB: {e}")

    # LOCAL FILE MODE
    if not os.path.exists('session_logs.json'):
        return []
    try:
        with open('session_logs.json', 'r') as f:
            data = json.load(f)
            return data[::-1]
    except:
        return []

def delete_session_log(log_date):
    """Deletes a log entry by its unique date timestamp."""
    database = get_db()
    
    # CLOUD MODE
    if database is not None:
        try:
            logs_coll = database['session_logs']
            logs_coll.delete_one({'date': log_date})
            return True
        except Exception as e:
            print(f"Error deleting log: {e}")
            return False

    # LOCAL FILE MODE
    if not os.path.exists('session_logs.json'):
        return False
        
    try:
        with open('session_logs.json', 'r') as f:
            history = json.load(f)
        
        # Filter out the item
        new_history = [h for h in history if h.get('date') != log_date]
        
        with open('session_logs.json', 'w') as f:
            json.dump(new_history, f, indent=4)
        return True
    except:
        return False
