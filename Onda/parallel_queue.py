"""Bounded desktop workers; modal choices are serialized on the Tk thread."""
import threading

CHOICES={'choose_flac','choose_media','choose_version','choose_catalog','choose_duplicate','review_metadata'}

class ParallelQueue:
    def __init__(self,app):
        self.app=app;self.workers=set();self.processes={};self.scope=None;self.limit=1;self.memory_wait=None
        self.choice_item=None;self.waiting=[];self.completed=set();self.attempted=set();self.reported=True

    def start(self,scope):
        self.completed.clear();self.attempted.clear();self.reported=False
        self.scope=set(scope) if scope is not None else None
        self.limit=int(self.app.concurrent_downloads.get())
        self.app.cancelled.clear();self.app.running=True
        self.fill()

    def extend(self,scope):
        if self.scope is not None:
            if scope is None:self.scope=None
            else:self.scope.update(scope)
        self.app.write_log("Novo download solicitado. Ele começa assim que houver uma vaga disponível.")
        self.fill()

    def fill(self):
        app=self.app
        if self.memory_wait is not None:
            app.after_cancel(self.memory_wait);self.memory_wait=None
        memory_blocked=False
        self.limit=max(1,min(15,int(app.concurrent_downloads.get())))
        if app.running:
            for item in app.tree.get_children():
                if len(self.workers)>=self.limit:break
                if item in self.workers or app.jobs[item]['state']!='Na fila' or self.scope is not None and item not in self.scope:continue
                from performance import can_start
                if not can_start(app):
                    memory_blocked=True;break
                self.workers.add(item);self.attempted.add(item);app.active=item
                app.jobs[item].pop('last_error',None)
                app.jobs[item]['saved_sizes']={};app.set_state(item,'Em andamento')
                config={**app.jobs[item],'_cleanup_work':True,'auto_metadata':app.auto_metadata.get(),'auto_match':app.auto_match.get(),'confirm_version':app.confirm_version.get() if hasattr(app,'confirm_version') else False,'ffmpeg':app.ffmpeg.get().strip(),
                        'cookies_file':app.download_cookies(app.jobs[item].get('url','')) if hasattr(app,'download_cookies') else app.social_cookies.get().strip(),'spotify_client_id':app.spotify_client_id.get(),
                        'spotify_client_secret':app.spotify_client_secret.get(),'resume_downloads':app.resume_downloads.get()}
                from performance import snapshot
                config.update(snapshot(app))
                threading.Thread(target=app.supervise,args=(item,config),daemon=True).start()
        app.active=next(iter(self.workers),None)
        if memory_blocked:
            self.memory_wait=app.after(2000,self.fill)
            if not self.workers:
                app.status.set("Aguardando memória livre para iniciar o próximo download.")
                app.detail.set("Ajuste o limite de RAM em Configurações → Desempenho ou pressione Parar.")
        app.start_button.configure(state='disabled' if self.workers or memory_blocked else 'normal')
        app.cancel_button.configure(state='normal' if self.workers or memory_blocked else 'disabled')
        if not self.workers and not memory_blocked:
            app.running=False;app.immediate_item=None
            interrupted=app.cancelled.is_set()
            app.set_progress(0 if interrupted else 100)
            app.status.set("Fila interrompida" if interrupted else "Fila finalizada")
            app.detail.set("Confira o estado de cada item. Os arquivos concluídos foram preservados.")
            if not self.reported:
                self.reported=True
                if not interrupted and not app.closing:
                    show=getattr(app,'show_failures',None)
                    if show:show(self.attempted.copy())
            if app.closing and not app.effects_page.busy:app.destroy()

    def admit(self,item,event):
        app=self.app
        if event['type']=='done':
            self.completed.add(item)
            remaining=len(self.workers-self.completed)
            if remaining:
                app.set_progress(None)
                app.status.set(f"{remaining} download(s) em andamento")
                app.detail.set("Um arquivo foi concluído. Aguardando os demais downloads.")
            else:
                app.set_progress(100)
                app.status.set("Download concluído")
                app.detail.set("Arquivos concluídos e salvos. Finalizando a execução…")
            return False
        # A completed worker must not reanimate the bar with late stage events.
        if item in self.completed and event['type'] in ('progress','processing','stage'):
            return False
        if event['type'] in CHOICES:
            if self.choice_item and self.choice_item!=item:
                self.waiting.append((item,event));return False
            self.choice_item=item
        app.active=item
        return True

    def choice_closed(self):
        self.choice_item=None
        while self.waiting:
            item,event=self.waiting.pop(0)
            if item in self.workers:
                self.app.events.put((item,event));break

    def finish(self,item,event):
        app=self.app
        if self.choice_item==item:app.dismiss_version_picker()
        self.workers.discard(item);self.processes.pop(item,None);self.completed.discard(item)
        if app.jobs[item].get('remove_after_stop'):
            del app.jobs[item];app.tree.delete(item)
        else:
            state='Cancelado' if event['cancelled'] else 'Concluído' if event['success'] else 'Falhou'
            if event['cancelled'] and getattr(app,'_schedule_paused',False):state='Na fila'
            app.set_state(item,state)
        app.refresh_queue();app.persist_queue();self.fill()

    def stop(self):
        from engine import stop_process
        app=self.app;app.running=False;app.cancelled.set();app.dismiss_version_picker()
        if self.memory_wait is not None:
            app.after_cancel(self.memory_wait);self.memory_wait=None
        if not self.workers:
            self.fill()
        self.waiting.clear()
        def terminate():
            with app.process_lock:
                processes=list(self.processes.values())
            for process in processes:stop_process(process)
        threading.Thread(target=terminate,daemon=True).start()

    def reply(self,item,reply):
        import json
        process=self.processes.get(item)
        if process is None or process.poll() is not None:return False
        process.stdin.write(json.dumps(reply)+'\n');process.stdin.flush()
        return True
