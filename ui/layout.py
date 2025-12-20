from nicegui import ui
from typing import Dict, Callable

def create_layout(nav_funcs: Dict[str, Callable]) -> ui.column:
    """
    Builds the main cockpit frame: Header, Sidebar, and Content Container.
    """
    # ---------------------------------------------------------
    # 1. HEADER (The Status Bar)
    # ---------------------------------------------------------
    with ui.header().classes('bg-slate-900 text-white shadow-lg items-center'):
        # Menu Button (toggles sidebar)
        ui.button(on_click=lambda: left_drawer.toggle(), icon='menu').props('flat color=white')
        
        # Title
        ui.label('SALLE BLANCHE LAB').classes('text-xl font-bold tracking-widest ml-2')
        
        ui.space() 
        
        # Status Badge
        with ui.row().classes('items-center gap-2'):
            ui.icon('verified', color='yellow').classes('text-lg')
            ui.label('GOLD CHASE 2025').classes('text-xs text-yellow-500 font-mono font-bold')

    # ---------------------------------------------------------
    # 2. SIDEBAR (Navigation & Doctrine)
    # ---------------------------------------------------------
    with ui.left_drawer(value=True).classes('bg-slate-800 text-white') as left_drawer:
        with ui.column().classes('w-full p-4 gap-4'):
            
            # A. Navigation Modules
            ui.label('MODULES').classes('text-slate-500 text-xs font-bold tracking-wider')
            
            with ui.column().classes('gap-2 w-full'):
                ui.button('DASHBOARD', icon='analytics', on_click=nav_funcs['dashboard']).props('flat align=left').classes('w-full text-slate-200 hover:bg-slate-700')
                ui.button('LIVE COCKPIT', icon='casino', on_click=nav_funcs['cockpit']).props('flat align=left').classes('w-full text-slate-200 hover:bg-slate-700')
                ui.button('SIMULATOR', icon='science', on_click=nav_funcs['simulator']).props('flat align=left').classes('w-full text-slate-200 hover:bg-slate-700')
                
                # UPDATED: Changed Name and Icon
                ui.button('OUR LOG', icon='history_edu', on_click=nav_funcs['logs']).props('flat align=left').classes('w-full text-slate-200 hover:bg-slate-700')
            
            ui.separator().classes('bg-slate-700 my-2')
            
            # B. Memory Cheat Codes
            ui.label('DOCTRINE').classes('text-slate-500 text-xs font-bold tracking-wider')
            
            with ui.card().classes('bg-slate-900 w-full p-3 border-l-4 border-red-500'):
                ui.label('"Act Your Wage"').classes('text-xs italic text-slate-300')
                ui.label('No Tier 3 bets with Tier 2 bankroll.').classes('text-[10px] text-slate-500')

            with ui.card().classes('bg-slate-900 w-full p-3 border-l-4 border-blue-500'):
                ui.label('"Reset to Base"').classes('text-xs italic text-slate-300')
                ui.label('After every press — win or lose.').classes('text-[10px] text-slate-500')

    # ---------------------------------------------------------
    # 3. MAIN CONTENT CONTAINER
    # ---------------------------------------------------------
    content = ui.column().classes('w-full items-center min-h-screen bg-slate-950')
    
    return content
