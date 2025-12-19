import csv
import os
import pandas as pd
from datetime import datetime
from nicegui import ui
import plotly.graph_objects as go

# --- CONFIGURATION ---
DATA_FILE = 'session_log.csv'
CSV_HEADERS = [
    'date', 'contribution', 
    'roulette_in', 'roulette_out', 
    'baccarat_in', 'baccarat_out', 
    'points', 'total_wealth', 'notes'
]

# --- DATA MANAGEMENT ---
def init_db():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)

def load_data():
    init_db()
    try:
        df = pd.read_csv(DATA_FILE)
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=CSV_HEADERS)
    
    if df.empty:
        return df

    df['date'] = pd.to_datetime(df['date'])
    
    # Calculate "Mattress" Strategy (Invested Capital)
    start_cap = df.iloc[0]['total_wealth'] - df.iloc[0]['contribution']
    df['cum_contrib'] = df['contribution'].cumsum()
    df['invested_capital'] = start_cap + df['cum_contrib']
    
    return df

def save_session(date, contrib, r_in, r_out, b_in, b_out, points, notes):
    df = load_data()
    
    if df.empty:
        prev_wealth = 0
    else:
        prev_wealth = df.iloc[-1]['total_wealth']

    roulette_pnl = r_out - r_in
    baccarat_pnl = b_out - b_in
    new_wealth = prev_wealth + contrib + roulette_pnl + baccarat_pnl
    
    with open(DATA_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            date, contrib, 
            r_in, r_out, 
            b_in, b_out, 
            points, new_wealth, notes
        ])

# --- UI COMPONENTS ---
def render_page():
    # Load Data
    df = load_data()
    
    # Current Metrics
    current_wealth = df.iloc[-1]['total_wealth'] if not df.empty else 0
    current_points = df.iloc[-1]['points'] if not df.empty else 0
    invested_cap = df.iloc[-1]['invested_capital'] if not df.empty and 'invested_capital' in df else 0
    pnl_lifetime = current_wealth - invested_cap
    
    # Main Container
    with ui.column().classes('w-full max-w-4xl mx-auto p-4 gap-6'):
        
        # 1. HEADER
        with ui.column().classes('w-full'):
            ui.label("The Captain's Log").classes('text-4xl font-serif font-bold text-slate-100')
            ui.label("Post-Session Ledger & Tracker").classes('text-slate-400')

        # 2. KPI CARDS (Dark Themed)
        with ui.row().classes('w-full gap-4'):
            # Wealth Card
            with ui.card().classes('flex-1 bg-slate-800 border-l-4 border-blue-500'):
                ui.label('CURRENT WEALTH (GA)').classes('text-xs text-slate-400 font-bold')
                ui.label(f"€{current_wealth:,.0f}").classes('text-3xl font-bold text-white')
            
            # PnL Card
            with ui.card().classes('flex-1 bg-slate-800 border-l-4 border-emerald-500'):
                ui.label('NET LIFE PNL').classes('text-xs text-slate-400 font-bold')
                color = 'text-emerald-400' if pnl_lifetime >= 0 else 'text-red-400'
                ui.label(f"€{pnl_lifetime:,.0f}").classes(f'text-3xl font-bold {color}')
                
            # Points Card
            with ui.card().classes('flex-1 bg-slate-800 border-l-4 border-amber-500'):
                ui.label('GOLD POINTS').classes('text-xs text-slate-400 font-bold')
                ui.label(f"{current_points:,.0f}").classes('text-3xl font-bold text-amber-400')

        # 3. CHART SECTION
        if not df.empty:
            fig = go.Figure()
            # Actual Wealth
            fig.add_trace(go.Scatter(
                x=df['date'], y=df['total_wealth'],
                mode='lines+markers', name='Actual Wealth',
                line=dict(color='#38bdf8', width=3)
            ))
            # Safe Mattress
            fig.add_trace(go.Scatter(
                x=df['date'], y=df['invested_capital'],
                mode='lines', name='Baseline (No Play)',
                line=dict(color='#94a3b8', width=2, dash='dash')
            ))
            # Insolvency
            fig.add_hline(y=1000, line_dash="dot", line_color="#ef4444", annotation_text="Iron Gate")

            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=40, r=20, t=40, b=40),
                height=350,
                legend=dict(orientation="h", y=1.1)
            )
            ui.plotly(fig).classes('w-full h-96 bg-slate-800 rounded-lg shadow-lg')

        # 4. INPUT FORM (Dark Theme Fix)
        # We use bg-slate-900 to ensure white text is visible
        with ui.expansion('LOG NEW SESSION', icon='edit_note', value=True).classes('w-full bg-slate-900 text-white border border-slate-700 rounded-lg'):
            with ui.column().classes('p-6 gap-6 w-full'):
                
                # --- ROW 1: Date & Contribution ---
                with ui.row().classes('w-full gap-4'):
                    date_input = ui.input('Date', value=datetime.now().strftime('%Y-%m-%d')).classes('w-1/3').props('dark')
                    contrib_input = ui.number('New Contribution (€)', value=0, format='%.0f').classes('flex-1').props('dark suffix="€"')
                
                ui.separator().classes('bg-slate-700')
                
                # --- ROW 2: ROULETTE ---
                with ui.row().classes('w-full items-center gap-4'):
                    with ui.row().classes('items-center w-32'):
                        ui.icon('casino').classes('text-2xl text-amber-400 mr-2')
                        ui.label('Roulette').classes('font-bold text-lg')
                    
                    r_in = ui.number('Start Balance', value=0).classes('flex-1').props('dark outlined label-color="amber"')
                    r_out = ui.number('End Balance', value=0).classes('flex-1').props('dark outlined label-color="amber"')

                # --- ROW 3: BACCARAT ---
                with ui.row().classes('w-full items-center gap-4'):
                    with ui.row().classes('items-center w-32'):
                        ui.icon('style').classes('text-2xl text-blue-400 mr-2')
                        ui.label('Baccarat').classes('font-bold text-lg')
                    
                    b_in = ui.number('Start Balance', value=0).classes('flex-1').props('dark outlined label-color="blue"')
                    b_out = ui.number('End Balance', value=0).classes('flex-1').props('dark outlined label-color="blue"')

                ui.separator().classes('bg-slate-700')

                # --- ROW 4: POINTS & NOTES ---
                with ui.row().classes('w-full gap-4'):
                    points_input = ui.number('Total Points Balance', value=current_points).classes('w-1/3').props('dark suffix="pts"')
                    notes_input = ui.input('Session Notes', placeholder='Strategy used...').classes('flex-1').props('dark')

                # --- SUBMIT BUTTON ---
                def submit():
                    save_session(
                        date_input.value,
                        float(contrib_input.value or 0),
                        float(r_in.value or 0),
                        float(r_out.value or 0),
                        float(b_in.value or 0),
                        float(b_out.value or 0),
                        float(points_input.value or 0),
                        notes_input.value
                    )
                    ui.notify('Session Logged Successfully', type='positive')
                    ui.open('/') # Reload to show new data

                ui.button('COMMIT TO LEDGER', on_click=submit).classes('w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-2')
