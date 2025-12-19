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
    """Creates the CSV file if it doesn't exist."""
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)

def load_data():
    """Loads history and calculates cumulative metrics."""
    init_db()
    try:
        df = pd.read_csv(DATA_FILE)
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=CSV_HEADERS)
    
    if df.empty:
        return df

    # Convert date
    df['date'] = pd.to_datetime(df['date'])
    
    # Calculate The "Mattress" Line (Capital + Contributions)
    # Assuming first row 'total_wealth' includes the start capital
    # We reconstruct the "Invested" line:
    
    # Base Capital (First wealth entry - First contribution)
    start_cap = df.iloc[0]['total_wealth'] - df.iloc[0]['contribution']
    
    # Cumulative Contributions
    df['cum_contrib'] = df['contribution'].cumsum()
    
    # The "What If" Line (Zero Risk)
    df['invested_capital'] = start_cap + df['cum_contrib']
    
    return df

def save_session(date, contrib, r_in, r_out, b_in, b_out, points, notes):
    """Calculates new wealth and saves the session."""
    df = load_data()
    
    # 1. Get Previous Wealth
    if df.empty:
        # FIRST RUN: We need to ask for Starting Capital. 
        # For now, we assume (Roulette In + Baccarat In) was the Start Capital 
        # unless a Contribution covers it.
        # Let's simplify: Previous Wealth = 0
        prev_wealth = 0
    else:
        prev_wealth = df.iloc[-1]['total_wealth']

    # 2. Calculate PnL for this session
    roulette_pnl = r_out - r_in
    baccarat_pnl = b_out - b_in
    
    # 3. New Wealth Calculation
    # New Wealth = Old Wealth + New Money (Contrib) + Gaming PnL
    new_wealth = prev_wealth + contrib + roulette_pnl + baccarat_pnl
    
    # 4. Append to CSV
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
    
    # Determine Status
    current_wealth = df.iloc[-1]['total_wealth'] if not df.empty else 0
    current_points = df.iloc[-1]['points'] if not df.empty else 0
    invested_cap = df.iloc[-1]['invested_capital'] if not df.empty and 'invested_capital' in df else 0
    
    pnl_lifetime = current_wealth - invested_cap
    
    with ui.column().classes('w-full max-w-4xl mx-auto p-4'):
        
        # === HEADER ===
        ui.label("The Captain's Log").classes('text-3xl font-serif font-bold text-slate-800')
        ui.label("Post-Session Ledger & Tracker").classes('text-slate-500 mb-6')

        # === KPI CARDS ===
        with ui.row().classes('w-full gap-4 mb-8'):
            with ui.card().classes('flex-1 bg-slate-100'):
                ui.label('Current Wealth (GA)').classes('text-xs text-slate-500 uppercase')
                ui.label(f"€{current_wealth:,.0f}").classes('text-2xl font-bold text-slate-800')
            
            with ui.card().classes('flex-1 bg-slate-100'):
                ui.label('Net Life PnL').classes('text-xs text-slate-500 uppercase')
                color = 'text-green-600' if pnl_lifetime >= 0 else 'text-red-600'
                ui.label(f"€{pnl_lifetime:,.0f}").classes(f'text-2xl font-bold {color}')
                
            with ui.card().classes('flex-1 bg-amber-50'):
                ui.label('MyMonteCarlo Points').classes('text-xs text-amber-700 uppercase')
                ui.label(f"{current_points:,.0f}").classes('text-2xl font-bold text-amber-900')

        # === CHARTS ===
        if not df.empty:
            # CHART 1: WEALTH vs "MATTRESS"
            fig_wealth = go.Figure()
            
            # The "Real" Line (You)
            fig_wealth.add_trace(go.Scatter(
                x=df['date'], y=df['total_wealth'],
                mode='lines+markers', name='Actual Wealth (GA)',
                line=dict(color='#1e293b', width=3)
            ))
            
            # The "What If" Line (Mattress)
            fig_wealth.add_trace(go.Scatter(
                x=df['date'], y=df['invested_capital'],
                mode='lines', name='No-Play Baseline',
                line=dict(color='#94a3b8', width=2, dash='dash')
            ))
            
            # The "Iron Gate" (Insolvency) - Hardcoded to 1000 for now, or fetch from config
            fig_wealth.add_hline(y=1000, line_dash="dot", line_color="red", annotation_text="Iron Gate")

            fig_wealth.update_layout(
                title="Financial Trajectory",
                template="simple_white",
                height=350,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            ui.plotly(fig_wealth).classes('w-full h-96 shadow-lg rounded-lg mb-8')

        # === INPUT FORM (COLLAPSIBLE) ===
        with ui.expansion('Log New Session', icon='edit').classes('w-full bg-white shadow rounded-lg'):
            with ui.column().classes('p-4 gap-4'):
                
                # DATE & CONTRIB
                with ui.row().classes('w-full'):
                    date_input = ui.input('Date', value=datetime.now().strftime('%Y-%m-%d')).classes('flex-1')
                    contrib_input = ui.number('New Contribution (€)', value=0, format='%.0f').classes('flex-1') \
                        .tooltip("Fresh money added to bankroll this session")

                ui.separator()
                
                # GAME INPUTS (Split)
                ui.label("Session Performance").classes('font-bold text-slate-700')
                
                # ROULETTE ROW
                with ui.row().classes('w-full items-center'):
                    ui.icon('casino').classes('text-2xl text-slate-400')
                    ui.label('Roulette').classes('w-20 font-bold')
                    r_in = ui.number('Start Bal', value=0).classes('flex-1')
                    r_out = ui.number('End Bal', value=0).classes('flex-1')
                
                # BACCARAT ROW
                with ui.row().classes('w-full items-center'):
                    ui.icon('style').classes('text-2xl text-slate-400')
                    ui.label('Baccarat').classes('w-20 font-bold')
                    b_in = ui.number('Start Bal', value=0).classes('flex-1')
                    b_out = ui.number('End Bal', value=0).classes('flex-1')

                ui.separator()
                
                # POINTS & NOTES
                points_input = ui.number('New Point Balance', value=current_points).classes('w-full')
                notes_input = ui.input('Session Notes', placeholder='Strategy used, mood, etc.').classes('w-full')

                # SAVE BUTTON
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
                    ui.notify('Session Logged!', type='positive')
                    # Refresh page to show new data
                    ui.open('/') # Or trigger a reload if inside a function

                ui.button('Commit to Ledger', on_click=submit).classes('w-full bg-slate-800 text-white')

# If running standalone for testing
if __name__ in {"__main__", "__mp_main__"}:
    render_page()
    ui.run(title="Salle Blanche Tracker")
