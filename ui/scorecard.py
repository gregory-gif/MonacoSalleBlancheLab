from nicegui import ui
from utils.persistence import load_profile, save_profile, log_session_result
from engine.tier_params import get_tier_for_ga

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
                            
                            with ui.card().classes('bg-red-900/30 border border-red-900 p-4 items-center text-center'):
                                ui.label('STOP LOSS (-10u)').classes('text-xs text-red-400 font-bold')
                                ui.label(f'€{data["stop_loss"]:,.0f}').classes('text-3xl font-black text-red-500')

                        # Rules Text
                        with ui.expansion('Engagement Rules', icon='gavel').classes('w-full bg-slate-800 text-slate-400 text-sm'):
                            with ui.column().classes('p-4 gap-2'):
                                ui.markdown('**1. Betting:** Banker Only (or Player Only). Stick to it.')
                                ui.markdown('**2. Pressing:** After 2 Wins, press +1 Unit.')
                                ui.markdown('**3. Iron Gate:** If 3 Losses in a row -> **PAUSE**. Wait for 1 Virtual Win, then restart.')

                        # Ratchet Ladder Visual
                        ui.label('RATCHET LADDER (Mental Checkpoints)').classes('text-xs text-yellow-500 font-bold uppercase mt-2')
                        
                        for step in data['ladder']:
                            with ui.row().classes('w-full justify-between items-center bg-slate-800 p-3 rounded'):
                                # Trigger (Left)
                                with ui.column().classes('gap-0'):
                                    ui.label(f"HIT: €{step['trig_eur']:,.0f}").classes('text-lg font-bold text-green-400')
                                    ui.label(f"(+{step['trigger_u']} Units)").classes('text-xs text-green-700')
                                
                                ui.icon('arrow_forward', color='grey')
                                
                                # Lock (Right)
                                with ui.column().classes('gap-0 items-end'):
                                    lock_val = step['lock_eur']
                                    if isinstance(lock_val, (int, float)):
                                        ui.label(f"LOCK: €{lock_val:,.0f}").classes('text-lg font-bold text-yellow-400')
                                    else:
                                        ui.label(f"{lock_val}").classes('text-lg font-black text-yellow-400')
                                    
                                    lock_u = step['lock_u']
                                    if isinstance(lock_u, (int, float)):
                                        ui.label(f"(+{lock_u} Units)").classes('text-xs text-yellow-700')

                def update_strategy_card(e):
                    try:
                        new_val = float(e.value)
                        state['start_ga'] = new_val # Update state
                        render_strategy_card(new_val)
                    except: pass

                input_start = ui.number(
                    value=db_ga, 
                    format='%.0f', 
                    on_change=update_strategy_card
                ).props('outlined dark prefix="€" input-class="text-2xl font-bold text-white"').classes('w-full')

                # Initial Render
                render_strategy_card(db_ga)

        # --- SECTION B: POST-FLIGHT DEBRIEF ---
        with ui.card().classes('w-full bg-slate-900 border border-slate-700 mt-4'):
            with ui.row().classes('w-full items-center justify-between px-4 py-2 border-b border-slate-800'):
                ui.label('DEBRIEF LOG').classes('text-sm font-bold text-green-400 tracking-widest')
                ui.icon('assignment', color='green').classes('text-xl')

            with ui.column().classes('p-6 w-full gap-6'):
                
                # 1. End Balance
                ui.label('Final Chip Count').classes('text-slate-500 text-xs font-bold uppercase')
                input_end = ui.number(value=db_ga, format='%.0f').props('outlined dark prefix="€" input-class="text-3xl font-black text-green-400"').classes('w-full')
                
                # 2. Volume
                ui.label('Volume (Shoes Played)').classes('text-slate-500 text-xs font-bold uppercase')
                slider_shoes = ui.slider(min=1, max=10, value=3).props('label-always color=blue')
                
                # 3. Submit
                def submit_log():
                    s_val = state['start_ga'] # Get from state dict
                    e_val = input_end.value
                    shoes = slider_shoes.value
                    
                    if s_val is not None and e_val is not None:
                        # 1. Save History
                        log_session_result(float(s_val), float(e_val), int(shoes))
                        
                        # 2. Update Wallet Profile
                        profile['ga'] = float(e_val)
                        save_profile(profile)
                        
                        ui.notify(f'Session Logged! New GA: €{e_val:,.0f}', type='positive')
                        ui.open('/') # Go back to dashboard

                ui.button('COMPLETE MISSION', on_click=submit_log).classes('w-full h-16 text-xl font-bold bg-green-600 hover:bg-green-500 shadow-lg mt-4')
