"""Validated desktop shortcut preferences; no UI or download dependencies."""
import json
import re

DEFAULT_BINDINGS = {'<Control-l>': 'links', '<Control-j>': 'queue', '<Control-h>': 'history', '<Control-a>': 'select-all', '<Control-f>': 'search', '<Control-Return>': 'download', '<Control-KP_Enter>': 'download', '<Control-Shift-Return>': 'add', '<Control-Shift-KP_Enter>': 'add', '<F5>': 'start', '<Shift-F5>': 'stop', '<Control-r>': 'retry', '<Alt-Up>': 'up', '<Alt-Down>': 'down', '<Alt-Home>': 'prioritize', '<Alt-v>': 'view', '<Control-Shift-Delete>': 'clear', '<Control-o>': 'folder', '<Control-comma>': 'settings', '<Control-m>': 'metadata', '<Control-Shift-l>': 'log', '<Control-Shift-e>': 'failures', '<F1>': 'help', '<Control-Tab>': 'next', '<Control-Shift-Tab>': 'previous', '<Control-ISO_Left_Tab>': 'previous', '<Control-Up>': 'scroll-up', '<Control-Down>': 'scroll-down', '<Control-Key-1>': 'tab:0', '<Control-Key-2>': 'tab:1', '<Control-Key-3>': 'tab:2', '<Control-Key-4>': 'tab:3', '<Control-Key-5>': 'tab:4', '<Control-Key-6>': 'tab:5', '<Control-Key-7>': 'tab:6', '<Control-Key-8>': 'tab:7', '<Control-Key-9>': 'tab:8'}
PRIMARY = {}
for sequence, action in DEFAULT_BINDINGS.items():
    PRIMARY.setdefault(action, sequence)

def canonical(sequence):
    if not isinstance(sequence,str) or len(sequence)>70:
        raise ValueError("Atalho inválido.")
    match=re.fullmatch(r"<((?:(?:Control|Shift|Alt)-)*)(?:Key-)?([A-Za-z0-9_]+)>",sequence)
    if not match:raise ValueError("Atalho inválido.")
    mods=match[1].strip("-").split("-") if match[1] else []
    key=match[2]
    if len(mods)!=len(set(mods)):raise ValueError("Atalho inválido.")
    if key=="KP_Enter":key="Return"
    if key=="ISO_Left_Tab":
        key="Tab"
        if "Shift" not in mods:mods.append("Shift")
    if len(key)==1:key=key.lower()
    allowed={"Return","Tab","Up","Down","Left","Right","Home","End","Prior","Next","Delete","BackSpace","comma","space"}
    if not (key in allowed or re.fullmatch(r"F(?:[1-9]|1[0-9]|2[0-4])",key) or (len(key)==1 and key.isascii() and key.isalnum())):
        raise ValueError("Atalho inválido.")
    if not any(m in mods for m in ("Control","Alt")) and not key.startswith("F"):raise ValueError("Use Ctrl, Alt ou uma tecla de função.")
    return "<"+"-".join([m for m in ("Control","Alt","Shift") if m in mods]+[key])+">"

RESERVED={canonical(s) for s in ("<Alt-F4>","<Alt-Tab>","<Control-Alt-Delete>","<Control-c>","<Control-v>","<Control-x>","<Control-z>","<Control-y>","<Control-Shift-z>")}
# Fixed widget actions and native clipboard chords are not remappable.
RESERVED.update(("<Alt-a>","<Shift-F10>","<Shift-Delete>","<Shift-Insert>","<Control-Insert>"))

def validate_overrides(value):
    if isinstance(value,str):
        try:value=json.loads(value)
        except (ValueError,TypeError):raise ValueError("Atalho inválido.")
    if not isinstance(value,dict) or len(value)>len(PRIMARY):raise ValueError("Atalho inválido.")
    result={}
    for action,sequence in value.items():
        if action not in PRIMARY:raise ValueError("Atalho inválido.")
        if not isinstance(sequence,str):raise ValueError("Atalho inválido.")
        sequence=canonical(sequence) if sequence else ""
        if sequence in RESERVED:raise ValueError("Atalho reservado para edição de texto ou para o sistema.")
        if sequence!=canonical(PRIMARY[action]):result[action]=sequence
    used={}
    for action,default in PRIMARY.items():
        sequence=result.get(action,canonical(default))
        if sequence:
            if sequence in used:raise ValueError("Este atalho já está em uso.")
            used[sequence]=action
    return result

def load_overrides(value):
    try:return validate_overrides(value)
    except ValueError:return {}

def effective_bindings(value):
    overrides=load_overrides(value)
    result={sequence:action for sequence,action in DEFAULT_BINDINGS.items() if action not in overrides}
    result.update({sequence:action for action,sequence in overrides.items() if sequence})
    return result

def display_shortcut(sequence):
    return sequence.strip("<>").replace("Key-","").replace("Control-","Ctrl+").replace("Alt-","Alt+").replace("Shift-","Shift+").replace("Return","Enter").replace("comma",",") or "—"
