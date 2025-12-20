from nicegui import ui
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import asyncio

# --- FIX: IMPORT BaccaratWorker INSTEAD OF SimulationWorker ---
from ui.simulator import BaccaratWorker 
from ui.roulette_sim import RouletteWorker
from engine.tier_params import TierConfig, generate_tier_map, get_tier_for_ga
from utils.persistence import load_profile, save_profile
from engine.strategy_rules import StrategyOverrides, BetStrategy

# SBM LOYALTY TIERS (2024 Rules)
SBM_TIERS = {
    'Silver': {'points': 5000, 'color': '#C0C0C0'},
    'Gold': {'points': 22500, 'color': '#FFD700'},
    'Platinum': {'points': 175000, 'color': '#E5E4E2'}
}

def show_career_mode():
    profile = load_profile()
    
    # Career State
    career_state = {
        'game_type': 'Baccarat', # Default
        'current_month': 1,
        'current_ga': profile.get('bankroll', 2000),
        'status_points': 0,
        'status_level': 'White',
        'history': [],
        'is_running': False
    }

    # --- UI COMPONENTS ---
    with ui.column().classes('w-full max-w-4xl mx-auto p-4 gap-6'):
        
        # HEADER: STATUS CARD
        with ui.card().classes('w-full bg-slate-900 p-6 border-l-8 border-yellow-500'):
            with ui.row().classes('w-full items-center justify-between'):
                with ui.column():
                    ui.label('MY MONACO CAREER').classes('text-xs text-slate-400 font-bold tracking-widest')
                    lbl_status = ui.label('WHITE MEMBER').classes('text-3xl font-black text-white')
                    lbl_points = ui.label('0 / 5,000 Points').classes('text-sm text-yellow-500 font-bold')
                
                with ui.column().classes('items-end'):
                    lbl_ga = ui.label(f"€{career_state['current_ga']:,.0f}").classes('text-4xl font-black text-green-400')
                    ui.label('General Account (GA)').classes('text-xs text-slate-500')

            # Progress Bar
            progress_bar = ui.linear_progress(value=0.0).props('color=yellow track-color=grey-8').classes('mt-4 h-4 rounded-full')

        # ACTION CENTER
        with ui.grid(columns=2).classes('w-full gap-6'):
            
            # LEFT: MISSION CONFIG
            with ui.card().classes('w-full bg-slate-800 p-4'):
                ui.label('MONTHLY MISSION').classes('font-bold text-white mb-4')
                
                select_game = ui.select(['Baccarat', 'Roulette'], value='Baccarat', label='Game Selection').classes('w-full')
                slider_sessions = ui.slider(min=1, max=20, value=4).props('label-always color=cyan')
                ui.label('Sessions this Month').classes('text-xs text-slate-400 mb-4')
                
                ui.separator().classes('bg-slate-700 mb-4')
                
                # ECOSYSTEM INPUTS
                ui.label('REAL LIFE CASHFLOW').classes('font-bold text-green-400 mb-2')
                num_contrib = ui.number(label='Monthly Deposit (€)', value=300, step=50).classes('w-full')
                switch_reinvest = ui.switch('Reinvest Profits (Compound)', value=True).props('color=green')

            # RIGHT: EXECUTION
            with ui.column().classes('justify-between'):
                # LOG
                log_container = ui.scroll_area().classes('w-full h-48 bg-black rounded p-2 text-xs font-mono text-green-300 border border-slate-700')
                
                btn_play_month = ui.button('PLAY NEXT MONTH', on_click=lambda: run_month()).props('icon=play_arrow color=yellow text-color=black size=xl').classes('w-full shadow-lg')

        # CAREER CHART
        chart_card = ui.card().classes('w-full bg-slate-900 p-4')
        
    # --- LOGIC ---
    async def run_month():
        if career_state['is_running']: return
        career_state['is_running'] = True
        btn_play_month.disable()
        
        try:
            # 1. Deposit
            deposit = float(num_contrib.value)
            career_state['current_ga'] += deposit
            log(f"Month {career_state['current_month']}: Deposited €{deposit}")
            
            # 2. Play Sessions
            game = select_game.value
            sessions = int(slider_sessions.value)
            monthly_pnl = 0
            monthly_points = 0
            
            # Define Standard Overrides for Career Mode (Safe Defaults)
            # NOTE: We use BetStrategy.BANKER for Baccarat as default
            base_overrides = StrategyOverrides(
                iron_gate_limit=3, stop_loss_units=20, profit_lock_units=10, 
                bet_strategy=BetStrategy.BANKER if game == 'Baccarat' else 'Red',
                shoes_per_session=2
            )
            
            # Generate Tier Map dynamically based on current wealth
            # We use a safety factor of 25x for career longevity
            tier_map = generate_tier_map(safety_factor=25, mode='Standard', game_type=game, base_bet=10.0)
            
            # Determine Starting Tier
            start_tier = get_tier_for_ga(career_state['current_ga'], tier_map, 1, 'Standard', game)
            active_level = start_tier.level

            for s in range(sessions):
                await asyncio.sleep(0.1) # UI Refresh
                
                # RUN THE SESSION (Using the correct Worker)
                if game == 'Baccarat':
                    # Fix: Use BaccaratWorker
                    pnl, vol, level, hands = BaccaratWorker.run_session(
                        career_state['current_ga'], base_overrides, tier_map, 
                        True, False, active_level, 'Standard'
                    )
                else:
                    # Fix: Use RouletteWorker
                    pnl, vol, level, hands, z, t = RouletteWorker.run_session(
                        career_state['current_ga'], base_overrides, tier_map, 
                        True, False, active_level, 'Standard'
                    )

                monthly_pnl += pnl
                career_state['current_ga'] += pnl
                
                # Points Calc (Approx 10 EUR turnover = 1 point, simplified)
                points = vol * 0.1 
                monthly_points += points
                
                # Update Active Level for next session (Ladder Logic)
                active_level = level 

            # 3. Update State
            career_state['status_points'] += monthly_points
            update_status_display()
            
            log(f"RESULT: {game} | PnL: €{monthly_pnl:,.0f} | Points: +{monthly_points:,.0f}")
            log(f"End Balance: €{career_state['current_ga']:,.0f}")
            
            # Check for Ruin
            if career_state['current_ga'] < 50:
                log("!!! INSOLVENCY - GAME OVER !!!")
                btn_play_month.disable()
                return

            career_state['current_month'] += 1
            update_chart()

        except Exception as e:
            ui.notify(f"Error: {str(e)}", type='negative')
            print(e)
        finally:
            career_state['is_running'] = False
            btn_play_month.enable()

    def update_status_display():
        pts = career_state['status_points']
        
        if pts >= SBM_TIERS['Platinum']['points']:
            lvl, col, target = 'PLATINUM', 'text-slate-200', 999999
        elif pts >= SBM_TIERS['Gold']['points']:
            lvl, col, target = 'GOLD', 'text-yellow-400', SBM_TIERS['Platinum']['points']
        elif pts >= SBM_TIERS['Silver']['points']:
            lvl, col, target = 'SILVER', 'text-gray-400', SBM_TIERS['Gold']['points']
        else:
            lvl, col, target = 'WHITE', 'text-white', SBM_TIERS['Silver']['points']
            
        lbl_status.set_text(f"{lvl} MEMBER")
        lbl_status.classes(replace=col)
        
        lbl_points.set_text(f"{pts:,.0f} / {target:,.0f} Points")
        
        pct = min(1.0, pts / target)
        progress_bar.set_value(pct)
        
        lbl_ga.set_text(f"€{career_state['current_ga']:,.0f}")

    def log(msg):
        with log_container:
            ui.label(f"> {msg}")
        log_container.scroll_to(percent=1.0)

    def update_chart():
        pass # Placeholder for chart update logic

    # Initial Draw
    update_status_display()
