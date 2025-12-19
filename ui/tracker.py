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

    # Basic cleanup
    df['date'] = pd.to_datetime(df['date'])
    
    # CALCULATE DERIVED METRICS FOR THE TABLE
    # PnL for each session
    df['roulette_pnl'] = df['roulette_out'] - df['roulette_in']
    df['baccarat_pnl'] = df['baccarat_out'] - df['baccarat_in']
    df['session_pnl'] = df['roulette_pnl'] + df['baccarat_pnl']
    
    # Calculate "Mattress" Strategy (Invested Capital)
    # Logic: Start Capital = (First Wealth) - (First Contribution)
    start_cap = df.iloc[0]['total_wealth'] - df.iloc[0]['contribution']
    df['cum_contrib'] = df['contribution'].cumsum()
    df['invested_capital'] = start_cap + df['cum_contrib']
    
    return df

def save_session(date, contrib, r_in, r_out, b_in, b_out, points, notes):
    df = load_data()
    
    if df.empty:
        # First entry ever: The calculation assumes previous wealth was 0
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

def delete_session(row_index):
    """Deletes a row by index and saves the file."""
    df = pd.read_csv(DATA_FILE)
    # Drop the row
    df = df.drop(index=row_index)
    # Save back
    df.to_csv(DATA_FILE, index=False)

# --- UI COMPONENTS ---
def render_page():
    # 1. LOAD DATA
    df = load_data()
    
    # 2. CALCULATE KPIS
    if not df.empty:
        current_wealth = df.iloc[-1]['total_wealth']
        current_points = df.iloc[-1]['points']
        invested_cap = df.iloc[-1]['invested_capital']
        pnl_lifetime = current_wealth - invested_cap
        
        # Prepare table data (Sort by newest first for display)
        # We keep the original index for deleting, so we reset_index but keep old one
        table_df = df.reset_index().sort_values(by='date', ascending=False)
        
        # Format dates for display
        table_df['date_str'] = table_df['date'].dt.strftime('%Y-%m-%d')
        
        # Convert to list of dicts for NiceGUI table
        rows = table_df.to_dict('records')
    else:
        current_wealth = 0
        current_points = 0
        pnl_lifetime = 0
        rows = []

    # 3. MAIN UI LAYOUT
    with ui.column().classes('w-full max-w-5xl mx-auto p-4 gap-8'):
        
        # --- HEADER ---
        with ui.column().classes('w-full'):
            ui.label("The Captain's Log").classes('text-4xl font-serif font-bold text-slate-100')
            ui.label("Post-Session Ledger & Tracker").classes('text-slate-400')

        # --- KPI CARDS ---
        with ui.row().classes('w-full gap-4'):
            # Wealth
            with ui.card().classes('flex-1 bg-slate-800 border-l-4 border-blue-500'):
                ui.label('CURRENT WEALTH (GA)').classes('text-xs text-slate-400 font-bold')
                ui.label(f"€{current_wealth:,.0f}").classes('text-3xl font-bold text-white')
            
            # PnL
            with ui.card().classes('flex-1 bg-slate-800 border-l-4 border-emerald-500'):
                ui.label('NET LIFE PNL').classes('text-xs text-slate-400 font-bold')
                color = 'text-emerald-400' if pnl_lifetime >= 0 else 'text-red-400'
                ui.label(f"€{pnl_lifetime:,.0f}").classes(f'text-3xl font-bold {color}')
                
            # Points
            with ui.card().classes('flex-1 bg-slate-800 border-l-4 border-amber-500'):
                ui.label('GOLD POINTS').classes('text-xs text-slate-400 font-bold')
                ui.label(f"{current_points:,.0f}").classes('text-3xl font-bold text-amber-400')

        # --- CHART ---
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
            # Iron Gate
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

        # --- INPUT FORM ---
        with ui.expansion('LOG NEW SESSION', icon='edit_note', value=False).classes('w-full bg-slate-900 text-white border border-slate-700 rounded-lg'):
            with ui.column().classes('p-6 gap-6 w-full'):
                
                # Row 1: Date & Contribution
                with ui.row().classes('w-full gap-4'):
                    date_input = ui.input('Date', value=datetime.now().strftime('%Y-%m-%d')).classes('w-1/3').props('dark')
                    contrib_input = ui.number('New Contribution (€)', value=0, format='%.0f').classes('flex-1').props('dark suffix="€"')
                
                ui.separator().classes('bg-slate-700')
                
                # Row 2: Games
                with ui.row().classes('w-full items-center gap-4'):
                    ui.icon('casino').classes('text-xl text-amber-400')
                    r_in = ui.number('Roulette Start', value=0).classes('flex-1').props('dark outlined label-color="amber"')
                    r_out = ui.number('Roulette End', value=0).classes('flex-1').props('dark outlined label-color="amber"')
                
                with ui.row().classes('w-full items-center gap-4'):
                    ui.icon('style').classes('text-xl text-blue-400')
                    b_in = ui.number('Baccarat Start', value=0).classes('flex-1').props('dark outlined label-color="blue"')
                    b_out = ui.number('Baccarat End', value=0).classes('flex-1').props('dark outlined label-color="blue"')

                ui.separator().classes('bg-slate-700')

                # Row 3: Meta
                with ui.row().classes('w-full gap-4'):
                    points_input = ui.number('Total Points Balance', value=current_points).classes('w-1/3').props('dark suffix="pts"')
                    notes_input = ui.input('Session Notes', placeholder='Strategy details...').classes('flex-1').props('dark')

                # Submit Logic
                def submit():
                    save_session(
                        date_input.value, float(contrib_input.value or 0),
                        float(r_in.value or 0), float(r_out.value or 0),
                        float(b_in.value or 0), float(b_out.value or 0),
                        float(points_input.value or 0), notes_input.value
                    )
                    ui.notify('Session Logged!', type='positive')
                    ui.open('/') # Reload

                ui.button('COMMIT TO LEDGER', on_click=submit).classes('w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-2')

        # --- SESSION HISTORY TABLE ---
        if rows:
            ui.label("Session History").classes('text-xl font-bold text-slate-300 mt-4')
            
            # Define Table Columns
            columns = [
                {'name': 'date_str', 'label': 'Date', 'field': 'date_str', 'sortable': True, 'align': 'left'},
                {'name': 'contribution', 'label': 'Contrib', 'field': 'contribution', 'format': lambda x: f'€{x:,.0f}' if x!=0 else '-'},
                {'name': 'session_pnl', 'label': 'Session PnL', 'field': 'session_pnl', 'format': lambda x: f'€{x:,.0f}'},
                {'name': 'total_wealth', 'label': 'Total GA', 'field': 'total_wealth', 'format': lambda x: f'€{x:,.0f}', 'classes': 'font-bold'},
                {'name': 'points', 'label': 'Points', 'field': 'points'},
                {'name': 'notes', 'label': 'Notes', 'field': 'notes', 'align': 'left'},
                {'name': 'actions', 'label': 'Actions', 'field': 'index'}
            ]

            # Render Table
            with ui.table(columns=columns, rows=rows, pagination=10).classes('w-full bg-slate-800 text-slate-200') as table:
                
                # Custom Slot for PnL Color (Green/Red)
                table.add_slot('body-cell-session_pnl', '''
                    <q-td :props="props" :class="props.value >= 0 ? 'text-emerald-400' : 'text-red-400'">
                        {{ props.value >= 0 ? '+' : '' }}{{ props.value }}
                    </q-td>
                ''')

                # Custom Slot for Delete Button
                # We use the row 'index' (which we added in step 2) to identify which row to delete
                table.add_slot('body-cell-actions', r'''
                    <q-td :props="props">
                        <q-btn icon="delete" flat dense color="red" @click="$parent.$emit('delete_row', props.row)" />
                    </q-td>
                ''')
                
                # Delete Handler
                def handle_delete(e):
                    row_data = e.args
                    # The 'index' field in row_data corresponds to the original DataFrame index
                    original_index = row_data['index']
                    delete_session(original_index)
                    ui.notify(f"Deleted entry from {row_data['date_str']}", type='warning')
                    ui.open('/') # Reload page
                
                table.on('delete_row', handle_delete)

        else:
            ui.label("No sessions logged yet.").classes('text-slate-500 italic mt-8')
