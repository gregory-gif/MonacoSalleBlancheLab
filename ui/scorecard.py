from nicegui import ui
from utils.persistence import load_profile, save_profile, log_session_result
from engine.tier_params import get_tier_for_ga

# Dummy class to satisfy legacy imports if needed, 
# though main.py usually imports the function 'show_scorecard'.
# If main.py imports 'Scorecard', we can redirect it.

def show_scorecard():
    # 1. Load Data
    profile = load_profile()
    db_ga = profile.get('ga', 1700.0)
    
    # State Variables (use a simple dict to hold mutable state in closure)
    state = {
        'start_ga': db_ga,
        'end_ga': db_ga,
        'shoes': 3
    }
    
    # 2. Helper to Calculate Strategy Numbers
    def get_strategy_numbers(bankroll):
        tier = get_tier_for_ga(bankroll)
        u = tier.base_unit
        
        return {
            'unit': u,
            'stop_loss': bankroll - (10 * u),
            'ladder': [
                {'trigger_u': 8, 'lock_u': 3, 'trig_eur': bankroll + (8*u), 'lock_eur': bankroll + (3*u)},
                {'trigger_u': 12, 'lock_u': 5, 'trig_eur': bankroll + (12*u), 'lock_eur': bankroll + (5*u)},
                {'trigger_u': 16, 'lock_u': 7, 'trig_eur': bankroll + (16*u), 'lock_eur': bankroll + (7*u)},
                {'trigger_u': 20, 'lock_u': 'MAX', 'trig_eur': bankroll + (20*u), 'lock_eur': 'COLOR UP'}
            ]
        }

    # 3. UI Layout
    with ui.column().classes('w-full max-w-3xl mx-auto gap-6 p-4'):
        
        # --- SECTION A: PRE-FLIGHT BRIEFING ---
        with ui.card().classes('w-full bg-slate-900 border border-slate-700'):
            with ui.row().classes('w-full items-center justify-between px-4 py-2 border-b border-slate-800'):
                ui.label('MISSION BRIEFING').classes('text-sm font-bold text-blue-400 tracking-widest')
                ui.icon('flight_takeoff', color='blue').classes('text-xl')

            with ui.column().classes('p-6 w-full gap-6'):
                # 1. Buy-In Input
                ui.label('1. Confirm Start Bankroll').classes('text-slate-500 text-xs font-bold uppercase')
                
                # We need a container to refresh the strategy card when input changes
                strategy_container = ui.column().classes('w-full gap-4')

                # 2. The Strategy Card (Refreshes dynamically)
                def render_strategy_card(bankroll):
                    strategy_container.clear()
                    data = get_strategy_numbers(bankroll)
                    u = data['unit']
                    
                    with strategy_container:
                        ui.separator().classes('bg-slate-800')
                        
                        # Base Unit & Stop Loss Row
                        with ui.grid(columns=2).classes('w-full gap-4'):
                            with ui.card().classes('bg-slate-800 p-4 items-center text-center'):
                                ui.label('BASE BET').classes('text-xs text-slate-500 font-bold')
                                ui.label(f'€{u}').classes('text-3xl font-black text-white')
                            
                            with ui.card().classes('bg-red-900/3
