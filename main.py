from nicegui import ui, app
import traceback

# MODULE IMPORTS
from auth import setup_auth
from ui.tracker import render_page as show_tracker
from ui.simulator import show_simulator
from ui.career_mode import show_career_mode
from ui.roulette_sim import show_roulette_sim

# ==============================================================================
# 1. SECURITY SETUP
# ==============================================================================
# Initialize the login pages
setup_auth()

# ==============================================================================
# 2. MAIN APP PAGE
# ==============================================================================
@ui.page('/')
def main_page():
    # --- THE GATEKEEPER CHECK ---
    # If the user is NOT authenticated, kick them to login immediately.
    if not app.storage.user.get('authenticated', False):
        ui.open('/login')
        return # Stop loading the rest of the page!

    # --- IF WE PASS, LOAD THE APP ---
    ui.dark_mode().enable()
    
    # --- Content Container ---
    content = ui.column().classes('w-full items-center')

    # --- Module Loader Logic ---
    def load_module(module_func):
        content.clear()
        try:
            with content:
                module_func()
        except Exception as e:
            ui.notify(f"Error loading module: {str(e)}", type='negative')
            with content:
                ui.label(f"ERROR: {str(e)}").classes('text-red-500')

    # --- Header ---
    with ui.header().classes('bg-slate-900 text-white shadow-lg items-center'):
        ui.button(icon='menu', on_click=lambda: left_drawer.toggle()).props('flat color=white')
        ui.label('SALLE BLANCHE LAB').classes('text-xl font-bold tracking-widest ml-2')
        ui.space()
        ui.button(icon='logout', on_click=lambda: ui.open('/logout')).props('flat color=white round').tooltip('Logout')

    # --- Sidebar ---
    with ui.left_drawer(value=True).classes('bg-slate-800 text-white') as left_drawer:
        with ui.column().classes('w-full p-4 gap-4'):
            ui.label('OPERATIONS').classes('text-slate-500 text-xs font-bold tracking-wider')
            with ui.column().classes('gap-2 w-full'):
                
                ui.button("CAPTAIN'S LOG", icon='edit_note', 
                          on_click=lambda: load_module(show_tracker)
                         ).props('flat align=left').classes('w-full text-amber-400 font-bold bg-slate-700/50 hover:bg-slate-700')
                
                ui.separator().classes('bg-slate-700 my-2 opacity-50')
                
                ui.button('BACCARAT LAB', icon='science', 
                          on_click=lambda: load_module(show_simulator)
                         ).props('flat align=left').classes('w-full text-slate-200 hover:bg-slate-700')
                
                ui.button('ROULETTE LAB', icon='donut_large', 
                          on_click=lambda: load_module(show_roulette_sim)
                         ).props('flat align=left').classes('w-full text-slate-200 hover:bg-slate-700')
                
                ui.button('CAREER SIM', icon='route', 
                          on_click=lambda: load_module(show_career_mode)
                         ).props('flat align=left').classes('w-full text-slate-200 hover:bg-slate-700')

    # --- Initial Load ---
    load_module(show_tracker)

# ==============================================================================
# 3. RUN
# ==============================================================================
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title='Salle Blanche Lab', port=8080, reload=True, favicon='♠️', show=True, storage_secret='monaco_vault_key')
