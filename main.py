from nicegui import ui, app
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
def nav_cockpit(): render_page(show_scorecard)
def nav_simulator(): render_page(show_simulator)
def nav_logs(): render_page(show_session_log)

# 3. Build the UI
nav_map = {
    'dashboard': nav_dashboard,
    'cockpit': nav_cockpit,
    'simulator': nav_simulator,
    'logs': nav_logs
}

content_container = create_layout(nav_map)

# 4. Load Default Page
with content_container:
    show_dashboard()

# 5. Launch the App
# CRITICAL: This must be at the far left (no indentation)
# CRITICAL: Do NOT put this inside an if __name__ == "__main__" block
ui.run(
    title='Salle Blanche Lab',
    viewport='width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no',
    favicon='♠️',
    dark=True,
    reconnect_timeout=10.0
)
