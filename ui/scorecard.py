from nicegui import ui

# --- STATE MANAGEMENT ---
class ScorecardState:
    def __init__(self):
        self.history = []  # List of 'B', 'P', 'T'
        self.banker_wins = 0
        self.player_wins = 0
        self.ties = 0

# Global state instance for the cockpit
state = ScorecardState()

def show_scorecard():
    # --- LOGIC HANDLERS ---
    def update_ui():
        # 1. Update Stats Labels
        total = len(state.history)
        if total > 0:
            p_b = (state.banker_wins / total) * 100
            p_p = (state.player_wins / total) * 100
            p_t = (state.ties / total) * 100
        else:
            p_b = p_p = p_t = 0
            
        lbl_banker.set_text(f"BANKER: {state.banker_wins} ({p_b:.1f}%)")
        lbl_player.set_text(f"PLAYER: {state.player_wins} ({p_p:.1f}%)")
        lbl_tie.set_text(f"TIE: {state.ties} ({p_t:.1f}%)")
        
        # 2. Update Bead Plate (The Visual Road)
        bead_plate.clear()
        with bead_plate:
            for res in state.history:
                color = 'bg-red-600' if res == 'B' else 'bg-blue-600' if res == 'P' else 'bg-green-600'
                text = res
                ui.label(text).classes(f'w-8 h-8 rounded-full {color} text-white flex items-center justify-center font-bold shadow-md')

        # 3. Update Big Road (Simplified for now as a text list to keep it robust)
        # In a full app, this would be the complex grid logic.
        big_road_lbl.set_text("History: " + " > ".join(state.history[-15:]))

    def add_result(res):
        state.history.append(res)
        if res == 'B': state.banker_wins += 1
        elif res == 'P': state.player_wins += 1
        else: state.ties += 1
        update_ui()

    def undo_last():
        if not state.history: return
        res = state.history.pop()
        if res == 'B': state.banker_wins -= 1
        elif res == 'P': state.player_wins -= 1
        else: state.ties -= 1
        update_ui()

    def reset_shoe():
        state.history = []
        state.banker_wins = 0
        state.player_wins = 0
        state.ties = 0
        update_ui()

    # --- UI LAYOUT ---
    with ui.column().classes('w-full max-w-4xl mx-auto p-4 gap-4'):
        
        # 1. HEADER & CONTROLS
        with ui.card().classes('w-full bg-slate-900 p-4 border-b-4 border-slate-700'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('LIVE COCKPIT').classes('text-2xl font-light text-slate-200 tracking-widest')
                ui.button('NEW SHOE', on_click=reset_shoe).props('outline color=yellow icon=refresh')

            ui.separator().classes('bg-slate-700 my-4')

            # INPUT BUTTONS
            with ui.row().classes('w-full justify-center gap-6'):
                # Player Button
                with ui.button(on_click=lambda: add_result('P')).classes('w-32 h-24 bg-blue-700 hover:bg-blue-600 rounded-xl shadow-[0_4px_0_rgb(29,78,216)] active:shadow-none active:translate-y-1 transition-all'):
                    with ui.column().classes('items-center gap-0'):
                        ui.label('PLAYER').classes('text-lg font-bold text-white')
                        ui.label('P').classes('text-4xl font-black text-blue-200 opacity-50')
                
                # Tie Button
                with ui.button(on_click=lambda: add_result('T')).classes('w-24 h-24 bg-green-700 hover:bg-green-600 rounded-xl shadow-[0_4px_0_rgb(21,128,61)] active:shadow-none active:translate-y-1 transition-all'):
                    with ui.column().classes('items-center gap-0'):
                        ui.label('TIE').classes('text-lg font-bold text-white')
                        ui.label('T').classes('text-4xl font-black text-green-200 opacity-50')

                # Banker Button
                with ui.button(on_click=lambda: add_result('B')).classes('w-32 h-24 bg-red-700 hover:bg-red-600 rounded-xl shadow-[0_4px_0_rgb(185,28,28)] active:shadow-none active:translate-y-1 transition-all'):
                    with ui.column().classes('items-center gap-0'):
                        ui.label('BANKER').classes('text-lg font-bold text-white')
                        ui.label('B').classes('text-4xl font-black text-red-200 opacity-50')

            # UNDO
            with ui.row().classes('w-full justify-center mt-4'):
                ui.button('UNDO LAST HAND', on_click=undo_last).props('flat color=grey size=sm icon=undo')

        # 2. STATISTICS BAR
        with ui.grid(columns=3).classes('w-full gap-2'):
            with ui.card().classes('bg-blue-900/50 p-2 items-center border border-blue-700'):
                lbl_player = ui.label('PLAYER: 0 (0.0%)').classes('text-blue-300 font-bold')
            with ui.card().classes('bg-green-900/50 p-2 items-center border border-green-700'):
                lbl_tie = ui.label('TIE: 0 (0.0%)').classes('text-green-300 font-bold')
            with ui.card().classes('bg-red-900/50 p-2 items-center border border-red-700'):
                lbl_banker = ui.label('BANKER: 0 (0.0%)').classes('text-red-300 font-bold')

        # 3. BEAD PLATE (THE ROAD)
        with ui.card().classes('w-full bg-white p-4 min-h-[120px]'):
            ui.label('BEAD PLATE (Roadmap)').classes('text-slate-900 text-xs font-bold mb-2 tracking-widest uppercase')
            
            # This container will hold the red/blue balls
            bead_plate = ui.row().classes('w-full flex-wrap gap-2')
            
            # Initial State
            if not state.history:
                with bead_plate:
                    ui.label('Waiting for first hand...').classes('text-slate-400 italic text-sm')

        # 4. RECENT HISTORY TEXT
        with ui.card().classes('w-full bg-slate-800 p-2'):
            big_road_lbl = ui.label('History: ').classes('text-slate-400 font-mono text-xs')

    # Trigger initial update to render state if returning to tab
    update_ui()
