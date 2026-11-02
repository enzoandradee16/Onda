"""Keep online playback on the existing PCM output and transport controls."""

import threading

from jukebox import RATE, Cancelled
from online_audio import RecoveringNetworkAudio, ReadAheadAudio, resolve


class OnlinePlayback:
    def __init__(self, bridge):
        self.bridge = bridge
        self.position = 0.0
        self.reader = None
        self.lock = threading.Lock()
        self.seek_serial = 0
        self.pending_seek = None

    def cancel(self):
        with self.lock:
            self.pending_seek = None
            self.seek_serial += 1
            if self.reader:
                self.reader.cancel()

    def seek(self, seconds):
        with self.lock:
            self.seek_serial += 1
            self.position = seconds
            self.pending_seek = (
                (self.seek_serial, seconds) if self.bridge._state['playing'] else None
            )

    def _take_seek(self):
        with self.lock:
            request, self.pending_seek = self.pending_seek, None
            return request

    def _has_seek(self):
        with self.lock:
            return self.pending_seek is not None

    def start(self):
        bridge = self.bridge
        bridge.revision += 1
        start = self.position if self.position < bridge.sourceDuration else 0.0
        self.position = start
        with self.lock:
            self.pending_seek = None
            self.seek_serial += 1
            initial_serial = self.seek_serial
        bridge.cancelled = threading.Event()
        bridge.paused.clear()
        cancel = bridge.cancelled
        revision = bridge.revision
        descriptor = dict(bridge.model['_stream'])
        config = dict(bridge.config())
        folder = config.get('ffmpeg', '')
        record = (
            dict(bridge.playlist[bridge.queue_index].get('record') or {})
            if 0 <= bridge.queue_index < len(bridge.playlist)
            else {}
        )
        record.setdefault(
            'title', bridge.model.get('media_title') or bridge.model.get('title', '')
        )
        record.setdefault('artists', [bridge.model.get('media_artist', '')])
        bridge._fade_initial = False
        bridge.update_state(playing=True, paused=False, status='Reproduzindo…')
        bridge.media_timer.start()
        bridge.clock_timer.start()
        bridge.sync_media()

        def worker():
            reader = output = None
            try:
                from jukebox_audio import PcmOutput
                from jukebox_equalizer import Equalizer

                def refresh():
                    fresh = resolve(
                        config,
                        record,
                        cancel.is_set,
                        source_url=descriptor.get('source_url', ''),
                    )
                    if cancel.is_set():
                        raise Cancelled()
                    descriptor.update(fresh['_stream'])
                    bridge.emit(revision, 'stream_refreshed', fresh['_stream'])
                    return fresh['_stream']

                def make_reader(seconds):
                    if cancel.is_set():
                        raise Cancelled()
                    reserve = ReadAheadAudio(
                        RecoveringNetworkAudio(descriptor, folder, seconds, refresh)
                    )
                    with self.lock:
                        rejected = cancel.is_set()
                        if not rejected:
                            self.reader = reserve
                    if rejected:
                        reserve.close()
                        raise Cancelled()
                    return reserve

                def make_output(seconds, serial):
                    sink = PcmOutput(
                        progress=lambda frames: bridge.emit(
                            revision,
                            'stream_position',
                            (serial, seconds + frames / RATE),
                        )
                    )
                    sink.gain = bridge.playback_gain
                    sink.last_gain = 0.0
                    return sink

                def transport_cancelled():
                    if self._has_seek():
                        raise InterruptedError()
                    return cancel.is_set()

                reader_start = start
                reader = make_reader(start)
                output = make_output(start, initial_serial)
                equalizer = Equalizer(RATE)
                while not cancel.is_set():
                    request = self._take_seek()
                    if request:
                        serial, target = request
                        if not reader.seek(target - reader_start):
                            reader.close()
                            serial, target = self._take_seek() or request
                            reader_start = target
                            reader = make_reader(target)
                        output.close()
                        output = make_output(target, serial)
                        equalizer = Equalizer(RATE)
                    while output.control(cancel.is_set, bridge.paused.is_set):
                        if self._has_seek():
                            break
                        cancel.wait(0.02)
                    if self._has_seek():
                        continue
                    try:
                        pcm = reader.read(interrupted=self._has_seek)
                    except InterruptedError:
                        continue
                    if self._has_seek():
                        continue
                    if not pcm:
                        try:
                            while output.buffers:
                                output._drain(transport_cancelled, bridge.paused.is_set)
                        except InterruptedError:
                            continue
                        if self._has_seek():
                            continue
                        if not cancel.is_set():
                            bridge.emit(revision, 'finished', None)
                        break
                    output.gain = bridge.playback_gain
                    equalizer.configure(bridge._equalizer)
                    try:
                        output.write(
                            equalizer.process(pcm),
                            transport_cancelled,
                            bridge.paused.is_set,
                        )
                    except InterruptedError:
                        continue
            except Cancelled:
                pass
            except Exception:
                if not cancel.is_set():
                    bridge.emit(
                        revision,
                        'error',
                        'Não foi possível reproduzir o áudio online. Tente abrir a música novamente.',
                    )
            finally:
                if output:
                    output.close()
                with self.lock:
                    if self.reader is reader:
                        self.reader = None
                if reader:
                    reader.close()
                bridge.emit(revision, 'stopped', None)

        bridge.start_worker(worker)


class StreamPreparation:
    """An independent job: transport stays live until analysis and effects are ready."""

    def __init__(self, bridge):
        self.bridge = bridge
        self.cancelled = threading.Event()
        self.source = None
        self.model = None

    def cancel(self):
        self.cancelled.set()

    def start(self):
        bridge = self.bridge
        source = bridge.model
        if self.source is source and not self.cancelled.is_set():
            return
        self.cancel()
        self.cancelled = threading.Event()
        cancel = self.cancelled
        self.source = source
        self.model = None
        config = dict(bridge.config())
        bridge.update_state(effects_pending=True, effects_error='')

        def worker():
            from online_audio import prepare_stream
            from playback_effects import prepare as prepare_effects
            from jukebox import check

            try:
                model = self.model or prepare_stream(source, config, cancel.is_set)
                self.model = model
                while not cancel.is_set():
                    effects = dict(bridge._effects)
                    error = prepare_effects(model['cache'], effects, cancel.is_set)
                    if error:
                        raise ValueError(error)
                    check(cancel.is_set)
                    if effects == bridge._effects:
                        break
                check(cancel.is_set)
                self.effects = effects
                bridge.emit(0, 'stream_prepared', self)
            except Cancelled:
                pass
            except Exception as error:
                if not cancel.is_set():
                    bridge.emit(0, 'stream_prepare_error', (self, str(error)))

        self.retry = worker
        bridge.start_worker(worker)
