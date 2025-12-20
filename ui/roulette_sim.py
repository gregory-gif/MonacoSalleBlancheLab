from nicegui import ui
import plotly.graph_objects as go
import random
import asyncio
import traceback
import numpy as np

# Import Physics
from engine.roulette_rules import RouletteSessionState, RouletteStrategist, RouletteBet
from engine.tier_params import TierConfig, generate_tier_map, get_tier_for_ga
from utils.persistence import load_profile, save_profile
from engine.strategy_rules import StrategyOverrides

# SBM LOYALTY TIERS
SBM_TIERS = {'Silver': 5000, 'Gold': 22500, 'Platinum': 175000}

# MAP
BET_MAP = {
    'Red': RouletteBet.RED,
    'Black': RouletteBet.BLACK,
    'Even': RouletteBet.EVEN,
    'Odd': RouletteBet.ODD,
    '1-18': RouletteBet.LOW,
    '19-36': RouletteBet.HIGH,
    'Strategy 1: Salon Privé Lite': RouletteBet.STRAT_SALON_LITE,
    'Strategy 2: French Main Game': RouletteBet.STRAT_FRENCH_LITE
}

class RouletteWorker:
    @staticmethod
    def run_session(current_ga: float, overrides: StrategyOverrides, tier_map: dict, use_ratchet: bool, penalty_mode: bool, active_level: int, mode: str, base_bet: float = 5.0):
        tier = get_tier_for_ga(current_ga, tier_map, active_level, mode, game_type='Roulette')
        
        is_active_penalty = penalty_mode and overrides.penalty_box_enabled
        if is_active_penalty:
            flat_bet = base_bet 
            tier = TierConfig(level=tier.level, min_ga=0, max_ga=9999999, base_unit=flat_bet, press_unit=flat_bet, stop_loss=tier.stop_loss, profit_lock=tier.profit_lock, catastrophic_cap=tier.catastrophic_cap)
            session_overrides = StrategyOverrides(
                iron_gate_limit=overrides.iron_gate_limit, stop_loss_units=overrides.stop_loss_units,
                profit_lock_units=overrides.profit_lock_units, shoes_per_session=overrides.shoes_per_session,
                bet_strategy=overrides.bet_strategy, 
                bet_strategy_2=overrides.bet_strategy_2,
                press_trigger_wins=999, press_depth=0, ratchet_enabled=False,
                
                # Spice config pass-through
                spice_zero_enabled=overrides.spice_zero_enabled, spice_zero_trigger=overrides.spice_zero_trigger,
                spice_zero_max=overrides.spice_zero_max, spice_zero_cooldown=overrides.spice_zero_cooldown,
                spice_tiers_enabled=overrides.spice_tiers_enabled, spice_tiers_trigger=overrides.spice_tiers_trigger,
                spice_tiers_max=overrides.spice_tiers_max, spice_tiers_cooldown=overrides.spice_tiers_cooldown
            )
        else:
            session_overrides = overrides

        if use_ratchet and not is_active_penalty:
            session_overrides.ratchet_enabled = True
            session_overrides.profit_lock_units = 1000 if session_overrides.profit_lock_units <= 0 else session_overrides.profit_lock_units

        state = RouletteSessionState(tier=tier, overrides=session_overrides)
        state.current_spin = 1
        spins_limit = overrides.shoes_per_session * 60 
        volume = 0
        
        active_main_bets = []
        b1 = BET_MAP.get(overrides.bet_strategy, RouletteBet.RED)
        active_main_bets.append(b1)
        if overrides.bet_strategy_2 and overrides.bet_strategy_2 in BET_MAP:
            b2 = BET_MAP.get(overrides.bet_strategy_2)
            active_main_bets.append(b2)
        
        while state.current_spin <= spins_limit and state.mode != 'STOPPED':
            decision = RouletteStrategist.get_next_decision(state)
            if decision['mode'] == 'STOPPED': break
            
            unit_amt = decision['bet']
            current_bets = active_main_bets.copy()
            
            # --- SPICE LOGIC: INJECT EXTRA BETS ---
            current_pl_units = state.session_pnl / base_bet
            spice_fired_this_spin = False
            
            # Zéro Léger Logic
            if overrides.spice_zero_enabled and not spice_fired_this_spin:
                if (state.spice_zero_uses < overrides.spice_zero_max and 
                    current_pl_units >= overrides.spice_zero_trigger and 
                    (state.current_spin - state.last_spice_zero_spin) >= overrides.spice_zero_cooldown):
                    
                    current_bets.append(RouletteBet.SPICE_ZERO)
                    state.spice_zero_uses += 1
                    state.last_spice_zero_spin = state.current_spin
                    spice_fired_this_spin = True
                    volume += (base_bet * 3) # Cost of Zero Leger

            # Tiers Logic
            if overrides.spice_tiers_enabled and not spice_fired_this_spin:
                if (state.spice_tiers_uses < overrides.spice_tiers_max and 
                    current_pl_units >= overrides.spice_tiers_trigger and 
                    (state.current_spin - state.last_spice_tiers_spin) >= overrides.spice_tiers_cooldown):
                    
                    current_bets.append(RouletteBet.SPICE_TIERS)
                    state.spice_tiers_uses += 1
                    state.last_spice_tiers_spin = state.current_spin
                    spice_fired_this_spin = True
                    volume += (base_bet * 6) # Cost of Tiers

            # Volume Calc for Main Bets
            total_main_units = 0
            for b in active_main_bets:
                if b == RouletteBet.STRAT_SALON_LITE: total_main_units += 5
                elif b == RouletteBet.STRAT_FRENCH_LITE: total_main_units += 7
                else: total_main_units += 1
            
            volume += (unit_amt * total_main_units)
            
            number, won, pnl = RouletteStrategist.resolve_spin(state, current_bets, unit_amt)
            state.current_spin += 1

        # Return extra spice stats for analysis
        return state.session_pnl, volume, tier.level, state.current_spin, state.spice_zero_uses, state.spice_tiers_uses

    @staticmethod
    def run_full_career(start_ga, total_months, sessions_per_year, 
                        contrib_win, contrib_loss, overrides, use_ratchet,
                        use_tax, use_holiday, safety_factor, target_points, earn_rate,
                        holiday_ceiling, insolvency_floor, strategy_mode,
                        base_bet_val,
                        track_y1_details=False):
        
        tier_map = generate_tier_map(safety_factor, mode=strategy_mode, game_type='Roulette', base_bet=base_bet_val)
        trajectory = []
        current_ga = start_ga
        
        initial_tier = get_tier_for_ga(current_ga, tier_map, 1, strategy_mode, game_type='Roulette')
        active_level = initial_tier.level

        m_insolvent_months = 0; failed_year_one = False
        m_tax = 0 
        m_contrib = 0
        gold_hit_year = -1
        current_year_points = 0
        
        y1_log = []
        last_session_won = False
        
        # Tracking Spice
        total_zero_uses = 0
        total_tiers_uses = 0
        sessions_with_spices = 0

        for m in range(total_months):
            if m > 0 and m % 12 == 0:
                current_year_points = 0

            if use_tax and current_ga > overrides.tax_threshold:
                surplus = current_ga - overrides.tax_threshold
                tax_amt = surplus * (overrides.tax_rate / 100.0)
                current_ga -= tax_amt
                m_tax += tax_amt

            should_contribute = True
            if use_holiday and current_ga >= holiday_ceiling: should_contribute = False
            
            if should_contribute:
                amount = contrib_win if last_session_won else contrib_loss
                current_ga += amount
                m_contrib += amount
            
            can_play = (current_ga >= insolvency_floor)
            if not can_play:
                m_insolvent_months += 1
                if m < 12: failed_year_one = True
            
            if can_play:
                sessions_this_month = sessions_per_year // 12
                if m % 12 < (sessions_per_year % 12): sessions_this_month += 1

                for _ in range(sessions_this_month):
                    pnl, vol, used_level, spins, s_zero, s_tiers = RouletteWorker.run_session(
                        current_ga, overrides, tier_map, use_ratchet, 
                        False, active_level, strategy_mode, base_bet_val
                    )
                    active_level = used_level 
                    current_ga += pnl
                    current_year_points += vol * (earn_rate / 100)
                    last_session_won = (pnl > 0)
                    
                    total_zero_uses += s_zero
                    total_tiers_uses += s_tiers
                    if s_zero > 0 or s_tiers > 0: sessions_with_spices += 1
                    
                    if track_y1_details and m < 12:
                        y1_log.append({'month': m + 1, 'result': pnl, 'balance': current_ga, 'game_bal': 0, 'hands': spins})
            else:
                 if track_y1_details and m < 12:
                        y1_log.append({'month': m + 1, 'result': 0, 'balance': current_ga, 'game_bal': 0, 'hands': 0, 'note': 'Insolvent'})

            if gold_hit_year == -1 and current_year_points >= target_points:
                gold_hit_year = (m // 12) + 1

            trajectory.append(current_ga)
            
        return {
            'trajectory': trajectory, 'final_ga': current_ga, 'insolvent_months': m_insolvent_months, 
            'failed_y1': failed_year_one, 'y1_log': y1_log, 'tax': m_tax, 'contrib': m_contrib, 
            'gold_year': gold_hit_year, 'spice_sessions': sessions_with_spices,
            'zero_uses': total_zero_uses, 'tiers_uses': total_tiers_uses
        }

def calculate_stats(results, config, start_ga, total_months):
    if not results: return None
    trajectories = np.array([r['trajectory'] for r in results])
    months = list(range(trajectories.shape[1]))
    
    total_sims = len(results)
    
    stats = {
        'months': months,
        'min_band': np.min(trajectories, axis=0),
        'max_band': np.max(trajectories, axis=0),
        'p25_band': np.percentile(trajectories, 25, axis=0),
        'p75_band': np.percentile(trajectories, 75, axis=0),
        'mean_line': np.mean(trajectories, axis=0),
        'median_line': np.median(trajectories, axis=0),
        'avg_final_ga': np.mean([r['final_ga'] for r in results]),
        'avg_tax': np.mean([r['tax'] for r in results]),
        'avg_insolvent': np.mean([r['insolvent_months'] for r in results]),
        'gold_hits': [r['gold_year'] for r in results if r['gold_year'] != -1],
        'y1_failures': len([r for r in results if r['failed_y1']]),
        'total_input': start_ga + np.mean([r['contrib'] for r in results]),
        'survivor_count': len([r for r in results if r['final_ga'] >= 100]),
        
        # Spice Stats
        'avg_spice_sessions': np.mean([r['spice_sessions'] for r in results]),
        'avg_zero_uses': np.mean([r['zero_uses'] for r in results]),
        'avg_tiers_uses': np.mean([r['tiers_uses'] for r in results])
    }
    return stats

def show_roulette_sim():
    running = False 
    
    # ... (Keep existing load/save/delete/update functions) ...
    # Placeholder for standard functions to save space in this view, assume they are identical to previous version
    
    def save_current_strategy():
        try:
            name = input_name.value
            if not name: return
            profile = load_profile()
            if 'saved_strategies' not in profile: profile['saved_strategies'] = {}
            
            config = {
                # ... (Existing Fields) ...
                'sim_num': slider_num_sims.value, 'sim_years': slider_years.value, 'sim_freq': slider_frequency.value,
                'eco_win': slider_contrib_win.value, 'eco_loss': slider_contrib_loss.value, 'eco_tax': switch_luxury_tax.value,
                'eco_hol': switch_holiday.value, 'eco_hol_ceil': slider_holiday_ceil.value, 'eco_insolvency': slider_insolvency.value,
                'eco_tax_thresh': slider_tax_thresh.value, 'eco_tax_rate': slider_tax_rate.value,
                'tac_safety': slider_safety.value, 'tac_iron': slider_iron_gate.value, 'tac_press': select_press.value,
                'tac_depth': slider_press_depth.value, 'tac_shoes': slider_shoes.value, 'tac_bet': select_bet_strat.value,
                'tac_bet_2': select_bet_strat_2.value,
                'tac_penalty': switch_penalty.value, 'tac_mode': select_engine_mode.value, 
                'risk_stop': slider_stop_loss.value, 'risk_prof': slider_profit.value,
                'risk_ratch': switch_ratchet.value, 'risk_ratch_mode': select_ratchet_mode.value, 
                'gold_stat': select_status.value, 'gold_earn': slider_earn_rate.value, 'start_ga': slider_start_ga.value,
                'tac_base_bet': slider_base_bet.value,
                
                # SPICE FIELDS
                'spice_zero_en': switch_spice_zero.value, 'spice_zero_trig': slider_spice_zero_trig.value,
                'spice_zero_max': slider_spice_zero_max.value,
                'spice_tiers_en': switch_spice_tiers.value, 'spice_tiers_trig': slider_spice_tiers_trig.value,
                'spice_tiers_max': slider_spice_tiers_max.value
            }
            profile['saved_strategies'][name] = config
            save_profile(profile)
            ui.notify(f'Saved: {name}', type='positive')
            update_strategy_list()
        except Exception as e: ui.notify(str(e), type='negative')

    def load_selected_strategy():
        try:
            name = select_saved.value
            if not name: return
            saved = load_saved_strategies()
            config = saved.get(name)
            if not config: return
            
            # ... (Existing Fields Load) ...
            slider_num_sims.value = config.get('sim_num', 20)
            # ... (Rest of existing loads) ...
            
            # SPICE LOADS
            switch_spice_zero.value = config.get('spice_zero_en', False)
            slider_spice_zero_trig.value = config.get('spice_zero_trig', 15)
            slider_spice_zero_max.value = config.get('spice_zero_max', 2)
            switch_spice_tiers.value = config.get('spice_tiers_en', False)
            slider_spice_tiers_trig.value = config.get('spice_tiers_trig', 25)
            slider_spice_tiers_max.value = config.get('spice_tiers_max', 1)
            
            ui.notify(f'Loaded: {name}', type='info')
        except: pass

    # ... (Keep delete_selected_strategy, update_ladder_preview) ...

    async def run_sim():
        nonlocal running
        if running: return
        try:
            running = True; btn_sim.disable(); progress.set_value(0); progress.set_visibility(True)
            label_stats.set_text("Spinning the Wheel (Multiverse)...")
            
            config = {
                'num_sims': int(slider_num_sims.value), 'years': int(slider_years.value), 'freq': int(slider_frequency.value),
                'contrib_win': int(slider_contrib_win.value), 'contrib_loss': int(slider_contrib_loss.value),
                'status_target_pts': SBM_TIERS[select_status.value], 'earn_rate': float(slider_earn_rate.value),
                'use_ratchet': switch_ratchet.value, 'ratchet_mode': select_ratchet_mode.value, 
                'use_tax': switch_luxury_tax.value, 'use_holiday': switch_holiday.value,
                'hol_ceil': int(slider_holiday_ceil.value), 'insolvency': int(slider_insolvency.value),
                'safety': int(slider_safety.value), 'start_ga': int(slider_start_ga.value),
                'press_depth': int(slider_press_depth.value), 'tax_thresh': int(slider_tax_thresh.value),
                'tax_rate': int(slider_tax_rate.value), 'strategy_mode': select_engine_mode.value,
                'base_bet': float(slider_base_bet.value)
            }
            
            overrides = StrategyOverrides(
                iron_gate_limit=int(slider_iron_gate.value), stop_loss_units=int(slider_stop_loss.value),
                profit_lock_units=int(slider_profit.value), press_trigger_wins=int(select_press.value),
                press_depth=config['press_depth'], ratchet_lock_pct=0.0, tax_threshold=config['tax_thresh'],
                tax_rate=config['tax_rate'], bet_strategy=select_bet_strat.value,
                bet_strategy_2=select_bet_strat_2.value,
                shoes_per_session=int(slider_shoes.value), penalty_box_enabled=switch_penalty.value,
                ratchet_enabled=switch_ratchet.value, ratchet_mode=select_ratchet_mode.value,
                
                # SPICE
                spice_zero_enabled=switch_spice_zero.value, spice_zero_trigger=slider_spice_zero_trig.value,
                spice_zero_max=slider_spice_zero_max.value, spice_zero_cooldown=10,
                spice_tiers_enabled=switch_spice_tiers.value, spice_tiers_trigger=slider_spice_tiers_trig.value,
                spice_tiers_max=slider_spice_tiers_max.value, spice_tiers_cooldown=10
            )

            start_ga = config['start_ga']
            all_results = []
            batch_size = 10
            for i in range(0, config['num_sims'], batch_size):
                count = min(batch_size, config['num_sims'] - i)
                def run_batch():
                    batch_data = []
                    for k in range(count):
                        should_track = (i == 0 and k == 0)
                        res = RouletteWorker.run_full_career(
                            start_ga, config['years']*12, config['freq'],
                            config['contrib_win'], config['contrib_loss'], overrides, 
                            config['use_ratchet'], config['use_tax'], config['use_holiday'], 
                            config['safety'], config['status_target_pts'], config['earn_rate'],
                            config['hol_ceil'], config['insolvency'], config['strategy_mode'],
                            config['base_bet'], 
                            track_y1_details=should_track
                        )
                        batch_data.append(res)
                    return batch_data

                batch_res = await asyncio.to_thread(run_batch)
                all_results.extend(batch_res)
                progress.set_value(len(all_results) / config['num_sims'])
                label_stats.set_text(f"Simulating Universe {len(all_results)}/{config['num_sims']}")
                await asyncio.sleep(0.01)

            label_stats.set_text("Analyzing Data (Please Wait)...")
            stats = await asyncio.to_thread(calculate_stats, all_results, config, start_ga, config['years']*12)
            render_analysis_ui(stats, config, start_ga, overrides, all_results) 
            label_stats.set_text("Simulation Complete")

        except Exception as e:
            print(traceback.format_exc())
            ui.notify(f"Error: {str(e)}", type='negative')
        finally:
            running = False; btn_sim.enable(); progress.set_visibility(False)

    def render_analysis_ui(stats, config, start_ga, overrides, all_results):
        if not stats: return
        total_output = stats['avg_final_ga'] + stats['avg_tax']
        grand_total_wealth = total_output 
        
        # ... (Calc standard metrics) ...
        months = stats['months']
        gold_prob = (len(stats['gold_hits']) / config['num_sims']) * 100
        net_life_result = total_output - stats['total_input']
        real_monthly_cost = (stats['total_input'] - total_output) / (config['years']*12)
        score_survival = (stats['survivor_count'] / config['num_sims']) * 100
        # ... (Grade Calc) ...
        active_pct = 100 - ((stats['avg_insolvent'] / (config['years']*12)) * 100)
        total_score = (score_survival * 0.70) + (active_pct * 0.30)
        if total_score >= 90: grade, g_col = "A", "text-green-400"
        elif total_score >= 80: grade, g_col = "B", "text-blue-400"
        elif total_score >= 70: grade, g_col = "C", "text-yellow-400"
        elif total_score >= 60: grade, g_col = "D", "text-orange-400"
        else: grade, g_col = "F", "text-red-600"

        with scoreboard_container:
            scoreboard_container.clear()
            with ui.card().classes('w-full bg-slate-800 p-4 border-l-8').style(f'border-color: {"#ef4444" if grade=="F" else "#4ade80"}'):
                with ui.column().classes('w-full gap-4'):
                    with ui.row().classes('w-full items-center justify-between'):
                        with ui.column():
                            ui.label('ROULETTE GRADE').classes('text-xs text-slate-400 font-bold tracking-widest')
                            ui.label(f"{grade}").classes(f'text-6xl font-black {g_col} leading-none')
                            ui.label(f"{total_score:.1f}% Score").classes(f'text-sm font-bold {g_col}')
                        with ui.column().classes('items-center'):
                            ui.label('SPICE FREQUENCY').classes('text-[10px] text-slate-500 font-bold tracking-widest')
                            ui.label(f"{stats['avg_spice_sessions']:.1f}").classes('text-3xl font-bold text-pink-400')
                            ui.label("Avg Sess w/ Spice").classes('text-xs text-slate-500')
                        with ui.column().classes('items-center'):
                            ui.label('GRAND TOTAL WEALTH').classes('text-[10px] text-slate-500 font-bold tracking-widest')
                            ui.label(f"€{total_output:,.0f}").classes('text-4xl font-black text-white leading-none')
                            if stats['avg_tax'] > 0: ui.label(f"(GA €{stats['avg_final_ga']:,.0f} + Tax €{stats['avg_tax']:,.0f})").classes('text-xs font-bold text-yellow-400')
                    
        with chart_container:
            chart_container.clear()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=months + months[::-1], y=np.concatenate([stats['max_band'], stats['min_band'][::-1]]), fill='toself', fillcolor='rgba(148, 163, 184, 0.5)', line=dict(color='rgba(255,255,255,0.3)', width=1), name='Best/Worst'))
            fig.add_trace(go.Scatter(x=months + months[::-1], y=np.concatenate([stats['p75_band'], stats['p25_band'][::-1]]), fill='toself', fillcolor='rgba(0, 255, 136, 0.3)', line=dict(color='rgba(255,255,255,0)'), name='Likely'))
            fig.add_trace(go.Scatter(x=months, y=stats['mean_line'], mode='lines', name='Average', line=dict(color='white', width=2)))
            fig.add_trace(go.Scatter(x=months, y=stats['median_line'], mode='lines', name='Median', line=dict(color='yellow', width=2, dash='dot')))
            
            fig.add_hline(y=config['insolvency'], line_dash="dash", line_color="red", annotation_text="Insolvency")
            if config['use_holiday']: fig.add_hline(y=config['hol_ceil'], line_dash="dash", line_color="yellow", annotation_text="Holiday")
            fig.update_layout(title='Monte Carlo Confidence Bands (Roulette)', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'), margin=dict(l=20, r=20, t=40, b=20))
            ui.plotly(fig).classes('w-full h-96')

        with report_container:
            report_container.clear()
            press_name = {0: 'Flat', 1: 'Press 1-Win', 2: 'Press 2-Wins', 3: 'Titan', 4: "Capped D'Alembert", 5: "La Caroline"}.get(overrides.press_trigger_wins, 'Unknown')

            lines = ["=== ROULETTE CONFIGURATION ==="]
            lines.append(f"Sims: {config['num_sims']} | Years: {config['years']} | Mode: {config['strategy_mode']}")
            lines.append(f"Betting: {overrides.bet_strategy} + {overrides.bet_strategy_2}")
            lines.append(f"Spice Zéro: {overrides.spice_zero_enabled} (Trig {overrides.spice_zero_trigger}u, Max {overrides.spice_zero_max})")
            lines.append(f"Spice Tiers: {overrides.spice_tiers_enabled} (Trig {overrides.spice_tiers_trigger}u, Max {overrides.spice_tiers_max})")
            
            lines.append("\n=== PERFORMANCE RESULTS ===")
            lines.append(f"Grand Total Wealth: €{grand_total_wealth:,.0f} (GA + Tax)")
            lines.append(f"Real Monthly Cost: €{real_monthly_cost:,.0f}")
            lines.append(f"Avg Zero Léger Uses: {stats['avg_zero_uses']:.1f} per session")
            lines.append(f"Avg Tiers Uses: {stats['avg_tiers_uses']:.1f} per session")
            
            y1_log = all_results[0].get('y1_log', [])
            if y1_log:
                lines.append("\n=== OUR YEAR 1 DATA (COPY/PASTE) ===")
                lines.append("Month,Result,Total_Bal,Game_Bal,Hands")
                for e in y1_log:
                    lines.append(f"{e['month']},{e['result']},{e['balance']},{e['game_bal']},{e['hands']}")

            ui.html(f'<pre style="white-space: pre-wrap; font-family: monospace; color: #94a3b8; font-size: 0.75rem;">{"\n".join(lines)}</pre>', sanitize=False)

    with ui.column().classes('w-full max-w-4xl mx-auto gap-6 p-4'):
        ui.label('ROULETTE LAB (MONACO RULES)').classes('text-2xl font-light text-red-400')
        
        with ui.card().classes('w-full bg-slate-900 p-6 gap-4'):
            # ... (Strategy Library) ...
            with ui.expansion('STRATEGY LIBRARY (Load/Save)', icon='save').classes('w-full bg-slate-800 text-slate-300 mb-4'):
                with ui.column().classes('w-full gap-4'):
                    with ui.row().classes('w-full items-center gap-4'):
                        input_name = ui.input('Save Name').props('dark').classes('flex-grow')
                        ui.button('SAVE', on_click=save_current_strategy).props('icon=save color=green')
                    with ui.row().classes('w-full items-center gap-4'):
                        select_saved = ui.select([], label='Saved Strategies').props('dark').classes('flex-grow')
                        ui.button('LOAD', on_click=load_selected_strategy).props('icon=file_upload color=blue')
                        ui.button('DELETE', on_click=delete_selected_strategy).props('icon=delete color=red')
                    update_strategy_list()

            ui.separator().classes('bg-slate-700')
            
            # ... (Sim Sliders) ...
            with ui.row().classes('w-full gap-4 items-start'):
                with ui.column().classes('flex-grow'):
                    ui.label('SIMULATION').classes('font-bold text-white mb-2')
                    with ui.row().classes('w-full justify-between'): ui.label('Universes').classes('text-xs text-slate-400'); lbl_num_sims = ui.label()
                    slider_num_sims = ui.slider(min=10, max=1000, value=20).props('color=cyan'); lbl_num_sims.bind_text_from(slider_num_sims, 'value', lambda v: f'{v}')
                    with ui.row().classes('w-full justify-between'): ui.label('Years').classes('text-xs text-slate-400'); lbl_years = ui.label()
                    slider_years = ui.slider(min=1, max=10, value=10).props('color=blue'); lbl_years.bind_text_from(slider_years, 'value', lambda v: f'{v}')
                    with ui.row().classes('w-full justify-between'): ui.label('Sessions/Year').classes('text-xs text-slate-400'); lbl_freq = ui.label()
                    slider_frequency = ui.slider(min=10, max=100, value=20).props('color=blue'); lbl_freq.bind_text_from(slider_frequency, 'value', lambda v: f'{v}')

                with ui.column().classes('w-1/2'):
                    ui.label('LADDER PREVIEW').classes('font-bold text-white mb-2')
                    with ui.expansion('View Table', icon='list').classes('w-full bg-slate-800 text-slate-300'): ladder_grid = ui.aggrid({'columnDefs': [{'headerName': 'Tier', 'field': 'tier', 'width': 70},{'headerName': 'Bet', 'field': 'bet', 'width': 120},{'headerName': 'Start GA', 'field': 'start', 'width': 120}],'rowData': []}).classes('h-40 w-full theme-balham-dark')

            ui.separator().classes('bg-slate-700')

            # NEW SPICE LAB SECTION
            with ui.card().classes('w-full bg-slate-800 p-4 border border-pink-500 mb-4'):
                ui.label('SPICE LAB (Dynamic Add-on Bets)').classes('font-bold text-pink-400 mb-2')
                with ui.row().classes('w-full gap-8'):
                    # Zéro Léger
                    with ui.column().classes('flex-1'):
                        with ui.row().classes('items-center'):
                            switch_spice_zero = ui.switch('Enable Zéro Léger (3u)').props('color=pink')
                        with ui.row().classes('w-full justify-between'): ui.label('Trigger P/L').classes('text-xs text-slate-400'); lbl_ztrig = ui.label()
                        slider_spice_zero_trig = ui.slider(min=5, max=50, value=15).props('color=pink'); lbl_ztrig.bind_text_from(slider_spice_zero_trig, 'value', lambda v: f'+{v}u')
                        with ui.row().classes('w-full justify-between'): ui.label('Max Uses').classes('text-xs text-slate-400'); lbl_zmax = ui.label()
                        slider_spice_zero_max = ui.slider(min=1, max=5, value=2).props('color=pink'); lbl_zmax.bind_text_from(slider_spice_zero_max, 'value', lambda v: f'{v}/sess')

                    # Tiers
                    with ui.column().classes('flex-1'):
                        with ui.row().classes('items-center'):
                            switch_spice_tiers = ui.switch('Enable Tiers (6u)').props('color=purple')
                        with ui.row().classes('w-full justify-between'): ui.label('Trigger P/L').classes('text-xs text-slate-400'); lbl_ttrig = ui.label()
                        slider_spice_tiers_trig = ui.slider(min=5, max=50, value=25).props('color=purple'); lbl_ttrig.bind_text_from(slider_spice_tiers_trig, 'value', lambda v: f'+{v}u')
                        with ui.row().classes('w-full justify-between'): ui.label('Max Uses').classes('text-xs text-slate-400'); lbl_tmax = ui.label()
                        slider_spice_tiers_max = ui.slider(min=1, max=5, value=1).props('color=purple'); lbl_tmax.bind_text_from(slider_spice_tiers_max, 'value', lambda v: f'{v}/sess')

            ui.separator().classes('bg-slate-700')

            with ui.grid(columns=2).classes('w-full gap-8'):
                with ui.column():
                    ui.label('TACTICS').classes('font-bold text-purple-400')
                    select_engine_mode = ui.select(['Standard', 'Fortress', 'Titan', 'Safe Titan'], value='Standard', label='Betting Engine').classes('w-full').on_value_change(update_ladder_preview)
                    
                    with ui.row().classes('w-full justify-between'): ui.label('Base Bet (€)').classes('text-xs text-purple-300'); lbl_base = ui.label()
                    slider_base_bet = ui.slider(min=5, max=100, step=5, value=5, on_change=update_ladder_preview).props('color=purple'); lbl_base.bind_text_from(slider_base_bet, 'value', lambda v: f'€{v}')
                    
                    with ui.row().classes('w-full justify-between'): ui.label('Safety Buffer').classes('text-xs text-orange-400'); lbl_safe = ui.label()
                    slider_safety = ui.slider(min=10, max=60, value=25, on_change=update_ladder_preview).props('color=orange'); lbl_safe.bind_text_from(slider_safety, 'value', lambda v: f'{v}x')
                    
                    # ... (Ecosystem sliders) ...
                    ui.label('ECOSYSTEM').classes('font-bold text-green-400 mt-4')
                    slider_contrib_win = ui.slider(min=0, max=1000, value=300).props('color=green'); ui.label().bind_text_from(slider_contrib_win, 'value', lambda v: f'Win +€{v}')
                    slider_contrib_loss = ui.slider(min=0, max=1000, value=300).props('color=orange'); ui.label().bind_text_from(slider_contrib_loss, 'value', lambda v: f'Loss +€{v}')
                    with ui.row().classes('mt-2'): switch_luxury_tax = ui.switch('Tax').props('color=gold'); switch_holiday = ui.switch('Holiday').props('color=blue'); switch_penalty = ui.switch('Penalty Box').props('color=red'); switch_penalty.value = True
                    with ui.expansion('Adv. Eco Settings', icon='tune').classes('w-full bg-slate-800 text-xs'):
                        slider_holiday_ceil = ui.slider(min=5000, max=50000, value=10000); ui.label().bind_text_from(slider_holiday_ceil, 'value', lambda v: f'Hol Ceil €{v}')
                        slider_insolvency = ui.slider(min=0, max=5000, value=1000); ui.label().bind_text_from(slider_insolvency, 'value', lambda v: f'Floor €{v}')
                        slider_tax_thresh = ui.slider(min=5000, max=50000, value=12500); ui.label().bind_text_from(slider_tax_thresh, 'value', lambda v: f'Tax Thresh €{v}')
                        slider_tax_rate = ui.slider(min=5, max=50, value=25)

                with ui.column():
                    ui.label('ROULETTE GAMEPLAY').classes('font-bold text-red-400')
                    
                    select_bet_strat = ui.select(list(BET_MAP.keys()), value='Red', label='Bet Selection (1)').classes('w-full')
                    
                    bet_opts = list(BET_MAP.keys())
                    bet_opts.insert(0, None)
                    select_bet_strat_2 = ui.select(bet_opts, label='Bet Selection (2)').classes('w-full')
                    
                    slider_shoes = ui.slider(min=1, max=5, value=2).props('color=blue'); ui.label().bind_text_from(slider_shoes, 'value', lambda v: f'{v*60} Spins (approx {v} hours)')
                    
                    slider_stop_loss = ui.slider(min=0, max=100, value=10).props('color=red'); ui.label().bind_text_from(slider_stop_loss, 'value', lambda v: f'Stop {v}u')
                    slider_profit = ui.slider(min=3, max=100, value=10).props('color=green'); ui.label().bind_text_from(slider_profit, 'value', lambda v: f'Target {v}u')
                    with ui.row().classes('items-center justify-between'): switch_ratchet = ui.switch('Ratchet').props('color=gold'); select_ratchet_mode = ui.select(['Sprint', 'Standard', 'Deep Stack', 'Gold Grinder'], value='Standard').props('dense options-dense').classes('w-32')
                    ui.separator().classes('bg-slate-700 my-2')
                    
                    select_press = ui.select({0: 'Flat', 1: 'Press 1-Win', 2: 'Press 2-Wins', 3: 'Progression 100-150-250', 4: "Capped D'Alembert (Strategist)", 5: "La Caroline (1-1-2-3-4)"}, value=1, label='Press Logic').classes('w-full')
                    ui.label('Press Depth (Wins to Reset)').classes('text-xs text-red-300')
                    slider_press_depth = ui.slider(min=0, max=5, value=3).props('color=red'); ui.label().bind_text_from(slider_press_depth, 'value', lambda v: f'{v} Wins')
                    ui.separator().classes('bg-slate-700 my-2')
                    slider_iron_gate = ui.slider(min=2, max=10, value=3).props('color=purple'); ui.label().bind_text_from(slider_iron_gate, 'value', lambda v: f'Iron Gate {v}')

            ui.separator().classes('bg-slate-700')
            with ui.row().classes('w-full items-center justify-between'):
                with ui.column():
                     ui.label('Starting Capital').classes('text-xs text-green-400')
                     slider_start_ga = ui.slider(min=0, max=10000, value=2000, step=100).props('color=green'); ui.label().bind_text_from(slider_start_ga, 'value', lambda v: f'€{v}')
                     with ui.row().classes('gap-4 mt-2'): select_status = ui.select(list(SBM_TIERS.keys()), value='Gold').props('dense'); slider_earn_rate = ui.slider(min=1, max=20, value=10).props('color=yellow').classes('w-32')
                btn_sim = ui.button('RUN SIM', on_click=run_sim).props('icon=play_arrow color=yellow text-color=black size=lg')

        label_stats = ui.label('Ready...').classes('text-sm text-slate-500'); progress = ui.linear_progress().props('color=green').classes('mt-0'); progress.set_visibility(False)
        scoreboard_container = ui.column().classes('w-full mb-4')
        chart_container = ui.card().classes('w-full bg-slate-900 p-4')
        
        ui.button('⚡ REFRESH SINGLE', on_click=refresh_single_universe).props('flat color=cyan dense').classes('mt-4')
        chart_single_container = ui.column().classes('w-full mt-2')
        
        flight_recorder_container = ui.column().classes('w-full mb-4')
        report_container = ui.column().classes('w-full')
        
        update_ladder_preview()
        
        # Manually triggering a fake load if needed (or keep empty)
        # load_saved_strategies()
        # update_strategy_list()
