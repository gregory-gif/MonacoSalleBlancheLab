from nicegui import ui
import plotly.graph_objects as go
from utils.persistence import load_profile, save_profile, get_session_logs

def show_dashboard():
    # 1. Load Data
    profile = load_profile()
    current_ga = profile.get('ga', 1700.0)
    
    # Fetch History for the Graph
    logs = get_session_logs()
    # Sort logs by date (Oldest -> Newest) so the line draws correctly
    logs.sort(key=lambda x: x.get('date', ''))
    
    # Prepare Data Points
    # We start with an empty list or specific points
    dates = [entry.get('date') for entry in logs]
    balances = [entry.get('end_ga') for entry in logs]
    
    # 2. Hero Section (The Big Number)
    with ui.column().classes('w-full items-center justify-center py-8 bg-gradient-to-b from-slate-900 to-slate-800'):
        ui.label('TOTAL GAME ACCOUNT').classes('text-xs font-bold text-slate-500 tracking-widest mb-1')
        lbl_ga = ui.label(f'€{current_ga:,.0f}').classes('text-6xl font-black text-white mb-4')
        
        with ui.row().classes('gap-4'):
            # Dynamic badge based on bankroll
            if current_ga < 1000:
                ui.chip('DANGER ZONE', icon='warning').props('color=red text-color=white')
            elif current_ga >= 22500:
                ui.chip('GOLD STATUS', icon='emoji_events').props('color=yellow text-color=black')
            else:
                ui.chip('Tier 1 Active', icon='verified').props('color=green text-color=white')

    # 3. PERFORMANCE CHART (The Replacement)
    with ui.card().classes('w-full max-w-4xl mx-auto -mt-4 p-0 bg-slate-900 border border-slate-700 shadow-xl overflow-hidden'):
        if not logs:
            with ui.column().classes('w-full p-8 items-center text-center'):
                ui.icon('ssid_chart', size='3em').classes('text-slate-700')
                ui.label('No data yet.').classes('text-slate-500 font-bold')
                ui.label('Complete your first session to see your wealth curve.').classes('text-sm text-slate-600')
        else:
            fig = go.Figure()
            
            # Add the Line Trace
            fig.add_trace(go.Scatter(
                x=dates, 
                y=balances, 
                mode='lines+markers',
                line=dict(color='#4ade80', width=3, shape='spline'), # Green line, smoothed
                marker=dict(size=6, color='#22c55e', line=dict(width=1, color='white')),
                name='Bankroll'
            ))

            # Styling
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Roboto", color='#94a3b8'),
                margin=dict(l=40, r=20, t=20, b=40),
                height=300,
                xaxis=dict(
                    showgrid=False, 
                    linecolor='#334155'
                ),
                yaxis=dict(
                    gridcolor='#334155',
                    zerolinecolor='#334155',
                    tickprefix="€"
                )
            )
            
            ui.plotly(fig).classes('w-full h-72')

    # 4. Wallet Settings (Preserved)
    with ui.column().classes('w-full max-w-4xl mx-auto p-4'):
        with ui.expansion('Wallet Settings', icon='account_balance_wallet').classes('w-full bg-slate-800 text-slate-300'):
            with ui.column().classes('p-4 w-full gap-4'):
                ui.label('Manual Correction (Deposit / Withdrawal)').classes('text-sm text-slate-500')
                
                with ui.row().classes('w-full items-center gap-4'):
                    input_ga = ui.number(label='Current Balance', value=current_ga, format='%.0f').classes('flex-grow').props('outlined dark input-class="text-xl font-bold"')
                    
                    def update_wallet():
                        new_val = input_ga.value
                        if new_val is not None:
                            profile['ga'] = float(new_val)
                            save_profile(profile)
                            lbl_ga.set_text(f'€{new_val:,.0f}')
                            ui.notify(f'Wallet updated to €{new_val:,.0f}', type='positive')
                            # Note: To see the graph update, user must refresh, 
                            # or we can refactor to reload page. For now, notify is enough.
                    
                    ui.button('SAVE', on_click=update_wallet).props('color=green icon=save')
