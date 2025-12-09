import os
from nicegui import ui
from ui.layout import create_layout
from ui.dashboard import show_dashboard
from ui.scorecard import show_scorecard
from ui.simulator import show_simulator
from ui.session_log import show_session_log

# 1. Navigation State
content_container = None

def render_page(target_func):
    if content_container:
        content_container.clear()
        with content_container:
            try:
                target_func()
            except Exception as e:
                ui.label(f"Error loading module: {str(e)}").classes('text-red-500')

# 2. Navigation Callbacks
def nav_dashboard(): render_page(show_dashboard)
def nav_simulator(): render_page(show_simulator) # Moved Up
def nav_cockpit(): render_page(show_scorecard)   # Moved Down
def nav_logs(): render_page(show_session_log)

# 3. Build the UI
# The order here determines the order in the sidebar if generated dynamically,
# but mostly it maps the keys.
nav_map = {
    'dashboard': nav_dashboard,
    'simulator': nav_simulator, # Reordered
    'cockpit': nav_cockpit,     # Reordered
    'logs': nav_logs
}

content_container = create_layout(nav_map)

# 4. Load Default Page
with content_container:
    show_dashboard()

print("STARTING NICEGUI APP...")

# 5. Launch the App (Native Mode)
ui.run(
    title='Salle Blanche Lab',
    viewport='width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no',
    favicon='♠️',
    dark=True,
    reconnect_timeout=10.0,
    host='0.0.0.0',
    port=int(os.environ.get('PORT', 8080))
)
