from nicegui import ui
from utils.persistence import load_profile, save_profile, log_session_result
from engine.tier_params import get_tier_for_ga

def show_scorecard():
    # 1. Load Data
    profile = load_profile()
    db_ga = profile.get('ga', 1700.0)
    
    # State Variables
    state = {
        'start_ga': db_ga,
        'end_ga': db_ga,
        'shoes': 3
    }
    
    # 2. Logic: Calculate Mission Parameters
    def calculate_mission(bankroll):
        tier = get_tier_for_ga(bankroll)
        u = tier.base_unit
        
        return {
            'tier_level': tier.level,
            'base_unit': u,
            'press_unit': tier.press_unit,
            'stop_loss': bankroll - (10 * u),
            'ladder': [
                {'name': 'STEP 1', 'hit': bankroll + (8*u), 'lock': bankroll + (3*u), 'u': '+8u'},
                {'name': 'STEP 2', 'hit': bankroll + (12*u), 'lock': bankroll + (5*u), 'u': '+12u'},
                {'name': 'STEP 3', 'hit': bankroll + (16*u), 'lock': bankroll + (7*u), 'u': '+16u'},
                {'name': 'MAX', 'hit': bankroll + (20*u), 'lock': 'COLOR UP', 'u': '+20u'}
            ]
        }

    # 3. UI Layout
    with ui.column().classes('w-full max-w-3xl mx-auto gap-8 p-4'):
        
        # ==========================================
        # SECTION 1: FLIGHT PLAN (Pre-Session)
        # ==========================================
        with ui.card().classes('w-full bg-slate-900 border border-slate-700'):
            # Header
            with ui.row().classes('w-full items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('flight_takeoff', color='blue').classes('text-2xl')
                    ui.label('FLIGHT PLAN').classes('text-lg font-bold text-blue-400 tracking-widest')
                ui.chip('CONSULT BEFORE PLAY', icon='visibility').props('color=blue-10 text-color=blue-400')

            # Content Container (Refreshes on input change)
            mission_container = ui.column().classes('w-full')

            def render_mission(bankroll):
                mission_container.clear()
                data = calculate_mission(bankroll)
                
                with mission_container:
                    with ui.column().classes('p-6 w-full gap-6'):
                        
                        # --- A. TACTICAL SPECS ---
                        with ui.grid(columns=3).classes('w-full gap-4'):
                            # Tier
                            with ui.column().classes('p-3 bg-slate-800 rounded text-center'):
                                ui.label('ACTIVE TIER').classes('text-xs text-slate-500 font-bold')
                                ui.label(f"Tier {data['tier_level']}").classes('text-xl font-black text-white')
                            # Base Bet
                            with ui.column().classes('p-3 bg-slate-800 rounded text-center'):
                                ui.label('BASE BET').classes('text-xs text-slate-500 font-bold')
                                ui.label(f"€{data['base_unit']}").classes('text-xl font-black text-green-400')
                            # Press
                            with ui.column().classes('p-3 bg-slate-800 rounded text-center'):
                                ui.label('PRESS UNIT').classes('text-xs text-slate-500 font-bold')
                                ui.label(f"+€{data['press_unit']}").classes('text-xl font-black text-yellow-400')

                        ui.separator().classes('bg-slate-800')

                        # --- B. RISK PARAMETERS ---
                        with ui.row().classes('w-full items-center justify-between bg-red-900/20 border border-red-900/50 p-4 rounded'):
                            with ui.column().classes('gap-0'):
                                ui.label('HARD STOP LOSS').classes('text-sm font-bold text-red-400')
                                ui.label('Walk away immediately if stack hits:').classes('text-xs text-red-300 opacity-80')
                            ui.label(f"€{data['stop_loss']:,.0f}").classes('text-3xl font-black text-red-500')

                        # --- C. RATCHET LADDER ---
                        ui.label('PROFIT LADDER (Mental Checkpoints)').classes('text-xs text-slate-500 font-bold uppercase mt-2')
                        
                        with ui.column().classes('w-full gap-2'):
                            for step in data['ladder']:
                                with ui.row().classes('w-full justify-between items-center bg-slate-800 px-4 py-3 rounded'):
                                    # Trigger
                                    with ui.row().classes('items-center gap-3'):
                                        ui.label(step['name']).classes('text-xs font-bold text-slate-600 w-12')
                                        with ui.column().classes('gap-0'):
                                            ui.label(f"Reach €{step['hit']:,.0f}").classes('text-lg font-bold text-white')
                                            ui.label(f"({step['u']})").classes('text-xs text-green-500')
                                    
                                    ui.icon('arrow_right_alt', color='grey')
                                    
                                    # Lock
                                    lock_display = step['lock']
                                    if isinstance(lock_display, (int, float)):
                                        ui.label(f"Lock €{lock_display:,.0f}").classes('text-lg font-bold text-yellow-400')
                                    else:
                                        ui.label(lock_display).classes('text-lg font-black text-yellow-400')

            # Render Initial State
            render_mission(db_ga)

            # Manual Override Expander
            with ui.expansion('Adjust Starting Bankroll', icon='edit').classes('w-full bg-slate-950 text-slate-500 text-sm'):
                with ui.row().classes('p-4 w-full items-center gap-4'):
                    ui.label('Override:').classes('text-xs')
                    ui.number(value=db_ga, format='%.0f', on_change=lambda e: render_mission(float(e.value)))\
                        .props('outlined dark dense').classes('w-32')

        # ==========================================
        # SECTION 2: POST-FLIGHT DEBRIEF (Input)
        # ==========================================
        with ui.card().classes('w-full bg-slate-900 border border-slate-700'):
            with ui.row().classes('w-full items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('assignment', color='green').classes('text-2xl')
                    ui.label('POST-FLIGHT REPORT').classes('text-lg font-bold text-green-400 tracking-widest')
                ui.chip('FILL AFTER SESSION', icon='edit').props('color=green-10 text-color=green-400')

            with ui.column().classes('p-6 w-full gap-8'):
                
                # 1. Result Input
                with ui.column().classes('w-full gap-2'):
                    ui.label('ENDING CHIP COUNT').classes('text-xs font-bold text-slate-400 uppercase')
                    input_end = ui.number(value=db_ga, format='%.0f', placeholder='e.g. 2350').props('outlined dark prefix="€" input-class="text-4xl font-black text-white text-center"').classes('w-full')
                    ui.label('Count your physical chips before cashing out.').classes('text-xs text-slate-600 text-center w-full')

                # 2. Volume Input
                with ui.column().classes('w-full gap-2'):
                    ui.label('VOLUME (SHOES PLAYED)').classes('text-xs font-bold text-slate-400 uppercase')
                    with ui.row().classes('w-full items-center gap-4'):
                        slider_shoes = ui.slider(min=1, max=8, value=3).props('label-always color=blue').classes('flex-grow')
                        ui.icon('repeat', color='blue').classes('text-xl')

                # 3. Submit Button
                def submit_log():
                    # We grab the current value from the rendered mission context or just re-read the input/profile logic
                    # Ideally, if user adjusted start_ga in the expander, we need to capture that.
                    # Simplified: We assume standard flow (Database -> Play -> Result). 
                    # If they manually adjusted start, we assume they updated the dashboard/profile first or we can add state tracking here.
                    
                    # For V1, let's use the DB Start GA.
                    s_val = db_ga 
                    e_val = input_end.value
                    shoes = slider_shoes.value
                    
                    if e_val is not None:
                        # Save History
                        log_session_result(float(s_val), float(e_val), int(shoes))
                        
                        # Update Profile (Wallet)
                        profile['ga'] = float(e_val)
                        save_profile(profile)
                        
                        ui.notify(f'Session Logged! New Balance: €{e_val:,.0f}', type='positive')
                        ui.open('/') # Return to dashboard

                ui.button('LOG SESSION & UPDATE WALLET', on_click=submit_log).classes('w-full h-16 text-lg font-bold bg-green-600 hover:bg-green-500 shadow-xl rounded-lg')

# Alias for main.py import
show_scorecard = show_scorecard
