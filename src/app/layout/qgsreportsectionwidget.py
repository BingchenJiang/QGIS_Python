"""Original report header/footer form and application-side signal connections."""
from pathlib import Path
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QWidget

UI_ROOT = Path(__file__).resolve().parents[2] / 'ui' / 'layout'


class QgsReportSectionWidget(QWidget):
    uiName = 'qgsreportwidgetsectionbase.ui'

    def __init__(self, parent, designer, section):
        super().__init__(parent)
        self.mOrganizer, self.mDesigner, self.mSection = parent, designer, section
        uic.loadUi(str(UI_ROOT / self.uiName), self)
        for part in ('Header', 'Footer', 'Body'):
            check = getattr(self, 'mCheckShow' + part, None)
            if check is None: continue
            enabled = getattr(section, part.lower() + 'Enabled')()
            button = getattr(self, 'mButtonEdit' + part)
            check.setChecked(enabled)
            button.setEnabled(enabled)
            check.toggled.connect(getattr(self, 'toggle' + part))
            check.toggled.connect(button.setEnabled)
            button.clicked.connect(getattr(self, 'edit' + part))

    def changed(self): self.mOrganizer.sectionChanged(self.mSection)

    def toggleHeader(self, enabled):
        self.mSection.setHeaderEnabled(enabled)
        self.changed()

    def toggleFooter(self, enabled):
        self.mSection.setFooterEnabled(enabled)
        self.changed()

    def toggleBody(self, enabled):
        self.mSection.setBodyEnabled(enabled)
        self.changed()

    def editHeader(self): return self.mOrganizer.editSectionLayout(self.mSection, 'Header')
    def editFooter(self): return self.mOrganizer.editSectionLayout(self.mSection, 'Footer')
    def editBody(self): return self.mOrganizer.editSectionLayout(self.mSection, 'Body')
