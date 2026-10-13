"""Measure an instrumented copy of the actual ONDA EXE, not user settings.

Only the copy's instance name, welcome flag and profiling hook differ from
production. No third-party monitoring dependency is required.
"""
import argparse
import ctypes as C
from ctypes import wintypes as W
import json
import os
from pathlib import Path
import random
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

REPO=Path(os.environ.get('ONDA_BENCH_REPO',str(Path(__file__).resolve().parents[1])))
OUT=Path(os.environ.get('ONDA_BENCH_OUT',str(Path(__file__).parent/'resultados')))
OUT.mkdir(exist_ok=True)

class PROCESSENTRY32W(C.Structure):
    _fields_=[('dwSize',W.DWORD),('cntUsage',W.DWORD),('th32ProcessID',W.DWORD),('th32DefaultHeapID',C.c_size_t),('th32ModuleID',W.DWORD),('cntThreads',W.DWORD),('th32ParentProcessID',W.DWORD),('pcPriClassBase',W.LONG),('dwFlags',W.DWORD),('szExeFile',W.WCHAR*260)]
class MEMORY(C.Structure):
    _fields_=[('cb',W.DWORD),('PageFaultCount',W.DWORD),('PeakWorkingSetSize',C.c_size_t),('WorkingSetSize',C.c_size_t),('QuotaPeakPagedPoolUsage',C.c_size_t),('QuotaPagedPoolUsage',C.c_size_t),('QuotaPeakNonPagedPoolUsage',C.c_size_t),('QuotaNonPagedPoolUsage',C.c_size_t),('PagefileUsage',C.c_size_t),('PeakPagefileUsage',C.c_size_t),('PrivateUsage',C.c_size_t)]
k=C.WinDLL('kernel32',use_last_error=True);ps=C.WinDLL('psapi',use_last_error=True)
k.CreateToolhelp32Snapshot.argtypes=[W.DWORD,W.DWORD];k.CreateToolhelp32Snapshot.restype=W.HANDLE
k.Process32FirstW.argtypes=[W.HANDLE,C.POINTER(PROCESSENTRY32W)];k.Process32NextW.argtypes=k.Process32FirstW.argtypes
k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE
k.CloseHandle.argtypes=[W.HANDLE]
k.GetProcessTimes.argtypes=[W.HANDLE,*([C.POINTER(W.FILETIME)]*4)]
ps.GetProcessMemoryInfo.argtypes=[W.HANDLE,C.POINTER(MEMORY),W.DWORD]

class Sampler:
    def __init__(self,pid):self.pid=pid;self.cpu={};self.samples=[]
    def sample(self):
        snap=k.CreateToolhelp32Snapshot(2,0);entry=PROCESSENTRY32W();entry.dwSize=C.sizeof(entry);parents={}
        try:
            success=k.Process32FirstW(snap,C.byref(entry))
            while success:
                parents[entry.th32ProcessID]=entry.th32ParentProcessID
                success=k.Process32NextW(snap,C.byref(entry))
        finally:k.CloseHandle(snap)
        group={self.pid}
        for _ in range(10):
            children={pid for pid,parent in parents.items() if parent in group}
            if children<=group:break
            group|=children
        rss=private=0
        for pid in group:
            handle=k.OpenProcess(0x410,False,pid)
            if not handle:continue
            try:
                ft=[W.FILETIME() for _ in range(4)]
                if k.GetProcessTimes(handle,*map(C.byref,ft)):
                    value=lambda t:(t.dwHighDateTime<<32)+t.dwLowDateTime
                    self.cpu[pid,value(ft[0])]=(value(ft[2])+value(ft[3]))/1e7
                mem=MEMORY();mem.cb=C.sizeof(mem)
                if ps.GetProcessMemoryInfo(handle,C.byref(mem),mem.cb):rss+=mem.WorkingSetSize;private+=mem.PrivateUsage
            finally:k.CloseHandle(handle)
        record={'t':time.perf_counter(),'rss_mb':rss/1048576,'private_mb':private/1048576,'cpu_s':sum(self.cpu.values())}
        self.samples.append(record)
        return record

PROBE=r'''
import functools,http.server,threading,time,random,shutil,subprocess,json,os
from pathlib import Path

def attach(app):
    target=Path(os.environ['ONDA_BENCH_LOG'])
    def emit(kind,**values):
        with target.open('a',encoding='utf-8') as f:f.write(json.dumps({'type':kind,'t':time.perf_counter(),**values})+'\n')
    # Wait until Tk has mapped and painted the normal window, then hide the
    # profiling copy during long downloads. The event loop remains active.
    def mapped():
        if not app.winfo_ismapped():app.after(10,mapped);return
        app.update_idletasks();emit('ready');app.withdraw()
        if os.environ['ONDA_BENCH_KIND']=='startup':app.after(1000,app.destroy)
        else:app.after(500,run)
    app.after_idle(mapped)
    def run():
        root=Path(os.environ['ONDA_BENCH_WORK']);root.mkdir(exist_ok=True)
        wav=root/'fixture.wav'
        subprocess.run([str(Path(os.environ['ONDA_BENCH_FFMPEG'])/'ffmpeg.exe'),'-v','error','-y','-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=60','-af','volume=0.1','-c:a','pcm_s16le',str(wav)],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_HEAD(self):self.headers_only()
            def headers_only(self):
                self.send_response(200);self.send_header('Content-Type','audio/wav');self.send_header('Content-Length',str(wav.stat().st_size));self.end_headers()
            def do_GET(self):
                self.headers_only()
                try:
                    with wav.open('rb') as f:
                        while chunk:=f.read(65536):
                            self.wfile.write(chunk);self.wfile.flush();time.sleep(65536/(2*1048576))
                except (BrokenPipeError,ConnectionResetError):pass
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        app.ffmpeg.set(os.environ['ONDA_BENCH_FFMPEG']);app.mode.set('Áudio · MP3 (320 kbps)');app.auto_match.set(True);app.review_metadata.set(False);app.duplicates.set('Manter ambos')
        # Keep heartbeat arrays inside the GUI process; the resource sampler
        # runs outside the measured process tree.
        lags=[];last=time.perf_counter()
        def heartbeat():
            nonlocal last
            now=time.perf_counter();lags.append(max(0,(now-last-.02)*1000));last=now;app.after(20,heartbeat)
        app.after(20,heartbeat)
        emit('idle_start');app.after(10000,lambda:idle_end())
        scenarios=[]
        for repeat in range(3):
            block=[(n,normal,repeat) for n in (1,2,4) for normal in (False,True)]
            random.Random(70+repeat).shuffle(block);scenarios.extend(block)
        cursor=0
        def idle_end():emit('idle_end');begin()
        def begin():
            nonlocal cursor,last
            if cursor==len(scenarios):server.shutdown();server.server_close();emit('finished');app.destroy();return
            workers,normal,repeat=scenarios[cursor];cursor+=1
            for key in list(app.jobs):app.tree.delete(key)
            app.jobs.clear();app.persist_queue();app.library.clear_history()
            folder=root/f'run-{cursor}';folder.mkdir();app.folder.set(str(folder));app.concurrent_downloads.set(str(workers));app.normalize_volume.set(normal)
            lags.clear();last=time.perf_counter()
            emit('trial_start',workers=workers,normalize=normal,repeat=repeat,trial=cursor)
            app.add([f'http://127.0.0.1:{server.server_port}/track-{j}.wav' for j in range(4)])
            app.start();app.after(20,check)
        def check():
            if app.running or app.active or app.parallel.workers:app.after(20,check);return
            states=[job['state'] for job in app.jobs.values()]
            emit('trial_end',trial=cursor,states=states,history=len(app.library.history()),lags_ms=lags.copy(),output_bytes=sum(p.stat().st_size for p in Path(app.folder.get()).glob('*.mp3')))
            if states!=['Concluído']*4:emit('failure',states=states);app.destroy();return
            app.after(800,begin)
'''

def metrics(samples,start,end):
    selected=[s for s in samples if start<=s['t']<=end]
    before=next((s for s in reversed(samples) if s['t']<=start),samples[0])
    after=next((s for s in samples if s['t']>=end),samples[-1])
    cpu=max(0,after['cpu_s']-before['cpu_s']);duration=end-start
    return {'wall_s':duration,'cpu_s':cpu,'cpu_one_core_pct':100*cpu/duration,'cpu_machine_pct':100*cpu/duration/os.cpu_count(),
            'peak_rss_mb':max((s['rss_mb'] for s in selected),default=0),'peak_private_mb':max((s['private_mb'] for s in selected),default=0),
            'median_rss_mb':statistics.median([s['rss_mb'] for s in selected]) if selected else 0}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--startup-only',action='store_true');args=parser.parse_args()
    python=REPO/'Portatil/_runtime/python/python.exe'
    env=dict(os.environ,PYTHONPATH=str(REPO/'Onda'))
    ffmpeg=subprocess.check_output([str(python),'-c','from ffmpeg_runtime import existing_folder; print(existing_folder() or "")'],env=env,text=True).strip()
    assert ffmpeg,'FFmpeg not prepared'
    root=Path(tempfile.mkdtemp(prefix='onda-performance-',dir=OUT))
    stage=root/'portable';stage.mkdir();(stage/'Onda').mkdir()
    for source in (REPO/'Portatil/Onda').glob('*'):
        if source.is_file():shutil.copyfile(source,stage/'Onda'/source.name)
    shutil.copyfile(REPO/'Portatil/Onda.exe',stage/'Onda.exe');shutil.copyfile(REPO/'Portatil/onda.ico',stage/'onda.ico')
    # A junction avoids copying a complete interpreter or modifying its files.
    subprocess.run(['powershell','-NoProfile','-Command',"New-Item -ItemType Junction -Path '"+str(stage/'_runtime').replace("'","''")+"' -Target '"+str(REPO/'Portatil/_runtime').replace("'","''")+"' | Out-Null"],check=True)
    instance=stage/'Onda/single_instance.py';instance.write_text(instance.read_text(encoding='utf-8').replace('C522DFD9-6BF4-4FE0-9CE4-5D3C5C88E470','Benchmark-'+root.name),encoding='utf-8')
    (stage/'Onda/benchmark_probe.py').write_text(PROBE,encoding='utf-8')
    entry=stage/'Onda/desktop_entry.py';text=entry.read_text(encoding='utf-8').replace('App(show_welcome=show_welcome)','App(show_welcome=False)')
    text=text.replace('    return app\n','    from benchmark_probe import attach\n    attach(app)\n    return app\n',1)
    entry.write_text(text,encoding='utf-8')
    results={'platform':'Windows','cpu_logical':os.cpu_count(),'fixture':{'tracks':4,'seconds_each':60,'source':'mono WAV 48kHz PCM16','destination':'MP3 320 kbps','bandwidth_mib_s_per_connection':2},'startup':[],'trials':[]}
    if args.startup_only and (OUT/'pc-results.json').exists():
        results=json.loads((OUT/'pc-results.json').read_text(encoding='utf-8'));results['startup']=[]
    all_samples=[]
    try:
        for i,kind in enumerate(['startup']*5+([] if args.startup_only else ['workloads'])):
            events=root/f'events-{i}.jsonl'
            env=dict(os.environ,LOCALAPPDATA=str(root/'settings'),ONDA_BENCH_LOG=str(events),ONDA_BENCH_KIND=kind,ONDA_BENCH_WORK=str(root/'work'),ONDA_BENCH_FFMPEG=ffmpeg)
            env['PATH']=ffmpeg+os.pathsep+env.get('PATH','')
            start=time.perf_counter();process=subprocess.Popen([str(stage/'Onda.exe')],env=env,cwd=stage)
            sampler=Sampler(process.pid);last_line=0;deadline=start+(900 if kind=='workloads' else 45)
            while process.poll() is None:
                sampler.sample()
                if time.perf_counter()>deadline:
                    subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True);raise TimeoutError(kind)
                if events.exists():
                    lines=events.read_text(encoding='utf-8').splitlines()
                    for line in lines[last_line:]:
                        event=json.loads(line)
                        if event['type'] in ('trial_start','trial_end'):print(json.dumps({k:v for k,v in event.items() if k!='lags_ms'}),flush=True)
                    last_line=len(lines)
                time.sleep(.1)
            sampler.sample();assert process.returncode==0,process.returncode
            data=[json.loads(line) for line in events.read_text(encoding='utf-8').splitlines()]
            ready=next(e for e in data if e['type']=='ready')
            results['startup'].append({'kind':kind,**metrics(sampler.samples,start,ready['t'])})
            if kind=='workloads':
                idle=[e for e in data if e['type'] in ('idle_start','idle_end')]
                results['idle']=metrics(sampler.samples,idle[0]['t'],idle[1]['t'])
                for begin,end in zip([e for e in data if e['type']=='trial_start'],[e for e in data if e['type']=='trial_end']):
                    assert end['states']==['Concluído']*4,end
                    lag=sorted(end['lags_ms'])
                    results['trials'].append({k:begin[k] for k in ('workers','normalize','repeat','trial')}|metrics(sampler.samples,begin['t'],end['t'])|{'ui_lag_p95_ms':lag[int((len(lag)-1)*.95)] if lag else 0,'ui_lag_max_ms':max(lag,default=0),'output_bytes':end['output_bytes']})
            all_samples.append(sampler.samples)
            (OUT/'pc-results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
            print(f'Finished {kind} {i+1}; startup {ready["t"]-start:.3f}s',flush=True)
        (OUT/('pc-startup-samples.json' if args.startup_only else 'pc-samples.json')).write_text(json.dumps(all_samples),encoding='utf-8')
    finally:
        # Remove the checked junction itself, never recurse through the runtime.
        junction=stage/'_runtime'
        if junction.exists():os.rmdir(junction)
        if root.resolve().is_relative_to(OUT.resolve()):shutil.rmtree(root)

if __name__=='__main__':main()
