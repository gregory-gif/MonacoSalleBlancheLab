from nicegui import ui, app
from ui.layout import create_layout
from ui.dashboard import show_dashboard
from ui.scorecard import show_scorecard
from ui.simulator import show_simulator
from ui.session_log import show_session_log

content_container = None

def render_page(target_func):
    if content_container:
        content_container.clear()
        with content_container:
            try:
                target_func()
            except Exception as e:
                ui.label(f"Error: {str(e)}").classes('text-red-500')

def nav_dashboard(): render_page(show_dashboard)
def nav_cockpit(): render_page(show_scorecard)
def nav_simulator(): render_page(show_simulator)
def nav_logs(): render_page(show_session_log)

nav_map = {
    'dashboard': nav_dashboard,
    'cockpit': nav_cockpit,
    'simulator': nav_simulator,
    'logs': nav_logs
}

content_container = create_layout(nav_map)

with content_container:
    show_dashboard()

print("STARTING NICEGUI APP...")

ui.run(
    title='Salle Blanche Lab',
    viewport='width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no',
    favicon='♠️',
    dark=True,
    reconnect_timeout=10.0
)
