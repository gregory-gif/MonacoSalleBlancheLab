from nicegui import ui
from utils.persistence import load_profile
from engine.strategy_rules import StrategyOverrides
from engine.tier_params import generate_tier_map, get_tier_for_ga
from ui.roulette_sim import RouletteWorker
from ui.simulator import BaccaratWorker
import numpy as np
import asyncio
import plotly.graph_objects as go

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
            
            ui.separator().classes('bg-slate-700 my-4')
            ui.label('💰 BETWEEN-SESSION CONTRIBUTIONS').classes('text-xs font-bold text-green-400 mb-2')
            switch_contributions = ui.switch('Enable Contributions').props('color=green')
            switch_contributions.value = False
            slider_contrib_win = ui.slider(min=0, max=1000, value=300, step=50).props('color=green')
            ui.label().bind_text_from(slider_contrib_win, 'value', lambda v: f'After Win: +€{v:,.0f}')
            slider_contrib_loss = ui.slider(min=0, max=1000, value=300, step=50).props('color=green')
            ui.label().bind_text_from(slider_contrib_loss, 'value', lambda v: f'After Loss: +€{v:,.0f}')

        # Results area placeholder
        results_area = ui.column().classes('w-full mt-8')
        progress_bar = ui.linear_progress().props('color=green').classes('mt-4')
        progress_bar.set_visibility(False)
        status_label = ui.label('').classes('text-sm text-slate-400 mt-2')

        async def run_sessions_sim():
            if not session_strategies:
                ui.notify('Add at least one strategy to the session.', type='warning')
                return
            
            try:
                progress_bar.set_visibility(True)
                progress_bar.set_value(0)
                status_label.set_text('Running simulations...')
                
                num_sessions = int(slider_num_sessions.value)
                start_bankroll = float(slider_start_bankroll.value)
                profile = load_profile()
                saved_strats = profile.get('saved_strategies', {})
                
                def run_all_sessions():
                    all_results = []
                    game_bankroll = start_bankroll  # Pure casino money
                    game_account = start_bankroll   # GA = Start + contributions + game profit
                    total_contributions = 0
                    use_contributions = switch_contributions.value
                    contrib_win = slider_contrib_win.value
                    contrib_loss = slider_contrib_loss.value
                    insolvency_floor = 0  # Cannot go below zero
                    
                    for s in range(num_sessions):
                        # INSOLVENCY CHECK - Cannot play if bankroll is at/below floor
                        if game_bankroll <= insolvency_floor:
                            # Record insolvent session
                            all_results.append({
                                'session': s+1, 
                                'game_bankroll': game_bankroll,
                                'pure_session_pnl': 0,
                                'game_account': game_account,
                                'contribution': 0,
                                'log': [{'game': 'INSOLVENT', 'strategy': 'NO PLAY', 'result': 0, 'bankroll': game_bankroll}],
                                'total_contributions_so_far': total_contributions,
                                'is_insolvent': True
                            })
                            continue
                        
                        session_log = []
                        starting_bankroll_this_session = game_bankroll
                        
                        for strat in session_strategies:
                            strat_cfg = saved_strats.get(strat['strategy'])
                            if not strat_cfg:
                                session_log.append({'game': strat['game'], 'strategy': strat['strategy'], 'result': 'NOT FOUND', 'bankroll': game_bankroll})
                                continue
                            
                            # Create overrides from saved config
                            from engine.strategy_rules import BetStrategy
                            
                            # Get bet strategy
                            raw_bet = strat_cfg.get('tac_bet', 'BANKER')
                            if strat['game'] == 'Baccarat':
                                bet_strat = getattr(BetStrategy, raw_bet, BetStrategy.BANKER)
                            else:
                                bet_strat = raw_bet  # For roulette it's a string
                            
                            overrides = StrategyOverrides(
                                iron_gate_limit=strat_cfg.get('tac_iron', 3),
                                stop_loss_units=strat_cfg.get('risk_stop', 10),
                                profit_lock_units=strat_cfg.get('risk_prof', 10),
                                press_trigger_wins=strat_cfg.get('tac_press', 1),
                                press_depth=strat_cfg.get('tac_depth', 3),
                                bet_strategy=bet_strat,
                                shoes_per_session=strat_cfg.get('tac_shoes', 3),
                                penalty_box_enabled=strat_cfg.get('tac_penalty', True),
                                ratchet_enabled=strat_cfg.get('risk_ratch', False),
                                ratchet_mode=strat_cfg.get('risk_ratch_mode', 'Standard'),
                                smart_exit_enabled=strat_cfg.get('smart_exit_enabled', True),
                                smart_window_start=strat_cfg.get('smart_window_start', 90),
                                min_profit_to_lock=strat_cfg.get('min_profit_to_lock', 20),
                                trailing_drop_pct=strat_cfg.get('trailing_drop_pct', 0.20)
                            )
                            
                            tier_map = generate_tier_map(
                                strat_cfg.get('tac_safety', 25), 
                                mode=strat_cfg.get('tac_mode', 'Standard'), 
                                game_type=strat['game'], 
                                base_bet=strat_cfg.get('tac_base_bet', 10.0)
                            )
                            active_level = 1
                            mode = strat_cfg.get('tac_mode', 'Standard')
                            base_bet = strat_cfg.get('tac_base_bet', 10.0)
                            
                            # Simulate
                            if strat['game'] == 'Roulette':
                                pnl, *_ = RouletteWorker.run_session(game_bankroll, overrides, tier_map, overrides.ratchet_enabled, overrides.penalty_box_enabled, active_level, mode, base_bet)
                            else:
                                pnl, *_ = BaccaratWorker.run_session(game_bankroll, overrides, tier_map, overrides.ratchet_enabled, overrides.penalty_box_enabled, active_level, mode, base_bet)
                            
                            # Update game bankroll with pure PnL
                            game_bankroll += pnl
                            # ENFORCE INSOLVENCY FLOOR - clamp at minimum
                            game_bankroll = max(game_bankroll, insolvency_floor)
                            session_log.append({'game': strat['game'], 'strategy': strat['strategy'], 'result': pnl, 'bankroll': game_bankroll})
                        
                        # Calculate pure session PnL (no contributions)
                        session_pnl = game_bankroll - starting_bankroll_this_session
                        
                        # Update GA with game profit/loss FIRST
                        game_account += session_pnl
                        
                        # Then apply contribution to GA
                        contribution_this_session = 0
                        if use_contributions:
                            if session_pnl > 0:
                                contribution_this_session = contrib_win
                            else:
                                contribution_this_session = contrib_loss
                            game_account += contribution_this_session
                            total_contributions += contribution_this_session
                        
                        all_results.append({
                            'session': s+1, 
                            'game_bankroll': game_bankroll,  # Pure game bankroll (clamped at floor)
                            'pure_session_pnl': session_pnl,  # Pure game result
                            'game_account': game_account,  # GA = Start + Contributions + Game Profit
                            'contribution': contribution_this_session,
                            'log': session_log,
                            'total_contributions_so_far': total_contributions,
                            'is_insolvent': False
                        })
                    return all_results, total_contributions
                
                # Run in thread
                all_results, total_contributions = await asyncio.to_thread(run_all_sessions)
                
                # Update progress
                progress_bar.set_value(1.0)
                status_label.set_text('Simulation complete!')
                progress_bar.set_visibility(False)
                
                # Calculate statistics - PURE GAME RESULTS
                pure_session_pnls = [r['pure_session_pnl'] for r in all_results]
                final_game_bankroll = all_results[-1]['game_bankroll']
                final_game_account = all_results[-1]['game_account']
                
                # Pure game profit (no contributions) - this is B_end - SB
                total_game_profit = final_game_bankroll - start_bankroll
                avg_game_profit = np.mean(pure_session_pnls)
                
                # Verify GA formula: GA_end should equal SB + C + P
                expected_ga = start_bankroll + total_contributions + total_game_profit
                assert abs(final_game_account - expected_ga) < 1e-6, f"GA mismatch: {final_game_account} != {expected_ga}"
                
                # Win rate based on pure session PnL
                profit_sessions = len([p for p in pure_session_pnls if p > 0])
                loss_sessions = len([p for p in pure_session_pnls if p <= 0])
                
                # Financial metrics - CORRECTED FORMULAS
                # Net result = C + P (contributions + game profit)
                net_result = total_contributions + total_game_profit
                
                # True monthly cost = -P / months (cost of pure casino EV)
                # This MUST NOT change when contributions are toggled on/off
                months = len(all_results)
                true_monthly_cost = -total_game_profit / months if months > 0 else 0
                
                # Display results
                results_area.clear()
                with results_area:
                    ui.label('📊 SESSION SIMULATOR RESULTS').classes('text-2xl text-orange-300 font-bold mb-4')
                    
                    # Summary Cards
                    with ui.row().classes('w-full gap-4 mb-4'):
                        with ui.card().classes('flex-1 bg-slate-800 p-4'):
                            ui.label('TOTAL SESSIONS').classes('text-xs text-slate-500 font-bold')
                            ui.label(f'{len(all_results)}').classes('text-3xl font-bold text-white')
                        
                        with ui.card().classes('flex-1 bg-slate-800 p-4'):
                            ui.label('PURE GAME PROFIT').classes('text-xs text-slate-500 font-bold')
                            color = 'text-green-400' if total_game_profit > 0 else 'text-red-400'
                            ui.label(f'€{total_game_profit:,.0f}').classes(f'text-3xl font-bold {color}')
                            ui.label(f'Avg: €{avg_game_profit:,.0f}/sess').classes('text-xs text-slate-500')
                        
                        with ui.card().classes('flex-1 bg-slate-800 p-4'):
                            ui.label('WIN RATE').classes('text-xs text-slate-500 font-bold')
                            win_pct = (profit_sessions / len(all_results)) * 100
                            color = 'text-green-400' if win_pct >= 50 else 'text-red-400'
                            ui.label(f'{win_pct:.1f}%').classes(f'text-3xl font-bold {color}')
                            ui.label(f'{profit_sessions}W / {loss_sessions}L').classes('text-xs text-slate-500')
                        
                        with ui.card().classes('flex-1 bg-slate-800 p-4'):
                            ui.label('MONTHLY COST').classes('text-xs text-slate-500 font-bold')
                            cost_color = 'text-red-400' if true_monthly_cost > 0 else 'text-green-400'
                            ui.label(f'€{true_monthly_cost:,.0f}').classes(f'text-3xl font-bold {cost_color}')
                            ui.label(f'Pure EV/month').classes('text-xs text-slate-500')
                    
                    # Bankroll progression chart - PURE GAME RESULTS
                    with ui.card().classes('w-full bg-slate-900 p-4 mb-4'):
                        ui.label('PURE GAME BANKROLL (No Contributions in Curve)').classes('text-sm font-bold text-yellow-400 mb-2')
                        
                        sessions = [r['session'] for r in all_results]
                        # Plot pure game bankroll progression (contributions already injected for next session)
                        game_bankrolls = [r['game_bankroll'] for r in all_results]
                        
                        fig = go.Figure()
                        
                        # Game bankroll line
                        fig.add_trace(go.Scatter(
                            x=sessions, 
                            y=game_bankrolls,
                            mode='lines+markers',
                            name='Game Bankroll',
                            line=dict(color='#22d3ee', width=2),
                            marker=dict(size=6, color='#22d3ee')
                        ))
                        
                        # Starting bankroll reference line
                        fig.add_hline(
                            y=start_bankroll,
                            line_dash="dash",
                            line_color="yellow",
                            annotation_text=f"Start: €{start_bankroll:,.0f}",
                            annotation_position="right"
                        )
                        
                        fig.update_layout(
                            title='Session-by-Session Bankroll',
                            xaxis_title='Session #',
                            yaxis_title='Final Bankroll (€)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='#94a3b8'),
                            margin=dict(l=20, r=20, t=40, b=20),
                            height=350
                        )
                        
                        ui.plotly(fig).classes('w-full')
                    
                    # Detailed results table
                    with ui.card().classes('w-full bg-slate-900 p-4 mb-4'):
                        ui.label('DETAILED SESSION RESULTS').classes('text-sm font-bold text-white mb-2')
                        table_rows = []
                        for res in all_results:
                            session_pnl = res['pure_session_pnl']
                            pnl_str = f"+€{session_pnl:,.0f}" if session_pnl >= 0 else f"€{session_pnl:,.0f}"
                            result = '✅ WIN' if session_pnl > 0 else ('➖ BREAK-EVEN' if session_pnl == 0 else '❌ LOSS')
                            contrib_str = f"+€{res['contribution']:,.0f}" if res['contribution'] > 0 else "-"
                            table_rows.append({
                                'Session': res['session'],
                                'Pure PnL': pnl_str,
                                'Contribution': contrib_str,
                                'Final Bankroll': f"€{res['game_bankroll']:,.0f}",
                                'Result': result
                            })
                        
                        ui.aggrid({
                            'columnDefs': [
                                {'headerName': '#', 'field': 'Session', 'width': 60},
                                {'headerName': 'Pure PnL', 'field': 'Pure PnL', 'width': 100},
                                {'headerName': 'Contribution', 'field': 'Contribution', 'width': 110},
                                {'headerName': 'Final Bankroll', 'field': 'Final Bankroll', 'width': 140},
                                {'headerName': 'Result', 'field': 'Result', 'width': 100}
                            ],
                            'rowData': table_rows,
                            'domLayout': 'autoHeight'
                        }).classes('w-full theme-balham-dark')
                    
                    # CSV Export for AI Analysis
                    with ui.card().classes('w-full bg-slate-900 p-4 mb-4'):
                        ui.label('📋 CSV EXPORT FOR AI ANALYSIS').classes('text-sm font-bold text-yellow-400 mb-2')
                        ui.label('Pure game PnL separated from contributions').classes('text-xs text-slate-500 mb-2')
                        
                        # Generate detailed CSV
                        csv_lines = []
                        csv_lines.append('Session,Game,Strategy,Pure_PNL,Bankroll_After,Contribution,Game_Bankroll')
                        for res in all_results:
                            session_num = res['session']
                            contribution = res['contribution']
                            game_bankroll = res['game_bankroll']
                            
                            for entry in res['log']:
                                csv_lines.append(f"{session_num},{entry['game']},{entry['strategy']},{entry['result']:.2f},{entry['bankroll']:.2f},{contribution:.2f},{game_bankroll:.2f}")
                        
                        csv_text = '\n'.join(csv_lines)
                        csv_area = ui.textarea(value=csv_text).classes('w-full font-mono text-xs').props('rows=10 readonly')
                        
                        def copy_csv():
                            ui.run_javascript(f'navigator.clipboard.writeText(`{csv_text}`)')
                            ui.notify('CSV copied to clipboard!', type='positive')
                        
                        ui.button('COPY CSV', on_click=copy_csv).props('icon=content_copy color=yellow').classes('w-full mt-2')
                        
                        # Summary statistics CSV
                        ui.label('SUMMARY STATISTICS CSV').classes('text-xs font-bold text-slate-400 mt-4 mb-2')
                        summary_csv = f"""Metric,Value
Total_Sessions,{len(all_results)}
Start_Bankroll,{start_bankroll:.2f}
Contributions_Enabled,{switch_contributions.value}
Contrib_After_Win,{slider_contrib_win.value:.2f}
Contrib_After_Loss,{slider_contrib_loss.value:.2f}
Total_Contributions,{total_contributions:.2f}
Final_Game_Bankroll,{final_game_bankroll:.2f}
Final_Game_Account,{final_game_account:.2f}
Total_Game_Profit,{total_game_profit:.2f}
Avg_Game_Profit_Per_Session,{avg_game_profit:.2f}
Net_Result,{net_result:.2f}
True_Monthly_Cost,{true_monthly_cost:.2f}
Win_Sessions,{profit_sessions}
Loss_Sessions,{loss_sessions}
Win_Rate,{(profit_sessions/len(all_results)*100):.2f}
Formula_Check,GA={start_bankroll:.2f}+{total_contributions:.2f}+{total_game_profit:.2f}={final_game_account:.2f}"""
                        summary_area = ui.textarea(value=summary_csv).classes('w-full font-mono text-xs').props('rows=12 readonly')
                        
                        def copy_summary():
                            ui.run_javascript(f'navigator.clipboard.writeText(`{summary_csv}`)')
                            ui.notify('Summary CSV copied!', type='positive')
                        
                        ui.button('COPY SUMMARY', on_click=copy_summary).props('icon=content_copy color=cyan').classes('w-full mt-2')
                    
                    # Strategy breakdown per session (expandable)
                    with ui.card().classes('w-full bg-slate-900 p-4'):
                        ui.label('STRATEGY BREAKDOWN BY SESSION').classes('text-sm font-bold text-white mb-2')
                        for res in all_results:
                            pure_pnl = res['pure_session_pnl']
                            contribution = res['contribution']
                            pnl_color = 'text-green-400' if pure_pnl > 0 else 'text-red-400'
                            contrib_str = f" + €{contribution:,.0f} contrib" if contribution > 0 else ""
                            with ui.expansion(
                                f"Session {res['session']}: Pure PnL €{pure_pnl:+,.0f}{contrib_str}",
                                icon='receipt_long'
                            ).classes('w-full bg-slate-800 text-white'):
                                for entry in res['log']:
                                    with ui.row().classes('w-full justify-between items-center p-2 border-b border-slate-700'):
                                        ui.label(f"{entry['game']} - {entry['strategy']}").classes('text-sm text-slate-300')
                                        result_color = 'text-green-400' if entry['result'] > 0 else 'text-red-400'
                                        ui.label(f"€{entry['result']:+,.2f}").classes(f'text-sm font-bold {result_color}')
                                        ui.label(f"→ €{entry['bankroll']:,.0f}").classes('text-xs text-slate-500')
            
            except Exception as e:
                progress_bar.set_visibility(False)
                status_label.set_text(f'Error: {str(e)}')
                ui.notify(f'Simulation error: {str(e)}', type='negative')
                import traceback
                print(traceback.format_exc())

        # Create run button with proper async handler
        ui.button('RUN SESSIONS SIM', on_click=run_sessions_sim).props('icon=play_arrow color=green size=lg').classes('w-full mt-4')

def setup():
    show_sessions_sim()
