from nicegui import ui
import plotly.graph_objects as go
from utils.persistence import load_profile, save_profile, get_session_logs

def show_dashboard():
    # 1. Load Data
    profile = load_profile()
    current_ga = profile.get('ga', 1700.0)
    
    # 2. Setup Data for Chart
    logs = get_session_logs()
    # Sort logs oldest -> newest
    logs.sort(key=lambda x: x.get('date', ''))
    
    # Clean up dates for the chart (remove seconds/microseconds)
    # Assuming date format is "%Y-%m-%d %H:%M:%S"
    dates = []
    for entry in logs:
        d_str = entry.get('date', '')
        # Try to slice off seconds if present to make axis cleaner
        try:
            if len(d_str) > 16: 
                d_str = d_str[:16] # "2025-12-09 10:00"
        except: pass
        dates.append(d_str)
        
    balances = [entry.get('end_ga') for entry in logs]

    # --- WALLET EDIT DIALOG ---
    # This hidden dialog opens only when you click the pencil icon
    with ui.dialog() as wallet_dialog, ui.card().classes('bg-slate-800 text-white p-6 min-w-[300px]'):
        ui.label('Adjust Bankroll').classes('text-lg font-bold mb-4')
        new_balance_input = ui.number('New Amount', value=current_ga, format='%.0f').props('autofocus outlined dark').classes('w-full mb-6')
        
        def commit_wallet_change():
            val = new_balance_input.value
            if val is not None:
                profile['ga'] = float(val)
                save_profile(profile)
                ui.notify(f'Wallet updated to €{val:,.0f}', type='positive')
                # Refresh page to update chart and label
                ui.navigate.to('/') 
        
        with ui.row().classes('w-full justify-end gap-2'):
            ui.button('Cancel', on_click=wallet_dialog.close).props('flat color=grey')
            ui.button('Save', on_click=commit_wallet_change).props('color=green')

    # --- MAIN LAYOUT ---
    with ui.column().classes('w-full max-w-5xl mx-auto gap-8 p-4 md:p-8'):
        
        # 3. HERO CARD (Bankroll & Status)
        with ui.card().classes('w-full p-8 bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 shadow-2xl rounded-2xl'):
            with ui.column().classes('w-full items-center text-center gap-2'):
                
                # Label
                ui.label('TOTAL GAME ACCOUNT').classes('text-xs font-bold text-blue-400 tracking-[0.2em] uppercase mb-2')
                
                # The Big Number + Edit Button
                with ui.row().classes('items-center gap-4'):
                    # Bankroll
                    lbl_ga = ui.label(f'€{current_ga:,.0f}').classes('text-6xl md:text-8xl font-black text-white tracking-tighter leading-none')
                    
                    # Edit Icon (Triggers Dialog)
                    ui.button(icon='edit', on_click=wallet_dialog.open).props('flat round color=slate-500').classes('opacity-50 hover:opacity-100 hover:bg-slate-700 transition-all')

                # Status Badges
                with ui.row().classes('gap-3 mt-6'):
                    # Tier Badge
                    with ui.element('div').classes('px-3 py-1 rounded-full bg-slate-700 border border-slate-600 flex items-center gap-2'):
                        ui.icon('verified', size='xs', color='green-400')
                        ui.label('Tier 1 Ready').classes('text-xs font-bold text-slate-300 uppercase')
                    
                    # Gold Status Badge (Dynamic)
                    is_gold = current_ga >= 22500
                    gold_bg = 'bg-yellow-900/30 border-yellow-600' if is_gold else 'bg-slate-800/50 border-slate-700 opacity-50'
                    gold_txt = 'text-yellow-400' if is_gold else 'text-slate-500'
                    
                    with ui.element('div').classes(f'px-3 py-1 rounded-full border flex items-center gap-2 {gold_bg}'):
                        ui.icon('emoji_events', size='xs').classes(gold_txt)
                        ui.label('Gold Chase').classes(f'text-xs font-bold uppercase {gold_txt}')

    
        # 4. WEALTH CHART
        with ui.card().classes('w-full p-0 bg-slate-900 border border-slate-700 shadow-lg rounded-xl overflow-hidden'):
            # Header
            with ui.row().classes('w-full px-6 py-4 border-b border-slate-800 justify-between items-center'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('show_chart', color='green-400')
                    ui.label('Performance History').classes('text-sm font-bold text-slate-300 uppercase')
                
                # Tiny stat
                if len(balances) > 1:
                    diff = balances[-1] - balances[0]
                    color = 'text-green-400' if diff >= 0 else 'text-red-400'
                    sign = '+' if diff >= 0 else ''
                    ui.label(f'{sign}€{diff:,.0f} All Time').classes(f'text-xs font-bold {color}')

            # Chart Area
            if not logs:
                with ui.column().classes('w-full h-64 items-center justify-center text-slate-600'):
                    ui.icon('ssid_chart', size='4em')
                    ui.label('No sessions recorded').classes('mt-2 text-sm')
            else:
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=dates, 
                    y=balances, 
                    mode='lines+markers',
                    line=dict(color='#4ade80', width=3, shape='spline', smoothing=1.3),
                    marker=dict(size=8, color='#166534', line=dict(width=2, color='#4ade80')),
                    hoverinfo='y+x',
                    name='Balance'
                ))

                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(family="Inter, sans-serif", color='#94a3b8'),
                    margin=dict(l=50, r=30, t=30, b=50),
                    height=400, # Taller for better visibility
                    xaxis=dict(
                        showgrid=False,
                        gridcolor='#334155',
                        zeroline=False,
                        tickangle=-45 # Tilt dates if crowded
                    ),
                    yaxis=dict(
                        gridcolor='#334155',
                        gridwidth=1,
                        zerolinecolor='#334155',
                        tickprefix="€"
                    ),
                    hovermode="x unified"
                )
                
                ui.plotly(fig).classes('w-full h-96')
