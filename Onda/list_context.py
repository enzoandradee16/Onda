"""Context menus share the same commands and state as each list's controls."""
import tkinter as tk
from pathlib import Path
from i18n import tr


def action(label, command, enabled=True):
    return (tr(label), command, bool(enabled))


def button(widget):
    return (str(widget.cget("text")), widget.invoke, not widget.instate(("disabled",)))


def copy_text(table,text):
    if text:
        table.clipboard_clear()
        table.clipboard_append(text)


def copy_rows(table):
    text="\n".join("\t".join(map(str,table.item(key,"values"))) for key in table.selection())
    copy_text(table,text)


class ListContext:
    def __init__(self, table, actions, changed=None):
        self.table,self.actions,self.changed=table,actions,changed
        table._list_context=self
        table.bind("<Button-3>",self.mouse,add="+")
        table.bind("<Shift-F10>",self.keyboard,add="+")
        table.bind("<KeyPress-Menu>",self.keyboard,add="+")

    def select(self,key):
        if key and self.table.exists(key):
            if key not in self.table.selection():
                self.table.selection_set(key)
                if self.changed:self.changed()
            self.table.focus(key)
        self.table.focus_set()

    def mouse(self,event):
        if self.table.identify_region(event.x,event.y) in ("heading","separator"):
            return
        key=self.table.identify_row(event.y)
        if not key:
            self.table.selection_remove(self.table.selection())
            if self.changed:self.changed()
        self.select(key)
        return self.popup(event.x_root,event.y_root)

    def keyboard(self,event):
        keys=self.table.selection()
        key=self.table.focus() or (keys[0] if keys else "")
        if key:self.select(key)
        box=self.table.bbox(key) if key else ()
        x,y=(box[0]+20,box[1]+box[3]) if box else (20,20)
        return self.popup(self.table.winfo_rootx()+x,self.table.winfo_rooty()+y)

    def popup(self,x,y):
        previous=getattr(self,"menu",None)
        if previous is not None:previous.destroy()
        menu=self.menu=tk.Menu(self.table,tearoff=False)
        try:
            for entry in self.actions():
                if entry is None:menu.add_separator()
                else:
                    label,command,enabled=entry
                    menu.add_command(label=label,command=command,state="normal" if enabled else "disabled")
            menu.add_separator()
            menu.add_command(label=tr("Copiar"),command=lambda:copy_rows(self.table),state="normal" if self.table.selection() else "disabled")
            owner=self.table
            while owner is not None:
                theme=getattr(owner,"theme_manager",None)
                if theme:
                    theme.walk(menu)
                    break
                owner=getattr(owner,"master",None)
            menu.tk_popup(x,y)
        finally:
            menu.grab_release()
        return "break"

    def card(self,widget,key):
        def show(event):
            self.select(key)
            return self.popup(event.x_root,event.y_root)
        def keyboard(event):
            self.select(key)
            return self.popup(widget.winfo_rootx()+20,widget.winfo_rooty()+20)
        widget.bind("<Button-3>",show,add="+")
        widget.bind("<Shift-F10>",keyboard,add="+")
        widget.bind("<KeyPress-Menu>",keyboard,add="+")
        for child in widget.winfo_children():self.card(child,key)


def display_actions(view,size):
    return [None,action("Compacto",lambda:view.set("Compacto")),action("Completa",lambda:view.set("Completa")),
            *[action("Cards: "+label,lambda label=label:size.set(label),view.get()=="Completa") for label in ("Pequeno","Médio","Grande")]]


def queue_actions(app):
    from advanced_ui import move_queue
    selected=app.tree.selection()
    movable=any(app.jobs.get(k,{}).get("state")!="Em andamento" for k in selected)
    return [action("Baixar selecionados",lambda:app.start(only_items=list(app.tree.selection())),any(app.jobs.get(k,{}).get("state")=="Na fila" for k in selected)),
            button(app.retry_button),button(app.remove_button),None,
            action("Mover para cima",lambda:move_queue(app,-1),movable),action("Mover para baixo",lambda:move_queue(app,1),movable),
            action("Próximo",lambda:move_queue(app,0),movable),None,
            action("Abrir pasta",app.open_folder),action("Copiar link",lambda:copy_text(app.tree,"\n".join(app.jobs[k]["url"] for k in app.tree.selection())),bool(selected)),action("Ver detalhes",app.show_log),button(app.cancel_button),
            action("Selecionar tudo",lambda:app.tree.selection_set(app.queue_filter.visible_keys()),bool(app.tree.get_children())),
            action("Limpar seleção",lambda:app.tree.selection_remove(app.tree.selection()),bool(selected)),button(app.clear_queue_button),
            *display_actions(app.queue_view,app.queue_card_size)]


def bind_queue(app):
    return ListContext(app.tree,lambda:queue_actions(app),app.refresh_queue)


def bind_history(page):
    def actions():
        keys=page.table.selection()
        row=page.rows.get(keys[0],{}) if keys else {}
        available=bool(row.get("path")) and Path(row["path"]).is_file()
        return [action("Abrir arquivo",page.open,available),action("Abrir pasta",lambda:page.open(True),available),action("Abrir origem",page.open_origin,bool(page.origin())),
                action("Editar áudio / letra",page.edit_audio,available),action("Editar metadados em lote",page.edit_batch,bool(keys)),action("Usar nos efeitos",page.effects,available),None,
                action("Copiar caminho",lambda:copy_text(page.table,row.get("path","")),bool(row)),action("Limpar histórico",page.clear,bool(page.rows)),*display_actions(page.app.history_view,page.app.history_card_size)]
    def changed():
        keys=page.table.selection()
        if keys:page.select_card(keys[0])
        else:
            page._selected_card.set("")
            page.highlight_cards()
    return ListContext(page.table,actions,changed)


def bind_catalog(page):
    return ListContext(page.table,lambda:[button(page.download_button),button(page.preview_button),button(page.source_button)],page.selected)


def bind_playlist(page):
    def actions():
        selected=bool(page.selected_keys())
        entries=[button(page.download_now_button),button(page.add_button),button(page.check_button)]
        entries=[(label,command,enabled and selected) for label,command,enabled in entries]
        return entries+[None,action("Selecionar visíveis",lambda:page.table.selection_set(page.table.get_children()),bool(page.table.get_children())),
                        action("Limpar seleção",lambda:page.table.selection_remove(page.table.selection()),bool(page.table.selection())),
                        button(page.list_button),button(page.export_button)]
    return ListContext(page.table,actions)


def bind_metadata(page):
    return ListContext(page.table,lambda:[button(page.source_button),button(page.cover_button),button(page.export_button)],page.select)


def bind_version(page,on_cancel):
    return ListContext(page.table,lambda:[button(page.select_button),button(page.open_button),
        *([button(page.preview_button)] if page.preview_button.winfo_manager() else []),None,action("Cancelar",on_cancel)],page.selected)


def bind_playlist_list(window,page):
    import webbrowser
    def actions():
        keys=window.table.selection()
        row=page.records.get(keys[0],{}) if keys else {}
        url=row.get("source_url","")
        return [action("Abrir na plataforma",lambda:webbrowser.open(url),url.startswith("https://")),button(page.export_button)]
    return ListContext(window.table,actions)
