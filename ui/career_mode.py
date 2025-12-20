from nicegui import ui
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import asyncio

# WORKERS
from ui.simulator import BaccaratWorker 
from ui.roulette_sim import RouletteWorker

# ENGINE
from engine.tier_params import TierConfig, generate_tier_map, get_tier_for_ga
from utils.persistence import load_profile, save_profile
from engine.strategy_rules import StrategyOverrides, BetStrategy

# SBM LOYALTY TIERS
SBM_TIERS = {
    'Silver': {'points': 5000, 'color': '#C0C0C0'},
    'Gold': {'points': 22500, 'color': '#FFD700'},
    'Platinum': {'points': 175000, 'color': '#E5E4E2'}
}

def show_career_mode():
    profile = load_profile()
    
    # 1. LOAD SAVED STRATEGIES (To use "Good" settings instead of defaults)
    saved_strategies = profile.get('saved_strategies', {})
    strategy_options = list(saved_strategies.keys()) if saved_strategies else ['Default (Safe)']
    
    # Career State
    career_state = {
        'game_type': 'Baccarat', 
        'current_month': profile.get('career_month', 1),
        'current_ga': profile.get('bankroll', 2000),
        'status_points': profile.get('status_points', 0),
        'history': profile.get('career_history', []),
        'is_running': False,
        'active_level': 1 # Tracks ladder progress
    }

    # --- UI COMPONENTS ---
    with ui.column().classes('w-full max-w-4xl mx-auto p-4 gap-6'):
        
        # HEADER
        with ui.card().classes('w-full bg-slate-900 p-6 border-l-8 border-yellow-500'):
            with ui.row().classes('w-full items-center justify-between'):
                with ui.column():
                    ui.label('MY MONACO CAREER').classes('text-xs text-slate-400 font-bold tracking-widest')
                    lbl_status = ui.label('WHITE MEMBER').classes('text-3xl font-black text-white')
                    lbl_points = ui.label('0 / 5,000 Points').classes('text-sm text-yellow-500 font-bold')
                with ui.column().classes('items-end'):
                    lbl_ga = ui.label(f"€{career_state['current_ga']:,.0f}").classes('text-4xl font-black text-green-400')
                    ui.label('General Account (GA)').classes('text-xs text-slate-500')
            progress_bar = ui.linear_progress(value=0.0).props('color=yellow track-color=grey-8').classes('mt-4 h-4 rounded-full')

        # CONTROLS
        with ui.grid(columns=2).classes('w-full gap-6'):
            # MISSION CARD
            with ui.card().classes('w-full bg-slate-800 p-4'):
                ui.label('MONTHLY MISSION').classes('font-bold text-white mb-4')
                
                # Game & Strategy Selector
                select_game = ui.select(['Baccarat', 'Roulette'], value='Baccarat', label='Game').classes('w-full')
                select_strat = ui.select(strategy_options, value=strategy_options[0] if strategy_options else None, label='Active Strategy').classes('w-full')
                
                slider_sessions = ui.slider(min=1, max=20, value=4).props('label-always color=cyan')
                ui.label('Sessions this Month').classes('text-xs text-slate-400 mb-4')
                
                ui.separator().classes('bg-slate-700 mb-4')
                ui.label('CASHFLOW').classes('font-bold text-green-400 mb-2')
                num_contrib = ui.number(label='Deposit (€)', value=300, step=50).classes('w-full')

            # LOG & ACTION
            with ui.column().classes('justify-between gap-4'):
                log_container = ui.scroll_area().classes('w-full h-48 bg-black rounded p-2 text-xs font-mono text-green-300 border border-slate-700')
                btn_play_month = ui.button('PLAY NEXT MONTH', on_click=lambda: run_month()).props('icon=play_arrow color=yellow text-color=black size=xl').classes('w-full shadow-lg')

    # --- LOGIC ---
    def get_strategy_config(name):
        # Pulls the exact settings you saved in the Simulator
        if not name or name not in saved_strategies:
            # Fallback safe default
            return StrategyOverrides(iron_gate_limit=2, stop_loss_units=20, profit_lock_units=10, bet_strategy=BetStrategy.BANKER, shoes_per_session=2)
        
        cfg = saved_strategies[name]
        
        # reconstruct overrides object from dict
        return StrategyOverrides(
            iron_gate_limit=cfg.get('tac_iron', 2),
            stop_loss_units=cfg.get('risk_stop', 20),
            profit_lock_units=cfg.get('risk_prof', 10),
            bet_strategy=getattr(BetStrategy, cfg.get('tac_bet', 'BANKER')) if 'tac_bet' in cfg and cfg['tac_bet'] in BetStrategy.__members__ else cfg.get('tac_bet', 'Red'),
            bet_strategy_2=cfg.get('tac_bet_2', None),
            shoes_per_session=cfg.get('tac_shoes', 2),
            press_trigger_wins=cfg.get('tac_press', 1),
            press_depth=cfg.get('tac_depth', 3),
            ratchet_enabled=cfg.get('risk_ratch', False),
            ratchet_mode=cfg.get('risk_ratch_mode', 'Standard'),
            penalty_box_enabled=cfg.get('tac_penalty', True),
            
            # Roulette Spices
            spice_zero_enabled=cfg.get('spice_zero_en', False),
            spice_zero_trigger=cfg.get('spice_zero_trig', 15),
            spice_zero_max=cfg.get('spice_zero_max', 100),
            spice_zero_cooldown=cfg.get('spice_zero_cool', 1),
            spice_tiers_enabled=cfg.get('spice_tiers_en', False),
            spice_tiers_trigger=cfg.get('spice_tiers_trig', 25),
            spice_tiers_max=cfg.get('spice_tiers_max', 100),
            spice_tiers_cooldown=cfg.get('spice_tiers_cool', 1)
        )

    async def run_month():
        if career_state['is_running']: return
        career_state['is_running'] = True
        btn_play_month.disable()
        
        try:
            # 1. Deposit
            deposit = float(num_contrib.value)
            career_state['current_ga'] += deposit
            log(f"Month {career_state['current_month']}: Deposited €{deposit}")
            
            # 2. Setup Physics
            game = select_game.value
            strat_name = select_strat.value
            overrides = get_strategy_config(strat_name)
            
            # Get saved base bet or default
            saved_cfg = saved_strategies.get(strat_name, {})
            base_bet = saved_cfg.get('tac_base_bet', 10.0) if saved_cfg else 10.0
            mode = saved_cfg.get('tac_mode', 'Standard') if saved_cfg else 'Standard'
            
            # Generate Tier Map
            tier_map = generate_tier_map(safety_factor=25, mode=mode, game_type=game, base_bet=base_bet)
            
            # Determine Starting Tier
            start_tier = get_tier_for_ga(career_state['current_ga'], tier_map, 1, mode, game)
            active_level = start_tier.level
            
            sessions = int(slider_sessions.value)
            monthly_pnl = 0
            monthly_points = 0
            
            log(f"Executing '{strat_name}' ({sessions} sessions)...")

            for s in range(sessions):
                await asyncio.sleep(0.1) 
                
                # RUN THE REAL WORKER (Same as Simulator)
                if game == 'Baccarat':
                    pnl, vol, level, hands = BaccaratWorker.run_session(
                        career_state['current_ga'], overrides, tier_map, 
                        overrides.ratchet_enabled, overrides.penalty_box_enabled, active_level, mode, base_bet
                    )
                else:
                    pnl, vol, level, hands, z, t = RouletteWorker.run_session(
                        career_state['current_ga'], overrides, tier_map, 
                        overrides.ratchet_enabled, overrides.penalty_box_enabled, active_level, mode, base_bet
                    )

                monthly_pnl += pnl
                career_state['current_ga'] += pnl
                
                # Points (10 EUR = 1 Pt approx)
                points = vol * 0.1 
                monthly_points += points
                active_level = level 

            # 3. Commit
            career_state['status_points'] += monthly_points
            
            # Update Profile
            profile['bankroll'] = career_state['current_ga']
            profile['status_points'] = career_state['status_points']
            profile['career_month'] = career_state['current_month'] + 1
            save_profile(profile)
            
            update_status_display()
            log(f"RESULT: PnL: €{monthly_pnl:+,.0f} | Points: +{monthly_points:,.0f}")
            log(f"End Balance: €{career_state['current_ga']:,.0f}")
            
            career_state['current_month'] += 1

        except Exception as e:
            ui.notify(f"Error: {str(e)}", type='negative')
            print(traceback.format_exc())
        finally:
            career_state['is_running'] = False
            btn_play_month.enable()

    def update_status_display():
        pts = career_state['status_points']
        if pts >= SBM_TIERS['Platinum']['points']: lvl, col, target = 'PLATINUM', 'text-slate-200', 999999
        elif pts >= SBM_TIERS['Gold']['points']: lvl, col, target = 'GOLD', 'text-yellow-400', SBM_TIERS['Platinum']['points']
        elif pts >= SBM_TIERS['Silver']['points']: lvl, col, target = 'SILVER', 'text-gray-400', SBM_TIERS['Gold']['points']
        else: lvl, col, target = 'WHITE', 'text-white', SBM_TIERS['Silver']['points']
            
        lbl_status.set_text(f"{lvl} MEMBER")
        lbl_status.classes(replace=col)
        lbl_points.set_text(f"{pts:,.0f} / {target:,.0f} Points")
        progress_bar.set_value(min(1.0, pts / target))
        lbl_ga.set_text(f"€{career_state['current_ga']:,.0f}")

    def log(msg):
        with log_container:
            ui.label(f"> {msg}")
        log_container.scroll_to(percent=1.0)

    update_status_display()
