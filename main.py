from nicegui import ui, app
import traceback

# ==============================================================================
# SECURITY & MODULE IMPORTS
# ==============================================================================
from auth import AuthMiddleware, setup_auth
from ui.tracker import render_page as show_tracker
from ui.simulator import show_simulator
from ui.career_mode import show_career_mode
from ui.roulette_sim import show_roulette_sim

# ==============================================================================
# 1. APP CONFIGURATION & SECURITY
# ==============================================================================
ui.dark_mode().enable()

# Initialize Security
app.add_middleware(AuthMiddleware)
setup_auth()

# ==============================================================================
# 2. CONTENT CONTAINER
# ==============================================================================
content = ui.column().classes('w-full items-center')

# --- SAFE LOADER DECORATOR ---
def safe_load(func):
    def wrapper():
        content.clear()
        try:
            with content:
                func()
        except Exception as e:
            ui.notify(f"Error loading module: {str(e)}", type='negative')
            print(traceback.format_exc())
            with content:
                ui.label(f"CRASH DETECTED IN MODULE").classes('text-red-500 text-2xl font-bold')
                ui.label(f"{str(e)}").classes('text-red-400')
                ui.label("Check server logs for details.").classes('text-slate-500')
    return wrapper

# --- PAGE LOADERS ---

@safe_load
def load_tracker():
    show_tracker()

@safe_load
def load_simulator():
    show_simulator()

@safe_load
def load_career():
    show_career_mode()

@safe_load
def load_roulette():
    show_roulette_sim()

# ==============================================================================
# 3. LAYOUT & SIDEBAR
# ==============================================================================
# Note: This layout only renders if the user is authenticated (handled by auth.py)
with ui.header().classes('bg-slate-900 text-white shadow-lg items-center'):
    ui.button(icon='menu', on_click=lambda: left_drawer.toggle()).props('flat color=white')
    ui.label('SALLE BLANCHE LAB').classes('text-xl font-bold tracking-widest ml-2')
    ui.space()
    
    # LOGOUT BUTTON
    ui.button(icon='logout', on_click=lambda: ui.open('/logout')).props('flat color=white round').tooltip('Secure Logout')

with ui.left_drawer(value=True).classes('bg-slate-800 text-white') as left_drawer:
    with ui.column().classes('w-full p-4 gap-4'):
        
        ui.label('OPERATIONS').classes('text-slate-500 text-xs font-bold tracking-wider')
        with ui.column().classes('gap-2 w-full'):
            ui.button("CAPTAIN'S LOG", icon='edit_note', on_click=load_tracker).props('flat align=left').classes('w-full text-amber-400 font-bold bg-slate-700/50 hover:bg-slate-700')
            ui.separator().classes('bg-slate-700 my-2 opacity-50')
            ui.button('BACCARAT LAB', icon='science', on_click=load_simulator).props('flat align=left').classes('w-full text-slate-200 hover:bg-slate-700')
            ui.button('ROULETTE LAB', icon='donut_large', on_click=load_roulette).props('flat align=left').classes('w-full text-slate-200 hover:bg-slate-700')
            ui.button('CAREER SIM', icon='route', on_click=load_career).props('flat align=left').classes('w-full text-slate-200 hover:bg-slate-700')

# ==============================================================================
# 4. INITIAL STARTUP
# ==============================================================================
load_tracker()

if __name__ in {"__main__", "__mp_main__"}:
    # CRITICAL: storage_secret is required for the login session to work!
    # Change 'monaco_vault_key' to something random and private.
    ui.run(title='Salle Blanche Lab', port=8080, reload=True, favicon='♠️', show=True, storage_secret='monaco_vault_key')
