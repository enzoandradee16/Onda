"""Copy product documentation without website sources or historical build reports."""

from pathlib import Path
import re
import shutil


def copy_docs(root, output):
    root, output = Path(root), Path(output)
    shutil.copytree(
        root / 'docs', output,
        ignore=shutil.ignore_patterns(
            'onda-site', 'design', 'IDEIAS-FUTURAS.md', 'ANDROID-ICONE.md',
            'VALIDACAO-RELEASE-*.md', '__pycache__',
        ),
    )
    index = output / 'GUIAS.md'
    text = index.read_text(encoding='utf-8')
    text = re.sub(r'## Planejamento\n.*?(?=## Referências técnicas)', '', text, flags=re.S)
    text = '\n'.join(
        line for line in text.splitlines()
        if '../Android/' not in line
    ) + '\n'
    index.write_text(text, encoding='utf-8')
