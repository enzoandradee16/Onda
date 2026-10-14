"""Local square cover cropper with a bounded preview and temporary output."""
from i18n import tr
from i18n_tk import display_var
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from PIL import Image, ImageOps, ImageTk


def crop_box(width, height, zoom=1.0, x=0.0, y=0.0):
    """Offsets are source pixels from the image center; clamp every edge."""
    side = min(width, height) / max(1.0, min(4.0, zoom))
    left = max(0.0, min(width-side, (width-side)/2-x))
    top = max(0.0, min(height-side, (height-side)/2-y))
    return left, top, left+side, top+side


class CoverCropper(tk.Toplevel):
    def __init__(self, parent, source, destination, accepted):
        with Image.open(source) as opened:
            if opened.width * opened.height > 40_000_000:
                raise ValueError('Escolha uma imagem de até 40 megapixels.')
            opened.thumbnail((2048, 2048))
            self.image = ImageOps.exif_transpose(opened).convert('RGBA')
        super().__init__(parent)
        self.title(tr('ONDA • Ajustar capa')); self.transient(parent.winfo_toplevel())
        self.resizable(False, False)
        self.destination=Path(destination); self.accepted=accepted
        self.zoom=tk.DoubleVar(value=1.0); self.x=self.y=0.0; self.drag=None
        body=ttk.Frame(self,padding=16);body.pack(fill='both',expand=True)
        ttk.Label(body,text=tr('Ajustar capa'),font=('Segoe UI',16,'bold')).pack(anchor='w')
        ttk.Label(body,text=tr('Arraste a imagem para mover e ajuste o zoom.'),wraplength=320).pack(anchor='w',pady=(4,12))
        self.canvas=tk.Canvas(body,width=320,height=320,highlightthickness=1,background='#191f27',cursor='fleur')
        self.canvas.pack()
        self.canvas.bind('<ButtonPress-1>',lambda e:setattr(self,'drag',(e.x,e.y)))
        self.canvas.bind('<B1-Motion>',self.move)
        self.canvas.bind('<ButtonRelease-1>',lambda e:setattr(self,'drag',None))
        ttk.Label(body,text=tr('Zoom')).pack(anchor='w',pady=(12,0))
        ttk.Scale(body,from_=1,to=4,variable=self.zoom,command=lambda _:self.render()).pack(fill='x')
        self.error=tk.StringVar();ttk.Label(body,textvariable=display_var(self.error),wraplength=320).pack(fill='x')
        actions=ttk.Frame(body);actions.pack(fill='x',pady=(8,0))
        ttk.Button(actions,text=tr('Redefinir'),command=self.reset).pack(side='left')
        ttk.Button(actions,text=tr('Cancelar'),command=self.destroy).pack(side='left',padx=6)
        ttk.Button(actions,text=tr('Aplicar capa'),style='Accent.TButton',command=self.apply).pack(side='right')
        self.bind('<Escape>',lambda _:self.destroy());self.render();self.grab_set()

    def bounds(self):
        box=crop_box(*self.image.size,self.zoom.get(),self.x,self.y)
        self.x=(self.image.width-box[2]-box[0])/2
        self.y=(self.image.height-box[3]-box[1])/2
        return box

    def render(self):
        self.photo=ImageTk.PhotoImage(self.image.resize((320,320),Image.Resampling.BILINEAR,box=self.bounds()),master=self)
        self.canvas.delete('all');self.canvas.create_image(0,0,anchor='nw',image=self.photo)
        for position in (320/3,640/3):
            self.canvas.create_line(position,0,position,320,fill='#ffffff',dash=(3,5))
            self.canvas.create_line(0,position,320,position,fill='#ffffff',dash=(3,5))

    def move(self,event):
        if self.drag is None:return
        ratio=min(self.image.size)/self.zoom.get()/320
        self.x+=(event.x-self.drag[0])*ratio;self.y+=(event.y-self.drag[1])*ratio
        self.drag=(event.x,event.y);self.render()

    def reset(self):
        self.zoom.set(1);self.x=self.y=0;self.render()

    def apply(self):
        try:
            box=self.bounds();size=max(1,min(1200,round(box[2]-box[0])))
            self.image.resize((size,size),Image.Resampling.LANCZOS,box=box).save(self.destination,'PNG')
            self.accepted(str(self.destination));self.destroy()
        except Exception as error:self.error.set(str(error))
