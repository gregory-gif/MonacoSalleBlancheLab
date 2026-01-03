from nicegui import ui
import plotly.graph_objects as go
import random
import asyncio
import traceback
import numpy as np
import json

# IMPORT RULES
from engine.baccarat_rules import BaccaratSessionState, BaccaratStrategist
from engine.strategy_rules import StrategyOverrides, BetStrategy
from engine.tier_params import TierConfig, generate_tier_map, get_tier_for_ga
from utils.persistence import load_profile, save_profile

SBM_TIERS = {'Silver': 5000, 'Gold': 22500, 'Platinum': 175000}

class BaccaratWorker:
    @staticmethod
    def run_session(current_ga: float, overrides: StrategyOverrides, tier_map: dict, use_ratchet: bool, penalty_mode: bool, active_level: int, mode: str, base_bet: float = 10.0, track_hands: bool = False):
        tier = get_tier_for_ga(current_ga, tier_map, active_level, mode, game_type='Baccarat')
        
        hand_log = []
        session_peak_profit = 0
        
        is_active_penalty = penalty_mode and overrides.penalty_box_enabled
        if is_active_penalty:
            flat_bet = base_bet 
            tier = TierConfig(level=tier.level, min_ga=0, max_ga=9999999, base_unit=flat_bet, press_unit=flat_bet, stop_loss=tier.stop_loss, profit_lock=tier.profit_lock, catastrophic_cap=tier.catastrophic_cap)
            session_overrides = StrategyOverrides(
                iron_gate_limit=overrides.iron_gate_limit, stop_loss_units=overrides.stop_loss_units,
                profit_lock_units=overrides.profit_lock_units, shoes_per_session=overrides.shoes_per_session,
                bet_strategy=overrides.bet_strategy, press_trigger_wins=999, press_depth=0, ratchet_enabled=False 
            )
        else:
            session_overrides = overrides

        if use_ratchet and not is_active_penalty:
            session_overrides.ratchet_enabled = True
            session_overrides.profit_lock_units = 1000 if session_overrides.profit_lock_units <= 0 else session_overrides.profit_lock_units

        state = BaccaratSessionState(tier=tier, overrides=session_overrides)
        state.current_shoe = 1
        volume = 0
        
        while state.current_shoe <= overrides.shoes_per_session and state.mode.name != 'STOPPED':
            decision = BaccaratStrategist.get_next_decision(state)
            if decision['mode'].name == 'STOPPED': break
            
            amt = decision['bet_amount']
            volume += amt
            
            # Check if we should place a tie bet this hand (1 unit after a tie)
            tie_bet_amt = 0
            if state.place_tie_bet_this_hand and amt > 0 and session_overrides.tie_bet_enabled:
                tie_bet_amt = tier.base_unit  # Always 1 base unit
                volume += tie_bet_amt
                state.tie_bets_placed += 1
            
            # Simulation Physics - Realistic Baccarat Probabilities
            is_banker = (overrides.bet_strategy == BetStrategy.BANKER)
            rng = random.random()
            
            # Probabilities: Banker 45.86%, Player 44.62%, Tie 9.52%
            if rng < 0.4586:  # Banker wins
                outcome = 'BANKER'
            elif rng < 0.9048:  # Player wins (0.4586 + 0.4462)
                outcome = 'PLAYER'
            else:  # Tie
                outcome = 'TIE'
            
            pnl = 0
            is_tie = False
            tie_bet_pnl = 0
            
            if outcome == 'TIE':
                # Tie: Main bet pushes (no win/loss), tie bet wins 8:1
                is_tie = True
                state.tie_count += 1
                if tie_bet_amt > 0:
                    tie_bet_pnl = tie_bet_amt * 8  # Win 8:1 on tie bet
                    pnl = tie_bet_pnl
            else:
                # Main bet resolution
                main_bet_won = (outcome == 'BANKER' and is_banker) or (outcome == 'PLAYER' and not is_banker)
                
                if main_bet_won:
                    pnl = amt * 0.95 if is_banker else amt
                else:
                    pnl = -amt
                
                # Tie bet loses if placed
                if tie_bet_amt > 0:
                    tie_bet_pnl = -tie_bet_amt
                    pnl += tie_bet_pnl
            
            # Track tie bet P&L separately
            state.tie_bets_pnl += tie_bet_pnl
            
            # Track hand-by-hand bankroll evolution
            if track_hands:
                hand_log.append({
                    'hand': state.hands_played_total + 1,
                    'shoe': state.current_shoe,
                    'bankroll': current_ga + state.session_pnl + pnl,
                    'session_pl': state.session_pnl + pnl,
                    'bet_size': amt,
                    'outcome': outcome,
                    'won': main_bet_won if outcome != 'TIE' else None,
                    'tie_bet_placed': tie_bet_amt > 0,
                    'tie_bet_pnl': tie_bet_pnl,
                    'press_level': state.current_press_streak,
                    'in_virtual': state.is_in_virtual_mode
                })
            
            # Update peak profit
            if state.session_pnl + pnl > session_peak_profit:
                session_peak_profit = state.session_pnl + pnl
            
            # Update state with outcome
            main_bet_won = (outcome == 'BANKER' and is_banker) or (outcome == 'PLAYER' and not is_banker)
            BaccaratStrategist.update_state_after_hand(state, main_bet_won, pnl, is_tie)
            
            if state.hands_played_in_shoe >= 70:
                state.current_shoe += 1
                state.hands_played_in_shoe = 0

        # Determine exit reason
        exit_reason = 'TIME_LIMIT'
        if state.mode.name == 'STOPPED':
            stop_val = -(overrides.stop_loss_units * tier.base_unit)
            target_val = overrides.profit_lock_units * tier.base_unit
            if state.session_pnl <= stop_val:
                exit_reason = 'STOP_LOSS'
            elif state.session_pnl >= target_val:
                exit_reason = 'TARGET'
            elif state.session_pnl <= state.locked_profit:
                exit_reason = 'RATCHET'

        return state.session_pnl, volume, tier.level, state.hands_played_total, exit_reason, state.current_press_streak, state.tie_count, state.tie_bets_placed, state.tie_bets_pnl, hand_log, session_peak_profit

    @staticmethod
    def run_full_career(start_ga, total_months, sessions_per_year, 
                        contrib_win, contrib_loss, overrides, use_ratchet,
                        use_tax, use_holiday, safety_factor, target_points, earn_rate,
                        holiday_ceiling, insolvency_floor, strategy_mode, base_bet_val,
                        track_y1_details=False):
        
        tier_map = generate_tier_map(safety_factor, mode=strategy_mode, game_type='Baccarat', base_bet=base_bet_val)
        trajectory = []
        current_ga = start_ga
        running_play_pnl = 0
        
        initial_tier = get_tier_for_ga(current_ga, tier_map, 1, strategy_mode, game_type='Baccarat')
        active_level = initial_tier.level

        m_insolvent_months = 0; failed_year_one = False
        m_tax = 0 
        m_contrib = 0
        gold_hit_year = -1
        current_year_points = 0
        
        y1_log = []
        last_session_won = False
        y1_session_counter = 0

        for m in range(total_months):
            if m > 0 and m % 12 == 0: current_year_points = 0

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
                    pnl, vol, used_level, hands, exit_reason, final_streak, tie_count, tie_bets, tie_pnl = BaccaratWorker.run_session(
                        current_ga, overrides, tier_map, use_ratchet, 
                        False, active_level, strategy_mode, base_bet_val
                    )
                    active_level = used_level 
                    current_ga += pnl
                    running_play_pnl += pnl
                    current_year_points += vol * (earn_rate / 100)
                    last_session_won = (pnl > 0)
                    
                    if track_y1_details and m < 12:
                        y1_session_counter += 1
                        y1_log.append({
                            'month': m + 1,
                            'session': y1_session_counter,
                            'result': pnl,
                            'balance': current_ga,
                            'game_bal': start_ga + running_play_pnl,
                            'hands': hands,
                            'volume': vol,
                            'tier': used_level,
                            'exit': exit_reason,
                            'streak_max': final_streak,
                            'tie_count': tie_count,
                            'tie_bets': tie_bets,
                            'tie_pnl': tie_pnl
                        })
            else:
                 if track_y1_details and m < 12:
                        y1_log.append({
                            'month': m + 1,
                            'session': 0,
                            'result': 0,
                            'balance': current_ga,
                            'game_bal': start_ga + running_play_pnl,
                            'hands': 0,
                            'volume': 0,
                            'tier': 0,
                            'exit': 'INSOLVENT',
                            'streak_max': 0,
                            'tie_count': 0,
                            'tie_bets': 0,
                            'tie_pnl': 0
                        })

            if gold_hit_year == -1 and current_year_points >= target_points:
                gold_hit_year = (m // 12) + 1

            trajectory.append(current_ga)
            
        return {
            'trajectory': trajectory, 'final_ga': current_ga, 'insolvent_months': m_insolvent_months, 
            'failed_y1': failed_year_one, 'tax': m_tax, 'contrib': m_contrib, 'gold_year': gold_hit_year,
            'y1_log': y1_log
        }

def calculate_stats(results, config, start_ga, total_months):
    if not results: return None
    trajectories = np.array([r['trajectory'] for r in results])
    months = list(range(trajectories.shape[1]))
    
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
        'survivor_count': len([r for r in results if r['final_ga'] >= 100])
    }
    return stats

def show_simulator():
    running = False
    session_detail_data = {} 
    
    def load_saved_strategies():
        try: return load_profile().get('saved_strategies', {})
        except: return {}
    def update_strategy_list():
        try: select_saved.options = list(load_saved_strategies().keys()); select_saved.update()
        except: pass
    
    def save_current_strategy():
        try:
            name = input_name.value
            if not name: return
            profile = load_profile()
            if 'saved_strategies' not in profile: profile['saved_strategies'] = {}
            config = {
                'sim_num': slider_num_sims.value, 'years': slider_years.value, 'freq': slider_frequency.value,
                'eco_win': slider_contrib_win.value, 'eco_loss': slider_contrib_loss.value, 'eco_tax': switch_luxury_tax.value,
                'eco_hol': switch_holiday.value, 'eco_hol_ceil': slider_holiday_ceil.value, 'eco_insolvency': slider_insolvency.value,
                'eco_tax_thresh': slider_tax_thresh.value, 'eco_tax_rate': slider_tax_rate.value,
                'tac_safety': slider_safety.value, 'tac_iron': slider_iron_gate.value, 'tac_press': select_press.value,
                'tac_depth': slider_press_depth.value, 'tac_shoes': slider_shoes.value, 'tac_bet': select_bet_strat.value,
                'tac_penalty': switch_penalty.value, 'tac_mode': select_engine_mode.value, 
                'risk_stop': slider_stop_loss.value, 'risk_prof': slider_profit.value,
                'risk_ratch': switch_ratchet.value, 'risk_ratch_mode': select_ratchet_mode.value, 
                'gold_stat': select_status.value, 'gold_earn': slider_earn_rate.value, 'start_ga': slider_start_ga.value,
                'tac_base_bet': slider_base_bet.value,
                'tie_bet_enabled': switch_tie_bet.value,
                # Smart Trailing Stop
                'smart_exit_enabled': switch_smart_exit.value,
                'smart_window_start': slider_smart_window.value,
                'min_profit_to_lock': slider_min_lock.value,
                'trailing_drop_pct': slider_trail_pct.value,
                # Doctrine Engine
                'doctrine_enabled': switch_doctrine_enabled.value,
                'doctrine_pl_stop': slider_doctrine_pl_stop.value,
                'doctrine_pl_target': slider_doctrine_pl_target.value,
                'doctrine_pl_press_wins': slider_doctrine_pl_press_wins.value,
                'doctrine_pl_press_depth': slider_doctrine_pl_press_depth.value,
                'doctrine_pl_iron': slider_doctrine_pl_iron.value,
                'doctrine_ti_stop': slider_doctrine_ti_stop.value,
                'doctrine_ti_target': slider_doctrine_ti_target.value,
                'doctrine_ti_press_wins': slider_doctrine_ti_press_wins.value,
                'doctrine_ti_press_depth': slider_doctrine_ti_press_depth.value,
                'doctrine_ti_iron': slider_doctrine_ti_iron.value,
                'doctrine_loss_trigger': slider_doctrine_loss_trigger.value,
                'doctrine_dd_pct': slider_doctrine_dd_pct.value,
                'doctrine_dd_eur': slider_doctrine_dd_eur.value,
                'doctrine_tight_min': slider_doctrine_tight_min.value,
                'doctrine_tight_max': slider_doctrine_tight_max.value,
                'doctrine_cooloff_enabled': switch_doctrine_cooloff.value,
                'doctrine_cooloff_floor': slider_doctrine_cooloff_floor.value,
                'doctrine_cooloff_months': slider_doctrine_cooloff_months.value,
                'doctrine_recovery_pct': slider_doctrine_recovery_pct.value
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
            slider_num_sims.value = config.get('sim_num', 20)
            slider_years.value = config.get('years', 10)
            slider_frequency.value = config.get('freq', 10)
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
            
            raw_bet = config.get('tac_bet', 'BANKER')
            if not raw_bet: raw_bet = 'BANKER'
            select_bet_strat.value = raw_bet
            
            switch_penalty.value = config.get('tac_penalty', True)
            select_engine_mode.value = config.get('tac_mode', 'Standard') 
            slider_stop_loss.value = config.get('risk_stop', 10)
            slider_profit.value = config.get('risk_prof', 10)
            switch_ratchet.value = config.get('risk_ratch', False)
            select_ratchet_mode.value = config.get('risk_ratch_mode', 'Standard')
            select_status.value = config.get('gold_stat', 'Gold')
            slider_earn_rate.value = config.get('gold_earn', 10)
            slider_start_ga.value = config.get('start_ga', 2000)
            slider_base_bet.value = config.get('tac_base_bet', 5.0)
            switch_tie_bet.value = config.get('tie_bet_enabled', False)
            
            # Smart Trailing Stop LOADS
            switch_smart_exit.value = config.get('smart_exit_enabled', True)
            slider_smart_window.value = config.get('smart_window_start', 190)
            slider_min_lock.value = config.get('min_profit_to_lock', 20)
            slider_trail_pct.value = config.get('trailing_drop_pct', 0.20)
            
            # Doctrine Engine LOADS
            switch_doctrine_enabled.value = config.get('doctrine_enabled', False)
            slider_doctrine_pl_stop.value = config.get('doctrine_pl_stop', 10)
            slider_doctrine_pl_target.value = config.get('doctrine_pl_target', 10)
            slider_doctrine_pl_press_wins.value = config.get('doctrine_pl_press_wins', 3)
            slider_doctrine_pl_press_depth.value = config.get('doctrine_pl_press_depth', 3)
            slider_doctrine_pl_iron.value = config.get('doctrine_pl_iron', 3)
            slider_doctrine_ti_stop.value = config.get('doctrine_ti_stop', 5)
            slider_doctrine_ti_target.value = config.get('doctrine_ti_target', 5)
            slider_doctrine_ti_press_wins.value = config.get('doctrine_ti_press_wins', 5)
            slider_doctrine_ti_press_depth.value = config.get('doctrine_ti_press_depth', 1)
            slider_doctrine_ti_iron.value = config.get('doctrine_ti_iron', 2)
            slider_doctrine_loss_trigger.value = config.get('doctrine_loss_trigger', 8)
            slider_doctrine_dd_pct.value = config.get('doctrine_dd_pct', 0.15)
            slider_doctrine_dd_eur.value = config.get('doctrine_dd_eur', 3000)
            slider_doctrine_tight_min.value = config.get('doctrine_tight_min', 1)
            slider_doctrine_tight_max.value = config.get('doctrine_tight_max', 2)
            switch_doctrine_cooloff.value = config.get('doctrine_cooloff_enabled', True)
            slider_doctrine_cooloff_floor.value = config.get('doctrine_cooloff_floor', 3000)
            slider_doctrine_cooloff_months.value = config.get('doctrine_cooloff_months', 1)
            slider_doctrine_recovery_pct.value = config.get('doctrine_recovery_pct', 0.07)
            
            ui.notify(f'Loaded: {name}', type='info')
        except: pass

    def delete_selected_strategy():
        try:
            name = select_saved.value
            if not name: return
            profile = load_profile()
            if 'saved_strategies' in profile and name in profile['saved_strategies']:
                del profile['saved_strategies'][name]
                save_profile(profile)
                ui.notify(f'Deleted: {name}', type='negative')
                select_saved.value = None
                update_strategy_list()
        except: pass

    def update_ladder_preview():
        try:
            factor = slider_safety.value
            mode = select_engine_mode.value
            base = slider_base_bet.value 
            t_map = generate_tier_map(factor, mode=mode, game_type='Baccarat', base_bet=base)
            rows = []
            for level, t in t_map.items():
                if t.min_ga == float('inf'): continue
                risk_pct = 0 if t.min_ga == 0 else (t.base_unit / t.min_ga) * 100
                start_str = f"€{t.min_ga:,.0f}"
                rows.append({'tier': f"Tier {level}", 'bet': f"€{t.base_unit} (Press +{t.press_unit})", 'start': start_str, 'risk': f"{risk_pct:.1f}%"})
            ladder_grid.options['rowData'] = rows
            ladder_grid.update()
        except Exception as e: pass 

    # --- QUICK REFRESH ---
    async def refresh_single_universe():
        nonlocal session_detail_data
        try:
            config = {
                'years': int(slider_years.value), 'freq': int(slider_frequency.value),
                'contrib_win': int(slider_contrib_win.value), 'contrib_loss': int(slider_contrib_loss.value),
                'use_ratchet': switch_ratchet.value, 'use_tax': switch_luxury_tax.value,
                'use_holiday': switch_holiday.value, 'hol_ceil': int(slider_holiday_ceil.value),
                'insolvency': int(slider_insolvency.value), 'safety': int(slider_safety.value),
                'start_ga': int(slider_start_ga.value), 'tax_thresh': int(slider_tax_thresh.value),
                'tax_rate': int(slider_tax_rate.value), 'strategy_mode': select_engine_mode.value,
                'status_target_pts': 0, 'earn_rate': 0,
                'base_bet': float(slider_base_bet.value) 
            }
            
            raw_bet = select_bet_strat.value
            if not raw_bet: raw_bet = 'BANKER'
            
            overrides = StrategyOverrides(
                iron_gate_limit=int(slider_iron_gate.value), stop_loss_units=int(slider_stop_loss.value),
                profit_lock_units=int(slider_profit.value), press_trigger_wins=int(select_press.value),
                press_depth=int(slider_press_depth.value), ratchet_lock_pct=0.0, tax_threshold=config['tax_thresh'],
                tax_rate=config['tax_rate'], bet_strategy=getattr(BetStrategy, raw_bet),
                shoes_per_session=int(slider_shoes.value), penalty_box_enabled=switch_penalty.value,
                ratchet_enabled=switch_ratchet.value, ratchet_mode=select_ratchet_mode.value,
                tie_bet_enabled=switch_tie_bet.value,
                # Smart Trailing Stop
                smart_exit_enabled=switch_smart_exit.value,
                smart_window_start=int(slider_smart_window.value),
                min_profit_to_lock=int(slider_min_lock.value),
                trailing_drop_pct=float(slider_trail_pct.value),
                # Doctrine Engine
                doctrine_enabled=switch_doctrine_enabled.value,
                doctrine_pl_stop=float(slider_doctrine_pl_stop.value),
                doctrine_pl_target=float(slider_doctrine_pl_target.value),
                doctrine_pl_press_wins=int(slider_doctrine_pl_press_wins.value),
                doctrine_pl_press_depth=int(slider_doctrine_pl_press_depth.value),
                doctrine_pl_iron=int(slider_doctrine_pl_iron.value),
                doctrine_ti_stop=float(slider_doctrine_ti_stop.value),
                doctrine_ti_target=float(slider_doctrine_ti_target.value),
                doctrine_ti_press_wins=int(slider_doctrine_ti_press_wins.value),
                doctrine_ti_press_depth=int(slider_doctrine_ti_press_depth.value),
                doctrine_ti_iron=int(slider_doctrine_ti_iron.value),
                doctrine_loss_trigger=float(slider_doctrine_loss_trigger.value),
                doctrine_dd_pct_trigger=float(slider_doctrine_dd_pct.value),
                doctrine_dd_eur_trigger=float(slider_doctrine_dd_eur.value),
                doctrine_tight_min=int(slider_doctrine_tight_min.value),
                doctrine_tight_max=int(slider_doctrine_tight_max.value),
                doctrine_cooloff_enabled=switch_doctrine_cooloff.value,
                doctrine_cooloff_floor=float(slider_doctrine_cooloff_floor.value),
                doctrine_cooloff_min_months=int(slider_doctrine_cooloff_months.value),
                doctrine_cooloff_recovery_pct=float(slider_doctrine_recovery_pct.value)
            )
            
            res = await asyncio.to_thread(BaccaratWorker.run_full_career, 
                config['start_ga'], config['years']*12, config['freq'],
                config['contrib_win'], config['contrib_loss'], overrides, 
                config['use_ratchet'], config['use_tax'], config['use_holiday'], 
                config['safety'], config['status_target_pts'], config['earn_rate'],
                config['hol_ceil'], config['insolvency'], config['strategy_mode'],
                config['base_bet'],
                False 
            )
            
            # Capture first session details for hand-by-hand analysis
            tier_map = generate_tier_map(config['safety'], mode=config['strategy_mode'], game_type='Baccarat', base_bet=config['base_bet'])
            pnl, vol, lvl, hands, exit_reason, streak, tie_count, tie_bets, tie_pnl, hand_log, peak_profit = await asyncio.to_thread(
                BaccaratWorker.run_session,
                config['start_ga'], overrides, tier_map, config['use_ratchet'], 
                switch_penalty.value, 1, config['strategy_mode'], config['base_bet'], True
            )
            session_detail_data['pnl'] = pnl
            session_detail_data['hands'] = hands
            session_detail_data['exit_reason'] = exit_reason
            session_detail_data['peak_profit'] = peak_profit
            session_detail_data['hand_log'] = hand_log
            session_detail_data['start_bankroll'] = config['start_ga']
            
            chart_single_container.clear()
            with chart_single_container:
                ui.label('QUICK BACCARAT REALITY CHECK').classes('text-xs text-cyan-400 font-bold mb-1')
                fig = go.Figure()
                fig.add_trace(go.Scatter(y=res['trajectory'], mode='lines', name='Balance', line=dict(color='#06b6d4', width=2)))
                fig.add_hline(y=config['insolvency'], line_dash="dash", line_color="red")
                fig.update_layout(height=250, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'))
                ui.plotly(fig).classes('w-full border border-slate-700 rounded')
            
            render_session_detail()

        except Exception as e:
            ui.notify(str(e), type='negative')
    
    def render_session_detail():
        """Render the session detail UI with bankroll evolution graph"""
        if not session_detail_data or not session_detail_data.get('hand_log'):
            return
        
        with session_detail_container:
            session_detail_container.clear()
            
            hand_log = session_detail_data['hand_log']
            start_bankroll = session_detail_data['start_bankroll']
            
            with ui.expansion('OUR LOG (Session 1) - Bankroll Evolution', icon='show_chart', value=False).classes('w-full bg-slate-800 text-slate-300 border-2 border-slate-600'):
                with ui.column().classes('w-full gap-2 p-2'):
                    # Session Summary
                    with ui.row().classes('w-full gap-4 items-center'):
                        ui.label(f"Final P/L: €{session_detail_data['pnl']:+,.0f}").classes('text-lg font-bold ' + ('text-green-400' if session_detail_data['pnl'] > 0 else 'text-red-400'))
                        ui.label(f"Exit: {session_detail_data['exit_reason']}").classes('text-sm text-slate-400')
                        ui.label(f"Hands: {session_detail_data['hands']}").classes('text-sm text-slate-400')
                        ui.label(f"Peak Profit: €{session_detail_data['peak_profit']:+,.0f}").classes('text-sm text-cyan-400')
                        ui.button('↻ REFRESH SESSION', on_click=lambda: asyncio.create_task(refresh_single_universe())).props('flat color=cyan dense size=sm')
                    
                    # Create bankroll evolution graph
                    fig = go.Figure()
                    
                    hands = [entry['hand'] for entry in hand_log]
                    bankrolls = [entry['bankroll'] for entry in hand_log]
                    session_pls = [entry['session_pl'] for entry in hand_log]
                    
                    # Main bankroll line
                    fig.add_trace(go.Scatter(
                        x=hands,
                        y=bankrolls,
                        mode='lines',
                        name='Bankroll',
                        line=dict(color='#3b82f6', width=2),
                        hovertemplate='Hand %{x}<br>Bankroll: €%{y:,.0f}<extra></extra>'
                    ))
                    
                    # Add starting bankroll reference line
                    fig.add_hline(y=start_bankroll, line_dash="dash", line_color="gray", annotation_text="Start", annotation_position="right")
                    
                    # Highlight tie wins (when tie bet was placed and won)
                    tie_win_hands = [entry['hand'] for entry in hand_log if entry['tie_bet_placed'] and entry['tie_bet_pnl'] > 0]
                    tie_win_bankrolls = [entry['bankroll'] for entry in hand_log if entry['tie_bet_placed'] and entry['tie_bet_pnl'] > 0]
                    
                    if tie_win_hands:
                        fig.add_trace(go.Scatter(
                            x=tie_win_hands,
                            y=tie_win_bankrolls,
                            mode='markers',
                            name='Tie Bet Win',
                            marker=dict(
                                size=10,
                                color='#10b981',
                                symbol='star'
                            ),
                            hovertemplate='Hand %{x}<br>Tie Win!<extra></extra>'
                        ))
                    
                    # Highlight virtual mode periods
                    virtual_hands = [entry['hand'] for entry in hand_log if entry['in_virtual']]
                    virtual_bankrolls = [entry['bankroll'] for entry in hand_log if entry['in_virtual']]
                    
                    if virtual_hands:
                        fig.add_trace(go.Scatter(
                            x=virtual_hands,
                            y=virtual_bankrolls,
                            mode='markers',
                            name='Virtual Mode',
                            marker=dict(
                                size=6,
                                color='#a855f7',
                                symbol='circle-open'
                            ),
                            hovertemplate='Hand %{x}<br>Virtual (Iron Gate)<extra></extra>'
                        ))
                    
                    fig.update_layout(
                        title='Session Bankroll Evolution',
                        xaxis_title='Hand Number',
                        yaxis_title='Bankroll (€)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(30,41,59,0.5)',
                        font=dict(color='#94a3b8'),
                        margin=dict(l=20, r=20, t=40, b=40),
                        hovermode='x unified',
                        showlegend=True,
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1
                        )
                    )
                    
                    ui.plotly(fig).classes('w-full h-80')
                    
                    # Optional: Add a compact stats table
                    with ui.row().classes('w-full gap-4 text-xs text-slate-400 justify-around'):
                        max_press = max([entry['press_level'] for entry in hand_log], default=0)
                        ui.label(f"Max Press Streak: {max_press}")
                        tie_bet_count = sum(1 for entry in hand_log if entry['tie_bet_placed'])
                        ui.label(f"Tie Bets Placed: {tie_bet_count}")
                        virtual_count = sum(1 for entry in hand_log if entry['in_virtual'])
                        ui.label(f"Virtual Mode Hands: {virtual_count}")

    async def run_sim():
        nonlocal running
        if running: return
        try:
            running = True; btn_sim.disable(); progress.set_value(0); progress.set_visibility(True)
            label_stats.set_text("Dealing Cards (Multiverse)...")
            
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
            
            raw_bet = select_bet_strat.value
            if not raw_bet: raw_bet = 'BANKER'
            
            overrides = StrategyOverrides(
                iron_gate_limit=int(slider_iron_gate.value), stop_loss_units=int(slider_stop_loss.value),
                profit_lock_units=int(slider_profit.value), press_trigger_wins=int(select_press.value),
                press_depth=config['press_depth'], ratchet_lock_pct=0.0, tax_threshold=config['tax_thresh'],
                tax_rate=config['tax_rate'], bet_strategy=getattr(BetStrategy, raw_bet),
                shoes_per_session=int(slider_shoes.value), penalty_box_enabled=switch_penalty.value,
                ratchet_enabled=switch_ratchet.value, ratchet_mode=select_ratchet_mode.value,
                # Smart Trailing Stop
                smart_exit_enabled=switch_smart_exit.value,
                smart_window_start=int(slider_smart_window.value),
                min_profit_to_lock=int(slider_min_lock.value),
                trailing_drop_pct=float(slider_trail_pct.value),
                # Doctrine Engine
                doctrine_enabled=switch_doctrine_enabled.value,
                doctrine_pl_stop=float(slider_doctrine_pl_stop.value),
                doctrine_pl_target=float(slider_doctrine_pl_target.value),
                doctrine_pl_press_wins=int(slider_doctrine_pl_press_wins.value),
                doctrine_pl_press_depth=int(slider_doctrine_pl_press_depth.value),
                doctrine_pl_iron=int(slider_doctrine_pl_iron.value),
                doctrine_ti_stop=float(slider_doctrine_ti_stop.value),
                doctrine_ti_target=float(slider_doctrine_ti_target.value),
                doctrine_ti_press_wins=int(slider_doctrine_ti_press_wins.value),
                doctrine_ti_press_depth=int(slider_doctrine_ti_press_depth.value),
                doctrine_ti_iron=int(slider_doctrine_ti_iron.value),
                doctrine_loss_trigger=float(slider_doctrine_loss_trigger.value),
                doctrine_dd_pct_trigger=float(slider_doctrine_dd_pct.value),
                doctrine_dd_eur_trigger=float(slider_doctrine_dd_eur.value),
                doctrine_tight_min=int(slider_doctrine_tight_min.value),
                doctrine_tight_max=int(slider_doctrine_tight_max.value),
                doctrine_cooloff_enabled=switch_doctrine_cooloff.value,
                doctrine_cooloff_floor=float(slider_doctrine_cooloff_floor.value),
                doctrine_cooloff_min_months=int(slider_doctrine_cooloff_months.value),
                doctrine_cooloff_recovery_pct=float(slider_doctrine_recovery_pct.value)
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
                        res = BaccaratWorker.run_full_career(
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

            label_stats.set_text("Analyzing Data...")
            stats = await asyncio.to_thread(calculate_stats, all_results, config, start_ga, config['years']*12)
            render_analysis(stats, config, start_ga, overrides, all_results) 
            label_stats.set_text("Simulation Complete")
            
            await refresh_single_universe()

        except Exception as e:
            print(traceback.format_exc())
            ui.notify(f"Error: {str(e)}", type='negative')
        finally:
            running = False; btn_sim.enable(); progress.set_visibility(False)

    def render_analysis(stats, config, start_ga, overrides, all_results):
        if not stats: return
        months = stats['months']
        total_output = stats['avg_final_ga'] + stats['avg_tax']
        grand_total_wealth = total_output 
        real_monthly_cost = (stats['total_input'] - total_output) / (config['years']*12)
        score_survival = (stats['survivor_count'] / config['num_sims']) * 100
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
                            ui.label('BACCARAT GRADE').classes('text-xs text-slate-400 font-bold tracking-widest')
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
                            ui.label(f"€{grand_total_wealth:,.0f}").classes('text-4xl font-black text-white leading-none')
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
            fig.update_layout(title='Monte Carlo Confidence Bands (Baccarat)', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'), margin=dict(l=20, r=20, t=40, b=20))
            ui.plotly(fig).classes('w-full h-96')

        with flight_recorder_container:
            flight_recorder_container.clear()
            y1_log = all_results[0].get('y1_log', [])
            with ui.expansion('OUR LOG (Year 1 - Sim #1)', icon='history_edu', value=True).classes('w-full bg-slate-800 text-slate-300 border-2 border-slate-600'):
                if y1_log:
                    table_rows = []
                    for entry in y1_log:
                        res_val = entry.get('result', 0)
                        table_rows.append({'Month': f"M{entry.get('month', '?')}", 'Result': f"€{res_val:+,.0f}", 'Balance': f"€{entry.get('balance', 0):,.0f}", 'Game Bal': f"€{entry.get('game_bal', 0):,.0f}", 'Hands': f"{entry.get('hands', 0)}" })
                    ui.aggrid({'columnDefs': [{'headerName': 'Mo', 'field': 'Month', 'width': 60}, {'headerName': 'PnL', 'field': 'Result', 'width': 90}, {'headerName': 'Tot. Bal', 'field': 'Balance', 'width': 100}, {'headerName': 'Game Bal', 'field': 'Game Bal', 'width': 100}, {'headerName': 'Spins', 'field': 'Hands', 'width': 80}], 'rowData': table_rows, 'domLayout': 'autoHeight'}).classes('w-full theme-balham-dark')

        with report_container:
            report_container.clear()
            lines = ["=== BACCARAT CONFIGURATION ==="]
            lines.append(f"Sims: {config['num_sims']} | Years: {config['years']} | Mode: {config['strategy_mode']}")
            lines.append(f"Betting: {overrides.bet_strategy.name} | Base Bet: €{config['base_bet']}")
            lines.append(f"Press: {select_press.value} (Wins: {overrides.press_trigger_wins})")
            lines.append(f"Iron Gate: {overrides.iron_gate_limit} | Stop: {overrides.stop_loss_units}u | Target: {overrides.profit_lock_units}u")
            
            # Doctrine Engine Configuration
            if overrides.doctrine_enabled:
                lines.append("\n=== DOCTRINE ENGINE v1.0 (ENABLED) ===")
                lines.append(f"PLATINUM: Stop={overrides.doctrine_pl_stop}u | Target={overrides.doctrine_pl_target}u | Press={overrides.doctrine_pl_press_wins}/{overrides.doctrine_pl_press_depth} | Iron={overrides.doctrine_pl_iron}")
                lines.append(f"TIGHT: Stop={overrides.doctrine_ti_stop}u | Target={overrides.doctrine_ti_target}u | Press={overrides.doctrine_ti_press_wins}/{overrides.doctrine_ti_press_depth} | Iron={overrides.doctrine_ti_iron}")
                lines.append(f"Triggers: Loss>{overrides.doctrine_loss_trigger}u | DD%>{overrides.doctrine_dd_pct_trigger*100:.0f}% | DD€>{overrides.doctrine_dd_eur_trigger:.0f}")
                lines.append(f"TIGHT Limits: Min={overrides.doctrine_tight_min} | Max={overrides.doctrine_tight_max} sessions")
                if overrides.doctrine_cooloff_enabled:
                    lines.append(f"COOL-OFF: Floor=€{overrides.doctrine_cooloff_floor:.0f} | Recovery<{overrides.doctrine_cooloff_recovery_pct*100:.0f}% | Min={overrides.doctrine_cooloff_min_months}mo")
            else:
                lines.append("\n=== DOCTRINE ENGINE: DISABLED ===")
            
            lines.append("\n=== PERFORMANCE RESULTS ===")
            lines.append(f"Total Survival Rate: {score_survival:.1f}%")
            lines.append(f"Grand Total Wealth: €{grand_total_wealth:,.0f}")
            lines.append(f"Real Monthly Cost: €{real_monthly_cost:,.0f}")
            lines.append(f"Active Play Time: {active_pct:.1f}%")
            
            # Tie Betting Statistics
            if y1_log and switch_tie_bet.value:
                total_ties = sum(e.get('tie_count', 0) for e in y1_log)
                total_tie_bets = sum(e.get('tie_bets', 0) for e in y1_log)
                total_tie_pnl = sum(e.get('tie_pnl', 0) for e in y1_log)
                if total_ties > 0:
                    lines.append("\n=== TIE BETTING STATISTICS ===")
                    lines.append(f"Total Ties: {total_ties}")
                    lines.append(f"Tie Bets Placed: {total_tie_bets}")
                    lines.append(f"Tie Bet P&L: €{total_tie_pnl:,.2f}")
                    lines.append(f"Tie Bet Win Rate: {(total_tie_pnl / (total_tie_bets * 10) if total_tie_bets > 0 else 0):.1%}")
            
            if y1_log:
                lines.append("\n=== YEAR 1 COMPREHENSIVE DATA (COPY/PASTE) ===")
                lines.append("Month,Session,Result,Total_Bal,Game_Bal,Hands,Volume,Tier,Exit_Reason,Streak_Max,Tie_Count,Tie_Bets,Tie_PL")
                for e in y1_log:
                    lines.append(
                        f"{e['month']},{e['session']},{e['result']:.0f},{e['balance']:.0f},{e['game_bal']:.0f},"
                        f"{e['hands']},{e['volume']:.0f},{e['tier']},{e['exit']},{e['streak_max']},"
                        f"{e.get('tie_count', 0)},{e.get('tie_bets', 0)},{e.get('tie_pnl', 0):.0f}"
                    )
            
            # SAFE STRING FORMATTING FOR REPORT
            log_content = "\n".join(lines)
            ui.html(f'<pre style="white-space: pre-wrap; font-family: monospace; color: #94a3b8; font-size: 0.75rem;">{log_content}</pre>', sanitize=False)

    # --- UI LAYOUT ---
    with ui.column().classes('w-full max-w-4xl mx-auto gap-6 p-4'):
        ui.label('BACCARAT LAB (MONACO RULES)').classes('text-2xl font-light text-cyan-400')
        
        with ui.card().classes('w-full bg-slate-900 p-6 gap-4'):
            
            # STRATEGY LIBRARY RESTORED HERE
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

            # CONTROLS
            with ui.grid(columns=2).classes('w-full gap-8'):
                with ui.column():
                    ui.label('TACTICS').classes('font-bold text-purple-400')
                    select_engine_mode = ui.select(['Standard', 'Fortress', 'Titan', 'Safe Titan'], value='Standard', label='Betting Engine').classes('w-full').on_value_change(update_ladder_preview)
                    
                    with ui.row().classes('w-full justify-between'): ui.label('Base Bet (€)').classes('text-xs text-purple-300'); lbl_base = ui.label()
                    slider_base_bet = ui.slider(min=5, max=100, step=5, value=10, on_change=update_ladder_preview).props('color=purple'); lbl_base.bind_text_from(slider_base_bet, 'value', lambda v: f'€{v}')
                    
                    with ui.row().classes('w-full justify-between'): ui.label('Safety Buffer').classes('text-xs text-orange-400'); lbl_safe = ui.label()
                    slider_safety = ui.slider(min=10, max=60, value=25, on_change=update_ladder_preview).props('color=orange'); lbl_safe.bind_text_from(slider_safety, 'value', lambda v: f'{v}x')
                    
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
                    ui.label('BACCARAT GAMEPLAY').classes('font-bold text-cyan-400')
                    
                    select_bet_strat = ui.select(['BANKER', 'PLAYER'], value='BANKER', label='Bet Selection').classes('w-full')
                    
                    slider_shoes = ui.slider(min=1, max=5, value=3).props('color=blue'); ui.label().bind_text_from(slider_shoes, 'value', lambda v: f'{v} Shoes (approx {v*70} hands)')
                    
                    with ui.row().classes('items-center mt-2'):
                        switch_tie_bet = ui.switch('🎲 Tie Follow Betting').props('color=cyan')
                        switch_tie_bet.value = False
                        ui.label('(1u bet after each tie)').classes('text-xs text-slate-400')
                    
                    ui.separator().classes('bg-slate-700 my-2')
                    
                    slider_stop_loss = ui.slider(min=0, max=100, value=10).props('color=red'); ui.label().bind_text_from(slider_stop_loss, 'value', lambda v: f'Stop {v}u')
                    slider_profit = ui.slider(min=1, max=100, value=10).props('color=green'); ui.label().bind_text_from(slider_profit, 'value', lambda v: f'Target {v}u')
                    
                    with ui.row().classes('items-center justify-between'): switch_ratchet = ui.switch('Ratchet').props('color=gold'); select_ratchet_mode = ui.select(['Sprint', 'Standard', 'Deep Stack', 'Gold Grinder'], value='Standard').props('dense options-dense').classes('w-32')
                    ui.separator().classes('bg-slate-700 my-2')
                    
                    select_press = ui.select({0: 'Flat', 1: 'Press 1-Win', 2: 'Press 2-Wins', 3: 'Progression 100-150-250', 4: "Capped D'Alembert", 5: "La Caroline"}, value=1, label='Press Logic').classes('w-full')
                    ui.label('Press Depth (Wins to Reset)').classes('text-xs text-red-300')
                    slider_press_depth = ui.slider(min=0, max=5, value=3).props('color=red'); ui.label().bind_text_from(slider_press_depth, 'value', lambda v: f'{v} Wins')
                    ui.separator().classes('bg-slate-700 my-2')
                    slider_iron_gate = ui.slider(min=2, max=10, value=3).props('color=purple'); ui.label().bind_text_from(slider_iron_gate, 'value', lambda v: f'Iron Gate {v}')
                    
                    # Smart Trailing Stop Controls
                    ui.separator().classes('bg-slate-700 my-2')
                    ui.label('🎯 SMART TRAILING STOP (190-220 hands)').classes('text-xs text-yellow-400 font-bold')
                    switch_smart_exit = ui.switch('Enable Smart Exit Window').props('color=yellow')
                    switch_smart_exit.value = True
                    with ui.row().classes('w-full justify-between items-center'): 
                        ui.label('Start Window').classes('text-xs text-slate-400')
                        lbl_smart_window = ui.label()
                    slider_smart_window = ui.slider(min=10, max=240, value=190, step=10).props('color=yellow')
                    lbl_smart_window.bind_text_from(slider_smart_window, 'value', lambda v: f'Hand {int(v)}')
                    with ui.row().classes('w-full justify-between items-center'): 
                        ui.label('Min Profit to Lock').classes('text-xs text-slate-400')
                        lbl_min_lock = ui.label()
                    slider_min_lock = ui.slider(min=5, max=50, value=20, step=5).props('color=yellow')
                    lbl_min_lock.bind_text_from(slider_min_lock, 'value', lambda v: f'+{int(v)}u')
                    with ui.row().classes('w-full justify-between items-center'): 
                        ui.label('Trailing Drop %').classes('text-xs text-slate-400')
                        lbl_trail_pct = ui.label()
                    slider_trail_pct = ui.slider(min=0.10, max=0.40, value=0.20, step=0.05).props('color=yellow')
                    lbl_trail_pct.bind_text_from(slider_trail_pct, 'value', lambda v: f'{int(v*100)}%')
                
                # ============================================================================
                # DOCTRINE ENGINE v1.0 - DYNAMIC STATE-DRIVEN BETTING
                # ============================================================================
                with ui.card().classes('w-full bg-slate-800 p-4 border-2 border-purple-500 mb-4'):
                    ui.label('⚡ DOCTRINE ENGINE v1.0 - STATE-DRIVEN BETTING').classes('font-bold text-purple-400 text-lg mb-4')
                    ui.label('Automatically switches between PLATINUM → TIGHT → COOL_OFF based on results').classes('text-xs text-slate-400 mb-3')
                    
                    switch_doctrine_enabled = ui.switch('Enable Doctrine Engine').props('color=purple')
                    switch_doctrine_enabled.value = False
                    
                    # PLATINUM DOCTRINE
                    with ui.expansion('💎 PLATINUM Doctrine (Standard Evening)', icon='star').classes('w-full bg-gradient-to-r from-purple-900 to-indigo-900 text-white mb-2'):
                        with ui.grid(columns=2).classes('w-full gap-3 p-3'):
                            with ui.column():
                                ui.label('Stop-Loss (units)').classes('text-xs text-slate-300')
                                slider_doctrine_pl_stop = ui.slider(min=5, max=50, value=10, step=1).props('color=purple')
                                ui.label().bind_text_from(slider_doctrine_pl_stop, 'value', lambda v: f'{int(v)}u')
                            with ui.column():
                                ui.label('Target (units)').classes('text-xs text-slate-300')
                                slider_doctrine_pl_target = ui.slider(min=5, max=50, value=10, step=1).props('color=purple')
                                ui.label().bind_text_from(slider_doctrine_pl_target, 'value', lambda v: f'{int(v)}u')
                            with ui.column():
                                ui.label('Press Wins').classes('text-xs text-slate-300')
                                slider_doctrine_pl_press_wins = ui.slider(min=1, max=10, value=3, step=1).props('color=purple')
                                ui.label().bind_text_from(slider_doctrine_pl_press_wins, 'value', lambda v: f'{int(v)} wins')
                            with ui.column():
                                ui.label('Press Depth').classes('text-xs text-slate-300')
                                slider_doctrine_pl_press_depth = ui.slider(min=1, max=10, value=3, step=1).props('color=purple')
                                ui.label().bind_text_from(slider_doctrine_pl_press_depth, 'value', lambda v: f'{int(v)} max' if v < 10 else 'Unlimited')
                            with ui.column():
                                ui.label('Iron Gate').classes('text-xs text-slate-300')
                                slider_doctrine_pl_iron = ui.slider(min=2, max=10, value=3, step=1).props('color=purple')
                                ui.label().bind_text_from(slider_doctrine_pl_iron, 'value', lambda v: f'{int(v)} losses')
                    
                    # TIGHT DOCTRINE
                    with ui.expansion('🛡️ TIGHT Doctrine (Recovery Mode)', icon='shield').classes('w-full bg-gradient-to-r from-orange-900 to-red-900 text-white mb-2'):
                        with ui.grid(columns=2).classes('w-full gap-3 p-3'):
                            with ui.column():
                                ui.label('Stop-Loss (units)').classes('text-xs text-slate-300')
                                slider_doctrine_ti_stop = ui.slider(min=3, max=20, value=5, step=1).props('color=orange')
                                ui.label().bind_text_from(slider_doctrine_ti_stop, 'value', lambda v: f'{int(v)}u')
                            with ui.column():
                                ui.label('Target (units)').classes('text-xs text-slate-300')
                                slider_doctrine_ti_target = ui.slider(min=3, max=20, value=5, step=1).props('color=orange')
                                ui.label().bind_text_from(slider_doctrine_ti_target, 'value', lambda v: f'{int(v)}u')
                            with ui.column():
                                ui.label('Press Wins').classes('text-xs text-slate-300')
                                slider_doctrine_ti_press_wins = ui.slider(min=3, max=15, value=5, step=1).props('color=orange')
                                ui.label().bind_text_from(slider_doctrine_ti_press_wins, 'value', lambda v: f'{int(v)} wins')
                            with ui.column():
                                ui.label('Press Depth').classes('text-xs text-slate-300')
                                slider_doctrine_ti_press_depth = ui.slider(min=0, max=3, value=1, step=1).props('color=orange')
                                ui.label().bind_text_from(slider_doctrine_ti_press_depth, 'value', lambda v: f'{int(v)} max')
                            with ui.column():
                                ui.label('Iron Gate').classes('text-xs text-slate-300')
                                slider_doctrine_ti_iron = ui.slider(min=1, max=5, value=2, step=1).props('color=orange')
                                ui.label().bind_text_from(slider_doctrine_ti_iron, 'value', lambda v: f'{int(v)} losses')
                    
                    # TRIGGERS
                    with ui.expansion('🚨 Triggers (PLATINUM → TIGHT)', icon='warning').classes('w-full bg-slate-900 text-white mb-2'):
                        with ui.grid(columns=2).classes('w-full gap-3 p-3'):
                            with ui.column():
                                ui.label('Big Loss Trigger (units)').classes('text-xs text-slate-300')
                                ui.label('Single loss > this triggers TIGHT').classes('text-xs text-slate-500 italic')
                                slider_doctrine_loss_trigger = ui.slider(min=5, max=20, value=8, step=1).props('color=red')
                                ui.label().bind_text_from(slider_doctrine_loss_trigger, 'value', lambda v: f'-{int(v)}u')
                            with ui.column():
                                ui.label('Drawdown % Trigger').classes('text-xs text-slate-300')
                                ui.label('% drop from peak GA').classes('text-xs text-slate-500 italic')
                                slider_doctrine_dd_pct = ui.slider(min=0.05, max=0.30, value=0.15, step=0.01).props('color=red')
                                ui.label().bind_text_from(slider_doctrine_dd_pct, 'value', lambda v: f'{int(v*100)}%')
                            with ui.column().classes('col-span-2'):
                                ui.label('Drawdown € Trigger').classes('text-xs text-slate-300')
                                ui.label('Absolute € drop from peak (0 = disabled)').classes('text-xs text-slate-500 italic')
                                slider_doctrine_dd_eur = ui.slider(min=0, max=10000, value=3000, step=500).props('color=red')
                                ui.label().bind_text_from(slider_doctrine_dd_eur, 'value', lambda v: f'€{int(v):,}' if v > 0 else 'Disabled')
                    
                    # TIGHT SESSION LIMITS
                    with ui.expansion('⏱️ TIGHT Session Limits', icon='schedule').classes('w-full bg-slate-900 text-white mb-2'):
                        with ui.grid(columns=2).classes('w-full gap-3 p-3'):
                            with ui.column():
                                ui.label('Minimum TIGHT Sessions').classes('text-xs text-slate-300')
                                ui.label('Before checking recovery').classes('text-xs text-slate-500 italic')
                                slider_doctrine_tight_min = ui.slider(min=1, max=5, value=1, step=1).props('color=yellow')
                                ui.label().bind_text_from(slider_doctrine_tight_min, 'value', lambda v: f'{int(v)} sessions')
                            with ui.column():
                                ui.label('Maximum TIGHT Sessions').classes('text-xs text-slate-300')
                                ui.label('Before COOL_OFF if still struggling').classes('text-xs text-slate-500 italic')
                                slider_doctrine_tight_max = ui.slider(min=1, max=5, value=2, step=1).props('color=yellow')
                                ui.label().bind_text_from(slider_doctrine_tight_max, 'value', lambda v: f'{int(v)} sessions')
                    
                    # COOL-OFF MODE
                    with ui.expansion('❄️ COOL-OFF Mode (Safety)', icon='ac_unit').classes('w-full bg-gradient-to-r from-blue-900 to-cyan-900 text-white mb-2'):
                        switch_doctrine_cooloff = ui.switch('Enable Cool-Off Mode').props('color=cyan')
                        switch_doctrine_cooloff.value = True
                        with ui.grid(columns=2).classes('w-full gap-3 p-3 mt-2'):
                            with ui.column():
                                ui.label('GA Floor (Insolvency)').classes('text-xs text-slate-300')
                                ui.label('Bankroll < this triggers COOL_OFF').classes('text-xs text-slate-500 italic')
                                slider_doctrine_cooloff_floor = ui.slider(min=1000, max=10000, value=3000, step=500).props('color=cyan')
                                ui.label().bind_text_from(slider_doctrine_cooloff_floor, 'value', lambda v: f'€{int(v):,}')
                            with ui.column():
                                ui.label('Minimum Cool-Off Months').classes('text-xs text-slate-300')
                                ui.label('Mandatory recovery time').classes('text-xs text-slate-500 italic')
                                slider_doctrine_cooloff_months = ui.slider(min=1, max=6, value=1, step=1).props('color=cyan')
                                ui.label().bind_text_from(slider_doctrine_cooloff_months, 'value', lambda v: f'{int(v)} months')
                            with ui.column().classes('col-span-2'):
                                ui.label('Recovery Threshold (%)').classes('text-xs text-slate-300')
                                ui.label('Drawdown < this % allows return to PLATINUM').classes('text-xs text-slate-500 italic')
                                slider_doctrine_recovery_pct = ui.slider(min=0.03, max=0.15, value=0.07, step=0.01).props('color=cyan')
                                ui.label().bind_text_from(slider_doctrine_recovery_pct, 'value', lambda v: f'{int(v*100)}%')
                    
                    # Note: Roulette coupling not relevant for Baccarat sim
                    ui.label('Note: Roulette coupling settings available in Roulette Simulator').classes('text-xs text-slate-500 italic mt-2')


            ui.separator().classes('bg-slate-700')
            with ui.row().classes('w-full items-center justify-between'):
                with ui.column():
                     ui.label('Starting Capital').classes('text-xs text-green-400')
                     slider_start_ga = ui.slider(min=0, max=100000, value=2000, step=100).props('color=green'); ui.label().bind_text_from(slider_start_ga, 'value', lambda v: f'€{v}')
                     with ui.row().classes('gap-4 mt-2'): select_status = ui.select(list(SBM_TIERS.keys()), value='Gold').props('dense'); slider_earn_rate = ui.slider(min=1, max=50, value=10).props('color=yellow').classes('w-32')
                btn_sim = ui.button('RUN SIM', on_click=run_sim).props('icon=play_arrow color=yellow text-color=black size=lg')

        label_stats = ui.label('Ready...').classes('text-sm text-slate-500'); progress = ui.linear_progress().props('color=green').classes('mt-0'); progress.set_visibility(False)
        
        scoreboard_container = ui.column().classes('w-full mb-4')
        chart_container = ui.card().classes('w-full bg-slate-900 p-4')
        
        ui.button('⚡ REFRESH SINGLE', on_click=refresh_single_universe).props('flat color=cyan dense').classes('mt-4')
        chart_single_container = ui.column().classes('w-full mt-2')
        session_detail_container = ui.column().classes('w-full mt-2')
        
        flight_recorder_container = ui.column().classes('w-full mb-4')
        report_container = ui.column().classes('w-full')
        
        update_ladder_preview()
