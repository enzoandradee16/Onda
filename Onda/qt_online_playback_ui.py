"""Keep online playback on the existing PCM output and transport controls."""

import threading

from jukebox import RATE, Cancelled
from online_audio import NetworkAudio, ReadAheadAudio


class OnlinePlayback:
    def __init__(self, bridge):
        self.bridge = bridge
        self.position = 0.0
        self.reader = None
        self.lock = threading.Lock()

    def cancel(self):
        with self.lock:
            if self.reader:
                self.reader.cancel()

    def start(self):
        bridge = self.bridge
        bridge.revision += 1
        start = self.position if self.position < bridge.sourceDuration else 0.0
        self.position = start
        bridge.cancelled = threading.Event()
        bridge.paused.clear()
        cancel = bridge.cancelled
        revision = bridge.revision
        descriptor = dict(bridge.model['_stream'])
        folder = bridge.config().get('ffmpeg', '')
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

                reader = ReadAheadAudio(NetworkAudio(descriptor, folder, start))
                with self.lock:
                    if cancel.is_set():
                        return
                    self.reader = reader
                equalizer = Equalizer(RATE)
                output = PcmOutput(
                    progress=lambda frames: bridge.emit(
                        revision, 'stream_position', start + frames / RATE
                    )
                )
                output.gain = bridge.playback_gain
                output.last_gain = 0.0
                while not cancel.is_set():
                    while output.control(cancel.is_set, bridge.paused.is_set):
                        cancel.wait(0.02)
                    pcm = reader.read()
                    if not pcm:
                        while output.buffers:
                            output._drain(cancel.is_set, bridge.paused.is_set)
                        if not cancel.is_set():
                            bridge.emit(revision, 'finished', None)
                        break
                    output.gain = bridge.playback_gain
                    equalizer.configure(bridge._equalizer)
                    output.write(
                        equalizer.process(pcm), cancel.is_set, bridge.paused.is_set
                    )
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
