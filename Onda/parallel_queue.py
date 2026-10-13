"""Bounded desktop workers; modal choices are serialized on the Tk thread."""
import threading

CHOICES={'choose_media','choose_version','choose_catalog','choose_duplicate','review_metadata'}

class ParallelQueue:
    def __init__(self,app):
        self.app=app;self.workers=set();self.processes={};self.scope=None;self.limit=1
        self.choice_item=None;self.waiting=[]

    def start(self,scope):
        self.scope=set(scope) if scope is not None else None
        self.limit=int(self.app.concurrent_downloads.get())
        self.app.cancelled.clear();self.app.running=True
        self.fill()

    def fill(self):
        app=self.app
        if app.running:
            for item in app.tree.get_children():
                if len(self.workers)>=self.limit:break
                if item in self.workers or app.jobs[item]['state']!='Na fila' or self.scope is not None and item not in self.scope:continue
                self.workers.add(item);app.active=item
                app.jobs[item]['saved_sizes']={};app.set_state(item,'Em andamento')
                config={**app.jobs[item],'auto_match':app.auto_match.get(),'ffmpeg':app.ffmpeg.get().strip(),
                        'cookies_file':app.social_cookies.get().strip(),'spotify_client_id':app.spotify_client_id.get(),
                        'spotify_client_secret':app.spotify_client_secret.get(),'resume_downloads':app.resume_downloads.get()}
                threading.Thread(target=app.supervise,args=(item,config),daemon=True).start()
        app.active=next(iter(self.workers),None)
        app.start_button.configure(state='disabled' if self.workers else 'normal')
        app.cancel_button.configure(state='normal' if self.workers else 'disabled')
        if not self.workers:
            app.running=False;app.immediate_item=None
            if app.closing and not app.effects_page.busy:app.destroy()

    def admit(self,item,event):
        app=self.app
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
        self.workers.discard(item);self.processes.pop(item,None)
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
