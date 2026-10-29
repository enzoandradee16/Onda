"""Bounded queue undo. Files and running download results are never rolled back."""

from copy import deepcopy


class QueueUndo:
    def __init__(self, limit=10):
        self.limit = limit
        self.entries = []
        self.finished = {}

    def remember(self, jobs, action, selected):
        self.entries.append((deepcopy(jobs), action, set(selected)))
        self.entries = self.entries[-self.limit :]
        retained = {job['id'] for rows, _, _ in self.entries for job in rows}
        self.finished = {
            key: value for key, value in self.finished.items() if key in retained
        }

    def record_finished_removal(self, job, success):
        if any(
            any(old['id'] == job['id'] for old in rows) for rows, _, _ in self.entries
        ):
            self.finished[job['id']] = deepcopy(
                dict(job, state='Concluído', percent=100) if success else job
            )

    def restore(self, jobs, active):
        if not self.entries:
            return jobs
        before, action, selected = self.entries[-1]
        if any(
            identity in selected and state['cancel'].is_set()
            for identity, state in active.items()
        ):
            raise ValueError('Aguarde o cancelamento terminar para desfazer.')
        self.entries.pop()
        live = {job['id']: job for job in jobs}
        restored = []
        for old in before:
            identity = old['id']
            job = live.pop(identity, None)
            if job is None:
                job = deepcopy(self.finished.get(identity, old))
                if old['state'] == 'Em andamento' and job['state'] != 'Concluído':
                    job['state'] = 'Na fila'
                    job['percent'] = 0
            elif (
                identity in selected
                and action in ('cancel', 'cancel_all')
                and identity not in active
                and job['state'] == 'Cancelado'
                and old['state'] in ('Na fila', 'Em andamento')
            ):
                job['state'] = 'Na fila'
                job['percent'] = 0
            job.pop('_remove', None)
            job.pop('_paused', None)
            restored.append(job)
        restored.extend(live.values())
        return restored
