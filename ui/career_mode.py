from nicegui import ui
import plotly.graph_objects as go
import numpy as np
import asyncio
import traceback
from copy import deepcopy

# --- CRITICAL INTEGRATION ---
# We import the physics engine from the main simulator to ensure 100% consistency.
# If the Main Simulator works, this MUST work.
from ui.simulator import SimulationWorker
from engine.strategy_rules import SessionState, BaccaratStrategist, PlayMode, StrategyOverrides, BetStrategy
from engine.tier_params import get_tier_for_ga, generate_tier_map
from utils.persistence import load_profile

class CareerManager:
    @staticmethod
    def run_compound_career(sequence_config, start_ga, total_years, sessions_per_year):
        # sequence_config is a list of dicts: {'strategy_name': '...', 'target_ga': 10000, 'config': {...}}
        
        current_ga = start_ga
        current_leg_idx = 0
        
        # Load Initial Strategy
        active_config = sequence_config[0]['config']
        active_strategy_name = sequence_config[0]['strategy_name']
        active_target = sequence_config[0]['target_ga']
        
        # Hydrate Params
        overrides, tier_map, safety, mode, use_ratch, use_penalty = CareerManager._extract_params(active_config)
        
        trajectory = []
        log = []
        months = total_years * 12
        active_level = 1
        
        # Running Stats
        running_hands = 0
        strategies_used = [active_strategy_name]
        
        for m in range(months):
            # 1. CHECK FOR PROMOTION (Switch Strategy?)
            if current_leg_idx < len(sequence_config) - 1:
                if current_ga >= active_target:
                    # PROMOTE!
                    current_leg_idx += 1
                    new_leg = sequence_config[current_leg_idx]
                    
                    log.append({
                        'month': m+1, 
                        'event': 'PROMOTION', 
                        'details': f"GRADUATED: {active_strategy_name} -> {new_leg['strategy_name']} (Bal: €{current_ga:,.0f})"
                    })
                    
                    # Hot Swap the Engine
                    active_strategy_name = new_leg['strategy_name']
                    active_config = new_leg['config']
                    active_target = new_leg['target_ga']
                    overrides, tier_map, safety, mode, use_ratch, use_penalty = CareerManager._extract_params(active_config)
                    strategies_used.append(active_strategy_name)
                    
                    # Reset Tier Level for new strategy? 
                    # Usually better to check where we fit in the new map
                    temp_tier = get_tier_for_ga(current_ga, tier_map, 1, mode)
                    active_level = temp_tier.level

            # 2. RUN MONTHLY SESSIONS
            sessions_this_month = sessions_per_year // 12
            if m % 12 < (sessions_per_year % 12): sessions_this_month += 1
            
            # Insolvency Check
            if current_ga < 100:
                # We do not log 1000 times. Just once.
                if len(log) == 0 or log[-1]['event'] != 'INSOLVENT':
                    log.append({'month': m+1, 'event': 'INSOLVENT', 'details': 'Bankroll < €100. Game Over.'})
                trajectory.append(current_ga)
                continue 

            for _ in range(sessions_this_month):
                # EXECUTE SESSION using the MAIN SIMULATOR ENGINE
                # This ensures consistency with the "Lab" results
                pnl, vol, used_lvl, hands = SimulationWorker.run_session(
                    current_ga, overrides, tier_map, use_ratch, use_penalty, active_level, mode
                )
                
                current_ga += pnl
                running_hands += hands
                active_level = used_lvl 
            
            # 3. APPLY ECOSYSTEM (Tax/Holiday)
            tax_rate = active_config.get('eco_tax_rate', 25)
            tax_thresh = active_config.get('eco_tax_thresh', 12500)
            use_tax = active_config.get('eco_tax', False)
            
            if use_tax and current_ga > tax_thresh:
                tax = (current_ga - tax_thresh) * (tax_rate / 100.0)
                current_ga -= tax
            
            trajectory.append(current_ga)
            
            # Periodic Logging
            if m % 12 == 0:
                log.append({
                    'month': m+1, 
                    'event': 'STATUS', 
                    'details': f"Year {(m//12)+1} | €{current_ga:,.0f} | {active_strategy_name}"
                })

        return trajectory, log, current_ga

    @staticmethod
    def _extract_params(config):
        # Maps saved config dict -> Simulation Engine Objects
        mode = config.get('tac_mode', 'Standard')
        safety = config.get('tac_safety', 25)
        
        tier_map = generate_tier_map(safety, mode=mode)
        
        overrides = StrategyOverrides(
            iron_gate_limit=config.get('tac_iron', 3),
            stop_loss_units=config.get('risk_stop', 10),
            profit_lock_units=config.get('risk_prof', 10),
            press_trigger_wins=config.get('tac_press', 1),
            press_depth=config.get('tac_depth', 3),
            ratchet_enabled=config.get('risk_ratch', False),
            ratchet_mode=config.get('risk_ratch_mode', 'Standard'),
            shoes_per_session=config.get('tac_shoes', 3),
            bet_strategy=BetStrategy.BANKER if config.get('tac_bet', 'Banker') == 'Banker' else BetStrategy.PLAYER,
            penalty_box_enabled=config.get('tac_penalty', True)
        )
        
        use_ratchet = config.get('risk_ratch', False)
        penalty_mode = config.get('tac_penalty', True)
        
        return overrides, tier_map, safety, mode, use_ratchet, penalty_mode

def show_career_mode():
    
    legs = [] 
    
    def refresh_leg_ui():
        legs_container.clear()
        with legs_container:
            for i, leg in enumerate(legs):
                with ui.card().classes('w-full bg-slate-800 p-2 mb-2'):
                    with ui.row().classes('items-center justify-between w-full'):
                        ui.label(f"LEG {i+1}: {leg['strategy']}").classes('text-lg font-bold text-white')
                        ui.button(icon='delete', on_click=lambda idx=i: remove_leg(idx)).props('flat color=red dense')
                    
                    if i < len(legs) - 1:
                        ui.label(f"Play until Bankroll >= €{leg['target']:,.0f}").classes('text-sm text-yellow-400')
                        ui.icon('arrow_downward').classes('text-slate-500 mx-auto my-1')
                    else:
                        ui.label("Final Leg (Plays until End of Time)").classes('text-sm text-green-400')

    def add_leg():
        strat = select_strat.value
        target = slider_target.value
        if not strat:
            ui.notify('Please select a strategy first', type='warning')
            return
        
        legs.append({'strategy': strat, 'target': target})
        refresh_leg_ui()

    def remove_leg(index):
        legs.pop(index)
        refresh_leg_ui()

    async def run_simulation():
        if not legs:
            ui.notify('Add at least one Strategy Leg!', type='negative')
            return
            
        progress.set_visibility(True)
        results_area.clear()
        
        profile = load_profile()
        saved_strats = profile.get('saved_strategies', {})
        
        sequence_config = []
        for leg in legs:
            cfg = saved_strats.get(leg['strategy'])
            if not cfg:
                ui.notify(f"Strategy {leg['strategy']} not found!", type='negative')
                return
            sequence_config.append({
                'strategy_name': leg['strategy'],
                'target_ga': leg['target'],
                'config': cfg
            })
            
        start_ga = slider_start_ga.value
        years = slider_years.value
        sessions = slider_freq.value
        
        traj, log, final_ga = await asyncio.to_thread(
            CareerManager.run_compound_career, 
            sequence_config, start_ga, years, sessions
        )
        
        progress.set_visibility(False)
        with results_area:
            # Score
            res_color = "text-green-400" if final_ga >= start_ga else "text-red-400"
            ui.label(f"FINAL: €{final_ga:,.0f}").classes(f'text-4xl font-black {res_color} mb-4')
            
            # Chart
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=traj, mode='lines', name='Balance', line=dict(color='#4ade80', width=2)))
            
            # Draw lines for leg targets
            for leg in legs[:-1]:
                fig.add_hline(y=leg['target'], line_dash="dash", line_color="yellow", annotation_text=f"Switch @ {leg['target']}")
                
            fig.update_layout(title='Career Trajectory (Single Universe)', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'))
            ui.plotly(fig).classes('w-full h-64')
            
            # Log
            with ui.expansion('Career Event Log', icon='history').classes('w-full bg-slate-800'):
                for l in log:
                    color = "text-yellow-400" if l['event'] == 'PROMOTION' else "text-slate-400"
                    if l['event'] == 'INSOLVENT': color = "text-red-500 font-bold"
                    ui.label(f"M{l['month']} | {l['event']}: {l['details']}").classes(f'text-xs {color}')

    # --- UI LAYOUT ---
    with ui.column().classes('w-full max-w-4xl mx-auto gap-6 p-4'):
        ui.label('CAREER SIMULATOR (MULTI-STAGE)').classes('text-2xl font-light text-purple-300')
        ui.label('Chain strategies. Example: "Grinder" to €10k -> "Titan" to Infinity.').classes('text-sm text-slate-500 -mt-4')
        
        with ui.grid(columns=2).classes('w-full gap-6'):
            # LEFT: CONTROLS
            with ui.card().classes('w-full bg-slate-900 p-4'):
                ui.label('1. BUILD SEQUENCE').classes('font-bold text-white mb-2')
                
                profile = load_profile()
                saved = list(profile.get('saved_strategies', {}).keys())
                
                select_strat = ui.select(saved, label='Select Strategy').classes('w-full')
                ui.label('Target Bankroll to Upgrade').classes('text-xs text-slate-500 mt-2')
                slider_target = ui.slider(min=5000, max=100000, step=1000, value=10000).props('color=yellow')
                ui.label().bind_text_from(slider_target, 'value', lambda v: f'Switch @ €{v:,.0f}')
                
                ui.button('ADD LEG', on_click=add_leg).props('icon=add color=purple').classes('w-full mt-4')
                
                ui.separator().classes('bg-slate-700 my-4')
                
                ui.label('2. GLOBAL SETTINGS').classes('font-bold text-white mb-2')
                slider_start_ga = ui.slider(min=1000, max=50000, value=2000).props('color=green'); ui.label().bind_text_from(slider_start_ga, 'value', lambda v: f'Start: €{v}')
                slider_years = ui.slider(min=1, max=20, value=5).props('color=blue'); ui.label().bind_text_from(slider_years, 'value', lambda v: f'{v} Years')
                slider_freq = ui.slider(min=10, max=100, value=20).props('color=blue'); ui.label().bind_text_from(slider_freq, 'value', lambda v: f'{v} Sess/Yr')
                
                ui.button('RUN CAREER', on_click=run_simulation).props('icon=play_arrow color=green size=lg').classes('w-full mt-6')

            # RIGHT: SEQUENCE VIEW
            with ui.column().classes('w-full'):
                ui.label('CAREER PATH').classes('font-bold text-white mb-2')
                legs_container = ui.column().classes('w-full')
                progress = ui.linear_progress().props('indeterminate color=purple').classes('w-full'); progress.set_visibility(False)
                results_area = ui.column().classes('w-full')

    refresh_leg_ui()
