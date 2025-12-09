from nicegui import ui
from utils.persistence import load_profile, save_profile

def show_dashboard():
    # 1. Load Data
    profile = load_profile()
    current_ga = profile.get('ga', 1700.0)
    
    # 2. Hero Section (The Big Number)
    with ui.column().classes('w-full items-center justify-center py-10 bg-gradient-to-b from-slate-900 to-slate-800'):
        ui.label('TOTAL GAME ACCOUNT').classes('text-sm font-bold text-slate-400 tracking-widest mb-2')
        # Display GA with thousand separator
        lbl_ga = ui.label(f'€{current_ga:,.0f}').classes('text-7xl font-black text-white mb-6')
        
        with ui.row().classes('gap-4'):
            ui.chip('Tier 1 Ready', icon='verified').props('color=green text-color=white')
            ui.chip('SBM Gold Chase', icon='emoji_events').props('color=gold text-color=black')

    # 3. Quick Actions Grid
    with ui.grid(columns=2).classes('w-full max-w-4xl mx-auto gap-4 p-4'):
        # Play Button
        with ui.button(on_click=lambda: ui.open('/cockpit')).classes('h-32 bg-blue-600 hover:bg-blue-500 rounded-xl shadow-lg'):
            with ui.column().classes('items-center'):
                ui.icon('play_arrow', size='3em')
                ui.label('START SESSION').classes('font-bold text-lg')
        
        # Sim Button
        with ui.button(on_click=lambda: ui.open('/simulator')).classes('h-32 bg-slate-700 hover:bg-slate-600 rounded-xl'):
            with ui.column().classes('items-center'):
                ui.icon('science', size='3em').classes('text-purple-400')
                ui.label('SIMULATOR').classes('font-bold text-lg text-slate-200')

    # 4. Wallet Settings (New Feature)
    with ui.column().classes('w-full max-w-4xl mx-auto p-4'):
        with ui.expansion('Wallet Settings', icon='account_balance_wallet').classes('w-full bg-slate-800 text-slate-300'):
            with ui.column().classes('p-4 w-full gap-4'):
                ui.label('Manually update your bankroll (e.g., after a deposit/withdrawal).').classes('text-sm text-slate-500')
                
                with ui.row().classes('w-full items-center gap-4'):
                    input_ga = ui.number(label='Current Bankroll', value=current_ga, format='%.0f').classes('flex-grow').props('outlined dark input-class="text-xl font-bold"')
                    
                    def update_wallet():
                        new_val = input_ga.value
                        if new_val is not None:
                            profile['ga'] = float(new_val)
                            save_profile(profile)
                            lbl_ga.set_text(f'€{new_val:,.0f}')
                            ui.notify(f'Wallet updated to €{new_val:,.0f}', type='positive')
                    
                    ui.button('SAVE', on_click=update_wallet).props('color=green icon=save')
