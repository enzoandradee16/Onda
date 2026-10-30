"""Main-thread adapter for the experimental LAN controller."""

import queue
import base64
import hashlib
import threading
import uuid
import math
from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer
from remote_control import RemoteServer, lan_addresses


class RemoteControl(QObject):
    changed = Signal()
    searchFinished = Signal(object)

    def __init__(self, workspace):
        super().__init__(workspace)
        self.workspace = workspace
        self.server = None
        self.error = ''
        self._artwork_source = None
        self._addresses = []
        self._queue_dirty = True
        self._search_cancel = threading.Event()
        self._search_slots = threading.BoundedSemaphore(2)
        self._search_revision = 0
        self._search_records = {}
        self._search_state = dict(busy=False, rows=[], message='', batch='')
        self.searchFinished.connect(self.search_finished)
        self.workspace.bridge.queueChanged.connect(self.queue_changed)
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.tick)

    @Property('QVariantMap', notify=changed)
    def state(self):
        return dict(
            enabled=self.server is not None,
            code=self.server.code if self.server else '',
            addresses=(
                [f'http://{ip}:{self.server.port}' for ip in self._addresses]
                if self.server
                else []
            ),
            paired=self.server.paired if self.server else False,
            error=self.error,
        )

    @Slot()
    def start(self):
        if self.server:
            return
        self.error = ''
        try:
            self.server = RemoteServer()
            self.server.start()
            self._addresses = lan_addresses()
            self._artwork_source = None
            self.refresh_queue()
            self.tick()
            self.timer.start()
        except OSError:
            self.server = None
            self.error = 'Não foi possível iniciar o controle remoto.'
        self.changed.emit()

    @Slot()
    def stop(self):
        self._search_cancel.set()
        self._search_revision += 1
        self._search_state = dict(busy=False, rows=[], message='', batch='')
        self._search_records = {}
        self.timer.stop()
        if self.server:
            self.server.close()
            self.server = None
        self.changed.emit()

    def tick(self):
        if not self.server:
            return
        bridge = self.workspace.bridge
        for _ in range(8):
            try:
                command, value = self.server.commands.get_nowait()
            except queue.Empty:
                break
            try:
                if command == 'volume':
                    params = bridge.playbackParams
                    bridge.setParams(
                        params['variation'], params['smooth'], value, params['normal']
                    )
                elif command == 'toggle':
                    bridge.playPause()
                elif command == 'play':
                    if not bridge.state.get('playing') or bridge.state.get('paused'):
                        bridge.playPause()
                elif command == 'pause':
                    if bridge.state.get('playing') and not bridge.state.get('paused'):
                        bridge.playPause()
                elif command == 'next':
                    bridge.nextTrack()
                elif command == 'previous':
                    bridge.previousTrack()
                elif command == 'shuffle':
                    bridge.setQueueShuffle(value)
                elif command == 'repeat':
                    bridge.setQueueRepeat(value)
                elif command == 'effects':
                    keys = {
                        'enabled': 'effectsEnabled',
                        'speed': 'speed',
                        'reverb': 'reverb',
                        'keep_pitch': 'keep_pitch',
                    }
                    self.workspace.options.update(
                        {keys[key]: item for key, item in value.items()}
                    )
                    self.workspace.sync_unified_effects()
                    self.workspace.optionsChanged.emit()
                elif command == 'jukebox':
                    params = dict(bridge.playbackParams, **value)
                    bridge.setParams(
                        params['variation'],
                        params['smooth'],
                        params['volume'],
                        params['normal'],
                    )
                elif command == 'search':
                    self.search(value)
                elif command == 'search_cancel':
                    self._search_cancel.set()
                    self._search_revision += 1
                    self._search_records = {}
                    self._search_state = dict(busy=False, rows=[], message='', batch='')
                elif command == 'search_add':
                    records = self._search_records.pop(value, [])
                    if records:
                        bridge.enqueueRecords(records)
                        if value == self._search_state['batch']:
                            self._search_records = {}
                            self._search_state = dict(
                                busy=False, rows=[], message='', batch=''
                            )
                        else:
                            self._search_state['rows'] = [
                                row
                                for row in self._search_state['rows']
                                if row['id'] != value
                            ]
                            batch = self._search_records.get(
                                self._search_state['batch'], []
                            )
                            batch[:] = [
                                row
                                for row in batch
                                if all(row is not added for added in records)
                            ]
                elif command == 'queue_clear':
                    bridge.clearPlaybackQueue()
                elif command == 'seek':
                    if value['track_id'] == self.track_id():
                        bridge.seekSeconds(min(value['value'], bridge.sourceDuration))
                elif command.startswith('queue_'):
                    index = next(
                        (
                            i
                            for i, row in enumerate(bridge.playlist)
                            if row['id'] == value['track_id']
                        ),
                        -1,
                    )
                    if index >= 0:
                        if command == 'queue_play':
                            bridge.playQueued(index)
                        elif command == 'queue_remove':
                            bridge.removeQueued(index)
                        elif command == 'queue_move':
                            bridge.moveQueued(index, value['value'])
                        elif command == 'queue_move_to':
                            target = next(
                                (
                                    i
                                    for i, row in enumerate(bridge.playlist)
                                    if row['id'] == value['value']
                                ),
                                -1,
                            )
                            if target >= 0:
                                bridge.moveQueued(index, target - index)
            except Exception as error:
                self.workspace.notify(error)
        state = bridge.state
        if self._queue_dirty:
            self.refresh_queue()
        self.refresh_artwork(state)
        effects = self.workspace.options
        self.server.update(
            dict(
                protocol=1,
                device_name=self.server.name,
                shuffle=bridge.queueShuffle,
                repeat=bridge.queueRepeat,
                features=3,
                title=str(state.get('title', ''))[:500],
                artist=str(state.get('artist', ''))[:500],
                ready=bool(state.get('ready')),
                playing=bool(state.get('playing')) and not bool(state.get('paused')),
                busy=bool(state.get('busy')),
                volume=round(bridge.playbackParams['volume']),
                track_id=self.track_id(),
                duration=bridge.sourceDuration,
                position=bridge.sourcePosition,
                speed=(
                    effects.get('speed', 100) / 100
                    if effects.get('effectsEnabled')
                    and not state.get('effects_pending')
                    else 1
                ),
                queue_revision=self.server.queue_revision,
                artwork_id=self.server.artwork_id,
                album=str(state.get('album', ''))[:500],
                effects=dict(
                    enabled=bool(effects.get('effectsEnabled')),
                    speed=effects.get('speed', 85),
                    reverb=effects.get('reverb', 25),
                    keep_pitch=bool(effects.get('keep_pitch')),
                ),
                effects_pending=bool(state.get('effects_pending')),
                jukebox={
                    key: bridge.playbackParams[key]
                    for key in ('variation', 'smooth', 'normal')
                },
                search=self._search_state,
            )
        )
        paired = self.server.paired
        if paired != getattr(self, '_paired', False):
            self._paired = paired
            self.changed.emit()

    def track_id(self):
        bridge = self.workspace.bridge
        if 0 <= bridge.queue_index < len(bridge.playlist):
            return bridge.playlist[bridge.queue_index]['id']
        model = bridge.model or {}
        source = str(model.get('cache') or model.get('source') or '')
        return hashlib.sha256(source.encode()).hexdigest()[:32] if source else ''

    def queue_changed(self):
        self._queue_dirty = True

    def refresh_queue(self):
        if not self.server:
            return
        self._queue_dirty = False
        rows = []
        recent = {
            identity: rank
            for rank, identity in enumerate(
                dict.fromkeys(reversed(self.workspace.bridge._queue_history))
            )
        }
        for entry in self.workspace.bridge.playlist:
            record = entry.get('record') or {}
            cover = record.get('cover_url') or entry.get('cover') or ''
            rows.append(
                dict(
                    id=entry['id'],
                    title=str(entry.get('title') or '')[:500],
                    artist=str(entry.get('artist') or '')[:500],
                    duration=entry.get('duration') or 0,
                    cover=(
                        cover
                        if isinstance(cover, str)
                        and cover.startswith('https://')
                        and len(cover) <= 2048
                        else ''
                    ),
                    preparation=str(entry.get('analysis') or ''),
                    recent_rank=recent.get(entry['id'], -1),
                )
            )
        self.server.update_queue(rows)

    def search(self, query):
        # A bounded background worker uses the same resolver as the desktop queue.
        if self._search_state['busy']:
            return
        if not self._search_slots.acquire(blocking=False):
            self._search_state['message'] = 'Aguarde o comando anterior.'
            return
        self._search_cancel.set()
        cancel = self._search_cancel = threading.Event()
        self._search_revision += 1
        revision = self._search_revision
        config = dict(self.workspace.config(), query=query.strip())
        self._search_records = {}
        self._search_state = dict(busy=True, rows=[], message='', batch='')

        def work():
            try:
                from qt_operations_ui import perform

                result = perform(
                    'playback_input', config, cancel, lambda *args, **kwargs: None
                )
            except Exception as error:
                result = dict(tracks=[], message=str(error)[:500])
            finally:
                self._search_slots.release()
            if not cancel.is_set():
                self.searchFinished.emit((revision, result))

        self.workspace.launch_thread(work)

    def search_finished(self, payload):
        revision, result = payload
        if not self.server or revision != self._search_revision:
            return
        records = result.get('tracks', [])[:5000]
        if result.get('is_collection'):
            records = [
                dict(row, _queue_collection=result.get('title') or 'Playlist')
                for row in records
            ]
        rows = []
        self._search_records = {}
        for record in records[:100]:
            identity = uuid.uuid4().hex
            self._search_records[identity] = [record]
            try:
                duration = float(record.get('duration_ms') or 0) / 1000 or float(
                    record.get('duration') or 0
                )
                duration = (
                    max(0, min(86400, duration)) if math.isfinite(duration) else 0
                )
            except (ValueError, TypeError, OverflowError):
                duration = 0
            artists = record.get('artists') or []
            artist = (
                ', '.join(str(item) for item in artists)
                if isinstance(artists, list)
                else str(artists)
            )
            rows.append(
                dict(
                    id=identity,
                    title=str(record.get('title') or '')[:500],
                    artist=artist[:500],
                    album=str(record.get('album') or '')[:500],
                    cover=str(record.get('cover_url') or '')[:2048],
                    duration=duration,
                )
            )
        batch = uuid.uuid4().hex if result.get('is_collection') and records else ''
        if batch:
            self._search_records[batch] = records
        self._search_state = dict(
            busy=False,
            rows=rows,
            message=str(
                result.get('message') or ('' if rows else 'Nenhuma música encontrada.')
            )[:500],
            batch=batch,
        )

    def refresh_artwork(self, state):
        from PySide6.QtCore import QByteArray, QBuffer, QIODevice, Qt
        from PySide6.QtGui import QImage

        cover = state.get('cover') or ''
        if not isinstance(cover, str) or not cover.startswith('data:image/'):
            cover = (self.workspace.bridge.model or {}).get('_cover') or cover
        key = (self.track_id(), cover)
        if key == self._artwork_source:
            return
        self._artwork_source = key
        raw = b''
        try:
            if isinstance(cover, str):
                encoded = (
                    cover.split(',', 1)[1] if cover.startswith('data:image/') else cover
                )
                if len(encoded) <= 4 * 1024 * 1024:
                    raw = base64.b64decode(encoded, validate=True)
            elif isinstance(cover, bytes) and len(cover) <= 3 * 1024 * 1024:
                raw = cover
            image = QImage.fromData(raw)
            if not image.isNull():
                if image.width() > 768 or image.height() > 768:
                    image = image.scaled(
                        768, 768, Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                data = QByteArray()
                buffer = QBuffer(data)
                buffer.open(QIODevice.WriteOnly)
                image.save(buffer, 'JPEG', 85)
                raw = bytes(data)
            else:
                raw = b''
        except (ValueError, TypeError):
            raw = b''
        identity = hashlib.sha256(raw).hexdigest()[:24] if raw else ''
        self.server.update_artwork(identity, raw)
