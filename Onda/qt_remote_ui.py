"""Main-thread adapter for the experimental LAN controller."""

import queue
import base64
import hashlib
import threading
import uuid
import math
import time
import socket
from collections import deque
from pathlib import Path
from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer
from remote_control import RemoteServer, lan_addresses, transferable_record


class RemoteControl(QObject):
    changed = Signal()
    searchFinished = Signal(object)
    artworkFinished = Signal(object)

    def __init__(self, workspace):
        super().__init__(workspace)
        self.workspace = workspace
        self.server = None
        self.error = ''
        self._computer_name = socket.gethostname()[:80] or 'ONDA PC'
        self._artwork_source = None
        self._artwork_slots = threading.BoundedSemaphore(2)
        self._addresses = []
        self._transfer_source_key = None
        self._lyrics_next = 0.0
        self._lyrics_key = None
        self._lyrics_revision = ''
        self._queue_dirty = True
        self._handoff = {}
        self._handoff_closed = deque(maxlen=128)
        self._handoff_transport = 0
        self._handoff_entry = ''
        self._handoff_origin = ''
        self._handoff_deadline = 0.0
        self._search_cancel = threading.Event()
        self._search_slots = threading.BoundedSemaphore(2)
        self._search_revision = 0
        self._search_records = {}
        self._search_state = dict(busy=False, rows=[], message='', batch='')
        self.searchFinished.connect(self.search_finished)
        self.artworkFinished.connect(self.artwork_finished)
        self.workspace.bridge.queueChanged.connect(self.queue_changed)
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.tick)

    @Property('QVariantMap', notify=changed)
    def state(self):
        return dict(
            enabled=self.server is not None,
            name=self.server.name if self.server else self._computer_name,
            code=self.server.code if self.server else '',
            addresses=(
                [f'http://{ip}:{self.server.port}' for ip in self._addresses]
                if self.server
                else []
            ),
            paired=self.server.paired if self.server else False,
            connected=self.server.connected if self.server else False,
            error=self.error,
        )

    @Slot(str, result=str)
    def qrCode(self, address):
        if not self.server or address not in self.state['addresses']:
            return ''
        from remote_pairing import pairing_qr

        return pairing_qr(address, self.server.code)

    @Slot()
    def start(self):
        if self.server:
            return
        self.error = ''
        try:
            self.server = RemoteServer()
            self._lyrics_key = None
            self._lyrics_next = 0.0
            self.server.start()
            self._addresses = lan_addresses()
            self._artwork_source = None
            self._transfer_source_key = None
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
        if (
            self._handoff.get('status') in ('released', 'starting')
            and self._handoff_deadline
        ):
            self.handoff_command('handoff_cancel', dict(id=self._handoff['id']))
        self.cancel_handoff()
        self._handoff = {}
        self.timer.stop()
        if self.server:
            server, self.server = self.server, None
            self._artwork_source = None
            server.revoke()

            # Let connected phones receive an explicit revoked response before closing.
            def close_server():
                time.sleep(2)
                server.close()

            threading.Thread(target=close_server, daemon=True).start()
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
                if command.startswith('handoff_'):
                    self.handoff_command(command, value)
                elif command == 'volume':
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
                if command.startswith('handoff_'):
                    self.cancel_handoff()
                    self._handoff = dict(id=value['id'], status='error')
                self.workspace.notify(error)
        self.handoff_tick()
        state = bridge.state
        if self._queue_dirty:
            self.refresh_queue()
        self.refresh_artwork(state)
        self.refresh_transfer_source()
        self.refresh_lyrics()
        effects = self.workspace.options
        self.server.update(
            dict(
                protocol=1,
                device_name=self.server.name,
                shuffle=bridge.queueShuffle,
                repeat=bridge.queueRepeat,
                features=5,
                transfer_record=self.transfer_record(),
                handoff=dict(self._handoff),
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
                lyrics_revision=self._lyrics_revision,
                artwork_id=self.server.artwork_id,
                album=str(state.get('album', ''))[:500],
                cover_url=str(
                    (bridge.currentMetadata or {}).get('cover_url')
                    or (bridge.model or {}).get('cover_url')
                    or ''
                )[:2048],
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
        connected = self.server.connected
        if paired != getattr(self, '_paired', False) or connected != getattr(
            self, '_connected', False
        ):
            self._paired = paired
            self._connected = connected
            self.changed.emit()

    def refresh_lyrics(self):
        now = time.monotonic()
        if (
            now < self._lyrics_next
            and self._lyrics_key
            and self._lyrics_key[0] == self.track_id()
        ):
            return
        self._lyrics_next = now + 0.5
        frame = self.workspace.lyricsClock(True)
        key = (self.track_id(), frame.get('revision', 0))
        if key == self._lyrics_key:
            return
        self._lyrics_key = key
        lines = []
        remaining = 120000
        for row in self.workspace.lyricsDocument()[:2000]:
            seconds = row.get('time')
            if (
                type(seconds) not in (int, float)
                or not math.isfinite(seconds)
                or not 0 <= seconds <= 86400
            ):
                continue
            if remaining <= 0:
                break
            text = str(row.get('text', ''))[: min(300, remaining)]
            remaining -= len(text)
            lines.append(dict(time=seconds, text=text))
        self._lyrics_revision = uuid.uuid4().hex
        self.server.update_lyrics(
            dict(track_id=key[0], revision=self._lyrics_revision, lines=lines)
        )

    def refresh_transfer_source(self):
        bridge = self.workspace.bridge
        model = bridge.model or {}
        key = (id(bridge.model), self.track_id())
        if key == self._transfer_source_key:
            return
        self._transfer_source_key = key
        stream = model.get('_stream')
        source = dict(track_id=self.track_id())
        if self.transfer_record() and isinstance(stream, dict):
            url = stream.get('url', '')
            if (
                isinstance(url, str)
                and url.startswith(('https://', 'http://'))
                and len(url) <= 16384
            ):
                headers = {
                    str(k): str(v)
                    for k, v in (stream.get('headers') or {}).items()
                    if str(k).lower()
                    in ('user-agent', 'referer', 'origin', 'accept', 'accept-language')
                    and len(str(v)) <= 4096
                }
                source['model'] = dict(
                    _stream=dict(url=url, headers=headers),
                    duration=bridge.sourceDuration,
                    title=str(
                        model.get('title') or bridge.state.get('title') or 'ONDA'
                    ),
                    media_title=str(bridge.state.get('title') or ''),
                    media_artist=str(bridge.state.get('artist') or ''),
                    album=str(bridge.state.get('album') or ''),
                    cover_url=str(model.get('cover_url') or ''),
                )
        self.server.update_transfer(source)

    def transfer_record(self):
        bridge = self.workspace.bridge
        if not 0 <= bridge.queue_index < len(bridge.playlist):
            return transferable_record(getattr(bridge, '_selected_record', None))
        entry = bridge.playlist[bridge.queue_index]
        if entry.get('kind') != 'catalog':
            return None
        return transferable_record(entry.get('record'))

    def cancel_handoff(self):
        bridge = self.workspace.bridge
        identity = self._handoff_entry
        self._handoff_entry = ''
        self._handoff_deadline = 0.0
        if identity:
            index = next(
                (i for i, row in enumerate(bridge.playlist) if row['id'] == identity),
                -1,
            )
            if index >= 0 and index != bridge.queue_index:
                bridge.removeQueued(index)

    def handoff_command(self, command, value):
        bridge = self.workspace.bridge
        identity = value['id']
        if command == 'handoff_cancel' and self._handoff.get('id') != identity:
            self._handoff_closed.append(identity)
            return
        if identity in self._handoff_closed:
            return
        if command == 'handoff_prepare':
            if self._handoff.get('id') == identity:
                return
            if self._handoff.get('status') in ('preparing', 'ready', 'starting') or (
                self._handoff.get('status') == 'released' and self._handoff_deadline
            ):
                return
            self.cancel_handoff()
            before = {row['id'] for row in bridge.playlist}
            if not bridge.enqueueRecords([value['record']]):
                self._handoff = dict(id=identity, status='error')
                return
            self._handoff_entry = next(
                row['id'] for row in bridge.playlist if row['id'] not in before
            )
            bridge._queue_priority = self._handoff_entry
            bridge.prepare_next_queued()
            self._handoff_deadline = time.monotonic() + 120
            self._handoff_origin = self.track_id()
            self._handoff = dict(id=identity, status='preparing')
        elif command == 'handoff_cancel' and self._handoff.get('id') == identity:
            if (
                self._handoff.get('status') in ('starting', 'started')
                and self._handoff.get('track_id') == self.track_id()
                and bridge.state.get('playing')
                and not bridge.state.get('paused')
                and getattr(bridge, '_transport_revision', 0) == self._handoff_transport
            ):
                bridge.playPause()
            if (
                self._handoff.get('status') == 'released'
                and self._handoff.get('playing')
                and self._handoff.get('track_id') == self.track_id()
                and bridge.state.get('paused')
                and getattr(bridge, '_transport_revision', 0) == self._handoff_transport
            ):
                bridge.playPause()
            self.cancel_handoff()
            self._handoff = dict(id=identity, status='cancelled')
            self._handoff_closed.append(identity)
        elif (
            command == 'handoff_commit'
            and self._handoff.get('id') == identity
            and self._handoff.get('status') == 'ready'
        ):
            index = next(
                (
                    i
                    for i, row in enumerate(bridge.playlist)
                    if row['id'] == self._handoff_entry
                ),
                -1,
            )
            if (
                index < 0
                or self._handoff_entry not in bridge._prepared
                or self.track_id() != self._handoff_origin
                or time.monotonic() > self._handoff_deadline
            ):
                self._handoff = dict(id=identity, status='error')
                return
            model = bridge._prepared[self._handoff_entry]
            invalid_stream = bool(model.get('_stream')) and not bridge.can_stream()
            missing_cache = (
                not model.get('_stream')
                and 'cache' in model
                and not (Path(model['cache']) / 'analysis.json').is_file()
            )
            if invalid_stream or missing_cache:
                self.cancel_handoff()
                self._handoff = dict(id=identity, status='error')
                self._handoff_closed.append(identity)
                return
            bridge.stop(reset_timer=False)
            bridge.playlist[index]['restore_seconds'] = value['position']
            bridge.playQueued(index, auto_play=value['playing'])
            if self.track_id() != self._handoff_entry or not bridge.state.get('ready'):
                if getattr(bridge, '_autoplay_entry', None) == self._handoff_entry:
                    bridge._autoplay_entry = None
                self.cancel_handoff()
                self._handoff = dict(id=identity, status='error')
                self._handoff_closed.append(identity)
                return
            self._handoff = dict(
                id=identity,
                status='starting' if value['playing'] else 'started',
                track_id=self._handoff_entry,
                position=value['position'],
            )
            self._handoff_transport = getattr(bridge, '_transport_revision', 0)
            self._handoff_entry = ''
            self._handoff_deadline = time.monotonic() + 12 if value['playing'] else 0.0
        elif command == 'handoff_release':
            if self._handoff.get('id') != identity and (
                self._handoff.get('status') in ('preparing', 'ready', 'starting')
                or (
                    self._handoff.get('status') == 'released' and self._handoff_deadline
                )
            ):
                return
            if self._handoff.get('id') == identity:
                return
            if value['track_id'] != self.track_id() or not bridge.state.get('ready'):
                self._handoff = dict(id=identity, status='error')
                return
            self.cancel_handoff()
            playing = bool(bridge.state.get('playing')) and not bool(
                bridge.state.get('paused')
            )
            if playing:
                bridge.playPause()
            self._handoff_transport = getattr(bridge, '_transport_revision', 0)
            self._handoff_deadline = (
                time.monotonic() + 15 if value.get('ack_required') else 0.0
            )
            self._handoff = dict(
                id=identity,
                status='released',
                track_id=self.track_id(),
                position=bridge.sourcePosition,
                playing=playing,
            )

        elif (
            command == 'handoff_complete'
            and self._handoff.get('id') == identity
            and self._handoff.get('status') in ('released', 'started')
        ):
            if (
                self._handoff.get('track_id') != self.track_id()
                or getattr(bridge, '_transport_revision', 0) != self._handoff_transport
            ):
                self._handoff['status'] = 'error'
                self._handoff_closed.append(identity)
                return
            self._handoff['status'] = 'complete'
            self._handoff_deadline = 0.0
            self._handoff_closed.append(identity)

    def handoff_tick(self):
        bridge = self.workspace.bridge
        status = self._handoff.get('status')
        if status in ('released', 'starting'):
            same_track = self._handoff.get('track_id') == self.track_id()
            owns_transport = (
                getattr(bridge, '_transport_revision', 0) == self._handoff_transport
            )
            if not same_track or not owns_transport:
                self._handoff['status'] = 'error'
                self._handoff_closed.append(self._handoff['id'])
                self._handoff_deadline = 0.0
                return
            if (
                status == 'starting'
                and bridge.state.get('playing')
                and not bridge.state.get('paused')
                and abs(bridge.sourcePosition - self._handoff.get('position', 0))
                > 0.015
            ):
                self._handoff['status'] = 'started'
                self._handoff_deadline = 0.0
            elif self._handoff_deadline and time.monotonic() > self._handoff_deadline:
                self.handoff_command('handoff_cancel', dict(id=self._handoff['id']))
                self._handoff['status'] = 'error'
                return
        if not self._handoff_entry:
            return
        bridge = self.workspace.bridge
        entry = next(
            (row for row in bridge.playlist if row['id'] == self._handoff_entry), None
        )
        if (
            entry is None
            or entry.get('analysis') == 'error'
            or time.monotonic() > self._handoff_deadline
        ):
            self.cancel_handoff()
            self._handoff['status'] = 'error'
        elif self._handoff_entry in bridge._prepared:
            self._handoff['status'] = 'ready'

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
        cover = (
            state.get('cover')
            or (self.workspace.bridge.model or {}).get('_cover')
            or ''
        )
        key = (self.track_id(), cover)
        if key == self._artwork_source:
            return
        self._artwork_source = key
        if isinstance(cover, str) and cover.startswith(('https://', 'http://')):
            # Streaming covers are URLs, not base64. Never fetch on the Qt thread.
            self.server.update_artwork('', b'')
            if not self._artwork_slots.acquire(blocking=False):
                self._artwork_source = None
                return

            def work():
                try:
                    from catalog_ui import cover_png

                    raw = cover_png(cover, size=768) or b''
                except Exception:
                    raw = b''
                self._artwork_slots.release()
                if key == self._artwork_source:
                    try:
                        self.artworkFinished.emit((key, raw))
                    except RuntimeError:
                        pass

            self.workspace.launch_thread(work)
            return
        raw = b''
        try:
            if isinstance(cover, str) and cover.startswith('file:'):
                from PySide6.QtCore import QUrl
                from pathlib import Path

                path = Path(QUrl(cover).toLocalFile())
                if path.is_file() and path.stat().st_size <= 4 * 1024 * 1024:
                    raw = path.read_bytes()
            elif isinstance(cover, str):
                encoded = (
                    cover.split(',', 1)[1] if cover.startswith('data:image/') else cover
                )
                if len(encoded) <= 4 * 1024 * 1024:
                    raw = base64.b64decode(encoded, validate=True)
            elif isinstance(cover, bytes) and len(cover) <= 3 * 1024 * 1024:
                raw = cover
        except (ValueError, TypeError, OSError):
            pass
        self.artwork_finished((key, raw))

    def artwork_finished(self, payload):
        from PySide6.QtCore import QByteArray, QBuffer, QIODevice, Qt
        from PySide6.QtGui import QImage

        key, raw = payload
        if not self.server or key != self._artwork_source:
            return
        image = QImage.fromData(raw)
        if image.isNull():
            raw = b''
        else:
            if image.width() > 768 or image.height() > 768:
                image = image.scaled(
                    768, 768, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            data = QByteArray()
            buffer = QBuffer(data)
            buffer.open(QIODevice.WriteOnly)
            image.save(buffer, 'JPEG', 85)
            raw = bytes(data)
        identity = hashlib.sha256(raw).hexdigest()[:24] if raw else ''
        self.server.update_artwork(identity, raw)
