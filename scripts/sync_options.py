"""Import original options forms and literal setting bindings from QGIS 3.34.10."""
import json
import os
import re
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get('QGIS_SOURCE_ROOT', r'C:\QGIS_COMPILE\QGIS-final-3_34_10'))


def main():
    for name in ('qgsoptionsbase', 'qgsrenderingoptionsbase'):
        tree = ET.parse(SOURCE / 'src/ui' / (name + '.ui'))
        for header in tree.findall('.//customwidget/header'): header.text = 'qgis.gui'
        for custom in tree.findall('.//customwidget'):
            if custom.findtext('class') == 'QgsDatumTransformTableWidget':
                custom.find('header').text = 'src.app.qgsdatumtransformtablewidget'
        tree.write(ROOT / 'src/ui' / (name + '.ui'), encoding='utf-8', xml_declaration=True)
    cpp = (SOURCE / 'src/app/options/qgsoptions.cpp').read_text(encoding='utf-8')
    # Only direct, literal read/write pairs are extracted. Enums, transforms,
    # colors and application effects are implemented explicitly in QgsOptions.
    pattern = r'(\w+)->(setChecked|setValue|setText|setCurrentIndex)\(mSettings->value\(QStringLiteral\("([^"%]+)"\),\s*(true|false|-?\d+(?:\.\d+)?|QStringLiteral\("[^"]*"\)|"[^"]*")\)\.(toBool|toInt|toDouble|toString)\(\)\)'
    bindings = []
    getters = {'setChecked': 'isChecked', 'setValue': 'value', 'setText': 'text', 'setCurrentIndex': 'currentIndex'}
    # These application behaviors have not yet been ported; don't expose a
    # checkbox which only writes an otherwise unused setting in this host.
    excluded = {'cbxCheckVersion', 'mCheckMonitorDirectories'}
    for name, setter, key, default, conversion in re.findall(pattern, cpp):
        if name in excluded: continue
        write = rf'setValue\(QStringLiteral\("{re.escape(key)}"\),\s*{name}->{getters[setter]}\(\)'
        if not re.search(write, cpp): continue
        if default.startswith('QStringLiteral'): default = default[len('QStringLiteral('):-1]
        bindings.append((name, setter, key.lstrip('/'), json.loads(default)))
    core = re.findall(r'(\w+)->(setChecked|setValue|setColor|setCurrentIndex)\(QgsSettingsRegistryCore::(\w+)->value\(\)\)', cpp)
    text = '"""Literal bindings extracted by scripts/sync_options.py; special cases live in QgsOptions."""\n'
    text += 'BINDINGS = ' + repr(bindings) + '\nCORE_BINDINGS = ' + repr(core) + '\n'
    (ROOT / 'src/app/options/qgsoptionsbindings.py').write_text(text, encoding='utf-8')
    print(f'Imported original option forms; {len(bindings)} literal settings and {len(core)} core settings.')


if __name__ == '__main__': main()
