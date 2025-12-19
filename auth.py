from nicegui import ui, app

# --- CONFIGURATION ---
USERNAME = "admin"
PASSWORD = "password123" 

def setup_auth():
    """Defines the login and logout pages."""
    
    @ui.page('/login')
    def login_page():
        def try_login():
            if username.value == USERNAME and password.value == PASSWORD:
                # Set the secure session flag
                app.storage.user['authenticated'] = True
                # Redirect to home
                ui.open('/') 
            else:
                ui.notify('Access Denied', type='negative')

        # Login Screen UI
        with ui.column().classes('absolute-center w-full max-w-sm p-8 bg-slate-900 rounded-xl shadow-2xl border border-slate-700'):
            ui.label('Salle Blanche Lab').classes('text-2xl font-bold text-white mb-2 self-center')
            ui.label('Restricted Access').classes('text-slate-500 text-sm mb-6 self-center')
            
            username = ui.input('Username').props('dark outlined').classes('w-full')
            password = ui.input('Password', password=True).props('dark outlined').classes('w-full').on('keydown.enter', try_login)
            
            ui.button('UNLOCK', on_click=try_login).classes('w-full mt-6 bg-amber-600 hover:bg-amber-500 text-white font-bold')

    @ui.page('/logout')
    def logout():
        # Clear the session
        app.storage.user['authenticated'] = False
        ui.open('/login')
