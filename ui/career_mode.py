from nicegui import ui
import plotly.graph_objects as go
import numpy as np
import asyncio
import traceback
from copy import deepcopy

# --- CRITICAL FIX: IMPORT BACCARAT WORKER ---
from ui.simulator import BaccaratWorker # Changed from SimulationWorker
from ui.roulette_sim import RouletteWorker
from engine.strategy_rules import StrategyOverrides, BetStrategy, PlayMode, build_doctrine_configs_from_overrides
from engine.tier_params import get_tier_for_ga, generate_tier_map
from engine.doctrine_engine import (
    DoctrineContext, choose_state_for_next_session, update_after_session,
    update_after_month, get_doctrine_config, log_state_transition
)
from utils.persistence import load_profile

# List of Roulette-specific bets to detect Game Type
ROULETTE_BETS = {'Red', 'Black', 'Even', 'Odd', '1-18', '19-36'}

class CareerManager:
    @staticmethod
    def run_compound_career(sequence_config, start_ga, total_years, sessions_per_year, fallback_threshold_pct=0.80, promotion_buffer_pct=1.20):
        current_ga = start_ga
        current_leg_idx = 0
        
        # Load Initial Strategy
        active_config = sequence_config[0]['config']
        active_strategy_name = sequence_config[0]['strategy_name']
        active_target = sequence_config[0]['target_ga']
        
        # Extract Params & Detect Game Type
        overrides, tier_map, safety, mode, use_ratch, use_penalty, game_type, base_bet = CareerManager._extract_params(active_config)
        
        # === DOCTRINE ENGINE INITIALIZATION ===
        doctrine_enabled = active_config.get('doctrine_en', False)
        doctrine_ctx = None
        platinum_cfg = None
        tight_cfg = None
        state_rules = None
        
        if doctrine_enabled:
            # Build doctrine configurations from overrides
            platinum_cfg, tight_cfg, state_rules = build_doctrine_configs_from_overrides(overrides)
            
            # Initialize doctrine context
            doctrine_ctx = DoctrineContext(
                state="PLATINUM",
                GA_current=current_ga,
                GA_peak=current_ga,
                last_result_u=0.0,
                tight_sessions_done=0,
                cooloff_months_done=0
            )
        
        trajectory = []
        log = []
        months = total_years * 12
        active_level = 1
        last_session_won = False
        
        total_input = start_ga
        
        # Track thresholds for fallback mechanism
        promotion_thresholds = [0]  # Track threshold that triggered each leg promotion
        
        for m in range(months):
            # 1. CHECK FOR DEMOTION (Fallback to previous strategy if bankroll drops too low)
            if current_leg_idx > 0:
                fallback_threshold = promotion_thresholds[current_leg_idx] * fallback_threshold_pct
                if current_ga < fallback_threshold:
                    # Demote to previous strategy
                    current_leg_idx -= 1
                    prev_leg = sequence_config[current_leg_idx]
                    
                    log.append({
                        'month': m+1, 
                        'event': 'FALLBACK', 
                        'details': f"DEMOTED: {active_strategy_name} -> {prev_leg['strategy_name']} (Bal: €{current_ga:,.0f}, fell below €{fallback_threshold:,.0f})"
                    })
                    
                    active_strategy_name = prev_leg['strategy_name']
                    active_config = prev_leg['config']
                    active_target = prev_leg['target_ga']
                    
                    # Refresh Params for previous Leg
                    overrides, tier_map, safety, mode, use_ratch, use_penalty, game_type, base_bet = CareerManager._extract_params(active_config)
                    
                    # Reset Tier Level based on old map
                    temp_tier = get_tier_for_ga(current_ga, tier_map, 1, mode, game_type=game_type)
                    active_level = temp_tier.level
            
            # 2. CHECK FOR PROMOTION (with buffer to avoid flip-flopping)
            if current_leg_idx < len(sequence_config) - 1:
                promotion_target = active_target * promotion_buffer_pct
                if current_ga >= promotion_target:
                    current_leg_idx += 1
                    new_leg = sequence_config[current_leg_idx]
                    
                    # Store the threshold that triggered this promotion
                    promotion_thresholds.append(promotion_target)
                    
                    log.append({
                        'month': m+1, 
                        'event': 'PROMOTION', 
                        'details': f"GRADUATED: {active_strategy_name} -> {new_leg['strategy_name']} (Bal: €{current_ga:,.0f})"
                    })
                    
                    active_strategy_name = new_leg['strategy_name']
                    active_config = new_leg['config']
                    active_target = new_leg['target_ga']
                    
                    # Refresh Params for new Leg
                    overrides, tier_map, safety, mode, use_ratch, use_penalty, game_type, base_bet = CareerManager._extract_params(active_config)
                    
                    # Reset Tier Level based on new map
                    temp_tier = get_tier_for_ga(current_ga, tier_map, 1, mode, game_type=game_type)
                    active_level = temp_tier.level

            # 3. ECOSYSTEM (Tax/Contrib)
            tax_rate = active_config.get('eco_tax_rate', 25)
            tax_thresh = active_config.get('eco_tax_thresh', 12500)
            use_tax = active_config.get('eco_tax', False)
            
            if use_tax and current_ga > tax_thresh:
                tax = (current_ga - tax_thresh) * (tax_rate / 100.0)
                current_ga -= tax

            contrib_win = active_config.get('eco_win', 300)
            contrib_loss = active_config.get('eco_loss', 300)
            hol_ceil = active_config.get('eco_hol_ceil', 10000)
            use_hol = active_config.get('eco_hol', False)
            
            should_contribute = True
            if use_hol and current_ga >= hol_ceil:
                should_contribute = False
            
            if should_contribute:
                amount = contrib_win if last_session_won else contrib_loss
                current_ga += amount
                total_input += amount 
            
            # 4. INSOLVENCY CHECK
            insolvency_floor = active_config.get('eco_insolvency', 1000)
            if current_ga < insolvency_floor:
                if len(log) == 0 or log[-1]['event'] != 'INSOLVENT':
                    log.append({'month': m+1, 'event': 'INSOLVENT', 'details': f'Bankroll < €{insolvency_floor}. Game Over.'})
                trajectory.append(current_ga)
                continue 

            # === DOCTRINE STATE MACHINE ===
            if doctrine_enabled and doctrine_ctx:
                # Update context with current GA
                doctrine_ctx.GA_current = current_ga
                
                # Determine next state
                old_state = doctrine_ctx.state
                new_state = choose_state_for_next_session(doctrine_ctx, state_rules)
                
                # Log state transition if changed
                if new_state != old_state:
                    reason = "Unknown"
                    if new_state == "TIGHT":
                        if doctrine_ctx.last_result_u <= -state_rules.loss_trigger_pl_u:
                            reason = f"Big loss: -{abs(doctrine_ctx.last_result_u):.1f}u"
                        else:
                            dd_pct = (doctrine_ctx.GA_peak - current_ga) / doctrine_ctx.GA_peak if doctrine_ctx.GA_peak > 0 else 0
                            reason = f"Drawdown: {dd_pct*100:.1f}%"
                    elif new_state == "COOL_OFF":
                        if current_ga < state_rules.cooloff_ga_floor:
                            reason = f"Insolvency: €{current_ga:,.0f} < €{state_rules.cooloff_ga_floor:,.0f}"
                        else:
                            reason = "Max TIGHT sessions exhausted"
                    elif new_state == "PLATINUM":
                        reason = "Recovered from drawdown"
                    
                    log_state_transition(doctrine_ctx, old_state, new_state, reason)
                    log.append({
                        'month': m+1,
                        'event': 'DOCTRINE',
                        'details': f"Doctrine: {old_state} → {new_state} ({reason})"
                    })
                    doctrine_ctx.state = new_state
                
                # Get active doctrine config
                active_doctrine_cfg = get_doctrine_config(doctrine_ctx.state, platinum_cfg, tight_cfg)
                
                # Override session parameters with doctrine config
                overrides.stop_loss_units = int(active_doctrine_cfg.stop_loss_u)
                overrides.profit_lock_units = int(active_doctrine_cfg.target_u)
                overrides.press_trigger_wins = active_doctrine_cfg.press_wins
                overrides.press_depth = active_doctrine_cfg.press_depth
                overrides.iron_gate_limit = active_doctrine_cfg.iron_gate

            # 5. PLAY SESSIONS (DYNAMIC ENGINE SELECTION)
            sessions_this_month = sessions_per_year // 12
            if m % 12 < (sessions_per_year % 12): 
                sessions_this_month += 1
            
            month_pnl = 0.0  # Track monthly P&L for doctrine
            for _ in range(sessions_this_month):
                session_ga_before = current_ga
                
                if game_type == 'Roulette':
                    # --- ROULETTE ENGINE (returns 10 values) ---
                    pnl, vol, used_lvl, spins, spice_stats, exit_reason, max_caroline, max_dalembert, press_streak, peak_profit = RouletteWorker.run_session(
                        current_ga, overrides, tier_map, use_ratch, use_penalty, active_level, mode, base_bet
                    )
                else:
                    # --- BACCARAT ENGINE (returns 6 values) ---
                    pnl, vol, used_lvl, hands, exit_reason, press_streak = BaccaratWorker.run_session(
                        current_ga, overrides, tier_map, use_ratch, use_penalty, active_level, mode, base_bet
                    )
                
                current_ga += pnl
                month_pnl += pnl
                active_level = used_lvl 
                last_session_won = (pnl > 0)
                
                # Update doctrine after each session
                if doctrine_enabled and doctrine_ctx:
                    result_u = pnl / base_bet
                    update_after_session(doctrine_ctx, result_u, current_ga, doctrine_ctx.state)
            
            # Update doctrine after month (for cool-off tracking)
            if doctrine_enabled and doctrine_ctx:
                update_after_month(doctrine_ctx)
            
            trajectory.append(current_ga)
            
            if m % 12 == 0:
                year_num = (m // 12) + 1
                status_detail = f"Year {year_num} | €{current_ga:,.0f} | {active_strategy_name} ({game_type})"
                
                # Add doctrine state to status if enabled
                if doctrine_enabled and doctrine_ctx:
                    status_detail += f" | Doctrine: {doctrine_ctx.state}"
                
                log.append({
                    'month': m+1, 
                    'event': 'STATUS', 
                    'details': status_detail
                })

        # Prepare doctrine summary if enabled
        doctrine_summary = None
        if doctrine_enabled and doctrine_ctx:
            doctrine_summary = {
                'final_state': doctrine_ctx.state,
                'platinum_sessions': doctrine_ctx.platinum_sessions,
                'tight_sessions': doctrine_ctx.tight_sessions,
                'cooloff_months': doctrine_ctx.cooloff_months,
                'transitions': doctrine_ctx.transitions,
                'peak_ga': doctrine_ctx.GA_peak
            }

        return trajectory, log, current_ga, total_input, doctrine_summary

    @staticmethod
    def _extract_params(config):
        mode = config.get('tac_mode', 'Standard')
        safety = config.get('tac_safety', 25)
        base_bet = config.get('tac_base_bet', 10.0)
        
        # 1. Detect Game Type
        bet_val = config.get('tac_bet', 'Banker')
        game_type = 'Roulette' if bet_val in ROULETTE_BETS else 'Baccarat'
        
        # 2. Generate appropriate Tier Map
        tier_map = generate_tier_map(safety, mode=mode, game_type=game_type, base_bet=base_bet)
        
        # 3. Handle Bet Strategy Object
        if game_type == 'Baccarat':
            bet_strat_obj = BetStrategy.BANKER if bet_val == 'BANKER' else BetStrategy.PLAYER
        else:
            bet_strat_obj = bet_val 

        overrides = StrategyOverrides(
            iron_gate_limit=config.get('tac_iron', 3),
            stop_loss_units=config.get('risk_stop', 10),
            profit_lock_units=config.get('risk_prof', 10),
            press_trigger_wins=config.get('tac_press', 1),
            press_depth=config.get('tac_depth', 3),
            ratchet_enabled=config.get('risk_ratch', False),
            ratchet_mode=config.get('risk_ratch_mode', 'Standard'),
            shoes_per_session=config.get('tac_shoes', 3),
            bet_strategy=bet_strat_obj,
            penalty_box_enabled=config.get('tac_penalty', True),
            
            # SPICE v5.0 Configs - Use defaults (all disabled) for career mode
            # Individual spice types can be configured in the UI if needed
            spice_global_max_per_session=config.get('spice_global_max_session', 3),
            spice_global_max_per_spin=config.get('spice_global_max_spin', 1),
            spice_disable_if_caroline_step4=config.get('spice_disable_caroline', True),
            spice_disable_if_pl_below_zero=config.get('spice_disable_below_zero', True),
            spice_unit_ratio=0.5 if config.get('spice_hybrid_mode', False) else 1.0
        )
        use_ratchet = config.get('risk_ratch', False)
        penalty_mode = config.get('tac_penalty', True)
        
        return overrides, tier_map, safety, mode, use_ratchet, penalty_mode, game_type, base_bet

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
        try:
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
                sequence_config.append({'strategy_name': leg['strategy'], 'target_ga': leg['target'], 'config': cfg})

            start_ga = slider_start_ga.value
            years = slider_years.value
            sessions = slider_freq.value
            num_sims = slider_num_sims.value


            async def run_batch_with_progress():
                batch_results = []
                error_details = []
                for i in range(num_sims):
                    try:
                        traj, log, final_ga, total_in, doctrine_summary = CareerManager.run_compound_career(
                            sequence_config, start_ga, years, sessions,
                            slider_fallback.value / 100.0, slider_promotion_buffer.value / 100.0
                        )
                        net_cost = total_in - final_ga
                        monthly_cost = net_cost / (years * 12)
                        batch_results.append({
                            'trajectory': traj,
                            'log': log,
                            'final': final_ga,
                            'monthly_cost': monthly_cost,
                            'doctrine_summary': doctrine_summary
                        })
                    except Exception as e:
                        error_msg = f"Sim {i+1} error: {str(e)}"
                        error_details.append(error_msg)
                        print(f"Simulation error: {e}")
                        import traceback
                        traceback.print_exc()
                        batch_results.append({
                            'trajectory': [],
                            'log': [
                                {'month': 0, 'event': 'ERROR', 'details': str(e)}
                            ],
                            'final': 0,
                            'monthly_cost': 0,
                            'doctrine_summary': None,
                            'error': str(e)
                        })
                    # Update progress bar (simulate progress)
                    progress.value = (i + 1) / num_sims
                    await asyncio.sleep(0)  # Yield to event loop for UI update
                return batch_results, error_details

            # Set progress bar to determinate mode
            progress.props('color=purple')
            progress.value = 0
            progress.set_visibility(True)
            results, error_details = await run_batch_with_progress()
            progress.set_visibility(False)

            # Filter out failed runs
            valid_results = [r for r in results if r['trajectory']]
            if not valid_results:
                error_msg = 'All simulations failed. Check logs for details.'
                if error_details:
                    error_msg += f'\n\nFirst error: {error_details[0]}'
                ui.notify(error_msg, type='negative', timeout=10000)
                return

            trajectories = np.array([r['trajectory'] for r in valid_results])
            months = list(range(trajectories.shape[1]))

            min_band = np.min(trajectories, axis=0)
            max_band = np.max(trajectories, axis=0)
            p25_band = np.percentile(trajectories, 25, axis=0)
            p75_band = np.percentile(trajectories, 75, axis=0)
            mean_line = np.mean(trajectories, axis=0)
            median_line = np.median(trajectories, axis=0)

            survivors = len([r for r in valid_results if r['final'] > 100])
            survival_rate = (survivors / len(valid_results)) * 100

            costs = [r['monthly_cost'] for r in valid_results]
            avg_cost = np.mean(costs)
            med_cost = np.median(costs)

            with results_area:
                with ui.row().classes('w-full justify-between mb-4'):
                    with ui.card().classes('bg-slate-800 p-2'):
                        ui.label('SURVIVAL RATE').classes('text-xs text-slate-400')
                        color = "text-green-400" if survival_rate > 90 else "text-red-400"
                        ui.label(f"{survival_rate:.1f}%").classes(f'text-2xl font-black {color}')

                    with ui.card().classes('bg-slate-800 p-2'):
                        ui.label('MEDIAN MONTHLY COST').classes('text-xs text-slate-400')
                        val_str = f"€{med_cost:,.0f}" if med_cost > 0 else f"+€{abs(med_cost):,.0f}"
                        col_str = "text-red-400" if med_cost > 0 else "text-green-400"
                        ui.label(val_str).classes(f'text-2xl font-black {col_str}')

                    with ui.card().classes('bg-slate-800 p-2'):
                        ui.label('AVG MONTHLY COST').classes('text-xs text-slate-400')
                        val_str = f"€{avg_cost:,.0f}" if avg_cost > 0 else f"+€{abs(avg_cost):,.0f}"
                        col_str = "text-red-400" if avg_cost > 0 else "text-green-400"
                        ui.label(val_str).classes(f'text-2xl font-black {col_str}')

                ui.label('THE MULTIVERSE (Probabilities)').classes('text-sm font-bold text-slate-400 mt-2')
                fig_multi = go.Figure()
                fig_multi.add_trace(go.Scatter(x=months + months[::-1], y=np.concatenate([max_band, min_band[::-1]]), fill='toself', fillcolor='rgba(148, 163, 184, 0.2)', line=dict(color='rgba(255,255,255,0)'), name='Range'))
                fig_multi.add_trace(go.Scatter(x=months + months[::-1], y=np.concatenate([p75_band, p25_band[::-1]]), fill='toself', fillcolor='rgba(74, 222, 128, 0.2)', line=dict(color='rgba(255,255,255,0)'), name='Likely'))
                fig_multi.add_trace(go.Scatter(x=months, y=median_line, mode='lines', name='Median', line=dict(color='yellow', width=2)))

                for leg in legs[:-1]:
                    fig_multi.add_hline(y=leg['target'], line_dash="dash", line_color="white", opacity=0.3)

                fig_multi.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'))
                ui.plotly(fig_multi).classes('w-full border border-slate-700 rounded mb-6')

                # YOUR REALITY section - placed before CSV tools
                ui.label('YOUR REALITY (Single Simulation #1)').classes('text-sm font-bold text-slate-400 mt-2')

                sim1_traj = valid_results[0]['trajectory']
                sim1_log = valid_results[0]['log']
                sim1_final = valid_results[0]['final']

                # Create a dedicated container for single sim that can be refreshed
                single_sim_chart = ui.column().classes('w-full')
                with single_sim_chart:
                    res_color = "text-green-400" if sim1_final >= start_ga else "text-red-400"
                    ui.label(f"Result: €{sim1_final:,.0f}").classes(f'text-xl font-bold {res_color} mb-2')

                    fig_single = go.Figure()
                    fig_single.add_trace(go.Scatter(y=sim1_traj, mode='lines', name='Balance', line=dict(color='#38bdf8', width=2)))

                    for leg in legs[:-1]:
                        fig_single.add_hline(y=leg['target'], line_dash="dash", line_color="yellow", annotation_text=f"Switch")

                    fig_single.update_layout(height=250, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'))
                    ui.plotly(fig_single).classes('w-full border border-slate-700 rounded')

                # Refresh function that updates the single sim chart
                async def refresh_single():
                    if not legs: return
                    try:
                        profile = load_profile()
                        saved_strats = profile.get('saved_strategies', {})
                        refresh_config = []
                        for leg in legs:
                            cfg = saved_strats.get(leg['strategy'])
                            refresh_config.append({'strategy_name': leg['strategy'], 'target_ga': leg['target'], 'config': cfg})
                        
                        traj, log, final, total_in, doctrine_summary = await asyncio.to_thread(
                            CareerManager.run_compound_career, refresh_config, slider_start_ga.value, slider_years.value, slider_freq.value,
                            slider_fallback.value / 100.0, slider_promotion_buffer.value / 100.0
                        )
                        
                        single_sim_chart.clear()
                        with single_sim_chart:
                            res_color = "text-green-400" if final >= slider_start_ga.value else "text-red-400"
                            ui.label(f"Result: €{final:,.0f}").classes(f'text-xl font-bold {res_color} mb-2')
                            
                            # Add doctrine stats if available
                            if doctrine_summary:
                                ui.label(f"Doctrine: {doctrine_summary['final_state']} | "
                                        f"Platinum: {doctrine_summary['platinum_sessions']}s | "
                                        f"Tight: {doctrine_summary['tight_sessions']}s | "
                                        f"Cool-Off: {doctrine_summary['cooloff_months']}m").classes('text-xs text-purple-400 mb-2')
                            
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(y=traj, mode='lines', name='Balance', line=dict(color='#38bdf8', width=2)))
                            for leg in legs[:-1]:
                                fig.add_hline(y=leg['target'], line_dash="dash", line_color="yellow")
                            fig.update_layout(height=250, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'))
                            ui.plotly(fig).classes('w-full border border-slate-700 rounded')

                    except Exception as e:
                        ui.notify(str(e), type='negative')
                        print(traceback.format_exc())

                ui.button('⚡ REFRESH SINGLE', on_click=refresh_single).props('flat color=cyan dense').classes('mt-2 mb-4')

                # CSV Export for AI Analysis
                with ui.card().classes('w-full bg-slate-900 p-4 mt-4 mb-4'):
                    ui.label('📋 CSV EXPORT FOR AI ANALYSIS').classes('text-sm font-bold text-yellow-400 mb-2')
                    ui.label('Condensed data - Sim #1 trajectory + all final results').classes('text-xs text-slate-500 mb-2')
                    
                    # Generate condensed CSV - Only Sim #1 monthly trajectory
                    # Get ecosystem settings from first leg
                    first_leg_cfg = sequence_config[0]['config']
                    contrib_win = first_leg_cfg.get('eco_win', 300)
                    contrib_loss = first_leg_cfg.get('eco_loss', 300)
                    
                    csv_lines = []
                    csv_lines.append('# CAREER SETTINGS')
                    csv_lines.append(f'Start_GA,{start_ga:.2f}')
                    csv_lines.append(f'Monthly_Contrib_Win,{contrib_win:.2f}')
                    csv_lines.append(f'Monthly_Contrib_Loss,{contrib_loss:.2f}')
                    csv_lines.append(f'Years,{years}')
                    csv_lines.append(f'Sessions_Per_Year,{sessions}')
                    csv_lines.append('')
                    
                    # Add Doctrine Engine Settings
                    if first_leg_cfg.get('doctrine_enabled', False):
                        csv_lines.append('# DOCTRINE ENGINE SETTINGS')
                        csv_lines.append('Doctrine_Enabled,True')
                        csv_lines.append(f"Platinum_StopLoss,{first_leg_cfg.get('doctrine_pl_stop', 10)}")
                        csv_lines.append(f"Platinum_Target,{first_leg_cfg.get('doctrine_pl_target', 10)}")
                        csv_lines.append(f"Platinum_PressWins,{first_leg_cfg.get('doctrine_pl_press_wins', 3)}")
                        csv_lines.append(f"Platinum_PressDepth,{first_leg_cfg.get('doctrine_pl_press_depth', 3)}")
                        csv_lines.append(f"Platinum_IronGate,{first_leg_cfg.get('doctrine_pl_iron', 3)}")
                        csv_lines.append(f"Tight_StopLoss,{first_leg_cfg.get('doctrine_ti_stop', 5)}")
                        csv_lines.append(f"Tight_Target,{first_leg_cfg.get('doctrine_ti_target', 5)}")
                        csv_lines.append(f"Tight_PressWins,{first_leg_cfg.get('doctrine_ti_press_wins', 5)}")
                        csv_lines.append(f"Tight_PressDepth,{first_leg_cfg.get('doctrine_ti_press_depth', 1)}")
                        csv_lines.append(f"Tight_IronGate,{first_leg_cfg.get('doctrine_ti_iron', 2)}")
                        csv_lines.append(f"Trigger_BigLoss,{first_leg_cfg.get('doctrine_loss_trigger', 8)}")
                        csv_lines.append(f"Trigger_DrawdownPct,{first_leg_cfg.get('doctrine_dd_pct', 0.15)}")
                        csv_lines.append(f"Trigger_DrawdownEur,{first_leg_cfg.get('doctrine_dd_eur', 3000)}")
                        csv_lines.append(f"Tight_MinSessions,{first_leg_cfg.get('doctrine_tight_min', 1)}")
                        csv_lines.append(f"Tight_MaxSessions,{first_leg_cfg.get('doctrine_tight_max', 2)}")
                        csv_lines.append(f"CoolOff_Enabled,{first_leg_cfg.get('doctrine_cooloff_enabled', True)}")
                        csv_lines.append(f"CoolOff_Floor,{first_leg_cfg.get('doctrine_cooloff_floor', 3000)}")
                        csv_lines.append(f"CoolOff_MinMonths,{first_leg_cfg.get('doctrine_cooloff_months', 1)}")
                        csv_lines.append(f"CoolOff_RecoveryPct,{first_leg_cfg.get('doctrine_recovery_pct', 0.07)}")
                        csv_lines.append('')
                    else:
                        csv_lines.append('# DOCTRINE ENGINE SETTINGS')
                        csv_lines.append('Doctrine_Enabled,False')
                        csv_lines.append('')
                    csv_lines.append('')
                    csv_lines.append('# SIM #1 MONTHLY TRAJECTORY')
                    csv_lines.append('Month,Bankroll')
                    for month_idx, bankroll in enumerate(sim1_traj, 1):
                        csv_lines.append(f"{month_idx},{bankroll:.2f}")
                    
                    # Add all simulations final results
                    csv_lines.append('')
                    csv_lines.append('# ALL SIMULATIONS FINAL RESULTS')
                    csv_lines.append('Simulation,Final_Bankroll,Net_Profit,Success')
                    for sim_idx, res in enumerate(valid_results, 1):
                        final = res['final']
                        net = final - start_ga
                        success = 1 if final > start_ga else 0
                        csv_lines.append(f"{sim_idx},{final:.2f},{net:.2f},{success}")
                    
                    # Add yearly milestones from Sim #1
                    csv_lines.append('')
                    csv_lines.append('# SIM #1 YEARLY MILESTONES')
                    csv_lines.append('Year,Bankroll')
                    for year in range(years):
                        month_idx = (year + 1) * 12 - 1
                        if month_idx < len(sim1_traj):
                            csv_lines.append(f"{year+1},{sim1_traj[month_idx]:.2f}")
                    
                    csv_text = '\n'.join(csv_lines)
                    csv_area = ui.textarea(value=csv_text).classes('w-full font-mono text-xs').props('rows=10 readonly')
                    
                    def copy_career_csv():
                        ui.run_javascript(f'navigator.clipboard.writeText(`{csv_text}`)')
                        ui.notify('Career CSV copied to clipboard!', type='positive')
                    
                    ui.button('COPY CSV', on_click=copy_career_csv).props('icon=content_copy color=yellow').classes('w-full mt-2')
                    
                    # Summary statistics CSV
                    ui.label('CAREER SUMMARY CSV').classes('text-xs font-bold text-slate-400 mt-4 mb-2')
                    final_bankrolls = [r['final'] for r in valid_results]
                    first_leg_cfg = sequence_config[0]['config']
                    contrib_win = first_leg_cfg.get('eco_win', 300)
                    contrib_loss = first_leg_cfg.get('eco_loss', 300)
                    career_summary_csv = f"""Metric,Value
Total_Simulations,{len(valid_results)}
Start_GA,{start_ga:.2f}
Monthly_Contrib_Win,{contrib_win:.2f}
Monthly_Contrib_Loss,{contrib_loss:.2f}
Years,{years}
Sessions_Per_Year,{sessions}
Survival_Rate,{survival_rate:.2f}
Median_Final_Bankroll,{np.median(final_bankrolls):.2f}
Avg_Final_Bankroll,{np.mean(final_bankrolls):.2f}
Min_Final_Bankroll,{np.min(final_bankrolls):.2f}
Max_Final_Bankroll,{np.max(final_bankrolls):.2f}
Median_Monthly_Cost,{med_cost:.2f}
Avg_Monthly_Cost,{avg_cost:.2f}
Total_Months,{years * 12}
Fallback_Threshold,{slider_fallback.value}
Promotion_Buffer,{slider_promotion_buffer.value}"""
                    
                    career_summary_area = ui.textarea(value=career_summary_csv).classes('w-full font-mono text-xs').props('rows=15 readonly')
                    
                    def copy_career_summary():
                        ui.run_javascript(f'navigator.clipboard.writeText(`{career_summary_csv}`)')
                        ui.notify('Career summary copied!', type='positive')
                    
                    ui.button('COPY SUMMARY', on_click=copy_career_summary).props('icon=content_copy color=cyan').classes('w-full mt-2')
                    
                    # Event log CSV
                    ui.label('EVENT LOG CSV (Sim #1)').classes('text-xs font-bold text-slate-400 mt-4 mb-2')
                    event_csv_lines = ['Month,Event,Details']
                    for l in sim1_log:
                        # Escape commas in details
                        details = l['details'].replace(',', ';')
                        event_csv_lines.append(f"{l['month']},{l['event']},{details}")
                    event_csv = '\\n'.join(event_csv_lines)
                    
                    event_csv_area = ui.textarea(value=event_csv).classes('w-full font-mono text-xs').props('rows=8 readonly')
                    
                    def copy_event_log():
                        ui.run_javascript(f'navigator.clipboard.writeText(`{event_csv}`)')
                        ui.notify('Event log copied!', type='positive')
                    
                    ui.button('COPY EVENT LOG', on_click=copy_event_log).props('icon=content_copy color=purple').classes('w-full mt-2')

                with ui.expansion('Event Log (Sim #1)', icon='history').classes('w-full bg-slate-800 mt-4'):
                    for l in sim1_log:
                        color = "text-yellow-400" if l['event'] == 'PROMOTION' else "text-slate-400"
                        if l['event'] == 'INSOLVENT': color = "text-red-500 font-bold"
                        if l['event'] == 'ERROR': color = "text-red-600 font-bold"
                        if l['event'] == 'DOCTRINE': color = "text-purple-400 font-bold"
                        ui.label(f"M{l['month']} | {l['event']}: {l['details']}").classes(f'text-xs {color}')
                
                # Doctrine Summary for Sim #1
                if sim1_doctrine := valid_results[0].get('doctrine_summary'):
                    with ui.expansion('⚡ Doctrine Summary (Sim #1)', icon='insights').classes('w-full bg-purple-900 mt-4'):
                        ui.label(f"Final State: {sim1_doctrine['final_state']}").classes('text-sm text-white font-bold')
                        ui.label(f"Peak GA: €{sim1_doctrine['peak_ga']:,.0f}").classes('text-xs text-slate-300')
                        ui.label(f"Platinum Sessions: {sim1_doctrine['platinum_sessions']}").classes('text-xs text-slate-300')
                        ui.label(f"Tight Sessions: {sim1_doctrine['tight_sessions']}").classes('text-xs text-slate-300')
                        ui.label(f"Cool-Off Months: {sim1_doctrine['cooloff_months']}").classes('text-xs text-slate-300')
                        
                        if sim1_doctrine['transitions']:
                            ui.label('State Transitions:').classes('text-xs text-purple-300 font-bold mt-2')
                            for trans in sim1_doctrine['transitions'][:10]:  # Show first 10 transitions
                                ui.label(f"Session {trans['session']}: {trans['from']} → {trans['to']} ({trans['reason']})").classes('text-xs text-slate-400')
        except Exception as e:
            ui.notify(f'Critical error: {e}', type='negative')
            import traceback; traceback.print_exc()
        finally:
            progress.set_visibility(False)

    # --- UI LAYOUT ---
    with ui.column().classes('w-full max-w-4xl mx-auto gap-6 p-4'):
        ui.label('CAREER SIMULATOR (MULTI-STAGE)').classes('text-2xl font-light text-purple-300')
        ui.label('Chain strategies. Analyze Probability (Multiverse) vs Reality (Single).').classes('text-sm text-slate-500 -mt-4')
        
        with ui.grid(columns=2).classes('w-full gap-6'):
            # LEFT: CONTROLS
            with ui.card().classes('w-full bg-slate-900 p-4'):
                ui.label('1. BUILD SEQUENCE').classes('font-bold text-white mb-2')
                
                profile = load_profile()
                saved = list(profile.get('saved_strategies', {}).keys())
                
                select_strat = ui.select(saved, label='Select Strategy').classes('w-full')
                ui.label('Target Bankroll to Upgrade').classes('text-xs text-slate-500 mt-2')
                slider_target = ui.slider(min=2000, max=100000, step=1000, value=10000).props('color=yellow')
                ui.label().bind_text_from(slider_target, 'value', lambda v: f'Switch @ €{v:,.0f}')
                
                ui.button('ADD LEG', on_click=add_leg).props('icon=add color=purple').classes('w-full mt-4')
                
                ui.separator().classes('bg-slate-700 my-4')
                
                ui.label('2. GLOBAL SETTINGS').classes('font-bold text-white mb-2')
                slider_start_ga = ui.slider(min=1000, max=50000, value=2000).props('color=green'); ui.label().bind_text_from(slider_start_ga, 'value', lambda v: f'Start: €{v}')
                slider_years = ui.slider(min=1, max=20, value=5).props('color=blue'); ui.label().bind_text_from(slider_years, 'value', lambda v: f'{v} Years')
                slider_freq = ui.slider(min=10, max=100, value=20).props('color=blue'); ui.label().bind_text_from(slider_freq, 'value', lambda v: f'{v} Sess/Yr')
                
                ui.label('Universes (Simulations)').classes('text-xs text-slate-400 mt-2')
                slider_num_sims = ui.slider(min=10, max=1000, value=20).props('color=cyan')
                ui.label().bind_text_from(slider_num_sims, 'value', lambda v: f'{v} Universes')
                
                ui.separator().classes('bg-slate-700 my-4')
                ui.label('🔄 FALLBACK MECHANISM').classes('font-bold text-orange-400 mb-2')
                ui.label('Fallback Threshold (% below promotion)').classes('text-xs text-slate-400')
                slider_fallback = ui.slider(min=60, max=95, value=80, step=5).props('color=orange')
                ui.label().bind_text_from(slider_fallback, 'value', lambda v: f'{v}% - Demote if bankroll drops below this')
                
                ui.label('Promotion Buffer (% above target)').classes('text-xs text-slate-400 mt-2')
                slider_promotion_buffer = ui.slider(min=100, max=150, value=120, step=5).props('color=yellow')
                ui.label().bind_text_from(slider_promotion_buffer, 'value', lambda v: f'{v}% - Promote when this reached')
                
                ui.button('RUN CAREER', on_click=run_simulation).props('icon=play_arrow color=green size=lg').classes('w-full mt-6')

            # RIGHT: SEQUENCE VIEW
            with ui.column().classes('w-full'):
                ui.label('CAREER PATH').classes('font-bold text-white mb-2')
                legs_container = ui.column().classes('w-full')
                progress = ui.linear_progress().props('indeterminate color=purple').classes('w-full'); progress.set_visibility(False)
                results_area = ui.column().classes('w-full')
                chart_single_container = ui.column().classes('w-full')

    refresh_leg_ui()
