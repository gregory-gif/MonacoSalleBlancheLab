from nicegui import ui

# STATE
class CockpitState:
    def __init__(self):
        self.history = [] # List of 'B', 'P', 'T'
        self.banker_wins = 0
        self.player_wins = 0
        self.ties = 0

state = CockpitState()

def show_scorecard():
    # --- LOGIC ---
    def update_stats():
        total = state.banker_wins + state.player_wins + state.ties
        if total == 0: return
        
        lbl_banker.set_text(f"BANKER: {state.banker_wins} ({(state.banker_wins/total)*100:.1f}%)")
        lbl_player.set_text(f"PLAYER: {state.player_wins} ({(state.player_wins/total)*100:.1f}%)")
        lbl_ties.set_text(f"TIE: {state.ties} ({(state.ties/total)*100:.1f}%)")
        
        # Update Road (Simple bead plate representation)
        road_html = '<div class="flex flex-wrap gap-1">'
        for res in state.history:
            color = 'red' if res == 'B' else 'blue' if res == 'P' else 'green'
            road_html += f'<div class="w-6 h-6 rounded-full bg-{color}-500 text-white flex items-center justify-center text-xs font-bold">{res}</div>'
        road_html += '</div>'
        road_container.content = road_html

    def add_result(result):
        state.history.append(result)
        if result == 'B': state.banker_wins += 1
        elif result == 'P': state.player_wins += 1
        else: state.ties += 1
        update_stats()

    def undo_last():
        if not state.history: return
        last = state.history.pop()
        if last == 'B': state.banker_wins -= 1
        elif last == 'P': state.player_wins -= 1
        else: state.ties -= 1
        update_stats()

    def reset_shoe():
        state.history = []
        state.banker_wins = 0
        state.player_wins = 0
        state.ties = 0
        update_stats()

    # --- UI LAYOUT ---
    with ui.column().classes('w-full max-w-4xl p-4 gap-4'):
        ui.label('LIVE COCKPIT').classes('text-2xl font-light text-slate-300')
        
        # 1. INPUTS
        with ui.card().classes('w-full bg-slate-900 p-4'):
            with ui.row().classes('w-full justify-center gap-4'):
                ui.button('BANKER', on_click=lambda: add_result('B')).props('color=red size=xl').classes('w-32')
                ui.button('PLAYER', on_click=lambda: add_result('P')).props('color=blue size=xl').classes('w-32')
                ui.button('TIE', on_click=lambda: add_result('T')).props('color=green size=xl').classes('w-24')
            
            with ui.row().classes('w-full justify-center gap-4 mt-4'):
                ui.button('UNDO', on_click=undo_last).props('flat color=grey')
                ui.button('NEW SHOE', on_click=reset_shoe).props('outline color=yellow')

        # 2. STATISTICS
        with ui.grid(columns=3).classes('w-full gap-4'):
            with ui.card().classes('bg-red-900 items-center p-2'):
                lbl_banker = ui.label('BANKER: 0 (0%)').classes('text-white font-bold')
            with ui.card().classes('bg-blue-900 items-center p-2'):
                lbl_player = ui.label('PLAYER: 0 (0%)').classes('text-white font-bold')
            with ui.card().classes('bg-green-900 items-center p-2'):
                lbl_ties = ui.label('TIE: 0 (0%)').classes('text-white font-bold')

        # 3. ROADMAP
        with ui.card().classes('w-full bg-white p-4 min-h-[100px]'):
            ui.label('BEAD PLATE').classes('text-black text-xs font-bold mb-2')
            road_container = ui.html('<div class="text-gray-400 text-sm italic">Waiting for results...</div>')
