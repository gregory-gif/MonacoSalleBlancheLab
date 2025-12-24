from nicegui import ui
import os

def show_docs_viewer():
    """Display documentation files with markdown rendering"""
    
    docs = {
        'CSV Data Dictionary': 'CSV_DATA_DICTIONARY.md',
        'Spice System Brief': 'SPICE_SYSTEM_BRIEF.md',
        'Quick Start Guide': 'SPICE_QUICK_START.md',
        'System Documentation': 'SPICE_SYSTEM_v5.0.md',
        'Architecture Visual': 'SPICE_ARCHITECTURE_VISUAL.md',
        'README': 'README.md'
    }
    
    selected_doc = None
    markdown_content = ui.markdown()
    
    def load_doc(filepath):
        """Load and display markdown file"""
        try:
            full_path = f'/workspaces/MonacoSalleBlancheLab/{filepath}'
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    markdown_content.content = content
                    ui.notify(f'Loaded: {filepath}', type='positive')
            else:
                markdown_content.content = f'**File not found:** {filepath}'
                ui.notify(f'File not found: {filepath}', type='warning')
        except Exception as e:
            markdown_content.content = f'**Error loading file:** {str(e)}'
            ui.notify(f'Error: {str(e)}', type='negative')
    
    with ui.column().classes('w-full max-w-6xl mx-auto gap-6 p-4'):
        ui.label('📚 DOCUMENTATION CENTER').classes('text-3xl font-light text-purple-400')
        
        # Document selector
        with ui.card().classes('w-full bg-slate-900 p-4'):
            ui.label('Select Document:').classes('text-sm text-slate-400 mb-2')
            
            with ui.row().classes('gap-2 flex-wrap'):
                for doc_name, doc_file in docs.items():
                    ui.button(
                        doc_name, 
                        on_click=lambda f=doc_file, n=doc_name: load_doc(f)
                    ).props('outline color=purple').classes('text-xs')
        
        # Content display area
        with ui.card().classes('w-full bg-slate-900 p-6'):
            with ui.scroll_area().classes('w-full h-[70vh]'):
                markdown_content.classes('prose prose-invert max-w-none')
        
        # Initial message
        markdown_content.content = '''
# Welcome to the Documentation Center

Select a document from above to view its contents.

## Available Documents:

- **CSV Data Dictionary**: Complete guide to Year 1 CSV export format
- **Spice System Brief**: Overview of the Spice System v5.0
- **Quick Start Guide**: Getting started with SPICE
- **System Documentation**: Full technical documentation
- **Architecture Visual**: System architecture diagrams
- **README**: Project overview

*Last updated: December 24, 2025*
'''
