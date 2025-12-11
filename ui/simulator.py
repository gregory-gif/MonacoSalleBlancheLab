from nicegui import ui
import plotly.graph_objects as go
import random
import asyncio
import traceback
import numpy as np
import json

from engine.strategy_rules import SessionState, BaccaratStrategist, PlayMode, StrategyOverrides, BetStrategy
from engine.tier_params import TierConfig, generate_tier_map, get_tier_for_ga
from utils.persistence import load_profile, save_profile

# SBM LOYALTY TIERS
SBM_TIERS = {
    'Silver': 5000,
    'Gold': 22500,
    'Platinum': 175000
}

class SimulationWorker:
    @staticmethod
    def run_session(current_ga: float, overrides: StrategyOverrides, tier_map: dict, use_ratchet: bool = False, penalty_mode: bool = False, active_level: int = 1, mode: str = 'Standard'):
        # Pass active_level and mode to get sticky tier
        tier = get_tier_for_ga(current_ga, tier_map, active_level, mode)
        
        # --- PENALTY BOX LOGIC ---
        is_active_penalty = penalty_mode and overrides.penalty_box_enabled
        
        if is_active_penalty:
            flat_bet = 100 if current_ga >= 2000 else 50
            tier = TierConfig(
                level=tier.level, min_ga=0, max_ga=9999999,
                base_unit=flat_bet, press_unit=flat_bet, 
                stop_loss=tier.stop_loss, profit_lock=tier.profit_lock, catastrophic_cap=tier.catastrophic_cap
            )
            session_overrides = StrategyOverrides(
                iron_gate_limit=overrides.iron_gate_limit, stop_loss_units=overrides.stop_loss_units,
                profit_lock_units=overrides.profit_lock_units, shoes_per_session=overrides.shoes_per_session,
                bet_strategy=overrides.bet_strategy, press_trigger_wins=999, press_depth=0, ratchet_enabled=False 
            )
        else:
            session_overrides = overrides

        # --- RATCHET SETUP ---
        if use_ratchet and not is_active_penalty:
            session_overrides = StrategyOverrides(
                iron_gate_limit=overrides.iron_gate_limit, stop_loss_units=overrides.stop_loss_units,
                profit_lock_units=1000, press_trigger_wins=overrides.press_trigger_wins,
                press_depth=overrides.press_depth, ratchet_enabled=True, ratchet_mode=overrides.ratchet_mode, 
                ratchet_lock_pct=0.0, shoes_per_session=overrides.shoes_per_session, bet_strategy=overrides.bet_strategy
            )
        
        state = SessionState(tier=tier, overrides=session_overrides)
        state.current_shoe = 1
        volume = 0 
        
        while state.current_shoe <= overrides.shoes_per_session and state.mode != PlayMode.STOPPED:
            decision = BaccaratStrategist.get_next_decision(state)
            if decision['mode'] == PlayMode.STOPPED: break
            
            bet = decision['bet_amount']
            volume += bet
            
            if use_ratchet and not is_active_penalty:
                if state.session_pnl <= state.locked_profit and state.locked_profit > -9999: break

            # Physics
            rnd = random.random()
            won = False
            pnl_change = 0
            is_tie = False
            
            if overrides.bet_strategy == BetStrategy.BANKER:
                prob_win = 0.4586; prob_loss = 0.4462; payout = 0.95 
            else:
                prob_win = 0.4462; prob_loss = 0.4586; payout = 1.0  
            
            if rnd < prob_win: won = True; pnl_change = bet * payout
            elif rnd < (prob_win + prob_loss): won = False; pnl_change = -bet
            else: is_tie = True; pnl_change = 0

            if not is_tie:
                BaccaratStrategist.update_state_after_hand(state, won, pnl_change)
            else:
                state.hands_played_in_shoe += 1

            if state.hands_played_in_shoe >= 80:
                state.current_shoe += 1
                state.hands_played_in_shoe = 0
                state.current_press_streak = 0
                if state.current_shoe == overrides.shoes_per_session: state.shoe3_start_pnl = state.session_pnl

        # Return result AND the tier level used (to persist state)
        return state.session_pnl, volume, tier.level

    @staticmethod
    def run_full_career(start_ga, total_months, sessions_per_year, 
                        contrib_win, contrib_loss, overrides, use_ratchet,
                        use_tax, use_holiday, safety_factor, target_points, earn_rate,
                        holiday_ceiling, insolvency_floor, strategy_mode):
        
        # GENERATE MAP
        tier_map = generate_tier_map(safety_factor, mode=strategy_mode)
        
        trajectory = []
        current_ga = start_ga
        
        # State Tracking
        active_level = 1 # Start at lowest
        
        # Initial Tier Calc to set starting level correct
        initial_tier = get_tier_for_ga(current_ga, tier_map, 1, strategy_mode)
        active_level = initial_tier.level

        m_contrib = 0; m_tax = 0; m_play_pnl = 0
        m_holidays = 0; m_insolvent_months = 0; m_total_volume = 0 
        gold_hit_year = -1; current_year_points = 0; failed_year_one = False
        last_session_won = False
        
        for m in range(total_months):
            if m > 0 and m % 12 == 0: current_year_points = 0

            # Tax
            if use_tax and current_ga > overrides.tax_threshold:
                surplus = current_ga - overrides.tax_threshold
                tax = surplus * (overrides.tax_rate / 100.0)
                current_ga -= tax
                m_tax += tax

            # Contribution
            should_contribute = True
            if use_holiday and current_ga >= holiday_ceiling: should_contribute = False
            
            if should_contribute:
                amount = contrib_win if last_session_won else contrib_loss
                current_ga += amount
                m_contrib += amount
            else:
                m_holidays += 1
            
            can_play = (current_ga >= insolvency_floor)
            if not can_play:
                m_insolvent_months += 1
                if m < 12: failed_year_one = True
            
            if can_play:
                # Calc sessions
                import math
                sess_float = (m + 1) * (sessions_per_year / 12)
                # Simple integer distribution
                if m % 12 < (sessions_per_year % 12):
                    sessions_this_month = (sessions_per_year // 12) + 1
                else:
                    sessions_this_month = (sessions_per_year // 12)

                for _ in range(sessions_this_month):
                    # Check penalty
                    t_now = get_tier_for_ga(current_ga, tier_map, active_level, strategy_mode)
                    is_penalty = False # Simplified penalty for speed/logic
                    
                    pnl, vol, used_level = SimulationWorker.run_session(
                        current_ga, overrides, tier_map, use_ratchet, 
                        penalty_mode=is_penalty, active_level=active_level, mode=strategy_mode
                    )
                    
                    # Update State
                    active_level = used_level # Persist the level for next session
                    current_ga += pnl
                    m_play_pnl += pnl
                    m_total_volume += vol
                    last_session_won = (pnl > 0)
                    current_year_points += vol * (earn_rate / 100)
            
            if gold_hit_year == -1 and current_year_points >= target_points:
                gold_hit_year = (m // 12) + 1
            
            trajectory.append(current_ga)
            
        return {
            'trajectory': trajectory, 'final_ga': current_ga, 'contrib': m_contrib,
            'tax': m_tax, 'play_pnl': m_play_pnl, 'holidays': m_holidays,
            'insolvent_months': m_insolvent_months, 'total_volume': m_total_volume,
            'gold_year': gold_hit_year, 'failed_y1': failed_year_one
        }

def show_simulator():
    running = False
    
    def load_saved_strategies():
        profile = load_profile()
        return profile.get('saved_strategies', {})

    def update_strategy_list():
        saved = load_saved_strategies()
        select_saved.options = list(saved.keys())
        select_saved.update()

    def save_current_strategy():
        name = input_name.value
        if not name: return
        profile = load_profile()
        if 'saved_strategies' not in profile: profile['saved_strategies'] = {}
        
        config = {
            'sim_num': slider_num_sims.value, 'sim_years': slider_years.value, 'sim_freq': slider_frequency.value,
            'eco_win': slider_contrib_win.value, 'eco_loss': slider_contrib_loss.value, 'eco_tax': switch_luxury_tax.value,
            'eco_hol': switch_holiday.value, 'eco_hol_ceil': slider_holiday_ceil.value, 'eco_insolvency': slider_insolvency.value,
            'eco_tax_thresh': slider_tax_thresh.value, 'eco_tax_rate': slider_tax_rate.value,
            'tac_safety': slider_safety.value, 'tac_iron': slider_iron_gate.value, 'tac_press': select_press.value,
            'tac_depth': slider_press_depth.value, 'tac_shoes': slider_shoes.value, 'tac_bet': select_bet_strat.value,
            'tac_penalty': switch_penalty.value, 
            'tac_mode': select_engine_mode.value, # CHANGED
            'risk_stop': slider_stop_loss.value, 'risk_prof': slider_profit.value,
            'risk_ratch': switch_ratchet.value, 'risk_ratch_mode': select_ratchet_mode.value, 
            'gold_stat': select_status.value, 'gold_earn': slider_earn_rate.value, 'start_ga': slider_start_ga.value
        }
        profile['saved_strategies'][name] = config
        save_profile(profile)
        ui.notify(f'Saved: {name}', type='positive')
        update_strategy_list()

    def load_selected_strategy():
        name = select_saved.value
        if not name: return
        saved = load_saved_strategies()
        config = saved.get(name)
        if not config: return
        
        slider_num_sims.value = config.get('sim_num', 20)
        slider_years.value = config.get('sim_years', 10)
        slider_frequency.value = config.get('sim_freq', 10)
        slider_contrib_win.value = config.get('eco_win', 300)
        slider_contrib_loss.value = config.get('eco_loss', 300)
        switch_luxury_tax.value = config.get('eco_tax', False)
        slider_tax_thresh.value = config.get('eco_tax_thresh', 12500)
        slider_tax_rate.value = config.get('eco_tax_rate', 25)
        switch_holiday.value = config.get('eco_hol', False)
        slider_holiday_ceil.value = config.get('eco_hol_ceil', 10000)
        slider_insolvency.value = config.get('eco_insolvency', 1000) 
        slider_safety.value = config.get('tac_safety', 25)
        slider_iron_gate.value = config.get('tac_iron', 3)
        select_press.value = config.get('tac_press', 1)
        slider_press_depth.value = config.get('tac_depth', 3)
        slider_shoes.value = config.get('tac_shoes', 3)
        select_bet_strat.value = config.get('tac_bet', 'Banker')
        switch_penalty.value = config.get('tac_penalty', True)
        select_engine_mode.value = config.get('tac_mode', 'Standard') # CHANGED
        slider_stop_loss.value = config.get('risk_stop', 10)
        slider_profit.value = config.get('risk_prof', 10)
        switch_ratchet.value = config.get('risk_ratch', False)
        select_ratchet_mode.value = config.get('risk_ratch_mode', 'Standard')
        select_status.value = config.get('gold_stat', 'Gold')
        slider_earn_rate.value = config.get('gold_earn', 10)
        slider_start_ga.value = config.get('start_ga', 2000)
        ui.notify(f'Loaded: {name}', type='info')

    def delete_selected_strategy():
        name = select_saved.value
        if not name: return
        profile = load_profile()
        if 'saved_strategies' in profile and name in profile['saved_strategies']:
            del profile['saved_strategies'][name]
            save_profile(profile)
            ui.notify(f'Deleted: {name}', type='negative')
            select_saved.value = None
            update_strategy_list()

    def update_ladder_preview():
        factor = slider_safety.value
        mode = select_engine_mode.value
        t_map = generate_tier_map(factor, mode=mode)
        
        rows = []
        for level, t in t_map.items():
            if t.min_ga == float('inf'): continue
            risk_pct = 0 if t.min_ga == 0 else (t.base_unit / t.min_ga) * 100
            start_str = f"€{t.min_ga:,.0f}"
            if mode == 'Titan' and level == 3: start_str = "€5,000 (Drop < €3,500)"
            
            rows.append({
                'tier': f"Tier {level}",
                'bet': f"€{t.base_unit} (Press +{t.press_unit})", # Show Press
                'start': start_str,
                'risk': f"{risk_pct:.1f}%"
            })
        ladder_grid.options['rowData'] = rows
        ladder_grid.update()

    async def run_sim():
        nonlocal running
        if running: return
        try:
            running = True; btn_sim.disable(); progress.set_value(0); progress.set_visibility(True)
            label_stats.set_text("Initializing Multiverse...")
            
            config = {
                'num_sims': int(slider_num_sims.value), 'years': int(slider_years.value), 'freq': int(slider_frequency.value),
                'contrib_win': int(slider_contrib_win.value), 'contrib_loss': int(slider_contrib_loss.value),
                'status_target_pts': SBM_TIERS[select_status.value], 'earn_rate': float(slider_earn_rate.value),
                'use_ratchet': switch_ratchet.value, 'ratchet_mode': select_ratchet_mode.value, 
                'use_tax': switch_luxury_tax.value, 'use_holiday': switch_holiday.value,
                'hol_ceil': int(slider_holiday_ceil.value), 'insolvency': int(slider_insolvency.value),
                'safety': int(slider_safety.value), 'start_ga': int(slider_start_ga.value),
                'press_depth': int(slider_press_depth.value), 'tax_thresh': int(slider_tax_thresh.value),
                'tax_rate': int(slider_tax_rate.value), 'strategy_mode': select_engine_mode.value # CHANGED
            }
            
            overrides = StrategyOverrides(
                iron_gate_limit=int(slider_iron_gate.value), stop_loss_units=int(slider_stop_loss.value),
                profit_lock_units=int(slider_profit.value), press_trigger_wins=int(select_press.value),
                press_depth=config['press_depth'], ratchet_lock_pct=0.0, tax_threshold=config['tax_thresh'],
                tax_rate=config['tax_rate'], bet_strategy=(BetStrategy.BANKER if select_bet_strat.value == 'Banker' else BetStrategy.PLAYER),
                shoes_per_session=int(slider_shoes.value), penalty_box_enabled=switch_penalty.value,
                ratchet_enabled=switch_ratchet.value, ratchet_mode=select_ratchet_mode.value 
            )

            start_ga = config['start_ga']
            all_results = []
            batch_size = 10
            for i in range(0, config['num_sims'], batch_size):
                count = min(batch_size, config['num_sims'] - i)
                def run_batch_careers():
                    batch_data = []
                    for _ in range(count):
                        res = SimulationWorker.run_full_career(
                            start_ga, config['years']*12, config['freq'],
                            config['contrib_win'], config['contrib_loss'], overrides, 
                            config['use_ratchet'], config['use_tax'], config['use_holiday'], 
                            config['safety'], config['status_target_pts'], config['earn_rate'],
                            config['hol_ceil'], config['insolvency'], config['strategy_mode']
                        )
                        batch_data.append(res)
                    return batch_data

                batch_res = await asyncio.to_thread(run_batch_careers)
                all_results.extend(batch_res)
                progress.set_value(len(all_results) / config['num_sims'])
                label_stats.set_text(f"Simulating Universe {len(all_results)}/{config['num_sims']}")

            label_stats.set_text("Analyzing Data...")
            render_analysis(all_results, config, start_ga, overrides)
            label_stats.set_text("Simulation Complete")

        except Exception as e:
            print(traceback.format_exc())
            ui.notify(f"Error: {str(e)}", type='negative', close_button=True)
        finally:
            running = False; btn_sim.enable(); progress.set_visibility(False)

    def render_analysis(results, config, start_ga, overrides):
        if not results: return
        
        trajectories = np.array([r['trajectory'] for r in results])
        months = list(range(trajectories.shape[1]))
        min_band = np.min(trajectories, axis=0); max_band = np.max(trajectories, axis=0)
        p25_band = np.percentile(trajectories, 25, axis=0); p75_band = np.percentile(trajectories, 75, axis=0)
        mean_line = np.mean(trajectories, axis=0)
        
        avg_final_ga = np.mean([r['final_ga'] for r in results])
        avg_tax = np.mean([r['tax'] for r in results])
        avg_insolvent = np.mean([r['insolvent_months'] for r in results])
        
        gold_hits = [r['gold_year'] for r in results if r['gold_year'] != -1]
        gold_prob = (len(gold_hits) / len(results)) * 100
        avg_year_hit = np.mean(gold_hits) if gold_hits else 0
        
        total_months = config['years'] * 12
        insolvency_pct = (avg_insolvent / total_months) * 100
        y1_failures = len([r for r in results if r['failed_y1']])
        y1_survival_rate = 100 - ((y1_failures / len(results)) * 100)
        
        total_input = start_ga + np.mean([r['contrib'] for r in results])
        total_output = avg_final_ga + avg_tax
        net_cost = total_input - total_output
        real_monthly_cost = net_cost / total_months
        
        survivor_count = len([r for r in results if r['final_ga'] >= 1500])
        score_survival = (survivor_count / len(results)) * 100
        if real_monthly_cost <= 0: score_cost = 100
        else: score_cost = max(0, 100 - (real_monthly_cost / 3)) 
        
        total_score = (gold_prob * 0.30) + (score_survival * 0.30) + (score_cost * 0.20) + ((100-insolvency_pct) * 0.20)
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
                            ui.label('STRATEGY GRADE').classes('text-xs text-slate-400 font-bold tracking-widest')
                            ui.label(f"{grade}").classes(f'text-6xl font-black {g_col} leading-none')
                            ui.label(f"{total_score:.1f}% Score").classes(f'text-sm font-bold {g_col}')
                        with ui.column().classes('items-center'):
                            ui.label('REAL MONTHLY COST').classes('text-[10px] text-slate-500 font-bold tracking-widest')
                            if real_monthly_cost > 0:
                                ui.label(f"€{real_monthly_cost:,.0f}").classes('text-4xl font-black text-red-400 leading-none')
                                ui.label("Net Cost").classes('text-xs font-bold text-red-900 bg-red-400 px-1 rounded')
                            else:
                                ui.label(f"+€{abs(real_monthly_cost):,.0f}").classes('text-4xl font-black text-green-400 leading-none')
                                ui.label("Net Profit").classes('text-xs font-bold text-green-900 bg-green-400 px-1 rounded')
                        with ui.column().classes('items-center'):
                            ui.label('GRAND TOTAL WEALTH').classes('text-[10px] text-slate-500 font-bold tracking-widest')
                            ui.label(f"€{total_output:,.0f}").classes('text-4xl font-black text-white leading-none')
                            if avg_tax > 0: ui.label(f"(GA €{avg_final_ga:,.0f} + Tax €{avg_tax:,.0f})").classes('text-xs font-bold text-yellow-400')

                    ui.separator().classes('bg-slate-700')
                    with ui.grid(columns=4).classes('w-full gap-4'):
                        with ui.column().classes('items-center'):
                            ui.label('Gold Chase').classes('text-[10px] text-slate-500 uppercase')
                            ui.label(f"{gold_prob:.0f}%").classes('text-2xl font-bold text-yellow-400')
                            if gold_prob > 0: ui.label(f"Year {avg_year_hit:.1f}").classes('text-[10px] text-slate-500')
                        with ui.column().classes('items-center'):
                            ui.label('Year 1 Survival').classes('text-[10px] text-slate-500 uppercase')
                            ui.label(f"{y1_survival_rate:.1f}%").classes(f'text-2xl font-bold {"text-green-400" if y1_survival_rate==100 else "text-red-400"}')
                        with ui.column().classes('items-center'):
                            ui.label('Cost Effic.').classes('text-[10px] text-slate-500 uppercase')
                            ui.label(f"{score_cost:.0f}%").classes('text-2xl font-bold text-green-400')
                        with ui.column().classes('items-center'):
                            ui.label('Total Survival').classes('text-[10px] text-slate-500 uppercase')
                            ui.label(f"{score_survival:.0f}%").classes('text-2xl font-bold text-blue-400')

        with chart_container:
            chart_container.clear()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=months + months[::-1], y=np.concatenate([max_band, min_band[::-1]]), fill='toself', fillcolor='rgba(148, 163, 184, 0.5)', line=dict(color='rgba(255,255,255,0.3)', width=1), name='Best/Worst'))
            fig.add_trace(go.Scatter(x=months + months[::-1], y=np.concatenate([p75_band, p25_band[::-1]]), fill='toself', fillcolor='rgba(0, 255, 136, 0.3)', line=dict(color='rgba(255,255,255,0)'), name='Likely'))
            fig.add_trace(go.Scatter(x=months, y=mean_line, mode='lines', name='Average', line=dict(color='white', width=2)))
            fig.add_hline(y=config['insolvency'], line_dash="dash", line_color="red", annotation_text="Insolvency")
            if config['use_holiday']: fig.add_hline(y=config['hol_ceil'], line_dash="dash", line_color="yellow", annotation_text="Holiday")
            fig.update_layout(title='Monte Carlo Confidence Bands', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'), margin=dict(l=20, r=20, t=40, b=20), xaxis=dict(title='Months Passed', gridcolor='#334155'), yaxis=dict(title='Game Account (€)', gridcolor='#334155'), showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            ui.plotly(fig).classes('w-full h-96')

        with report_container:
            report_container.clear()
            lines = ["=== CONFIGURATION ==="]
            lines.append(f"Sims: {config['num_sims']} | Years: {config['years']} | Mode: {config['strategy_mode']}")
            lines.append(f"Betting: {overrides.bet_strategy.name} | Shoes/Sess: {overrides.shoes_per_session}")
            lines.append(f"Gold Probability: {gold_prob:.1f}%")
            if config['strategy_mode'] == 'Titan':
                lines.append("TITAN HYSTERESIS: Active")
                lines.append(" - Tier 2 (100/150) -> Tier 3 (150/250) @ €5,000")
                lines.append(" - Drop back to Tier 2 only if < €3,500")
            elif config['strategy_mode'] == 'Fortress':
                lines.append("FORTRESS MODE: Active (Cap @ 100)")
            ui.html(f'<pre style="white-space: pre-wrap; font-family: monospace; color: #94a3b8; font-size: 0.75rem;">{"\n".join(lines)}</pre>', sanitize=False)

    # --- MAIN UI ---
    with ui.column().classes('w-full max-w-4xl mx-auto gap-6 p-4'):
        ui.label('RESEARCH LAB: MY MONTE-CARLO').classes('text-2xl font-light text-slate-300')
        with ui.card().classes('w-full bg-slate-900 p-6 gap-4'):
            
            # Library Panel
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

            # Engine Controls
            with ui.row().classes('w-full gap-4 items-start'):
                with ui.column().classes('flex-grow'):
                    ui.label('SIMULATION').classes('font-bold text-white mb-2')
                    with ui.row().classes('w-full justify-between'):
                        ui.label('Universes').classes('text-xs text-slate-400'); lbl_num_sims = ui.label()
                    slider_num_sims = ui.slider(min=10, max=100, value=20).props('color=cyan')
                    lbl_num_sims.bind_text_from(slider_num_sims, 'value', lambda v: f'{v}')
                    
                    with ui.row().classes('w-full justify-between'):
                        ui.label('Duration (Years)').classes('text-xs text-slate-400'); lbl_years = ui.label()
                    slider_years = ui.slider(min=1, max=10, value=10).props('color=blue')
                    lbl_years.bind_text_from(slider_years, 'value', lambda v: f'{v}')
                    
                    with ui.row().classes('w-full justify-between'):
                        ui.label('Freq (Sess/Yr)').classes('text-xs text-slate-400'); lbl_freq = ui.label()
                    slider_frequency = ui.slider(min=9, max=50, value=10).props('color=blue')
                    lbl_freq.bind_text_from(slider_frequency, 'value', lambda v: f'{v}')

                with ui.column().classes('w-1/2'):
                    ui.label('LADDER PREVIEW').classes('font-bold text-white mb-2')
                    with ui.expansion('View Table', icon='list').classes('w-full bg-slate-800 text-slate-300'):
                        ladder_grid = ui.aggrid({'columnDefs': [{'headerName': 'Tier', 'field': 'tier', 'width': 70},{'headerName': 'Bet', 'field': 'bet', 'width': 120},{'headerName': 'Start GA', 'field': 'start', 'width': 120}],'rowData': []}).classes('h-40 w-full theme-balham-dark')

            ui.separator().classes('bg-slate-700')

            # Strategy Controls
            with ui.grid(columns=2).classes('w-full gap-8'):
                with ui.column():
                    ui.label('TACTICS').classes('font-bold text-purple-400')
                    
                    select_engine_mode = ui.select(['Standard', 'Fortress', 'Titan'], value='Standard', label='Betting Engine').classes('w-full').on_value_change(update_ladder_preview)
                    
                    with ui.row().classes('w-full justify-between'):
                        ui.label('Safety Buffer').classes('text-xs text-orange-400'); lbl_safe = ui.label()
                    slider_safety = ui.slider(min=10, max=60, value=25, on_change=update_ladder_preview).props('color=orange')
                    lbl_safe.bind_text_from(slider_safety, 'value', lambda v: f'{v}x')
                    
                    # Ecosystem Sliders (Simplified layout for brevity)
                    ui.label('ECOSYSTEM').classes('font-bold text-green-400 mt-4')
                    slider_contrib_win = ui.slider(min=0, max=1000, value=300).props('color=green'); ui.label().bind_text_from(slider_contrib_win, 'value', lambda v: f'Win +€{v}')
                    slider_contrib_loss = ui.slider(min=0, max=1000, value=300).props('color=orange'); ui.label().bind_text_from(slider_contrib_loss, 'value', lambda v: f'Loss +€{v}')
                    
                    with ui.row().classes('mt-2'):
                        switch_luxury_tax = ui.switch('Tax').props('color=gold')
                        switch_holiday = ui.switch('Holiday').props('color=blue')
                        switch_penalty = ui.switch('Penalty Box').props('color=red'); switch_penalty.value = True

                    # Hidden complex settings
                    with ui.expansion('Adv. Eco Settings', icon='tune').classes('w-full bg-slate-800 text-xs'):
                        slider_holiday_ceil = ui.slider(min=5000, max=50000, value=10000); ui.label().bind_text_from(slider_holiday_ceil, 'value', lambda v: f'Hol Ceil €{v}')
                        slider_insolvency = ui.slider(min=0, max=5000, value=1000); ui.label().bind_text_from(slider_insolvency, 'value', lambda v: f'Floor €{v}')
                        slider_tax_thresh = ui.slider(min=5000, max=50000, value=12500); ui.label().bind_text_from(slider_tax_thresh, 'value', lambda v: f'Tax Thresh €{v}')
                        slider_tax_rate = ui.slider(min=5, max=50, value=25)

                with ui.column():
                    ui.label('GAMEPLAY').classes('font-bold text-red-400')
                    select_bet_strat = ui.select(['Banker', 'Player'], value='Banker', label='Bet Strategy').classes('w-full')
                    slider_shoes = ui.slider(min=1, max=5, value=3).props('color=blue'); ui.label().bind_text_from(slider_shoes, 'value', lambda v: f'{v} Shoes')
                    
                    slider_stop_loss = ui.slider(min=5, max=50, value=10).props('color=red'); ui.label().bind_text_from(slider_stop_loss, 'value', lambda v: f'Stop {v}u')
                    slider_profit = ui.slider(min=3, max=50, value=10).props('color=green'); ui.label().bind_text_from(slider_profit, 'value', lambda v: f'Target {v}u')
                    
                    with ui.row().classes('items-center justify-between'):
                         switch_ratchet = ui.switch('Ratchet').props('color=gold')
                         select_ratchet_mode = ui.select(['Sprint', 'Standard', 'Deep Stack', 'Gold Grinder'], value='Standard').props('dense options-dense').classes('w-32')

                    ui.separator().classes('bg-slate-700 my-2')
                    select_press = ui.select({0: 'Flat', 1: 'Press 1-Win', 2: 'Press 2-Wins'}, value=1, label='Press Logic').classes('w-full')
                    slider_press_depth = ui.slider(min=0, max=5, value=3).props('color=red')
                    
                    ui.separator().classes('bg-slate-700 my-2')
                    slider_iron_gate = ui.slider(min=2, max=6, value=3).props('color=purple'); ui.label().bind_text_from(slider_iron_gate, 'value', lambda v: f'Iron Gate {v}')

            ui.separator().classes('bg-slate-700')
            
            with ui.row().classes('w-full items-center justify-between'):
                with ui.column():
                     ui.label('Starting Capital').classes('text-xs text-green-400')
                     slider_start_ga = ui.slider(min=1000, max=10000, value=5000, step=100).props('color=green')
                     ui.label().bind_text_from(slider_start_ga, 'value', lambda v: f'€{v}')
                     
                     with ui.row().classes('gap-4 mt-2'):
                         select_status = ui.select(list(SBM_TIERS.keys()), value='Gold').props('dense')
                         slider_earn_rate = ui.slider(min=1, max=20, value=10).props('color=yellow').classes('w-32')
                
                btn_sim = ui.button('RUN SIM', on_click=run_sim).props('icon=play_arrow color=yellow text-color=black size=lg')
        
        label_stats = ui.label('Ready...').classes('text-sm text-slate-500')
        progress = ui.linear_progress().props('color=green').classes('mt-0'); progress.set_visibility(False)
        scoreboard_container = ui.column().classes('w-full mb-4')
        chart_container = ui.card().classes('w-full bg-slate-900 p-4')
        report_container = ui.column().classes('w-full')
        
        update_ladder_preview()
