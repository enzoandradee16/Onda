def fixture(folder):
    from pathlib import Path
    from mobile_backend import _native
    from PIL import Image
    from audio_library import write_audio
    import subprocess
    root=Path(folder)/'history-fixture';root.mkdir(exist_ok=True)
    path=root/'song.mp3';cover=root/'cover.png'
    Image.new('RGB',(64,64),'blue').save(cover)
    subprocess.run([str(_native/'libffmpeg.so'),'-y','-f','lavfi','-i','sine=frequency=440:duration=1','-c:a','libmp3lame',str(path)],check=True,capture_output=True)
    write_audio(path,{'title':'History Song','artists':['History Artist'],'album':'History Album','release_date':'2026','genre':'House'},str(cover))
    return str(path)
