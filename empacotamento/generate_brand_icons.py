"""Regenerate branded vectors and the multi-resolution Windows icon from one path."""

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'Onda'))
from brand_mark import SVG_PATH, STROKE, icon


def generate():
    res = ROOT / 'Celular/app/src/main/res'
    vectors = list((res / 'drawable').glob('launcher_wave_*.xml'))
    for target in vectors:
        text = target.read_text(encoding='utf-8')
        text = re.sub(
            r'<group [^>]*>',
            '<group android:translateX="24" android:translateY="34.8" android:scaleX="0.6" android:scaleY="0.6">',
            text,
        )
        text = re.sub(
            r'android:strokeWidth="[^"]*"', f'android:strokeWidth="{STROKE}"', text
        )
        text = re.sub(
            r'android:pathData="[^"]*"', f'android:pathData="{SVG_PATH}"', text
        )
        target.write_text(text, encoding='utf-8')
    template = (res / 'drawable/launcher_wave_dark_pink.xml').read_text(
        encoding='utf-8'
    )
    for name, color in [('monochrome', '#FFFFFFFF'), ('contrast', '#FFFFFF00')]:
        (res / f'drawable/launcher_wave_{name}.xml').write_text(
            re.sub(
                r'android:strokeColor="[^"]*"',
                f'android:strokeColor="{color}"',
                template,
            ),
            encoding='utf-8',
        )
    (res / 'values/brand_mark.xml').write_text(
        f'<resources>\n    <string name="onda_brand_path" translatable="false">{SVG_PATH}</string>\n</resources>\n',
        encoding='utf-8',
    )
    notification = f'''<vector xmlns:android="http://schemas.android.com/apk/res/android" android:width="24dp" android:height="24dp" android:viewportWidth="100" android:viewportHeight="100">
    <group android:translateY="18">
        <path android:fillColor="@android:color/transparent" android:strokeColor="#FFFFFFFF" android:strokeWidth="{STROKE}" android:strokeLineCap="round" android:strokeLineJoin="round" android:pathData="{SVG_PATH}"/>
    </group>
</vector>
'''
    (res / 'drawable/ic_onda_notification.xml').write_text(
        notification, encoding='utf-8'
    )
    contrast = res / 'mipmap-anydpi-v26/ic_onda_launcher_contrast.xml'
    contrast.write_text(
        '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n    <background android:drawable="@color/launcher_background_black"/>\n    <foreground android:drawable="@drawable/launcher_wave_contrast"/>\n</adaptive-icon>\n',
        encoding='utf-8',
    )
    for target in (res / 'mipmap-anydpi-v26').glob('ic_onda_launcher_*.xml'):
        text = target.read_text(encoding='utf-8')
        if '<monochrome' not in text:
            text = text.replace(
                '</adaptive-icon>',
                '    <monochrome android:drawable="@drawable/launcher_wave_monochrome"/>\n</adaptive-icon>',
            )
        target.write_text(text, encoding='utf-8')
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 64"><path fill="none" stroke="#79e2c4" stroke-width="{STROKE}" stroke-linecap="round" stroke-linejoin="round" d="{SVG_PATH}"/></svg>\n'
    (ROOT / 'Onda/assets/onda-mark.svg').write_text(svg, encoding='utf-8')
    (ROOT / 'docs/onda-site/assets/onda.svg').write_text(svg, encoding='utf-8')
    output = ROOT / 'Portatil/onda.ico'
    if output.parent.is_dir():
        icon(256).save(
            output,
            format='ICO',
            sizes=[(size, size) for size in (16, 24, 32, 48, 64, 128, 256)],
        )
    print(
        f'Brand vectors regenerated: {len(vectors)} color variants, launcher masks, notification and Windows ICO.'
    )


if __name__ == '__main__':
    generate()
