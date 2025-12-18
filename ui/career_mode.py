from nicegui import ui
import plotly.graph_objects as go
import numpy as np
import asyncio
import traceback
from copy import deepcopy

from engine.strategy_rules import SessionState, BaccaratStrategist, PlayMode, StrategyOverrides, BetStrategy
from engine.tier_params import get_tier_for_ga, generate_tier_map
from utils.persistence import load_profile

# SBM LOYALTY TIERS (Reference)
SBM_TIERS = {'Silver': 5000, 'Gold': 22500, 'Platinum': 175000}

class CareerWorker:
    @staticmethod
    def run_session(current_ga, overrides, tier_map, use_ratchet, penalty_mode, active_level, mode):
        # Re-using the core physics logic locally to avoid circular dependencies or import errors
        tier = get_tier_for_ga(current_ga, tier_map, active_level, mode)
        
        is_active_penalty = penalty_mode and overrides.penalty_box_enabled
        if is_active_penalty:
            flat_bet = 100 
            from engine.tier_params import TierConfig
            tier = TierConfig(level=tier.level, min_ga=0, max_ga=9999999, base_unit=flat_bet, press_unit=flat_bet, stop_loss=tier.stop_loss, profit_lock=tier.profit_lock, catastrophic_cap=tier.catastrophic_cap)
            session_overrides = deepcopy(overrides)
            session_overrides.ratchet_enabled = False
            session_overrides.press_trigger_wins = 999
        else:
            session_overrides = overrides

        # Ratchet Logic Check
        if use_ratchet and not is_active_penalty:
            # Ensure profit lock is set if overrides didn't have it
            if session_overrides.profit_lock_units <= 0: session_overrides.profit_lock_units = 1000

        state = SessionState(tier=tier, overrides=session_overrides)
        state.current_shoe = 1
        
        import random
        volume = 0
        
        while state.current_shoe <= session_overrides.shoes_per_session and state.mode != PlayMode.STOPPED:
            decision = BaccaratStrategist.get_next_decision(state)
            if decision['mode'] == PlayMode.STOPPED: break
            
            bet = decision['bet_amount']
            volume += bet
            
            # Ratchet Stop Check
            if use_ratchet and not is_active_penalty:
                if state.session_pnl <= state.locked_profit and state.locked_profit > -9999: break

            # Hand Physics
            rnd = random.random()
            won = False
            pnl_change = 0
            is_tie = False
            
            if session_overrides.bet_strategy == BetStrategy.BANKER:
                prob_win = 0.4586; prob_loss = 0.4462; payout = 0.95 
            else:
                prob_win = 0.4462; prob_loss = 0.4586; payout = 1.0  
            
            if rnd < prob_win: won = True; pnl_change = bet * payout
            elif rnd < (prob_win + prob_loss): won = False; pnl_change = -bet
            else: is_tie = True; pnl_change = 0

            if not is_tie: BaccaratStrategist.update_state_after_hand(state, won, pnl_change)
            else: state.hands_played_in_shoe += 1

            if state.hands_played_in_shoe >= 80:
                state.current_shoe += 1
                state.hands_played_in_shoe = 0
                state.current_press_streak = 0

        return state.session_pnl, volume, tier.level, state.hands_played_total

    @staticmethod
    def run_compound_career(sequence_config, start_ga, total_years, sessions_per_year):
        # sequence_config is a list of dicts: {'strategy_name': '...', 'target_ga': 10000, 'config': {...}}
        
        current_ga = start_ga
        current_leg_idx = 0
        active_config = sequence_config[0]['config']
        active_strategy_name = sequence_config[0]['strategy_name']
        active_target = sequence_config[0]['target_ga']
        
        # Hydrate the first strategy params
        active_overrides, active_tier_map, active_safety, active_mode, active_ratchet, active_penalty = CareerWorker._extract_params(active_config)
        
        trajectory = []
        log = []
        months = total_years * 12
        active_level = 1
        
        # Running Stats
        running_hands = 0
        strategies_used = []
        
        for m in range(months):
            # 1. CHECK FOR PROMOTION
            # If we hit the target of the current leg, we graduate to the next leg
            if current_leg_idx < len(sequence_config) - 1:
                # We have a next leg available
                if current_ga >= active_target:
                    current_leg_idx += 1
                    new_leg = sequence_config[current_leg_idx]
                    
                    # Log the promotion
                    log.append({
                        'month': m+1, 
                        'event': 'PROMOTION', 
                        'details': f"Graduated from {active_strategy_name} to {new_leg['strategy_name']} @ €{current_ga:,.0f}"
                    })
                    
                    # Swap Engines
                    active_strategy_name = new_leg['strategy_name']
                    active_config = new_leg['config']
                    active_target = new_leg['target_ga']
                    active_overrides, active_tier_map, active_safety, active_mode, active_ratchet, active_penalty = CareerWorker._extract_params(active_config)
                    strategies_used.append(active_strategy_name)

            # 2. RUN MONTHLY SESSIONS
            # Calculate sessions for this month
            sessions_this_month = sessions_per_year // 12
            if m % 12 < (sessions_per_year % 12): sessions_this_month += 1
            
            monthly_pnl = 0
            
            # Insolvency Check
            if current_ga < 100:
                log.append({'month': m+1, 'event': 'INSOLVENT', 'details': 'Bankroll < €100'})
                trajectory.append(current_ga)
                continue # Skip playing, you are broke

            for _ in range(sessions_this_month):
                pnl, vol, used_lvl, hands = CareerWorker.run_session(
                    current_ga, active_overrides, active_tier_map, active_ratchet, active_penalty, active_level, active_mode
                )
                current_ga += pnl
                monthly_pnl += pnl
                running_hands += hands
                active_level = used_lvl # Persist tier state
            
            # 3. APPLY ECOSYSTEM (Tax/Holiday from CURRENT strategy settings)
            # Use safe defaults if keys missing
            tax_rate = active_config.get('eco_tax_rate', 25)
            tax_thresh = active_config.get('eco_tax_thresh', 12500)
            use_tax = active_config.get('eco_tax', False)
            
            if use_tax and current_ga > tax_thresh:
                tax = (current_ga - tax_thresh) * (tax_rate / 100.0)
                current_ga -= tax
            
            trajectory.append(current_ga)
            
            # Log periodic status
            if m % 12 == 0 or m == months-1:
                log.append({
                    'month': m+1, 
                    'event': 'STATUS', 
                    'details': f"Bal: €{current_ga:,.0f} | Strat: {active_strategy_name}"
                })

        return trajectory, log, current_ga

    @staticmethod
    def _extract_params(config):
        # Helper to unpack saved config dict into engine objects
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
    
    # State
    legs = [] # List of {strategy: name, target: value}
    
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
        
        # Load Configs
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
        
        # Run Sim (Single Thread for now for simplicity)
        traj, log, final_ga = await asyncio.to_thread(
            CareerWorker.run_compound_career, 
            sequence_config, start_ga, years, sessions
        )
        
        # Render Results
        progress.set_visibility(False)
        with results_area:
            ui.label(f"FINAL RESULT: €{final_ga:,.0f}").classes('text-3xl font-black text-white mb-4')
            
            # Chart
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=traj, mode='lines', name='Balance', line=dict(color='#4ade80', width=2)))
            
            # Add Threshold Lines
            for leg in legs[:-1]:
                fig.add_hline(y=leg['target'], line_dash="dash", line_color="yellow", annotation_text=f"Switch @ {leg['target']}")
                
            fig.update_layout(title='Career Trajectory', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'))
            ui.plotly(fig).classes('w-full h-64')
            
            # Event Log
            with ui.expansion('Career Event Log', icon='history').classes('w-full bg-slate-800'):
                for l in log:
                    color = "text-yellow-400" if l['event'] == 'PROMOTION' else "text-slate-400"
                    ui.label(f"M{l['month']} | {l['event']}: {l['details']}").classes(f'text-xs {color}')

    # --- UI LAYOUT ---
    with ui.column().classes('w-full max-w-4xl mx-auto gap-6 p-4'):
        ui.label('CAREER SIMULATOR (MULTI-STAGE)').classes('text-2xl font-light text-purple-300')
        ui.label('Chain multiple strategies together to simulate a progressive career.').classes('text-sm text-slate-500 -mt-4')
        
        with ui.grid(columns=2).classes('w-full gap-6'):
            # LEFT: CONTROLS
            with ui.card().classes('w-full bg-slate-900 p-4'):
                ui.label('1. BUILD YOUR SEQUENCE').classes('font-bold text-white mb-2')
                
                # Load Strategies
                profile = load_profile()
                saved = list(profile.get('saved_strategies', {}).keys())
                
                select_strat = ui.select(saved, label='Select Strategy').classes('w-full')
                ui.label('Target Bankroll to Upgrade (Ignored for last leg)').classes('text-xs text-slate-500 mt-2')
                slider_target = ui.slider(min=5000, max=100000, step=1000, value=10000).props('color=yellow')
                ui.label().bind_text_from(slider_target, 'value', lambda v: f'Target: €{v:,.0f}')
                
                ui.button('ADD LEG', on_click=add_leg).props('icon=add color=purple').classes('w-full mt-4')
                
                ui.separator().classes('bg-slate-700 my-4')
                
                ui.label('2. GLOBAL SETTINGS').classes('font-bold text-white mb-2')
                slider_start_ga = ui.slider(min=1000, max=50000, value=2000).props('color=green'); ui.label().bind_text_from(slider_start_ga, 'value', lambda v: f'Start: €{v}')
                slider_years = ui.slider(min=1, max=20, value=5).props('color=blue'); ui.label().bind_text_from(slider_years, 'value', lambda v: f'{v} Years')
                slider_freq = ui.slider(min=10, max=100, value=20).props('color=blue'); ui.label().bind_text_from(slider_freq, 'value', lambda v: f'{v} Sessions/Year')
                
                ui.button('RUN CAREER', on_click=run_simulation).props('icon=play_arrow color=green size=lg').classes('w-full mt-6')

            # RIGHT: SEQUENCE VIEW
            with ui.column().classes('w-full'):
                ui.label('CAREER PATH').classes('font-bold text-white mb-2')
                legs_container = ui.column().classes('w-full')
                progress = ui.linear_progress().props('indeterminate color=purple').classes('w-full'); progress.set_visibility(False)
                results_area = ui.column().classes('w-full')

    refresh_leg_ui()
