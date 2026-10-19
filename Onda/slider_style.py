"""Shared round slider thumb, preserving ttk keyboard and pointer behavior."""
from tkinter import ttk
from PIL import Image, ImageDraw, ImageTk
from appearance import blend


def configure_sliders(root, colors, scale=1):
    style=ttk.Style(root)
    size=max(18,round(22*scale))
    key=(style.theme_use(),size)
    cache=getattr(root,'_slider_images',{})
    if key not in cache:
        images=[ImageTk.PhotoImage(Image.new('RGBA',(size,size)),master=root) for _ in range(4)]
        element=f'Onda{size}.Horizontal.Scale.slider'
        style.element_create(element,'image',images[0],('disabled',images[1]),('pressed',images[2]),('focus',images[3]),border=0,sticky='')
        track_image=ImageTk.PhotoImage(Image.new('RGBA',(512,size)),master=root)
        trough=f'Onda{size}.Horizontal.Scale.trough'
        style.element_create(trough,'image',track_image,border=(2,0,2,0),width=8,sticky='we')
        cache[key]=(element,images,trough,track_image);root._slider_images=cache
    element,images,trough,track_image=cache[key]
    for image,ink,focus in zip(images,(colors['accent'],colors['disabled'],colors['accent_hover'],colors['accent']),(False,False,False,True)):
        picture=Image.new('RGBA',(size*4,size*4));draw=ImageDraw.Draw(picture)
        inset=12
        draw.ellipse((inset,inset,size*4-inset-1,size*4-inset-1),fill=ink)
        if focus:draw.ellipse((2,2,size*4-3,size*4-3),outline=colors['text'],width=4)
        image.paste(picture.resize((size,size),Image.Resampling.LANCZOS))
    style.layout('Horizontal.TScale',[(trough,{'sticky':'we','children':[(element,{'side':'left','sticky':''})]})])
    track=blend(colors['bg'],colors['text'],.3) if colors['mode']=='Preto puro' else colors['line']
    picture=Image.new('RGBA',(512,size));ImageDraw.Draw(picture).rounded_rectangle((0,(size-4)//2,511,(size-4)//2+3),radius=2,fill=track)
    track_image.paste(picture)
    style.configure('Horizontal.TScale',background=colors['bg'],troughcolor=track,bordercolor=track,lightcolor=track,darkcolor=track,sliderrelief='flat')
    style.map('Horizontal.TScale',background=[('disabled',colors['bg']),('active',colors['bg'])])
