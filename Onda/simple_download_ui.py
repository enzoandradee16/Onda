"""Reuse existing controls; hiding them never overwrites saved selections."""
def bind_simple_grid(app, container):
    def refresh(*_):
        container.grid_remove() if app.simple_download_ui.get() else container.grid()
    trace=app.simple_download_ui.trace_add('write',refresh)
    container.bind('<Destroy>',lambda event:app.simple_download_ui.trace_remove('write',trace) if event.widget is container else None,add='+')
    refresh()
