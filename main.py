from nicegui import ui
from ui.layout import create_layout
from ui.dashboard import show_dashboard
from ui.scorecard import show_scorecard
from ui.simulator import show_simulator
from ui.session_log import show_session_log

# 1. Navigation State
# We need a reference to the content container to clear/update it
content_container = None

def render_page(target_func):
    """
    Clears the main content area and renders the requested module.
    """
    if content_container:
        content_container.clear()
        with content_container:
            try:
                target_func()
            except Exception as e:
                ui.label(f"Error loading module: {str(e)}").classes('text-red-500')

# 2. Navigation Callbacks
# These wrappers are passed to the sidebar buttons in layout.py
def nav_dashboard():
    render_page(show_dashboard)

def nav_cockpit():
    render_page(show_scorecard)

def nav_simulator():
    render_page(show_simulator)

def nav_logs():
    render_page(show_session_log)

# 3. Build the UI
# Map keys to functions (must match keys used in ui/layout.py)
nav_map = {
    'dashboard': nav_dashboard,
    'cockpit': nav_cockpit,
    'simulator': nav_simulator,
    'logs': nav_logs
}

# Create the Shell (Sidebar, Header) and get the Content Container
content_container = create_layout(nav_map)

# 4. Load Default Page (Dashboard)
with content_container:
    show_dashboard()

# 5. Launch the App
# CRITICAL FIX FOR RENDER: 
# ui.run() is called at the module level, NOT inside an 'if __name__ == "__main__":' block.
# This ensures Gunicorn can find and start the application.
ui.run(
    title='Salle Blanche Lab',
    viewport='width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no',
    favicon='♠️',
    dark=True,
    reconnect_timeout=10.0
)
