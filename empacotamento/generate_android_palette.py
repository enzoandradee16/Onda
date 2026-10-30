"""Keep Android accents and launcher variants aligned with the desktop palette."""

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'Onda'))
from appearance import ACCENTS, THEME_MODES

NAMES = dict(
    zip(
        ACCENTS,
        (
            'Aqua',
            'Blue',
            'Purple',
            'Pink',
            'Orange',
            'Red',
            'Green',
            'Lime',
            'Yellow',
            'Gold',
            'Cyan',
            'Turquoise',
            'Indigo',
            'Lilac',
            'Coral',
            'Gray',
            'Mint',
            'Emerald',
            'Sky',
            'Petrol',
            'Magenta',
            'Wine',
            'Peach',
            'Brown',
        ),
    )
)


def generate():
    mobile = ROOT / 'Android/app/src/main/java/br/com/onda/mobile'
    path = mobile / 'MainActivity.kt'
    text = path.read_text(encoding='utf-8')
    modes = (
        'internal val appearanceModes=listOf('
        + ','.join(f'"{mode}"' for mode in THEME_MODES)
        + ')\n'
    )
    if 'internal val appearanceModes=' in text:
        text = re.sub(r'internal val appearanceModes=.*\n', modes, text, count=1)
    else:
        text = text.replace(
            'val accents=linkedMapOf(', modes + '\nval accents=linkedMapOf(', 1
        )
    for variable, constructor, index in (
        ('accents', 'linkedMapOf', 0),
        ('lightAccents', 'mapOf', 1),
    ):
        rows = ',\n'.join(
            f'    "{name}" to 0xFF{colors[index][1:].upper()}'
            for name, colors in ACCENTS.items()
        )
        text = re.sub(
            rf'val {variable}={constructor}\([\s\S]*?\)\n',
            f'val {variable}={constructor}(\n{rows}\n)\n',
            text,
            count=1,
        )
    path.write_text(text, encoding='utf-8')
    path = mobile / 'LauncherIcons.kt'
    text = path.read_text(encoding='utf-8')
    rows = ',\n'.join(
        f'        "{name}" to "{suffix}"' for name, suffix in NAMES.items()
    )
    text = re.sub(
        r'private val colors=linkedMapOf\([\s\S]*?\)',
        f'private val colors=linkedMapOf(\n{rows})',
        text,
        count=1,
    )
    path.write_text(text, encoding='utf-8')

    res = ROOT / 'Android/app/src/main/res'
    template = (res / 'drawable/launcher_wave_dark_aqua.xml').read_text(
        encoding='utf-8'
    )
    manifest = ROOT / 'Android/app/src/main/AndroidManifest.xml'
    manifest_text = manifest.read_text(encoding='utf-8')
    alias_template = re.search(
        r'    <activity-alias android:name="\.LauncherLightAqua".*?</activity-alias>',
        manifest_text,
        re.S,
    ).group()
    aliases = []
    for mode, background, vector_mode in (
        ('System', 'system_background', 'system'),
        ('Dark', 'background_dark', 'dark'),
        ('Light', 'background_light', 'light'),
        ('Black', 'background_black', 'dark'),
        ('White', 'background_white', 'light'),
    ):
        for name, suffix in NAMES.items():
            slug = suffix.lower()
            vector = f'launcher_wave_{vector_mode}_{slug}'
            color = (
                f'@color/launcher_system_{slug}'
                if vector_mode == 'system'
                else ACCENTS[name][vector_mode == 'light']
            )
            vector_path = res / f'drawable/{vector}.xml'
            if not vector_path.exists():
                vector_path.write_text(
                    re.sub(
                        r'android:strokeColor="[^"]*"',
                        f'android:strokeColor="{color}"',
                        template,
                    ),
                    encoding='utf-8',
                )
            icon_name = f'ic_onda_launcher_{mode.lower()}_{slug}'
            target = res / f'mipmap-anydpi-v26/{icon_name}.xml'
            if not target.exists():
                target.write_text(
                    f'<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n    <background android:drawable="@color/launcher_{background}"/>\n    <foreground android:drawable="@drawable/{vector}"/>\n    <monochrome android:drawable="@drawable/launcher_wave_monochrome"/>\n</adaptive-icon>\n',
                    encoding='utf-8',
                )
            alias = f'Launcher{mode}{suffix}'
            if f'android:name=".{alias}"' not in manifest_text:
                aliases.append(
                    alias_template.replace('LauncherLightAqua', alias).replace(
                        'ic_onda_launcher_light_aqua', icon_name
                    )
                )
    if aliases:
        manifest_text = manifest_text.replace(
            '</application>', '\n'.join(aliases) + '\n    </application>'
        )
        manifest.write_text(manifest_text, encoding='utf-8')
    for folder, index in (('values', 1), ('values-night', 0)):
        target = res / folder / 'launcher_colors.xml'
        text = target.read_text(encoding='utf-8')
        colors = {
            f'launcher_system_{NAMES[name].lower()}': pair[index]
            for name, pair in ACCENTS.items()
        }
        colors['launcher_background_white'] = '#ffffff'
        additions = ''.join(
            f'    <color name="{name}">{color.upper()}</color>\n'
            for name, color in colors.items()
            if f'name="{name}"' not in text
        )
        if additions:
            target.write_text(
                text.replace('</resources>', additions + '</resources>'),
                encoding='utf-8',
            )


if __name__ == '__main__':
    generate()
