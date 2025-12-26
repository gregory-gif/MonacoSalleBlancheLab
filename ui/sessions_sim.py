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
                    for s in range(num_sessions):
                        session_log = []
                        bankroll = start_bankroll
                        for strat in session_strategies:
                            strat_cfg = saved_strats.get(strat['strategy'])
                            if not strat_cfg:
                                session_log.append({'game': strat['game'], 'strategy': strat['strategy'], 'result': 'NOT FOUND', 'bankroll': bankroll})
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
                                pnl, *_ = RouletteWorker.run_session(bankroll, overrides, tier_map, overrides.ratchet_enabled, overrides.penalty_box_enabled, active_level, mode, base_bet)
                            else:
                                pnl, *_ = BaccaratWorker.run_session(bankroll, overrides, tier_map, overrides.ratchet_enabled, overrides.penalty_box_enabled, active_level, mode, base_bet)
                            
                            bankroll += pnl
                            session_log.append({'game': strat['game'], 'strategy': strat['strategy'], 'result': pnl, 'bankroll': bankroll})
                        
                        all_results.append({'session': s+1, 'final_bankroll': bankroll, 'log': session_log})
                    return all_results
                
                # Run in thread
                all_results = await asyncio.to_thread(run_all_sessions)
                
                # Update progress
                progress_bar.set_value(1.0)
                status_label.set_text('Simulation complete!')
                progress_bar.set_visibility(False)
                
                # Calculate statistics
                final_bankrolls = [r['final_bankroll'] for r in all_results]
                avg_final = np.mean(final_bankrolls)
                min_final = np.min(final_bankrolls)
                max_final = np.max(final_bankrolls)
                profit_sessions = len([b for b in final_bankrolls if b > start_bankroll])
                loss_sessions = len([b for b in final_bankrolls if b <= start_bankroll])
                total_profit = sum([b - start_bankroll for b in final_bankrolls])
                avg_profit_per_session = total_profit / len(final_bankrolls)
                
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
                            ui.label('AVG FINAL BANKROLL').classes('text-xs text-slate-500 font-bold')
                            ui.label(f'€{avg_final:,.0f}').classes('text-3xl font-bold text-cyan-400')
                        
                        with ui.card().classes('flex-1 bg-slate-800 p-4'):
                            ui.label('WIN RATE').classes('text-xs text-slate-500 font-bold')
                            win_pct = (profit_sessions / len(all_results)) * 100
                            color = 'text-green-400' if win_pct >= 50 else 'text-red-400'
                            ui.label(f'{win_pct:.1f}%').classes(f'text-3xl font-bold {color}')
                            ui.label(f'{profit_sessions}W / {loss_sessions}L').classes('text-xs text-slate-500')
                        
                        with ui.card().classes('flex-1 bg-slate-800 p-4'):
                            ui.label('NET P/L').classes('text-xs text-slate-500 font-bold')
                            pl_color = 'text-green-400' if total_profit > 0 else 'text-red-400'
                            ui.label(f'€{total_profit:,.0f}').classes(f'text-3xl font-bold {pl_color}')
                            ui.label(f'Avg: €{avg_profit_per_session:,.0f}/sess').classes('text-xs text-slate-500')
                    
                    # Bankroll progression chart
                    with ui.card().classes('w-full bg-slate-900 p-4 mb-4'):
                        ui.label('BANKROLL PROGRESSION').classes('text-sm font-bold text-white mb-2')
                        
                        sessions = [r['session'] for r in all_results]
                        bankrolls = [r['final_bankroll'] for r in all_results]
                        
                        fig = go.Figure()
                        
                        # Line chart
                        fig.add_trace(go.Scatter(
                            x=sessions, 
                            y=bankrolls,
                            mode='lines+markers',
                            name='Bankroll',
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
                        
                        # Average line
                        fig.add_hline(
                            y=avg_final,
                            line_dash="dot",
                            line_color="white",
                            annotation_text=f"Avg: €{avg_final:,.0f}",
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
                            profit = res['final_bankroll'] - start_bankroll
                            profit_str = f"+€{profit:,.0f}" if profit >= 0 else f"€{profit:,.0f}"
                            result = '✅ WIN' if profit > 0 else ('➖ BREAK-EVEN' if profit == 0 else '❌ LOSS')
                            table_rows.append({
                                'Session': res['session'],
                                'Final': f"€{res['final_bankroll']:,.0f}",
                                'P/L': profit_str,
                                'Result': result
                            })
                        
                        ui.aggrid({
                            'columnDefs': [
                                {'headerName': '#', 'field': 'Session', 'width': 60},
                                {'headerName': 'Final Bankroll', 'field': 'Final', 'width': 140},
                                {'headerName': 'Profit/Loss', 'field': 'P/L', 'width': 120},
                                {'headerName': 'Result', 'field': 'Result', 'width': 120}
                            ],
                            'rowData': table_rows,
                            'domLayout': 'autoHeight'
                        }).classes('w-full theme-balham-dark')
                    
                    # Strategy breakdown per session (expandable)
                    with ui.card().classes('w-full bg-slate-900 p-4'):
                        ui.label('STRATEGY BREAKDOWN BY SESSION').classes('text-sm font-bold text-white mb-2')
                        for res in all_results:
                            profit = res['final_bankroll'] - start_bankroll
                            profit_color = 'text-green-400' if profit > 0 else 'text-red-400'
                            with ui.expansion(
                                f"Session {res['session']}: €{res['final_bankroll']:,.0f} ({profit:+,.0f})",
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
