# Add this to the very bottom of utils/persistence.py

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
        
        # Filter out the item with the matching date
        new_history = [h for h in history if h.get('date') != log_date]
        
        with open('session_logs.json', 'w') as f:
            json.dump(new_history, f, indent=4)
        return True
    except:
        return False
