"""Prepare local official artifacts without publishing or changing prior releases.

Run windows first, build/sign both Android ABIs separately, then run finalize.
Signing keys are deliberately outside this workflow and outside the archives.
"""

import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import zipfile
from build_installer import build as build_installer

ROOT = Path(__file__).resolve().parents[1]
VERSION = re.search(
    r"VERSION = '([^']+)'", (ROOT / 'Onda/app_version.py').read_text()
).group(1)
ANDROID_VERSION_CODE = int(
    re.search(
        r'\bversionCode\s*=\s*(\d+)',
        (ROOT / 'Android/app/build.gradle.kts').read_text(encoding='utf8'),
    ).group(1)
)
WORK = ROOT / 'diagnosticos/resultados' / ('release-' + VERSION)
BUNDLE = WORK / 'portable'
RELEASE = ROOT / 'Release' / VERSION


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8'
    )


def run(args, **kwargs):
    return subprocess.run(list(map(str, args)), check=True, cwd=ROOT, **kwargs)


def tracked():
    # A local preparation must include new sources/screenshots and omit deletions.
    names = {
        name.decode('utf8')
        for name in subprocess.check_output(
            ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
            cwd=ROOT,
        ).split(b'\0')
        if name
    }
    names.update(
        (
            'empacotamento/InstallerText.cs',
            'empacotamento/InstallerStrings.xml',
            'empacotamento/Uninstaller.cs',
            'empacotamento/Uninstaller.xaml',
            'empacotamento/test_uninstaller.py',
        )
    )
    return [ROOT / name for name in sorted(names) if (ROOT / name).is_file()]


def safe(path):
    assert path.suffix.lower() not in {
        '.jks',
        '.keystore',
        '.p12',
        '.key',
        '.pyc',
    }, path
    assert path.name.lower() not in {
        'cookies.txt',
        'credentials.json',
        'preferences.json',
        'queue.json',
        'onda.sqlite3',
        '.env',
        'language.json',
        'local.properties',
    }, path


def verify_third_party_sources(path):
    """Reject stale extractor sources and corrupted source members before shipping."""
    gradle = (ROOT / 'Android/app/build.gradle.kts').read_text(encoding='utf8')
    required = {
        (
            name,
            re.search(r'install\("' + re.escape(name) + r'==([^"\s]+)"\)', gradle)[1],
        )
        for name in ('gallery-dl', 'yt-dlp')
    }
    with zipfile.ZipFile(path) as archive:
        origins = json.loads(archive.read('Fontes-de-terceiros/ORIGENS.json'))
        available = {
            (row['project'].lower().replace('_', '-'), row['version'])
            for row in origins
        }
        assert (
            required <= available
        ), 'Updated Android extractor sources are missing; use --third-party-sources.'
        for row in origins:
            filename = row['filename']
            assert (
                Path(filename).name == filename
                and '/' not in filename
                and '\\' not in filename
            )
            with archive.open('Fontes-de-terceiros/' + filename) as stream:
                assert (
                    hashlib.file_digest(stream, 'sha256').hexdigest() == row['sha256']
                ), filename
    return origins


def windows():
    assert not BUNDLE.exists(), 'Use a fresh diagnostic bundle directory.'
    BUNDLE.mkdir(parents=True)
    shutil.copytree(
        ROOT / 'Portatil/_runtime',
        BUNDLE / '_runtime',
        ignore=shutil.ignore_patterns(
            '__pycache__', '*.pyc', 'objects-*', '*.obj', '*.pdb', '*.lib', '*.exp'
        ),
    )
    assert not (BUNDLE / '_runtime/ffmpeg').exists()
    for source in tracked():
        relative = source.relative_to(ROOT)
        if (
            relative.parts[0] == 'Onda'
            and not source.name.startswith('test_')
            and source.suffix != '.bat'
        ):
            target = BUNDLE / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    for name in (
        'LICENSE',
        'THIRD_PARTY_NOTICES.md',
        'CHANGELOG.md',
        'RELEASE_NOTES.md',
        'Leia-me.txt',
        'README.md',
        'README.en.md',
        'README.es.md',
        'RECURSOS-AVANCADOS.md',
    ):
        shutil.copy2(ROOT / name, BUNDLE / name)
    shutil.copytree(ROOT / 'docs', BUNDLE / 'docs')
    shutil.copy2(ROOT / 'Portatil/onda.ico', BUNDLE / 'onda.ico')
    compiler = (
        Path(os.environ['WINDIR']) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    )
    run(
        [
            compiler,
            '/nologo',
            '/target:winexe',
            '/platform:x64',
            '/reference:System.Windows.Forms.dll',
            '/win32icon:' + str(BUNDLE / 'onda.ico'),
            '/out:' + str(BUNDLE / 'Onda.exe'),
            ROOT / 'empacotamento/Launcher.cs',
        ]
    )
    profile = WORK / 'self-test-profile'
    profile.mkdir()
    env = dict(
        os.environ,
        LOCALAPPDATA=str(profile),
        QT_QPA_PLATFORM='offscreen',
        QSG_RHI_BACKEND='software',
        PYTHONIOENCODING='utf8',
    )
    report = WORK / 'windows-launcher.json'
    run([BUNDLE / 'Onda.exe', '--qt-self-test', report], env=env, timeout=120)
    assert json.loads(report.read_text(encoding='utf8'))['ok']
    output = WORK / 'installer'
    build_installer(BUNDLE, output)
    installer_report = WORK / 'installer-self-test.json'
    run(
        [
            output / f'Onda-{VERSION}-Setup-Windows-x64.exe',
            '--self-test',
            installer_report,
        ],
        timeout=120,
    )
    assert json.loads(installer_report.read_text(encoding='utf8'))['ok']
    assert (output / f'Onda-{VERSION}-Setup-Windows-x64.exe').is_file()
    uninstall_report = WORK / 'uninstaller-self-test.json'
    run(
        [output / 'uninstaller/Desinstalar ONDA.exe', '--self-test', uninstall_report],
        timeout=120,
    )
    assert json.loads(uninstall_report.read_text(encoding='utf-8-sig'))['ok']
    print('Windows bundle, launcher test and installer ready.', flush=True)


def finalize(
    prior,
    reuse_android_from=None,
    installer_validation=None,
    allow_uncommitted=False,
    base_commit=None,
    uninstaller_validation=None,
    third_party_sources=None,
):
    assert not RELEASE.exists(), 'Never replace an existing release directory.'
    dirty = bool(
        subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).strip()
    )
    head = subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True
    ).strip()
    commit = subprocess.check_output(
        ['git', 'rev-parse', '--verify', (base_commit or 'HEAD') + '^{commit}'],
        cwd=ROOT,
        text=True,
    ).strip()
    uncommitted = dirty or commit != head
    assert (
        allow_uncommitted or not uncommitted
    ), 'Use --allow-uncommitted to explicitly prepare a local source snapshot.'
    frontend_check = json.loads(
        (WORK / 'installer-self-test.json').read_text(encoding='utf8')
    )
    assert (
        frontend_check['ok']
        and frontend_check['embedded_backend_verified']
        and frontend_check['version'] == VERSION
    )
    assert frontend_check['languages'] == ['pt-BR', 'es', 'en']
    uninstaller_check = json.loads(
        (WORK / 'uninstaller-self-test.json').read_text(encoding='utf-8-sig')
    )
    assert (
        uninstaller_check['ok'] and uninstaller_check['keeps_data_and_tools_by_default']
    )
    uninstaller_checks = None
    if uninstaller_validation:
        uninstaller_checks = json.loads(
            Path(uninstaller_validation).read_text(encoding='utf8')
        )
        assert uninstaller_checks['ok'] and all(
            c['ok'] for c in uninstaller_checks['checks']
        )
    installer_checks = None
    if installer_validation:
        installer_checks = json.loads(
            Path(installer_validation).read_text(encoding='utf8')
        )
        assert installer_checks['ok'] and all(
            c['ok'] for c in installer_checks['checks']
        )
    current_validation = None
    if (WORK / 'current-validation.json').is_file():
        current_validation = json.loads(
            (WORK / 'current-validation.json').read_text(encoding='utf8')
        )
        assert current_validation['ok']
    previous = ROOT / 'Release' / prior
    previous_manifest = json.loads(
        (previous / 'MANIFEST.json').read_text(encoding='utf-8-sig')
    )
    previous_sources = json.loads(
        (previous / 'SOURCE_MANIFEST.json').read_text(encoding='utf-8-sig')
    )
    for entry in previous_sources['files']:
        # The build guide only corrected the old Celular directory name to Android.
        # Recipes, source locks, licenses and native hashes must remain unchanged.
        if entry['path'] == 'Android/nativebuild/README.md':
            continue
        if entry['path'].startswith('Android/nativebuild/') or entry['path'] in (
            'docs/dependencias.json',
            'Onda/requirements.txt',
        ):
            assert sha(ROOT / entry['path']) == entry['sha256'], (
                'Dependency sources changed: ' + entry['path']
            )
    android = ROOT / 'Android/build' / ('release-' + VERSION)
    validation = json.loads(
        (android / 'signature-validation.json').read_text(encoding='utf8')
    )
    assert (
        validation['version_code'] == ANDROID_VERSION_CODE
        and validation['version'] == VERSION
    )
    for abi in ('arm64-v8a', 'x86_64'):
        assert (
            validation['apks'][abi]['certificate_sha256']
            == previous_manifest['android_certificate_sha256']
        )
        assert (
            validation['apks'][abi]['verified']
            and validation['apks'][abi]['aligned_16kb']
        )
    android_source_commit = commit
    android_uncommitted = uncommitted
    if reuse_android_from:
        # A Windows-only packaging change can preserve the already verified APKs.
        reuse_android_from = Path(reuse_android_from).resolve()
        original = json.loads(
            (reuse_android_from / 'MANIFEST.json').read_text(encoding='utf8')
        )
        original_sources = json.loads(
            (reuse_android_from / 'SOURCE_MANIFEST.json').read_text(encoding='utf8')
        )
        source_rows = [
            r
            for r in original_sources['files']
            if r['path'].startswith(('Android/', 'Onda/'))
        ]
        assert {r['path'] for r in source_rows} == {
            p.relative_to(ROOT).as_posix()
            for p in tracked()
            if p.relative_to(ROOT).parts[0] in ('Android', 'Onda')
        }, 'Android/shared source inventory changed'
        for row in source_rows:
            assert sha(ROOT / row['path']) == row['sha256'], (
                'Android/shared source changed: ' + row['path']
            )
        for abi in ('arm64-v8a', 'x86_64'):
            name = f'ONDA-Android-{VERSION}-{abi}.apk'
            expected = next(
                a['sha256'] for a in original['artifacts'] if a['filename'] == name
            )
            assert sha(reuse_android_from / name) == expected == sha(android / name)
        android_source_commit = original.get(
            'android_binary_source_commit', original['git_commit']
        )
        android_uncommitted = original.get(
            'android_binary_contains_uncommitted_changes',
            original.get('contains_uncommitted_preparation', False),
        )
    third_party_archive = (
        Path(third_party_sources).resolve()
        if third_party_sources
        else previous / f'Onda-{prior}-Fontes-de-terceiros.zip'
    )
    verify_third_party_sources(third_party_archive)
    RELEASE.mkdir()
    for kind in ('Fontes-de-terceiros', 'Fontes-nativos-Android'):
        if kind == 'Fontes-de-terceiros' and third_party_sources:
            source = third_party_archive
        else:
            source = previous / f'Onda-{prior}-{kind}.zip'
            expected = next(
                a['sha256']
                for a in previous_manifest['artifacts']
                if a['filename'] == source.name
            )
            assert sha(source) == expected
        shutil.copy2(source, RELEASE / f'Onda-{VERSION}-{kind}.zip')
    shutil.copy2(WORK / 'installer' / f'Onda-{VERSION}-Setup-Windows-x64.exe', RELEASE)
    for abi in ('arm64-v8a', 'x86_64'):
        shutil.copy2(android / f'ONDA-Android-{VERSION}-{abi}.apk', RELEASE)
    for source, target in [
        ('RELEASE_NOTES.md', 'RELEASE_NOTES.md'),
        ('PUBLICAR_RELEASE.md', 'PUBLICAR.md'),
        ('THIRD_PARTY_NOTICES.md', 'THIRD_PARTY_NOTICES.md'),
        ('Android/THIRD_PARTY_NOTICES_ANDROID.md', 'THIRD_PARTY_NOTICES_ANDROID.md'),
        (f'docs/VALIDACAO-RELEASE-{VERSION}.md', 'VALIDACAO.md'),
    ]:
        shutil.copy2(ROOT / source, RELEASE / target)
    files = sorted(tracked())
    for path in files:
        safe(path)
        assert path.suffix.lower() not in {'.apk', '.exe'}
    source_manifest = {
        'version': VERSION,
        'git_commit': commit,
        'contains_uncommitted_changes': uncommitted,
        'files': [
            {
                'path': p.relative_to(ROOT).as_posix(),
                'bytes': p.stat().st_size,
                'sha256': sha(p),
            }
            for p in files
        ],
    }
    write_json(RELEASE / 'SOURCE_MANIFEST.json', source_manifest)
    with zipfile.ZipFile(
        RELEASE / f'Onda-{VERSION}-Fontes.zip',
        'w',
        zipfile.ZIP_DEFLATED,
        compresslevel=6,
    ) as archive:
        for path in files:
            archive.write(path, f'Onda-{VERSION}/' + path.relative_to(ROOT).as_posix())
        archive.write(
            RELEASE / 'SOURCE_MANIFEST.json', f'Onda-{VERSION}/SOURCE_MANIFEST.json'
        )
    with zipfile.ZipFile(
        RELEASE / f'Onda-{VERSION}-Portable-Windows-x64.zip',
        'w',
        zipfile.ZIP_DEFLATED,
        compresslevel=6,
    ) as archive:
        for path in sorted(BUNDLE.rglob('*')):
            if (
                not path.is_file()
                or '__pycache__' in path.parts
                or path.suffix in {'.pyc', '.log'}
            ):
                continue
            safe(path)
            archive.write(
                path, f'Onda-{VERSION}/' + path.relative_to(BUNDLE).as_posix()
            )
    for source in files:
        relative = source.relative_to(ROOT)
        if (
            relative.parts[0] == 'Onda'
            and not source.name.startswith('test_')
            and source.suffix != '.bat'
        ):
            assert source.read_bytes() == (BUNDLE / relative).read_bytes(), relative
    for path in RELEASE.glob('*.zip'):
        with zipfile.ZipFile(path) as archive:
            assert archive.testzip() is None, path
    artifacts = [
        {'filename': p.name, 'bytes': p.stat().st_size, 'sha256': sha(p)}
        for p in sorted(RELEASE.iterdir())
        if p.suffix in {'.zip', '.apk', '.exe'}
    ]
    assert len(artifacts) == 7
    write_json(
        RELEASE / 'MANIFEST.json',
        {
            'version': VERSION,
            'git_commit': commit,
            'prepared_on': date.today().isoformat(),
            'contains_uncommitted_preparation': uncommitted,
            'status': 'official-prepared-local-not-published',
            'android_version': VERSION,
            'android_version_code': ANDROID_VERSION_CODE,
            'android_certificate_sha256': previous_manifest[
                'android_certificate_sha256'
            ],
            'android_binary_source_commit': android_source_commit,
            'android_binary_contains_uncommitted_changes': android_uncommitted,
            'android_shared_sources_verified_unchanged': bool(reuse_android_from),
            'android_release_apks_verified': validation,
            'windows_numeric_version': VERSION + '.0',
            'windows_authenticode_signed': False,
            'windows_launcher_self_test': True,
            'windows_installer_interface': 'ONDA standalone WPF frontend',
            'windows_installer_languages': frontend_check['languages'],
            'windows_installer_translation_keys': frontend_check['translation_keys'],
            'windows_installer_backend': 'embedded Inno Setup; original production AppId',
            'windows_installer_validation': installer_checks,
            'windows_uninstaller_interface': 'ONDA standalone WPF frontend; original Inno backend',
            'windows_uninstaller_self_test': uninstaller_check,
            'windows_uninstaller_validation': uninstaller_checks,
            'current_validation': current_validation,
            'prior_validation': {
                'pc_passed': 149,
                'pc_skipped': 4,
                'android_jvm_passed': 72,
                'android_instrumented_debug_x86_64_passed': 45,
            },
            'physical_arm64_validation': False,
            'validation': 'VALIDACAO.md',
            'artifacts': artifacts,
        },
    )
    (RELEASE / 'SHA256SUMS.txt').write_text(
        ''.join(
            f'{sha(p)}  {p.name}\n'
            for p in sorted(RELEASE.iterdir())
            if p.name != 'SHA256SUMS.txt'
        ),
        encoding='ascii',
    )
    print(
        json.dumps(
            {'release': str(RELEASE), 'git_commit': commit, 'artifacts': artifacts},
            indent=2,
        ),
        flush=True,
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['windows', 'finalize'])
    parser.add_argument('--prior', default='1.2.0-rc2')
    parser.add_argument(
        '--work',
        type=Path,
        help='Fresh build workspace; never a prior release directory',
    )
    parser.add_argument(
        '--release-output',
        type=Path,
        help='Fresh candidate directory for reviewing a replacement',
    )
    parser.add_argument(
        '--reuse-android-from',
        type=Path,
        help='Verify Android/shared sources and preserve the APK provenance from this release',
    )
    parser.add_argument(
        '--installer-validation',
        type=Path,
        help='Integration report from an isolated audit build',
    )
    parser.add_argument(
        '--uninstaller-validation', type=Path, help='Custom uninstaller audit report'
    )
    parser.add_argument(
        '--third-party-sources',
        type=Path,
        help='Source archive matching updated Android extractors',
    )
    parser.add_argument(
        '--allow-uncommitted',
        action='store_true',
        help='Explicitly mark local changes in the source and release manifests',
    )
    parser.add_argument(
        '--base-commit',
        help='Base commit for a local source snapshot; requires --allow-uncommitted when different from HEAD',
    )
    args = parser.parse_args()
    if args.work:
        WORK = args.work.resolve()
        BUNDLE = WORK / 'portable'
    if args.release_output:
        RELEASE = args.release_output.resolve()
    if args.stage == 'windows':
        windows()
    else:
        finalize(
            args.prior,
            args.reuse_android_from,
            args.installer_validation,
            args.allow_uncommitted,
            args.base_commit,
            args.uninstaller_validation,
            args.third_party_sources,
        )
