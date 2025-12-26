from nicegui import ui
from utils.persistence import load_profile
from engine.strategy_rules import StrategyOverrides
from engine.tier_params import generate_tier_map, get_tier_for_ga
from ui.roulette_sim import RouletteWorker
from ui.simulator import BaccaratWorker
import numpy as np
import asyncio

# --- SESSIONS SIM PAGE ---
def show_sessions_sim():
    session_strategies = []  # List of dicts: { 'game': 'Roulette'/'Baccarat', 'strategy': str, 'params': dict }

    def refresh_strategy_ui():
        strategy_container.clear()
        with strategy_container:
            for i, strat in enumerate(session_strategies):
                with ui.row().classes('items-center gap-2'):
                    ui.label(f"{i+1}. {strat['game']} - {strat['strategy']}").classes('text-white')
                    ui.button(icon='delete', on_click=lambda idx=i: remove_strategy(idx)).props('flat color=red dense')

    def add_strategy():
        game = select_game.value
        strat = select_strat.value
        if not game or not strat:
            ui.notify('Select game and strategy', type='warning')
            return
        session_strategies.append({'game': game, 'strategy': strat, 'params': {}})
        refresh_strategy_ui()

    def remove_strategy(idx):
        session_strategies.pop(idx)
        refresh_strategy_ui()

    # --- UI LAYOUT ---
    with ui.column().classes('w-full max-w-4xl mx-auto gap-6 p-4'):
        ui.label('SESSIONS SIMULATOR').classes('text-2xl font-light text-orange-300')
        ui.label('Simulate playing multiple strategies in a single session with a shared bankroll.').classes('text-sm text-slate-500 -mt-4')

        with ui.card().classes('w-full bg-slate-900 p-4'):
            ui.label('1. BUILD SESSION SEQUENCE').classes('font-bold text-white mb-2')
            profile = load_profile()
            saved = list(profile.get('saved_strategies', {}).keys())
            select_game = ui.select(['Roulette', 'Baccarat'], label='Game').classes('w-32')
            select_strat = ui.select(saved, label='Select Strategy').classes('w-full')
            ui.button('ADD TO SESSION', on_click=add_strategy).props('icon=add color=purple').classes('w-full mt-2')
            strategy_container = ui.column().classes('w-full mt-4')
            refresh_strategy_ui()

        with ui.card().classes('w-full bg-slate-900 p-4 mt-4'):
            ui.label('2. SESSION SETTINGS').classes('font-bold text-white mb-2')
            slider_start_bankroll = ui.slider(min=100, max=100000, value=1000).props('color=yellow')
            ui.label().bind_text_from(slider_start_bankroll, 'value', lambda v: f'Starting Bankroll: €{v:,.0f}')
            slider_num_sessions = ui.slider(min=1, max=500, value=20).props('color=cyan')
            ui.label().bind_text_from(slider_num_sessions, 'value', lambda v: f'{v} Sessions')

        # Results area placeholder
        results_area = ui.column().classes('w-full mt-8')
        progress_bar = ui.linear_progress().props('color=green').classes('mt-4')
        progress_bar.set_visibility(False)
        status_label = ui.label('').classes('text-sm text-slate-400 mt-2')

        async def run_sessions_sim():
            if not session_strategies:
                ui.notify('Add at least one strategy to the session.', type='warning')
                return
            
            progress_bar.set_visibility(True)
            progress_bar.set_value(0)
            status_label.set_text('Running simulations...')
            
            num_sessions = slider_num_sessions.value
            start_bankroll = slider_start_bankroll.value
            profile = load_profile()
            saved_strats = profile.get('saved_strategies', {})
            all_results = []
            
            for s in range(num_sessions):
                session_log = []
                bankroll = start_bankroll
                for strat in session_strategies:
                    strat_cfg = saved_strats.get(strat['strategy'])
                    if not strat_cfg:
                        session_log.append({'game': strat['game'], 'strategy': strat['strategy'], 'result': 'NOT FOUND', 'bankroll': bankroll})
                        continue
                    # Prepare overrides and tier map
                    overrides = StrategyOverrides(**strat_cfg)
                    tier_map = generate_tier_map(strat_cfg.get('tac_safety', 25), mode=strat_cfg.get('tac_mode', 'Standard'), game_type=strat['game'], base_bet=strat_cfg.get('tac_base_bet', 10.0))
                    active_level = 1
                    mode = strat_cfg.get('tac_mode', 'Standard')
                    base_bet = strat_cfg.get('tac_base_bet', 10.0)
                    # Simulate
                    if strat['game'] == 'Roulette':
                        pnl, *_ = RouletteWorker.run_session(bankroll, overrides, tier_map, overrides.ratchet_enabled, overrides.penalty_box_enabled, active_level, mode, base_bet)
                    else:
                        pnl, *_ = BaccaratWorker.run_session(bankroll, overrides, tier_map, overrides.ratchet_enabled, overrides.penalty_box_enabled, active_level, mode, base_bet)
                    bankroll += pnl
                    session_log.append({'game': strat['game'], 'strategy': strat['strategy'], 'result': pnl, 'bankroll': bankroll})
                all_results.append({'session': s+1, 'final_bankroll': bankroll, 'log': session_log})
                
                # Update progress
                progress_bar.set_value((s + 1) / num_sessions)
                status_label.set_text(f'Completed {s + 1}/{num_sessions} sessions...')
                await asyncio.sleep(0.01)  # Allow UI to update
            
            progress_bar.set_visibility(False)
            status_label.set_text('Simulation complete!')
            
            # Display results
            results_area.clear()
            with results_area:
                ui.label('SESSION SIM RESULTS').classes('text-lg text-orange-300 font-bold')
                table_rows = []
                for res in all_results:
                    table_rows.append({'Session': res['session'], 'Final Bankroll': f"€{res['final_bankroll']:,.0f}"})
                if table_rows:
                    ui.aggrid({'columnDefs': [{'headerName': 'Session', 'field': 'Session', 'width': 80}, {'headerName': 'Final Bankroll', 'field': 'Final Bankroll', 'width': 120}], 'rowData': table_rows, 'domLayout': 'autoHeight'}).classes('w-full theme-balham-dark')
                # Expandable logs
                for res in all_results:
                    with ui.expansion(f"Session {res['session']} Log", icon='history').classes('w-full bg-slate-800 mt-2'):
                        for entry in res['log']:
                            ui.label(f"{entry['game']} - {entry['strategy']}: Result = {entry['result']} | Bankroll: €{entry['bankroll']:,.0f}").classes('text-xs text-slate-300')

        # Create run button with proper async handler
        ui.button('RUN SESSIONS SIM', on_click=run_sessions_sim).props('icon=play_arrow color=green size=lg').classes('w-full mt-4')

def setup():
    show_sessions_sim()
