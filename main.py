from nicegui import ui
import traceback

# ==============================================================================
# MODULE IMPORTS
# ==============================================================================
# We import the new Tracker as 'show_tracker' for consistency
from ui.tracker import render_page as show_tracker  
from ui.dashboard import show_dashboard
from ui.simulator import show_simulator
from ui.career_mode import show_career_mode
from ui.roulette_sim import show_roulette_sim

# ==============================================================================
# 1. APP CONFIGURATION
# ==============================================================================
ui.dark_mode().enable()

# ==============================================================================
# 2. CONTENT CONTAINER
# ==============================================================================
# This container holds the active page content
content = ui.column().classes('w-full items-center')

# --- SAFE LOADER DECORATOR ---
# Prevents the "White Page of Death" by catching errors during module loading
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
    # This is the new "Captain's Log" (Tracker + Ledger)
    show_tracker()

@safe_load
def load_dashboard():
    # Existing financial dashboard
    show_dashboard()

@safe_load
def load_simulator():
    # Baccarat Simulator
    show_simulator()

@safe_load
def load_career():
    # Career/Life Simulator
    show_career_mode()

@safe_load
def load_roulette():
    # Roulette Simulator
    show_roulette_sim()

# ==============================================================================
# 3. LAYOUT & SIDEBAR
# ==============================================================================
with ui.header().classes('bg-slate-900 text-white shadow-lg items-center'):
    ui.button(icon='menu', on_click=lambda: left_drawer.toggle()).props('flat color=white')
    ui.label('SALLE BLANCHE LAB').classes('text-xl font-bold tracking-widest ml-2')
    ui.space()
    with ui.row().classes('items-center gap-2'):
        ui.icon('verified', color='yellow').classes('text-lg')
        ui.label('GOLD CHASE 2025').classes('text-xs text-yellow-500 font-mono font-bold')

with ui.left_drawer(value=True).classes('bg-slate-800 text-white') as left_drawer:
    with ui.column().classes('w-full p-4 gap-4'):
        
        ui.label('OPERATIONS').classes('text-slate-500 text-xs font-bold tracking-wider')
        with ui.column().classes('gap-2 w-full'):
            # NAVIGATION
            # New Home Page: Captain's Log
            ui.button("CAPTAIN'S LOG", icon='edit_note', on_click=load_tracker).props('flat align=left').classes('w-full text-amber-400 font-bold bg-slate-700/50 hover:bg-slate-700')
            
            ui.button('FINANCIALS', icon='analytics', on_click=load_dashboard).props('flat align=left').classes('w-full text-slate-200 hover:bg-slate-700')
            
            ui.separator().classes('bg-slate-700 my-2 opacity-50')
            
            ui.button('BACCARAT LAB', icon='science', on_click=load_simulator).props('flat align=left').classes('w-full text-slate-200 hover:bg-slate-700')
            ui.button('ROULETTE LAB', icon='donut_large', on_click=load_roulette).props('flat align=left').classes('w-full text-slate-200 hover:bg-slate-700')
            ui.button('CAREER SIM', icon='route', on_click=load_career).props('flat align=left').classes('w-full text-slate-200 hover:bg-slate-700')
        
        ui.separator().classes('bg-slate-700 my-2')
        
        ui.label('DOCTRINE').classes('text-slate-500 text-xs font-bold tracking-wider')
        with ui.card().classes('bg-slate-900 w-full p-3 border-l-4 border-red-500'):
            ui.label('"Act Your Wage"').classes('text-xs italic text-slate-300')
        with ui.card().classes('bg-slate-900 w-full p-3 border-l-4 border-blue-500'):
            ui.label('"Reset to Base"').classes('text-xs italic text-slate-300')

# ==============================================================================
# 4. INITIAL STARTUP
# ==============================================================================
# Load the Tracker immediately (No more Live Cockpit)
load_tracker()

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title='Salle Blanche Lab', port=8080, reload=True, favicon='♠️', show=True)
