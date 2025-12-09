from nicegui import ui
from utils.persistence import get_session_logs, delete_session_log

def show_session_log():
    # 1. Fetch Data
    logs = get_session_logs()
    
    # 2. UI Layout
    with ui.column().classes('w-full max-w-4xl mx-auto gap-4 p-4'):
        ui.label('SESSION HISTORY').classes('text-2xl font-light text-slate-300 mb-4')
        
        if not logs:
            ui.label('No sessions recorded yet.').classes('text-slate-500 italic')
            return

        # 3. Create Rows
        # We use a simple grid card for each entry instead of a complex data table for mobile friendliness
        for entry in logs:
            with ui.card().classes('w-full bg-slate-900 border border-slate-700'):
                with ui.row().classes('w-full items-center justify-between no-wrap'):
                    
                    # Left: Stats
                    with ui.column().classes('gap-1'):
                        ui.label(entry.get('date', 'Unknown Date')).classes('text-xs text-slate-500')
                        
                        # PnL Color
                        pnl = entry.get('pnl', 0)
                        color = 'text-green-400' if pnl >= 0 else 'text-red-400'
                        sign = '+' if pnl >= 0 else ''
                        
                        with ui.row().classes('items-baseline gap-2'):
                            ui.label(f"{sign}€{pnl}").classes(f'text-2xl font-bold {color}')
                            ui.label(f"End GA: €{entry.get('end_ga', 0)}").classes('text-sm text-slate-400')

                    # Right: Delete Button
                    # We wrap the delete logic in a closure to capture the specific entry date
                    def make_delete_handler(date_to_delete):
                        def handler():
                            delete_session_log(date_to_delete)
                            ui.notify('Log Deleted', type='negative')
                            show_session_log() # Refresh page
                        return handler

                    ui.button(icon='delete', color='red', on_click=make_delete_handler(entry.get('date'))) \
                        .props('flat dense').classes('opacity-50 hover:opacity-100')
