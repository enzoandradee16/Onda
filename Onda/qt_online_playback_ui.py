"""Keep online playback on the existing PCM output and transport controls."""

import threading
import time

from jukebox import RATE, Cancelled
from online_audio import RecoveringNetworkAudio, ReadAheadAudio, resolve
from progressive_audio_cache import ProgressiveAudioCache, CacheReadError


class OnlinePlayback:
    def __init__(self, bridge):
        self.bridge = bridge
        self.position = 0.0
        self.reader = None
        self.cache = None
        self.cache_model = None
        self.buffered = 0.0
        self.lock = threading.Lock()
        self.seek_serial = 0
        self.pending_seek = None
        self.outgoing = None
        self.worker_cancel = None
        self.fade_in = None
        self.fade_out = None
        self.fade_paused_at = None

    def pause_fade(self, paused):
        if self.fade_in is None and self.fade_out is None and self.outgoing is None:
            return
        now = time.monotonic()
        if paused and self.fade_paused_at is None:
            self.fade_paused_at = now
        elif not paused and self.fade_paused_at is not None:
            elapsed = now - self.fade_paused_at
            if self.fade_in is not None:
                self.fade_in += elapsed
            if self.fade_out is not None:
                self.fade_out += elapsed
            self.fade_paused_at = None
        old = self.outgoing
        if old:
            old.pause_fade(paused)

    def finish_overlap(self):
        old, self.outgoing = self.outgoing, None
        if old:
            old.cancel()
        self.fade_in = None
        self.fade_paused_at = None

    def gain(self):
        now = (
            self.fade_paused_at if self.fade_paused_at is not None else time.monotonic()
        )
        if self.fade_in is None and self.fade_out is None and self.outgoing is None:
            return 1.0
        seconds = self.bridge.transitionSeconds
        if self.fade_out is not None:
            value = max(0.0, min(1.0, 1 - (now - self.fade_out) / seconds))
            if value == 0:
                self.cancel()
            return value
        if self.fade_in is not None:
            value = min(1.0, (now - self.fade_in) / seconds)
            if value == 1:
                old, self.outgoing = self.outgoing, None
                if old:
                    old.cancel()
            return value
        return 0.0 if self.outgoing else 1.0

    def cancel(self):
        self.fade_in = self.fade_out = self.fade_paused_at = None
        if self.worker_cancel:
            self.worker_cancel.set()
        old, self.outgoing = self.outgoing, None
        if old:
            old.cancel()
        with self.lock:
            self.pending_seek = None
            self.seek_serial += 1
            if self.reader:
                self.reader.cancel()
            if self.cache:
                self.cache.cancel()

    def seek(self, seconds):
        self.finish_overlap()
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
            self.cache_model = bridge.model
            self.buffered = 0.0
        bridge.cancelled = threading.Event()
        bridge.paused.clear()
        cancel = bridge.cancelled
        self.worker_cancel = cancel
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
            reader = output = cache = None
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

                def network(seconds):
                    return RecoveringNetworkAudio(
                        dict(descriptor), folder, seconds, refresh
                    )

                try:
                    identity = (
                        descriptor.get('source_url')
                        or record.get('source_url')
                        or descriptor['url']
                    )
                    from stream_warmup import take

                    cache = take(bridge.model) or ProgressiveAudioCache(
                        identity,
                        bridge.sourceDuration,
                        network,
                        progress=lambda value: bridge.emit(
                            revision, 'stream_buffer', value
                        ),
                        automatic=config.get('automatic_cache_cleanup', True),
                    )
                    cache.progress = lambda value: bridge.emit(
                        revision, 'stream_buffer', value
                    )
                    with self.lock:
                        self.cache = cache
                    bridge.emit(revision, 'stream_buffer', cache.buffered_seconds)
                except (OSError, ValueError):
                    cache = None

                def make_reader(seconds, use_cache=True):
                    if cancel.is_set():
                        raise Cancelled()
                    cached = (
                        cache is not None
                        and use_cache
                        and (seconds == 0 or cache.covers(seconds))
                    )
                    if cached:
                        try:
                            cache.start()
                            source = cache.reader(seconds)
                        except OSError:
                            cached = False
                    if not cached:
                        source = network(seconds)
                    reserve = ReadAheadAudio(source)
                    reserve.cached_source = cached
                    if cached and (cache.complete or cache.covers(seconds + 1)):
                        reserve.warmup_blocks = 1
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
                    if (
                        cache is not None
                        and cache.complete
                        and not reader.cached_source
                    ):
                        next_position = reader_start + reader.cursor / (RATE * 4)
                        reader.close()
                        reader_start = next_position
                        reader = make_reader(next_position)
                    try:
                        pcm = reader.read(interrupted=self._has_seek)
                    except InterruptedError:
                        continue
                    except CacheReadError:
                        next_position = reader_start + reader.cursor / (RATE * 4)
                        reader.close()
                        reader_start = next_position
                        reader = make_reader(next_position, use_cache=False)
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
                    old = self.outgoing
                    if old is not None and self.fade_in is None:
                        self.fade_in = old.fade_out = time.monotonic()
                    output.gain = lambda: bridge.playback_gain() * self.gain()
                    equalizer.configure(bridge._equalizer)
                    try:
                        output.write(
                            equalizer.process(pcm),
                            transport_cancelled,
                            bridge.paused.is_set,
                        )
                    except InterruptedError:
                        continue
                    if cache is not None:
                        cache.start()
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
                self.finish_overlap()
                if output:
                    output.close()
                with self.lock:
                    if self.reader is reader:
                        self.reader = None
                if reader:
                    reader.close()
                if cache:
                    cache.close()
                    with self.lock:
                        if self.cache is cache:
                            self.cache = None
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
