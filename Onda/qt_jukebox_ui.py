"""Qt adapter for the existing Jukebox engine; workers never touch QML objects."""

import base64
from collections import deque
import json
import math
import os
from pathlib import Path
import queue
import threading
import time
import uuid
from types import SimpleNamespace

from PySide6.QtCore import QObject, Property, Signal, Slot, Qt, QTimer, QUrl
from jukebox import prepare, fetch_audio, Cancelled, RATE
from jukebox_stream import Stream
from jukebox_equalizer import clean, presets, preset_name
from preferences import PreferenceStore
from i18n import tr, set_language
from error_localization import error_text


class JukeboxBridge(QObject):
    changed = Signal()
    playbackRequested = Signal()
    queueChanged = Signal()
    tracksAdded = Signal('QStringList')
    preparationChanged = Signal()
    positionChanged = Signal()
    graphChanged = Signal()
    appearanceChanged = Signal()
    equalizerChanged = Signal()
    _event = Signal(int, str, object)

    def __init__(self, store=None, parent=None):
        super().__init__(parent)
        self.store = store or PreferenceStore()
        try:
            self.preferences = self.store.load() or {}
        except (ValueError, OSError):
            self.preferences = {}
        set_language(self.store.load_language())
        self.closed = False
        self.revision = 0
        self.cancelled = threading.Event()
        self.paused = threading.Event()
        self._mini_active = False
        self._visual_level = 0.0
        from playback_controls import SleepTimer

        self.queue_repeat = 'Desativada'
        self.queue_shuffle = False
        self._shuffle_order = []
        self._queue_history = []
        self._history_back = False
        self.sleep = SleepTimer()
        self.playlist = []
        self.queue_index = -1
        self.track_minutes = 0
        self.autoplay_revision = None
        self.request_number = 0
        self.lookup_cancelled = threading.Event()
        self.task_is_lookup = False
        self.clock_timer = QTimer(self)
        self.clock_timer.setInterval(500)
        self.clock_timer.timeout.connect(self.tick_sleep)
        self.workers = []
        self.seeks = queue.SimpleQueue()
        self.model = None
        self.records = []
        self._state = {
            'title': tr('Escolha suas músicas.'),
            'artist': '',
            'album': '',
            'cover': '',
            'status': tr(
                'Abra arquivos, pesquise músicas ou adicione álbuns e playlists à fila.'
            ),
            'busy': False,
            'playing': False,
            'paused': False,
            'ready': False,
            'progress': 0,
            'results': [],
        }
        self._topology_rows = None
        self._topology_options = None
        self._topology_links = []
        self._graph_cache = None
        self._position = 0.0
        self._phase = 0.0
        self._elapsed = 0.0
        self._jumps = 0
        self.flow = []
        self.used_edges = set()
        self._params = (45.0, 35.0, 80.0, True)
        self._equalizer = clean(self.preferences.get('jukebox_equalizer'))
        self._effects = {}
        self._effects_status = None
        self._effect_prepare_cancel = threading.Event()
        self.effect_prepare_timer = QTimer(self)
        self.effect_prepare_timer.setSingleShot(True)
        self.effect_prepare_timer.setInterval(400)
        self.effect_prepare_timer.timeout.connect(self.prewarm_effects)
        self.config_provider = None
        self.media_state_provider = None
        self.media_command_handler = None
        self.window = None
        self.media = None
        self.media_failed = False
        self.media_timer = QTimer(self)
        self.media_timer.setInterval(100)
        self.media_timer.timeout.connect(self.sync_media)
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(400)
        self.save_timer.timeout.connect(self.save_preferences)
        self._prepared = {}
        self._queue_cancel = {}
        self._queue_preparing = False
        self._autoplay_entry = None
        self._beat_index = 0
        self._next_index = -1
        self._jump_blend = 0.0
        self._track_started = 0.0
        self._timer_last = self.sleep.clock()
        self._switch_requests = queue.SimpleQueue()
        self._switch_pending = None
        self._switch_models = {}
        self._fade_initial = False
        self._pending = {}
        self._event.connect(self.handle_event, Qt.ConnectionType.QueuedConnection)
        self._switch_after = None

    @Property('QVariantMap', notify=changed)
    def state(self):
        state = dict(self._state)
        state["status"] = (
            error_text(state["status"])
            if state.get("status_error")
            else tr(state["status"])
        )
        return state

    @Property('QVariantList', notify=queueChanged)
    def queuedTracks(self):
        return [
            dict(row, current=index == self.queue_index)
            for index, row in enumerate(self.playlist)
        ]

    @Property('QVariantMap', notify=preparationChanged)
    def queuePreparation(self):
        return {
            row['id']: int(row.get('preparation_progress', 0))
            for row in self.playlist
            if row.get('analysis') == 'preparing'
        }

    @Property('QVariantMap', notify=changed)
    def currentMetadata(self):
        record = (
            dict(self.playlist[self.queue_index].get('record') or {})
            if 0 <= self.queue_index < len(self.playlist)
            else dict(self.model or {})
        )
        record['album'] = self._state.get('album') or record.get('album') or ''
        record['cover_url'] = (
            record.get('cover_url') or (self.model or {}).get('cover_url') or ''
        )
        return record

    @Property('QVariantList', notify=queueChanged)
    def upcomingTracks(self):
        rows = self.queuedTracks
        result = []
        for index, row in enumerate(rows):
            if index < self.queue_index:
                continue
            if (
                not row['current']
                and row['id'] in self._queue_history
                and self.queue_repeat != 'Todas'
            ):
                continue
            label = (
                'Tocando agora'
                if row['current']
                else (
                    'Próximas na fila'
                    if row.get('manual')
                    else 'Próximas de: ' + (row.get('collection') or 'Playlist')
                )
            )
            result.append(
                dict(
                    row,
                    queueIndex=index,
                    section=label if not result or result[-1]['group'] != label else '',
                    group=label,
                )
            )
        return result

    @Property('QVariantList', notify=queueChanged)
    def recentTracks(self):
        rows = {
            row['id']: dict(row, queueIndex=i)
            for i, row in enumerate(self.queuedTracks)
        }
        return [
            rows[identity]
            for identity in dict.fromkeys(reversed(self._queue_history))
            if identity in rows and not rows[identity]['current']
        ]

    def remember_current(self):
        if not self._history_back and 0 <= self.queue_index < len(self.playlist):
            identity = self.playlist[self.queue_index]['id']
            if not self._queue_history or self._queue_history[-1] != identity:
                self._queue_history = (self._queue_history + [identity])[-200:]
        self._history_back = False

    @Property('QVariantMap', notify=changed)
    def playback(self):
        return {
            'queue': self.queuedTracks,
            'current': self.queue_index,
            'trackMinutes': self.track_minutes,
            'sleepActive': self.sleep.deadline is not None,
            'remaining': math.ceil(self.sleep.remaining()),
            'switchRemaining': (
                math.ceil(
                    max(
                        0,
                        self.track_minutes * 60 - (self._elapsed - self._track_started),
                    )
                )
                if self.track_minutes
                else 0
            ),
            'gradual': self.preferences.get('jukebox_gradual_transition', True),
        }

    @Slot(int)
    def setSleep(self, minutes):
        if minutes <= 0:
            self.sleep.cancel()
        else:
            self.sleep.arm(min(180, minutes) * 60, fade=10)
        self._timer_last = self.sleep.clock()
        self.refresh_clock()
        self.changed.emit()

    def refresh_clock(self):
        if self.sleep.deadline is not None or self.track_minutes:
            self.clock_timer.start()
        else:
            self.clock_timer.stop()

    def tick_sleep(self):
        now = self.sleep.clock()
        delta = max(0, now - self._timer_last)
        self._timer_last = now
        if self.sleep.deadline is not None:
            if not self._state['playing'] or self.paused.is_set():
                self.sleep.deadline += delta
            elif self.sleep.remaining() <= 0:
                self.stop()
                self.update_state(
                    status=tr('Temporizador encerrado. Reprodução parada suavemente.')
                )
        self.changed.emit()

    @Slot(int)
    def setTrackMinutes(self, minutes):
        self.track_minutes = max(0, min(180, minutes))
        self._track_started = self._elapsed
        self.refresh_clock()
        self.changed.emit()

    @Slot(bool)
    def setGradualTransition(self, enabled):
        self.preferences['jukebox_gradual_transition'] = enabled
        self._pending['jukebox_gradual_transition'] = enabled
        self.save_timer.start()
        self.changed.emit()
        self.appearanceChanged.emit()

    def playback_gain(self):
        if not self.preferences.get('jukebox_gradual_transition', True):
            return 1.0
        gain = (
            min(
                self.sleep.gain(),
                max(0.0, min(1.0, self._elapsed / self.transitionSeconds)),
            )
            if self._fade_initial
            else self.sleep.gain()
        )
        target = self.normal_next_index()
        if (
            self._params[3]
            and self.model
            and (target is None or self.playlist[target]['id'] not in self._prepared)
        ):
            gain = min(
                gain,
                max(0.0, min(1.0, self.normal_remaining() / self.transitionSeconds)),
            )
        return gain

    def normal_remaining(self):
        speed = (
            self._effects.get('speed', 100) / 100
            if self._effects.get('enabled') and not self._state.get('effects_pending')
            else 1.0
        )
        return max(0.0, self.sourceDuration - self.sourcePosition) / max(0.5, speed)

    def normal_next_index(self):
        if self.queue_repeat == 'Uma' and self.queue_index >= 0:
            return self.queue_index
        target = self.queue_index + 1
        while (
            target < len(self.playlist)
            and self.playlist[target]['id'] in self._queue_history
            and self.queue_repeat != 'Todas'
        ):
            target += 1
        if target >= len(self.playlist) and self.queue_repeat == 'Todas':
            target = 0
        return target if 0 <= target < len(self.playlist) else None

    def normal_transition(self):
        if (
            not self._params[3]
            or not self._state['playing']
            or self.paused.is_set()
            or self.track_minutes
            or not self.preferences.get('jukebox_gradual_transition', True)
        ):
            return
        if self._switch_pending is not None or self._autoplay_entry is not None:
            return
        target = self.normal_next_index()
        if target is None or self.normal_remaining() > self.transitionSeconds + 0.5:
            return
        if self.playlist[target]['id'] not in self._prepared:
            return
        if self.queue_repeat == 'Uma':
            self.playQueued(target)
        else:
            self.nextTrack()

    @Property(int, notify=changed)
    def transitionSeconds(self):
        return max(
            1, min(10, int(self.preferences.get('jukebox_transition_seconds', 2)))
        )

    @Slot(int)
    def setTransitionSeconds(self, seconds):
        self.persist({'jukebox_transition_seconds': max(1, min(10, seconds))})
        self.changed.emit()
        self.appearanceChanged.emit()

    def queue_info(self, entry, record, cover=''):
        artists = record.get('artists') or []
        entry.update(
            title=record.get('title') or entry['title'],
            artist=', '.join(artists) if isinstance(artists, list) else str(artists),
            album=record.get('album') or '',
            cover=cover or record.get('cover_url') or '',
            duration=int(
                record.get('duration') or float(record.get('duration_ms') or 0) / 1000
            ),
        )

    def retain_media_metadata(self, model, entry):
        model = dict(model)
        record = entry.get('record') or {}
        title = model.get('media_title') or model.get('title') or ''
        known = record.get('title') or entry.get('title') or ''
        if known and (
            not title
            or title.casefold()
            in ('audio', 'áudio', 'video', 'vídeo', 'media', 'source')
        ):
            model['media_title'] = known
        artists = record.get('artists') or []
        model['media_artist'] = (
            model.get('media_artist')
            or (', '.join(artists) if isinstance(artists, list) else str(artists))
            or entry.get('artist', '')
        )
        model['album'] = (
            model.get('album') or record.get('album') or entry.get('album', '')
        )
        model['cover_url'] = (
            model.get('cover_url') or record.get('cover_url') or entry.get('cover', '')
        )
        return model

    @Slot('QVariantList')
    def enqueueFiles(self, urls):
        added = []
        for value in urls:
            url = QUrl(value)
            if url.isLocalFile() and len(self.playlist) < 5000:
                entry = {
                    'id': uuid.uuid4().hex,
                    'title': Path(url.toLocalFile()).stem,
                    'source': url.toLocalFile(),
                    'kind': 'file',
                    'artist': '',
                    'album': '',
                    'cover': '',
                    'duration': 0,
                }
                self.playlist.append(entry)
                added.append(dict(entry))
        self.queueChanged.emit()
        self.changed.emit()
        for entry in self.playlist:
            entry.setdefault('analysis', 'pending')
        if added:
            self.prepare_next_queued()
            self.tracksAdded.emit([row['id'] for row in added])

    def prepare_local(self, source, config, cancel, progress):
        model = prepare(source, config.get('ffmpeg', ''), cancel.is_set, progress)
        from audio_library import read_audio, cover_preview

        model['_cover'] = cover_preview(source, size=768) or ''
        try:
            tags = read_audio(source)
            model['media_title'] = tags.get('title', '')
            model['media_artist'] = ', '.join(tags.get('artists', []))
            model['album'] = tags.get('album') or ''
        except (OSError, ValueError):
            pass
        return model

    def fetch_record(self, record, config, cancel, progress):
        direct = record.get('_jukebox_direct')

        def staged_progress(stage, percent):
            progress(
                round(
                    min(100, max(0, percent)) * (0.6 if stage == 'download' else 0.39)
                )
                + (0 if stage == 'download' else 60)
            )

        model = fetch_audio(
            dict(config, url=record['source_url']) if direct else config,
            None if direct else record,
            cancel.is_set,
            lambda _: None,
            stage_progress=staged_progress,
        )
        if model.get('cover_url') and not cancel.is_set():
            from catalog_ui import cover_png

            try:
                model['_cover'] = base64.b64encode(
                    cover_png(model['cover_url'], size=768) or b''
                ).decode()
            except (OSError, ValueError):
                pass
        return model

    def prepare_next_queued(self):
        if self.closed or self._queue_preparing:
            return
        from playback_preparation import preparation_ahead

        ahead = preparation_ahead(self.preferences.get('playback_prepare_ahead', 2))
        current = max(0, self.queue_index)
        wanted = {
            row['id']
            for row in self.playlist[max(0, current - 1) : current + ahead + 1]
        }
        target = self.normal_next_index()
        if target is not None:
            wanted.add(self.playlist[target]['id'])
        wanted.update(
            identity
            for identity in (
                self._autoplay_entry,
                self._switch_pending,
                self._switch_after,
                getattr(self, '_queue_priority', None),
            )
            if identity
        )
        wanted.update(value[0] for value in self._switch_models.values())
        from playback_session import prepared_reference, restored_prepared

        for row in self.playlist:
            if row['id'] in self._prepared and row['id'] not in wanted:
                row['prepared_cache'] = prepared_reference(
                    self._prepared.pop(row['id'])
                )
        # A persisted/transient status is not proof that a worker still exists.
        for row in self.playlist:
            if row['id'] not in wanted:
                continue
            if row['id'] in self._prepared:
                row['analysis'] = 'ready'
            elif row.get('analysis') in ('preparing', 'ready'):
                row['analysis'] = 'pending'
        candidates = [
            row
            for row in self.playlist
            if row['id'] in wanted and row.get('analysis') == 'pending'
        ]
        entry = next(
            (row for row in candidates if row['id'] == self._autoplay_entry),
            next(iter(candidates), None),
        )
        if entry is None:
            return
        entry['analysis'] = 'preparing'
        entry['preparation_progress'] = 0
        self._queue_preparing = True
        identity = entry['id']
        cancel = threading.Event()
        self._queue_cancel[identity] = cancel
        config = self.config()
        entry = dict(entry)
        self.queueChanged.emit()
        self.preparationChanged.emit()

        def worker():
            last_sent = [-1, 0.0]

            def progress(value):
                percent = max(0, min(99, int(value)))
                now = time.monotonic()
                if (
                    not cancel.is_set()
                    and percent != last_sent[0]
                    and (now - last_sent[1] >= 0.1 or percent >= 99)
                ):
                    last_sent[:] = [percent, now]
                    self.emit(
                        0,
                        'queue_progress',
                        dict(id=identity, owner=cancel, progress=percent),
                    )

            try:
                model = restored_prepared(entry.get('prepared_cache'))
                if model is None:
                    model = (
                        self.prepare_local(entry['source'], config, cancel, progress)
                        if entry['kind'] == 'file'
                        else self.fetch_record(
                            entry['record'], config, cancel, progress
                        )
                    )
                self.emit(
                    0,
                    'queue_prepared',
                    {'id': identity, 'owner': cancel, 'model': model},
                )
            except Exception as error:
                self.emit(
                    0,
                    'queue_prepared',
                    {'id': identity, 'owner': cancel, 'error': str(error)},
                )

        self.start_worker(worker)

    @Slot(int)
    def retryQueued(self, index):
        if 0 <= index < len(self.playlist):
            self._queue_priority = self.playlist[index]['id']
            self.playlist[index]['analysis'] = 'pending'
            self.prepare_next_queued()

    def enqueueRecord(self, record):
        return self.enqueueRecords([record])

    def enqueueRecords(self, records):
        accepted = records[: max(0, 5000 - len(self.playlist))]
        added = []
        for record in accepted:
            entry = {
                'id': uuid.uuid4().hex,
                'title': record['title'],
                'record': dict(record),
                'kind': 'catalog',
                'analysis': 'pending',
                'manual': not bool(record.get('_queue_collection')),
                'collection': record.get('_queue_collection', ''),
            }
            self.queue_info(entry, record)
            if entry['manual'] and self.queue_index >= 0:
                insertion = self.queue_index + 1
                while insertion < len(self.playlist) and self.playlist[insertion].get(
                    'manual'
                ):
                    insertion += 1
                self.playlist.insert(insertion, entry)
            else:
                self.playlist.append(entry)
            added.append(entry['id'])
        if accepted:
            self.queueChanged.emit()
            self.changed.emit()
            self.prepare_next_queued()
            self.tracksAdded.emit(added)
        if len(accepted) < len(records):
            self.update_state(
                status=tr(
                    'Limite de 5.000 músicas na fila de reprodução. Remova músicas antes de adicionar outras.'
                )
            )
        return len(accepted)

    @Slot(int)
    def enqueueResult(self, index):
        if 0 <= index < len(self.records):
            self.enqueueRecord(self.records[index])

    @Slot(int)
    def removeQueued(self, index):
        if not 0 <= index < len(self.playlist):
            return
        if (
            index == self.queue_index
            and self._state['busy']
            and self.autoplay_revision is not None
        ):
            self.cancelOperation()
        removed = self.playlist.pop(index)
        self._prepared.pop(removed['id'], None)
        if self._autoplay_entry == removed['id']:
            self._autoplay_entry = None
        if removed['id'] in self._queue_cancel:
            self._queue_cancel[removed['id']].set()
        if index < self.queue_index:
            self.queue_index -= 1
        elif index == self.queue_index:
            self.queue_index = -1
        self.queueChanged.emit()
        self.changed.emit()

    @Slot(int, int)
    def moveQueued(self, index, direction):
        target = index + direction
        if not 0 <= index < len(self.playlist) or not 0 <= target < len(self.playlist):
            return
        current = (
            self.playlist[self.queue_index]['id'] if self.queue_index >= 0 else None
        )
        self.playlist.insert(target, self.playlist.pop(index))
        self.queue_index = next(
            (i for i, row in enumerate(self.playlist) if row['id'] == current), -1
        )
        self.queueChanged.emit()
        self.changed.emit()
        self.prepare_next_queued()

    @Slot()
    def clearPlaybackQueue(self):
        self._queue_history = []
        self._shuffle_order = []
        if self._state['busy'] and self.autoplay_revision is not None:
            self.cancelOperation()
        for cancel in self._queue_cancel.values():
            cancel.set()
        self._prepared.clear()
        self.playlist = []
        self.queue_index = -1
        self._autoplay_entry = None
        self.queueChanged.emit()
        self.changed.emit()

    @Slot()
    def clearManualQueue(self):
        current = (
            self.playlist[self.queue_index]['id']
            if 0 <= self.queue_index < len(self.playlist)
            else None
        )
        removed = {
            row['id']
            for i, row in enumerate(self.playlist)
            if i > self.queue_index and row.get('manual')
        }
        self.playlist = [row for row in self.playlist if row['id'] not in removed]
        for identity in removed:
            self._prepared.pop(identity, None)
            if identity in self._queue_cancel:
                self._queue_cancel[identity].set()
        if self._autoplay_entry in removed:
            self._autoplay_entry = None
        self.queue_index = next(
            (i for i, row in enumerate(self.playlist) if row['id'] == current), -1
        )
        self.queueChanged.emit()
        self.changed.emit()
        self.prepare_next_queued()

    @Slot(int)
    def playQueued(self, index):
        if not 0 <= index < len(self.playlist):
            return
        entry = self.playlist[index]
        model = self._prepared.get(entry['id'])
        if model is None:
            if self._switch_pending is not None:
                self._switch_after = entry['id']
            self._autoplay_entry = entry['id']
            if entry.get('analysis') == 'error':
                self.retryQueued(index)
            self.prepare_next_queued()
            return
        if not (Path(model['cache']) / 'analysis.json').is_file():
            self._prepared.pop(entry['id'], None)
            entry['analysis'] = 'pending'
            self._autoplay_entry = entry['id']
            self.prepare_next_queued()
            return
        if self._state['playing'] and not self.paused.is_set():
            if self._switch_pending is not None:
                self._switch_after = entry['id']
                self._autoplay_entry = None
                return
            self._switch_pending = entry['id']
            self._switch_models[str(model['cache'])] = (entry['id'], model)
            seconds = (
                self.transitionSeconds
                if self.preferences.get('jukebox_gradual_transition', True)
                else 0
            )
            self._switch_requests.put((str(model['cache']), seconds))
            self.update_state(status=tr('Transição para a próxima música…'))
            return
        self.activate_queued(index, model)

    def activate_queued(self, index, model):
        self.remember_current()
        self.stop(reset_timer=False)
        self.queue_index = index
        self.handle_event(self.revision, 'result', model)
        restored = self.playlist[index].pop('restore_seconds', 0)
        if restored:
            self.seekSeconds(restored)
        self.playPause()
        self.queueChanged.emit()
        self.changed.emit()
        self.prepare_next_queued()

    @Slot()
    def previousTrack(self):
        while self._queue_history:
            identity = self._queue_history.pop()
            target = next(
                (i for i, row in enumerate(self.playlist) if row['id'] == identity), -1
            )
            if target >= 0 and target != self.queue_index:
                self._history_back = True
                self.playQueued(target)
                return
        if self.queue_index > 0:
            self._history_back = True
            self.playQueued(self.queue_index - 1)
        elif self.model:
            self.seek(0)

    @Property(str, notify=queueChanged)
    def queueRepeat(self):
        return self.queue_repeat

    @Property(bool, notify=queueChanged)
    def queueShuffle(self):
        return self.queue_shuffle

    @Slot(str)
    def setQueueRepeat(self, value):
        if value in ('Desativada', 'Todas', 'Uma'):
            self.queue_repeat = value
            self.queueChanged.emit()

    @Slot(bool)
    def setQueueShuffle(self, value):
        value = bool(value)
        if value == self.queue_shuffle:
            return
        current = (
            self.playlist[self.queue_index]['id']
            if 0 <= self.queue_index < len(self.playlist)
            else None
        )
        if value:
            import random

            self._shuffle_order = [row['id'] for row in self.playlist]
            start = self.queue_index + 1 if current else 0
            manual = [row for row in self.playlist[start:] if row.get('manual')]
            upcoming = [row for row in self.playlist[start:] if not row.get('manual')]
            random.shuffle(upcoming)
            self.playlist[start:] = manual + upcoming
        else:
            order = {
                identity: index for index, identity in enumerate(self._shuffle_order)
            }
            self.playlist.sort(key=lambda row: order.get(row['id'], len(order)))
            manual = [
                row
                for row in self.playlist
                if row.get('manual')
                and row['id'] != current
                and row['id'] not in self._queue_history
            ]
            manual_ids = {row['id'] for row in manual}
            self.playlist = [
                row for row in self.playlist if row['id'] not in manual_ids
            ]
            insertion = next(
                (i + 1 for i, row in enumerate(self.playlist) if row['id'] == current),
                0,
            )
            self.playlist[insertion:insertion] = manual
            self._shuffle_order = []
        self.queue_shuffle = value
        self.queue_index = next(
            (i for i, row in enumerate(self.playlist) if row['id'] == current), -1
        )
        self.queueChanged.emit()
        self.changed.emit()
        self.prepare_next_queued()

    @Slot()
    def nextTrack(self):
        anchor = self._autoplay_entry or self._switch_after or self._switch_pending
        target = next(
            (i + 1 for i, row in enumerate(self.playlist) if row['id'] == anchor),
            self.queue_index + 1,
        )
        while (
            target < len(self.playlist)
            and self.playlist[target]['id'] in self._queue_history
            and self.queue_repeat != 'Todas'
        ):
            target += 1
        if target >= len(self.playlist) and self.queue_repeat == 'Todas':
            target = 0
        if target < len(self.playlist):
            self.playQueued(target)
        else:
            self.setTrackMinutes(0)
            self.update_state(
                status=tr('Fim da fila de reprodução. A música atual continua.')
            )

    @Property(float, notify=positionChanged)
    def position(self):
        return self._position

    @Property(float, notify=positionChanged)
    def audioLevel(self):
        return (
            self._visual_level
            if self._state['playing'] and not self._state['paused']
            else 0.0
        )

    @Property(float, notify=positionChanged)
    def sourcePosition(self):
        beats = (self.model or {}).get('beats', [])
        index = min(int(self._position), len(beats) - 2)
        return (
            beats[index] + (beats[index + 1] - beats[index]) * self._phase
            if index >= 0
            else 0.0
        )

    @Property(float, notify=changed)
    def sourceDuration(self):
        return float((self.model or {}).get('duration', 0))

    @Slot(float)
    def seekSeconds(self, seconds):
        import bisect

        beats = (self.model or {}).get('beats', [])
        if len(beats) > 1:
            index = max(0, min(len(beats) - 2, bisect.bisect_right(beats, seconds) - 1))
            phase = max(
                0.0,
                min(
                    0.999999,
                    (seconds - beats[index])
                    / max(0.000001, beats[index + 1] - beats[index]),
                ),
            )
            self.seek(index, phase)

    @Property(float, notify=positionChanged)
    def phase(self):
        return self._phase

    @Property(str, notify=positionChanged)
    def elapsed(self):
        minutes, seconds = divmod(int(self._elapsed), 60)
        return f'{minutes:02}:{seconds:02}'

    @Property(int, notify=positionChanged)
    def jumps(self):
        return self._jumps

    @Property('QVariantMap', notify=graphChanged)
    def graph(self):
        if self._graph_cache is not None:
            return self._graph_cache
        rows = self.model['neighbors'] if self.model else [[] for _ in range(64)]
        normal = self._params[3]
        from jukebox import variation_neighbors

        options = (self._params[0], normal)
        if self._topology_rows is not rows or self._topology_options != options:
            self._topology_rows = rows
            self._topology_options = options
            selected = [] if normal else variation_neighbors(rows, self._params[0])
            total = sum(map(len, selected))
            stride = max(1, math.ceil(total / 1800))
            offset = 0
            links = []
            for i, row in enumerate(selected):
                links.extend(
                    (i, row[k]) for k in range((-offset) % stride, len(row), stride)
                )
                offset += len(row)
            self._topology_links = links
        links = self._topology_links
        self._graph_cache = {
            'count': len(rows),
            'links': links,
            'flow': list(self.flow),
            'used': sorted(self.used_edges),
            'variation': self._params[0],
        }
        return self._graph_cache

    @Property('QVariantMap', notify=positionChanged)
    def cursor(self):
        n = max(1, len(self.model['neighbors']) if self.model else 64)

        def point(index):
            angle = index / n * math.tau - math.pi / 2
            return math.cos(angle), math.sin(angle)

        if 0 <= self._next_index < n and self._next_index != (self._beat_index + 1) % n:
            a = point(self._beat_index)
            b = point(self._next_index)
            t = self._jump_blend
            return {
                'x': a[0] * (1 - t) ** 2 + b[0] * t * t,
                'y': a[1] * (1 - t) ** 2 + b[1] * t * t,
            }
        x, y = point(self._position)
        return {'x': x, 'y': y}

    @Property(str, constant=True)
    def brandPath(self):
        from brand_mark import SVG_PATH

        return SVG_PATH

    @Property('QVariantMap', notify=appearanceChanged)
    def palette(self):
        from appearance import palette

        return palette(
            self.preferences.get('theme_mode', 'Preto puro'),
            self.preferences.get('theme_accent', 'Verde-Água'),
            self.preferences.get('pure_black_separators', False),
        )

    @Property(bool, notify=appearanceChanged)
    def animations(self):
        return self.preferences.get('qt_animations', True)

    @Property(float, notify=appearanceChanged)
    def fontScale(self):
        try:
            return max(
                0.75,
                min(
                    2,
                    float(
                        str(self.preferences.get('interface_font_size', '100%')).rstrip(
                            '%'
                        )
                    )
                    / 100,
                ),
            )
        except (ValueError, TypeError):
            return 1.0

    @Property(float, notify=appearanceChanged)
    def spacing(self):
        return {'Compacto': 0.85, 'Confortável': 1.15}.get(
            self.preferences.get('interface_spacing'), 1.0
        )

    @Property('QStringList', constant=True)
    def themes(self):
        return ['Claro', 'Escuro', 'Preto puro', 'Seguir o sistema', 'Alto contraste']

    @Property('QStringList', constant=True)
    def accents(self):
        from appearance import ACCENTS

        return list(ACCENTS)

    @Property(str, notify=appearanceChanged)
    def theme(self):
        return self.preferences.get('theme_mode', 'Preto puro')

    @Property(str, notify=appearanceChanged)
    def interfaceFamily(self):
        from interface_fonts import qt_font_family, DEFAULT_FONT

        return qt_font_family(self.preferences.get('interface_font', DEFAULT_FONT))

    @Property(str, notify=appearanceChanged)
    def accent(self):
        return self.preferences.get('theme_accent', 'Verde-Água')

    @Property('QVariantMap', notify=equalizerChanged)
    def equalizer(self):
        return self._equalizer

    @Property('QStringList', constant=True)
    def presetNames(self):
        return list(presets())

    @Property(str, notify=equalizerChanged)
    def presetName(self):
        return preset_name(self._equalizer)

    def update_graph(self):
        self._graph_cache = None
        self.graphChanged.emit()

    @Slot(str, result=str)
    def translate(self, text):
        return tr(text)

    @Slot(str, result=str)
    def translateError(self, text):
        return error_text(text)

    def refreshSearchResults(self):
        self.update_state(
            results=[
                dict(
                    r,
                    artist=', '.join(r.get('artists', [])),
                    album=r.get('album') or '',
                    cover=r.get('cover_url') or '',
                )
                for r in self.records
            ]
        )

    def update_state(self, **values):
        if "status" in values:
            values.setdefault("status_error", False)
        if any(self._state.get(k) != v for k, v in values.items()):
            self._state.update(values)
            self.changed.emit()

    def persist(self, values):
        self.preferences.update(values)
        self._pending.update(values)
        self.save_timer.start()

    @Slot()
    def save_preferences(self):
        self.save_timer.stop()
        if not self._pending:
            return
        if not self.store.remember_enabled():
            self._pending.clear()
            return
        try:
            latest = self.store.load() or {}
            latest.update(self._pending)
            self.store.save(latest)
            self._pending.clear()
        except (ValueError, OSError):
            self.update_state(
                status=tr('Não foi possível salvar as configurações deste computador.')
            )

    @Slot(str, str, bool)
    def setAppearance(self, theme, accent, animations):
        if theme not in self.themes or accent not in self.accents:
            return
        self.persist(
            {'theme_mode': theme, 'theme_accent': accent, 'qt_animations': animations}
        )
        self.appearanceChanged.emit()

    @Slot(float, float, float, bool)
    def setParams(self, variation, smooth, volume, normal):
        values = tuple(max(0.0, min(100.0, v)) for v in (variation, smooth, volume)) + (
            bool(normal),
        )
        graph_changed = values[0] != self._params[0] or values[3] != self._params[3]
        self._params = values
        if graph_changed:
            self.update_graph()
        self.changed.emit()

    @Property('QVariantMap', notify=changed)
    def playbackParams(self):
        return dict(
            variation=self._params[0],
            smooth=self._params[1],
            volume=self._params[2],
            normal=self._params[3],
        )

    @Slot('QVariantMap')
    def setEffects(self, value):
        from playback_effects import clean as clean_effects

        self._effects = clean_effects(dict(value))
        self.changed.emit()
        self._effect_prepare_cancel.set()
        self.effect_prepare_timer.start()

    def prewarm_effects(self):
        if not self._effects.get('enabled') or self.closed:
            return
        cancel = threading.Event()
        self._effect_prepare_cancel = cancel
        effects = dict(self._effects)
        from playback_preparation import preparation_ahead

        ahead = preparation_ahead(self.preferences.get('playback_prepare_ahead', 2))
        models = ([self.model] if self.model else []) + [
            self._prepared[row['id']]
            for row in self.playlist[
                max(0, self.queue_index + 1) : self.queue_index + ahead + 1
            ]
            if row['id'] in self._prepared
        ]

        def worker():
            from playback_effects import prepare as prepare_effects

            for model in models:
                if cancel.is_set():
                    break
                try:
                    prepare_effects(model['cache'], effects, cancel.is_set)
                except Cancelled:
                    break

        self.start_worker(worker)

    @Slot(str)
    def applyPreset(self, name):
        if name in presets():
            self.set_equalizer(presets()[name])

    def set_equalizer(self, value):
        self._equalizer = clean(value)
        self.persist({'jukebox_equalizer': json.dumps(self._equalizer)})
        self.equalizerChanged.emit()

    @Slot(bool)
    def enableEqualizer(self, value):
        self.set_equalizer(dict(self._equalizer, enabled=value))

    @Slot(float)
    def setPreamp(self, value):
        self.set_equalizer(dict(self._equalizer, preamp=value))

    @Slot(int, float, float, float)
    def setBand(self, index, frequency, gain, q):
        if not 0 <= index < 10:
            return
        value = clean(self._equalizer)
        value['bands'][index] = {'frequency': frequency, 'gain': gain, 'q': q}
        self.set_equalizer(value)

    @Slot()
    def resetEqualizer(self):
        self.set_equalizer(dict(clean(), enabled=self._equalizer['enabled']))

    def config(self):
        if self.config_provider is not None:
            return self.config_provider()
        from ffmpeg_runtime import existing_folder
        from credentials import CredentialStore, CredentialError

        try:
            credentials = CredentialStore().load() or ('', '')
        except CredentialError:
            credentials = ('', '')
        return {
            'ffmpeg': str(existing_folder() or ''),
            'spotify_client_id': credentials[0],
            'spotify_client_secret': credentials[1],
        }

    def emit(self, revision, kind, value):
        if not self.closed:
            self._event.emit(revision, kind, value)

    def task(self, function, stop_current=True):
        if stop_current:
            self.stop(reset_timer=False)
            self.cancelled = threading.Event()
            cancel = self.cancelled
        else:
            self.lookup_cancelled.set()
            self.lookup_cancelled = threading.Event()
            cancel = self.lookup_cancelled
        self.task_is_lookup = not stop_current
        self.request_number += 1
        request = self.request_number
        revision = self.revision

        def post(kind, value):
            if request == self.request_number and not cancel.is_set():
                self.emit(
                    revision,
                    'lookup_error' if kind == 'error' and not stop_current else kind,
                    value,
                )

        self.update_state(busy=True, progress=0, results=[])

        def worker():
            try:
                post('result', function(cancel, lambda v: post('progress', v)))
            except Cancelled:
                pass
            except Exception as error:
                post('error', str(error))
            finally:
                post('idle', None)

        self.start_worker(worker)

    def start_worker(self, function):
        self.workers = [worker for worker in self.workers if worker.is_alive()]
        thread = threading.Thread(target=function, daemon=True)
        self.workers.append(thread)
        thread.start()

    @Slot(QUrl)
    def openFile(self, url):
        if not url.isLocalFile():
            return
        self._selection_insert = max(0, self.queue_index + 1)
        self._selected_record = None
        self.queue_index = -1
        self.queueChanged.emit()
        source = url.toLocalFile()
        config = self.config()
        self.update_state(status=tr('Analisando ritmo e trechos semelhantes…'))
        self.task(
            lambda cancel, progress: self.prepare_local(
                source, config, cancel, progress
            )
        )

    @Slot(str)
    def search(self, query):
        query = query.strip()
        if not query or self._state['busy']:
            return
        config = self.config()
        provider = self.preferences.get('catalog_provider', 'Todos')
        self.update_state(status=tr('Pesquisando…'))

        def search(cancel, progress):
            from metadata import MetadataClient
            from playback_input import resolve_input
            from spotify_account import SpotifyAccount

            client = MetadataClient(
                config['spotify_client_id'], config['spotify_client_secret']
            )
            try:
                return resolve_input(
                    query,
                    client,
                    dict(config, catalog_provider=provider),
                    SpotifyAccount(self.store.path.with_name('spotify-account.dpapi')),
                    cancel.is_set,
                )
            finally:
                client.close()

        self.task(search, stop_current=False)

    @Slot(int)
    def selectResult(self, index):
        if not 0 <= index < len(self.records) or self._state['busy']:
            return
        self._selection_insert = max(0, self.queue_index + 1)
        self.queue_index = -1
        self.prepare_record(dict(self.records[index]))

    def prepare_record(self, record):
        self._selected_record = dict(record)
        config = self.config()
        self.update_state(status=tr('Obtendo áudio para análise…'))
        self.task(
            lambda cancel, progress: self.fetch_record(record, config, cancel, progress)
        )

    @Slot(int, str, object)
    def handle_event(self, revision, kind, value):
        if self.closed:
            return
        if kind == 'queue_progress':
            owner = value['owner']
            entry = next(
                (row for row in self.playlist if row['id'] == value['id']), None
            )
            if (
                entry is not None
                and self._queue_cancel.get(value['id']) is owner
                and not owner.is_set()
                and entry.get('analysis') == 'preparing'
            ):
                entry['preparation_progress'] = value['progress']
                self.preparationChanged.emit()
            return
        if kind == 'queue_prepared':
            owner = value.get('owner')
            if owner is not None and self._queue_cancel.get(value['id']) is not owner:
                return
            self._queue_preparing = False
            self._queue_cancel.pop(value['id'], None)
            if owner is not None and owner.is_set():
                entry = next(
                    (row for row in self.playlist if row['id'] == value['id']), None
                )
                if entry is not None:
                    entry.update(analysis='pending', preparation_progress=0, error='')
                self.queueChanged.emit()
                self.preparationChanged.emit()
                self.prepare_next_queued()
                return
            if getattr(self, '_queue_priority', None) == value['id']:
                self._queue_priority = None
            entry = next(
                (row for row in self.playlist if row['id'] == value['id']), None
            )
            if entry is not None:
                entry['analysis'] = 'error' if 'error' in value else 'ready'
                entry['error'] = value.get('error', '')
                entry['preparation_progress'] = 0 if 'error' in value else 100
                if 'model' in value:
                    model = self.retain_media_metadata(value['model'], entry)
                    self._prepared[value['id']] = model
                    from playback_session import prepared_reference

                    entry['prepared_cache'] = prepared_reference(model)
                    self.effect_prepare_timer.start()
                    cover = model.get('_cover', '')
                    cover = (
                        base64.b64encode(cover).decode()
                        if isinstance(cover, bytes)
                        else cover
                    )
                    entry.update(
                        title=model.get('media_title')
                        or model.get('title')
                        or entry['title'],
                        artist=model.get('media_artist') or entry.get('artist', ''),
                        album=model.get('album') or '',
                        cover=(
                            ('data:image/png;base64,' + cover)
                            if cover
                            else model.get('cover_url', '')
                        ),
                        duration=int(model.get('duration') or 0),
                    )
                    if (
                        self.track_minutes
                        and self._elapsed - self._track_started
                        >= self.track_minutes * 60
                    ):
                        self._track_started = (
                            self._elapsed - self.track_minutes * 60 + 2
                        )
                    if self._autoplay_entry == entry['id']:
                        self._autoplay_entry = None
                        self.playQueued(self.playlist.index(entry))
                elif self._autoplay_entry == entry['id']:
                    self._autoplay_entry = None
                    self.update_state(status=entry['error'], status_error=True)
            self.queueChanged.emit()
            self.preparationChanged.emit()
            self.changed.emit()
            self.prepare_next_queued()
            return
        if kind == 'queue_info':
            entry = next(
                (row for row in self.playlist if row['id'] == value['id']), None
            )
            if entry is not None:
                self.queue_info(entry, value['record'], value['cover'])
                self.queueChanged.emit()
            return
        if revision != self.revision:
            return
        if kind == 'progress':
            self.update_state(progress=value)
        elif kind == 'result':
            if 'tracks' in value:
                if value.get('is_collection'):
                    for row in value['tracks']:
                        row['_queue_collection'] = value.get('title') or 'Playlist'
                    count = self.enqueueRecords(value['tracks'])
                    self.records = []
                    self.update_state(
                        results=[],
                        status=tr('{count} músicas adicionadas à fila.').replace(
                            '{count}', str(count)
                        )
                        + ' '
                        + (value.get('coverage_summary') or '')
                        + (
                            ' '
                            + tr(
                                'Limite de 5.000 músicas na fila de reprodução. Remova músicas antes de adicionar outras.'
                            )
                            if count < len(value['tracks'])
                            else ''
                        ),
                    )
                    return
                self.records = value['tracks']
                self.refreshSearchResults()
                self.update_state(
                    status=(
                        tr('Escolha uma música nos resultados.')
                        if self.records
                        else tr('Nenhuma música encontrada.')
                    )
                )
            else:
                if 0 <= self.queue_index < len(self.playlist):
                    value = self.retain_media_metadata(
                        value, self.playlist[self.queue_index]
                    )
                self.model = value
                self.flow = []
                self.used_edges = set()
                self._position = 0
                self._phase = 0
                self._beat_index = 0
                self._next_index = -1
                self._jump_blend = 0.0
                cover = value.get('_cover', '')
                cover = (
                    base64.b64encode(cover).decode()
                    if isinstance(cover, bytes)
                    else cover
                )
                self.update_state(
                    title=value.get('media_title') or value['title'],
                    artist=value.get('media_artist') or '',
                    album=value.get('album') or '',
                    cover=(
                        ('data:image/png;base64,' + cover)
                        if cover
                        else value.get('cover_url', '')
                    ),
                    ready=True,
                    results=[],
                    status=tr(
                        'Análise concluída.'
                        if value['links']
                        else 'Sem saltos compatíveis: a faixa será repetida normalmente.'
                    ),
                )
                if self.queue_index < 0 and len(self.playlist) < 5000:
                    record = getattr(self, '_selected_record', None)
                    entry = dict(
                        id=uuid.uuid4().hex,
                        title=self._state['title'],
                        artist=self._state['artist'],
                        album=self._state['album'],
                        cover=self._state['cover'],
                        duration=int(value.get('duration') or 0),
                        analysis='ready',
                    )
                    if record:
                        entry.update(kind='catalog', record=record)
                    else:
                        entry.update(kind='file', source=value.get('source', ''))
                    insertion = min(
                        len(self.playlist),
                        getattr(self, '_selection_insert', len(self.playlist)),
                    )
                    self.playlist.insert(insertion, entry)
                    self.queue_index = insertion
                    self._prepared[entry['id']] = value
                    self.queueChanged.emit()
                    self._selection_insert = len(self.playlist)
                if self.queue_index >= 0 and self.autoplay_revision == revision:
                    self.playlist[self.queue_index].update(
                        title=self._state['title'],
                        artist=self._state['artist'],
                        album=self._state['album'],
                        cover=self._state['cover'],
                        duration=int(value.get('duration') or 0),
                    )
                    self.queueChanged.emit()
                self.update_graph()
                self.positionChanged.emit()
        elif kind == 'switch_error':
            self._switch_pending = None
            entry_model = self._switch_models.pop(value['cache'], None)
            if entry_model is not None:
                entry = next(
                    (row for row in self.playlist if row['id'] == entry_model[0]), None
                )
                if entry is not None:
                    entry['analysis'] = 'error'
                    entry['error'] = value['error']
                    self.queueChanged.emit()
            self.update_state(status=value['error'], status_error=True)
        elif kind == 'track_started':
            entry_model = self._switch_models.pop(value, None)
            if entry_model is not None:
                identity, model = entry_model
                self._switch_pending = None
                self._fade_initial = False
                self.remember_current()
                self.queue_index = next(
                    (i for i, row in enumerate(self.playlist) if row['id'] == identity),
                    -1,
                )
                self.handle_event(revision, 'result', model)
                self._track_started = 0.0
                self.queueChanged.emit()
                self.prepare_next_queued()
                following = self._switch_after
                self._switch_after = None
                target = next(
                    (
                        i
                        for i, row in enumerate(self.playlist)
                        if row['id'] == following
                    ),
                    -1,
                )
                if target >= 0:
                    self.playQueued(target)
        elif kind == 'position':
            self._visual_level = max(0.0, min(1.0, float(value.get('level', 0.0))))
            self._position = value['index'] + value['phase']
            self._phase = value['phase']
            self._elapsed = value['elapsed']
            self._jumps = value['jumps']
            self._beat_index = value['index']
            self._next_index = value.get('next', -1)
            self._jump_blend = value.get('blend', 0.0)
            if value['edges']:
                self.flow = (self.flow + value['edges'])[-24:]
                self.used_edges.update(tuple(edge) for edge in value['edges'])
            if value['edges']:
                self.update_graph()
            self.positionChanged.emit()
            self.normal_transition()
            if self.track_minutes:
                remaining = self.track_minutes * 60 - (
                    self._elapsed - self._track_started
                )
                if self.queue_repeat == 'Uma':
                    self._track_started = self._elapsed
                    return
                target = (
                    0
                    if self.queue_repeat == 'Todas'
                    and self.queue_index + 1 >= len(self.playlist)
                    else self.queue_index + 1
                )
                if remaining <= 0:
                    if target >= len(self.playlist):
                        self.nextTrack()
                    elif self.playlist[target].get('analysis') == 'error':
                        self.setTrackMinutes(0)
                        self.update_state(
                            status=self.playlist[target].get('error', ''),
                            status_error=True,
                        )
                    else:
                        self.nextTrack()
        elif kind == 'effects_status':
            pending, error = value
            self.update_state(effects_pending=pending, effects_error=error)
        elif kind == 'finished':
            self.stop(reset_timer=False)
            if self.queue_repeat == 'Uma':
                self.seek(0)
                self.playPause()
            elif (
                self.queue_index + 1 < len(self.playlist)
                or self.queue_repeat == 'Todas'
                and self.playlist
            ):
                self.nextTrack()
            else:
                self.update_state(status=tr('Fim da fila de reprodução.'))
        elif kind == 'lookup_error':
            self.update_state(status=str(value), status_error=True)
        elif kind == 'error':
            self.autoplay_revision = None
            self.update_state(
                status=str(value), status_error=True, playing=False, paused=False
            )
            self.media_timer.stop()
            self.sync_media()
        elif kind == 'idle':
            self.update_state(busy=False)
            if self.autoplay_revision == revision and self._state['ready']:
                self.autoplay_revision = None
                self.playPause()
        elif kind == 'stopped':
            self.update_state(playing=False, paused=False)
            self.media_timer.stop()
            self.sync_media()

    @Slot()
    def playPause(self):
        if self._state['playing']:
            if self.paused.is_set():
                self.playbackRequested.emit()
                self.paused.clear()
            else:
                self.paused.set()
            self.update_state(paused=self.paused.is_set())
            self.sync_media()
            return
        if self._state['busy']:
            return
        if not self.model:
            if self.playlist:
                self.playQueued(max(0, self.queue_index))
            return
        self.playbackRequested.emit()
        self.cancelled = threading.Event()
        self.paused.clear()
        cancel = self.cancelled
        revision = self.revision
        cache = self.model['cache']
        initial = int(self._position)
        initial_phase = self._phase
        self.seeks = queue.SimpleQueue()
        seeks = self.seeks
        switch_requests = self._switch_requests
        self._fade_initial = True
        self._elapsed = 0
        self._track_started = 0
        self._jumps = 0
        self.flow = []
        self.used_edges = set()
        self.positionChanged.emit()
        self.update_graph()
        self.update_state(playing=True, paused=False, status=tr('Reproduzindo…'))
        self.sync_media()
        self.media_timer.start()

        def worker():
            session = output = None
            try:
                from jukebox_audio import PcmOutput

                session = Stream(cache)
                session.seek(initial, phase=initial_phase)
                timeline = deque()
                submitted = 0
                heard_jumps = 0
                track_base = 0
                cursor_initial = initial
                elapsed_offset = 0.0

                def progress(played):
                    nonlocal heard_jumps
                    edges = []
                    index = cursor_initial
                    phase = 0.0
                    next_index = -1
                    blend = 0.0
                    level = 0.0

                    def announce(end, part):
                        nonlocal track_base, elapsed_offset
                        if part.get('track_changed'):
                            track_base = end - part['frames']
                            elapsed_offset = 0.0
                            self.emit(
                                revision, 'track_started', part.pop('track_changed')
                            )

                    while timeline and timeline[0][0] <= played:
                        end, part = timeline.popleft()
                        announce(end, part)
                        if part.get('edge_completed', True):
                            edges.append((part['index'], part['next']))
                        heard_jumps = part['jumps']
                        index = (
                            part['next']
                            if part.get('edge_completed', True)
                            else part['index']
                        )
                        level = (part.get('visual_levels') or [0.0])[-1]
                    if timeline:
                        end, part = timeline[0]
                        announce(end, part)
                        index = part['index']
                        frames = part['frames']
                        local = max(
                            0.0, min(1.0, (played - end + frames) / max(1, frames))
                        )
                        phase = (
                            part.get('phase_start', 0)
                            + (part.get('phase_end', 1) - part.get('phase_start', 0))
                            * local
                        )
                        levels = part.get('visual_levels') or [0.0]
                        level = levels[min(len(levels) - 1, int(local * len(levels)))]
                        next_index = part['next']
                        portion = part.get('transition', 0) / max(
                            0.0001, part.get('beat_seconds', frames / RATE)
                        )
                        if portion > 0:
                            blend = max(0.0, min(1.0, (phase - 1 + portion) / portion))
                    self.emit(
                        revision,
                        'position',
                        dict(
                            index=index,
                            phase=phase,
                            edges=edges,
                            elapsed=elapsed_offset + max(0, played - track_base) / RATE,
                            jumps=heard_jumps,
                            next=next_index,
                            blend=blend,
                            level=level,
                        ),
                    )

                output = PcmOutput(progress=progress)
                output.gain = self.playback_gain
                if self.preferences.get('jukebox_gradual_transition', True):
                    output.last_gain = 0.0
                while not cancel.is_set():
                    if not session.transitioning and not switch_requests.empty():
                        target_cache, seconds = switch_requests.get()
                        try:
                            session.switch(target_cache, seconds)
                        except Exception as error:
                            self.emit(
                                revision,
                                'switch_error',
                                dict(cache=target_cache, error=str(error)),
                            )
                    target = None
                    while not seeks.empty():
                        target = seeks.get()
                    if target is not None:
                        expected, index, phase = (
                            (*target, 0.0)
                            if isinstance(target, tuple) and len(target) == 2
                            else (
                                target
                                if isinstance(target, tuple)
                                else (None, target, 0.0)
                            )
                        )
                        if session.seek(index, expected_cache=expected, phase=phase):
                            elapsed_offset += (
                                max(0, getattr(output, 'last_frame', 0) - track_base)
                                / RATE
                            )
                            gain = output.last_gain
                            output.close()
                            timeline.clear()
                            submitted = 0
                            track_base = 0
                            heard_jumps = 0
                            cursor_initial = index
                            output = PcmOutput(progress=progress)
                            output.gain = self.playback_gain
                            output.last_gain = gain
                    part = session.chunk(
                        *self._params, equalizer=self._equalizer, effects=self._effects
                    )
                    frames = len(part['pcm']) // 4
                    submitted += frames
                    if (
                        self._mini_active
                        and self.preferences.get('translucent_effects', True)
                        and self.preferences.get('qt_animations', True)
                    ):
                        from mini_player_effects import pcm_envelope

                        part['visual_levels'] = pcm_envelope(part['pcm'], RATE)
                    status = (
                        part.get('effects_pending', False),
                        part.get('effects_error', ''),
                    )
                    if status != self._effects_status:
                        self._effects_status = status
                        self.emit(revision, 'effects_status', status)
                    metadata = dict(part)
                    metadata.pop('pcm')
                    metadata['frames'] = frames
                    metadata['transition'] = part.get('transition_seconds', 0)
                    timeline.append((submitted, metadata))
                    output.write(part['pcm'], cancel.is_set, self.paused.is_set)
                    if part.get('finished') and part.get('edge_completed', True):
                        while output.buffers:
                            output._drain(cancel.is_set, self.paused.is_set)
                        self.emit(revision, 'finished', None)
                        break
            except Cancelled:
                pass
            except Exception as error:
                self.emit(revision, 'error', str(error))
            finally:
                if output:
                    output.close()
                if session:
                    session.close()
                self.emit(revision, 'stopped', None)

        self.start_worker(worker)

    @Slot()
    def closeSearch(self):
        if self.task_is_lookup and self._state['busy']:
            self.cancelOperation()
        self.records = []
        self.update_state(
            results=[],
            status=(
                tr('Pausado.' if self._state['paused'] else 'Reproduzindo…')
                if self._state['playing']
                else (
                    tr('Análise concluída.')
                    if self._state['ready']
                    else tr(
                        'Abra arquivos, pesquise músicas ou adicione álbuns e playlists à fila.'
                    )
                )
            ),
        )

    @Slot()
    def cancelOperation(self):
        if self.task_is_lookup:
            self.lookup_cancelled.set()
            self.request_number += 1
            self.update_state(busy=False)
        else:
            self.stop()

    @Slot()
    def stop(self, reset_timer=True):
        self._switch_after = None
        if reset_timer:
            self.sleep.cancel()
            self.track_minutes = 0
            self.clock_timer.stop()
        self._switch_requests = queue.SimpleQueue()
        self._switch_pending = None
        self._switch_models.clear()
        self._fade_initial = False
        self.autoplay_revision = None
        self._autoplay_entry = None
        self.lookup_cancelled.set()
        self.request_number += 1
        self.revision += 1
        self.cancelled.set()
        self.paused.clear()
        self.media_timer.stop()
        self._position = 0.0
        self._phase = 0.0
        self._beat_index = 0
        self._next_index = -1
        self._jump_blend = 0.0
        self.flow = []
        self.used_edges = set()
        self._elapsed = 0.0
        self._jumps = 0
        self.update_state(playing=False, paused=False, busy=False)
        self.update_graph()
        self.positionChanged.emit()
        self.sync_media()

    @Slot(int)
    def seek(self, index, phase=0.0):
        if self.model and 0 <= index < len(self.model['neighbors']):
            self.seeks.put((str(self.model['cache']), index, phase))
            self._position = float(index) + phase
            self._phase = phase
            self.flow = []
            self.used_edges = set()
            self.update_graph()
            self.positionChanged.emit()

    def media_state(self):
        state = self.media_state_provider() if self.media_state_provider else None
        return state or dict(
            self._state,
            owner='jukebox',
            previous=bool(self.model),
            next=bool(self.playlist)
            and (
                self.queue_repeat == 'Todas'
                or self.queue_index + 1 < len(self.playlist)
            ),
        )

    def sync_media(self):
        if self.closed:
            return
        state = self.media_state()
        if state['playing']:
            self.media_timer.start()
        if (
            state['playing']
            and self.media is None
            and not self.media_failed
            and self.window is not None
            and os.name == 'nt'
        ):
            try:
                from windows_media import MediaControls

                self.media = MediaControls(
                    SimpleNamespace(winfo_id=lambda: int(self.window.winId()))
                )
            except (OSError, AttributeError):
                self.media_failed = True
        if self.media:
            for _ in range(8):
                try:
                    button = self.media.events.get_nowait()
                except queue.Empty:
                    break
                if self.media_command_handler and self.media_command_handler(button):
                    continue
                if button == 0 and (not self._state['playing'] or self.paused.is_set()):
                    self.playPause()
                elif (
                    button == 1 and self._state['playing'] and not self.paused.is_set()
                ):
                    self.playPause()
                elif button == 2:
                    self.stop()
                elif button == 6:
                    self.nextTrack()
                elif button == 7:
                    self.previousTrack()
            state = self.media_state()
            if hasattr(self.media, 'navigation'):
                self.media.navigation(
                    state.get('previous', False), state.get('next', False)
                )
            self.media.update(
                state['title'],
                state['artist'],
                state['playing'],
                state['paused'],
                state.get('cover', ''),
            )
        if not state['playing']:
            self.media_timer.stop()

    @Slot()
    def shutdown(self):
        self._effect_prepare_cancel.set()
        self.effect_prepare_timer.stop()
        if self.closed:
            return
        self.stop()
        self.clock_timer.stop()
        self.closed = True
        self.save_preferences()
        for cancel in self._queue_cancel.values():
            cancel.set()
        if self.media:
            self.media.close()
            self.media = None
        deadline = time.monotonic() + 2
        for worker in self.workers:
            worker.join(timeout=max(0, deadline - time.monotonic()))
        self._event.disconnect(self.handle_event)
        self.media_timer.timeout.disconnect(self.sync_media)
        self.save_timer.timeout.disconnect(self.save_preferences)
