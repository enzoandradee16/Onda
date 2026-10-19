"""Small function icons rendered from shapes; no external assets are required."""
import math


def icon_kind(title):
    title = title.casefold()
    for phrase, kind in (("equalizador", "settings"), ("equalizer", "settings"), ("ecualizador", "settings"), ("ajustar capa", "crop"), ("preparar áudio e vídeo", "download"), ("flac pelo navegador", "download"), ("editar áudio", "metadata"), ("lista da playlist", "metadata"), ("conectar spotify", "metadata"), ("boas-vindas", "help"), ("configurações", "settings"), ("detalhes dos downloads", "log"),
                         ("sobre o onda", "help"), ("metadados", "metadata"),
                         ("revisar antes", "metadata"), ("escolha a versão", "version"),
                         ("escolha o formato", "download"), ("fotos e vídeos", "media"),
                         ("arquivo já existe", "duplicate")):
        if phrase in title:
            return kind
    return None


def draw_icon(kind, size, colors=None):
    from PIL import Image, ImageDraw
    image = Image.new("RGBA", (96, 96))
    draw = ImageDraw.Draw(image)
    colors=colors or {}
    ink, pale, dark = colors.get("accent","#65dfbd"), colors.get("text","#eef3fa"), colors.get("bg","#10151e")
    draw.rounded_rectangle((2, 2, 94, 94), radius=22, fill=dark)
    if kind == "onda":
        for x,top,bottom in ((18,42,54),(32,28,68),(48,16,80),(64,28,68),(78,42,54)):
            draw.line((x,top,x,bottom),fill=ink,width=6)
            draw.ellipse((x-3,top-3,x+3,top+3),fill=ink)
            draw.ellipse((x-3,bottom-3,x+3,bottom+3),fill=ink)
    elif kind == "settings":
        for index in range(8):
            angle = index * math.pi / 4
            draw.line([(48 + math.cos(angle) * 24, 48 + math.sin(angle) * 24),
                       (48 + math.cos(angle) * 35, 48 + math.sin(angle) * 35)], fill=ink, width=12)
        draw.ellipse((22, 22, 74, 74), fill=ink)
        draw.ellipse((36, 36, 60, 60), fill=dark)
    elif kind == "help":
        draw.ellipse((16, 16, 80, 80), outline=ink, width=6)
        draw.arc((34, 28, 62, 54), 180, 455, fill=pale, width=6)
        draw.line((48, 52, 48, 60), fill=pale, width=6)
        draw.ellipse((45, 66, 51, 72), fill=pale)
    elif kind == "metadata":
        draw.line((42, 62, 42, 26, 70, 20, 70, 55), fill=ink, width=7)
        draw.ellipse((22, 54, 43, 70), fill=ink)
        draw.ellipse((50, 48, 71, 64), fill=ink)
        draw.line((26, 80, 70, 80), fill=pale, width=5)
    elif kind == "version":
        draw.polygon(((22, 20), (22, 68), (60, 44)), fill=ink)
        draw.line((48, 72, 58, 82, 78, 58), fill=pale, width=7)
    elif kind == "download":
        draw.line((48, 18, 48, 60), fill=ink, width=8)
        draw.line((28, 44, 48, 64, 68, 44), fill=ink, width=8)
        draw.line((22, 66, 22, 78, 74, 78, 74, 66), fill=pale, width=6)
    elif kind == "crop":
        draw.line((28, 16, 28, 68, 80, 68), fill=ink, width=7)
        draw.line((16, 28, 68, 28, 68, 80), fill=pale, width=7)
        draw.line((38, 57, 49, 44, 59, 53), fill=ink, width=5)
    elif kind == "media":
        draw.rounded_rectangle((16, 20, 80, 76), radius=5, outline=ink, width=6)
        draw.ellipse((28, 30, 40, 42), fill=pale)
        draw.line((22, 66, 42, 48, 54, 58, 68, 40, 76, 50), fill=ink, width=6)
    else:
        if kind == "duplicate":
            draw.rounded_rectangle((18, 16, 62, 66), radius=4, outline=pale, width=5)
        draw.rounded_rectangle((30, 28, 78, 82), radius=4, outline=ink, width=6)
        for y in (42, 54, 66):
            draw.line((40, y, 66, y), fill=pale, width=4)
    return image.resize((size, size), Image.Resampling.LANCZOS)


def apply_window_icon(window, colors=None, *, force=False):
    kind = icon_kind(window.title()) or "onda"
    if colors is None:
        manager=getattr(window._root(),"theme_manager",None)
        colors=getattr(manager,"colors",None) or {}
    root=window is window._root()
    key=(kind,colors.get("accent"),colors.get("text"),colors.get("bg"))
    if getattr(window,"_function_icon_key",None)==key:
        if force:
            window.iconphoto(root, *window._function_icons)
        return
    from PIL import ImageTk
    icons = [ImageTk.PhotoImage(draw_icon(kind, size, colors), master=window) for size in (16, 32, 48)]
    window.iconphoto(root, *icons)
    window._function_icons = icons  # Tk only stores the image names; keep Python references.
    window._function_icon_kind = kind
    window._function_icon_key = key
