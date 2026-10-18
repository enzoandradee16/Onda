"""Desktop resource controls; defaults preserve existing behavior."""
import os
import subprocess

def cpu_threads():
    return max(1,os.cpu_count() or 1)

def thread_choices():
    return ('Automático',)+tuple(str(n) for n in range(1,cpu_threads()+1))

PRIORITIES=('Normal','Baixa','Acima do normal')
RESERVES={'Desativado':0,'512 MB':512,'1 GB':1024,'2 GB':2048,'4 GB':4096}
DEFAULTS={'conversion_threads':'Automático','worker_priority':'Normal','memory_reserve':'Desativado'}

def clean(values):
    choices={'worker_priority':PRIORITIES,'memory_reserve':RESERVES}
    result={key:value for key,value in values.items() if key in choices and isinstance(value,str) and value in choices[key]}
    value=values.get('conversion_threads')
    if value=='Automático':result['conversion_threads']=value
    elif isinstance(value,str) and value.isascii() and value.isdecimal() and len(value)<=4 and int(value)>0:
        result['conversion_threads']=str(min(int(value),cpu_threads()))
    return result

def snapshot(app):
    return {key:getattr(app,key).get() if hasattr(app,key) else default for key,default in DEFAULTS.items()}

def thread_args(config,default=None):
    value=clean(config).get('conversion_threads','Automático')
    if value=='Automático':return ['-threads',str(min(default,cpu_threads()))] if default else []
    count=int(value)
    return ['-threads',str(count),'-filter_threads',str(count),'-filter_complex_threads',str(count)] if count else []

def priority_flags(config):
    if os.name!='nt':return 0
    flag={'Baixa':'BELOW_NORMAL_PRIORITY_CLASS','Acima do normal':'ABOVE_NORMAL_PRIORITY_CLASS'}.get(config.get('worker_priority'))
    return getattr(subprocess,flag,0) if flag else 0

def available_memory_mb():
    if os.name!='nt':return None
    import ctypes
    class MemoryStatus(ctypes.Structure):
        _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(name,ctypes.c_ulonglong) for name in
            ('total_phys','avail_phys','total_page','avail_page','total_virtual','avail_virtual','avail_extended')]
    status=MemoryStatus();status.length=ctypes.sizeof(status)
    return status.avail_phys//(1024*1024) if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)) else None

def can_start(app):
    reserve=RESERVES.get(app.memory_reserve.get(),0) if hasattr(app,'memory_reserve') else 0
    available=available_memory_mb() if reserve else None
    return available is None or available>=reserve

def controls(app,parent):
    from tkinter import ttk
    from i18n import tr
    from i18n_tk import TranslatedCombobox
    ttk.Label(parent,text=tr('Uso de recursos'),font=('Segoe UI',13,'bold')).pack(anchor='w',pady=(0,12))
    ttk.Label(parent,text=tr('CPU detectada: {count} processadores lógicos.').replace('{count}',str(cpu_threads())),style='Muted.TLabel').pack(anchor='w',pady=(0,8))
    for key,label,choices in (
        ('concurrent_downloads','Downloads simultâneos',tuple(str(n) for n in range(1,16))),
        ('conversion_threads','Threads por conversão',thread_choices()),
        ('worker_priority','Prioridade das tarefas',PRIORITIES),
        ('memory_reserve','Aguardar quando a RAM livre ficar abaixo de',tuple(RESERVES))):
        ttk.Label(parent,text=tr(label)).pack(anchor='w',pady=(8,4))
        TranslatedCombobox(parent,textvariable=getattr(app,key),values=choices,state='readonly',width=28).pack(anchor='w',fill='x')
    ttk.Label(parent,text=tr('Menos downloads simultâneos e threads reduzem o consumo. A prioridade baixa favorece outros programas. As mudanças valem para novas tarefas; tarefas ativas continuam.'),style='Muted.TLabel',wraplength=480).pack(anchor='w',pady=(12,8))
    ttk.Label(parent,text=tr('O limite de RAM apenas adia novos downloads até haver memória livre. Não reserva RAM, não encerra tarefas e não limita o consumo total ou um percentual exato de CPU.'),style='Muted.TLabel',wraplength=480).pack(anchor='w')
