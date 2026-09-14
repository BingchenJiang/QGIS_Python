"""Python counterpart of the application-side QgsReportSectionModel."""
from qgis.PyQt.QtCore import QAbstractItemModel, QModelIndex, Qt
from qgis.PyQt.QtGui import QIcon, QPainter
from qgis.core import QgsApplication, QgsReportSectionFieldGroup


class QgsReportSectionModel(QAbstractItemModel):
    def __init__(self, report, parent=None):
        super().__init__(parent)
        self.mReport, self.mEditedSection = report, None
        self.retainSections()

    def retainSections(self):
        # QModelIndex.internalPointer does not retain a Python SIP wrapper.
        self.mSections = []
        def visit(section):
            self.mSections.append(section)
            for child in section.childSections(): visit(child)
        if self.mReport is not None: visit(self.mReport)

    def sectionForIndex(self, index):
        return index.internalPointer() if index.isValid() and self.mReport is not None else None

    def indexForSection(self, section):
        if section is None or section not in self.mSections: return QModelIndex()
        return self.createIndex(0 if section is self.mReport else section.row(), 0, section)

    def rowCount(self, parent=QModelIndex()):
        if self.mReport is None or parent.column() > 0: return 0
        return self.sectionForIndex(parent).childCount() if parent.isValid() else 1

    def columnCount(self, parent=QModelIndex()): return 1

    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent): return QModelIndex()
        section = self.sectionForIndex(parent).childSection(row) if parent.isValid() else self.mReport
        return self.createIndex(row, column, section)

    def parent(self, index):
        section = self.sectionForIndex(index)
        return self.indexForSection(section.parentSection()) if section is not None else QModelIndex()

    def data(self, index, role=Qt.DisplayRole):
        section = self.sectionForIndex(index)
        if section is None: return None
        if role in (Qt.DisplayRole, Qt.ToolTipRole): return section.description()
        if role == Qt.EditRole: return section.type()
        if role == Qt.DecorationRole:
            if section is not self.mEditedSection: return section.icon()
            pixmap = section.icon().pixmap(24, 24)
            painter = QPainter(pixmap)
            painter.drawPixmap(0, 0, 24, 24, QgsApplication.getThemePixmap('/mActionToggleEditing.svg'))
            painter.end()
            return QIcon(pixmap)
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        return '章节' if orientation == Qt.Horizontal and role == Qt.DisplayRole else None

    def sectionChanged(self, section):
        index = self.indexForSection(section)
        if index.isValid(): self.dataChanged.emit(index, index)

    def setEditedSection(self, section):
        previous, self.mEditedSection = self.mEditedSection, section
        self.sectionChanged(previous)
        self.sectionChanged(section)

    def addSection(self, parent, section):
        parentSection = self.sectionForIndex(parent) or self.mReport
        parent = self.indexForSection(parentSection)
        row = parentSection.childCount()
        self.beginInsertRows(parent, row, row)
        parentSection.appendChild(section)
        self.retainSections()
        self.endInsertRows()

    def removeRows(self, row, count, parent=QModelIndex()):
        section = self.sectionForIndex(parent)
        if section is None or count <= 0 or row < 0 or row + count > section.childCount(): return False
        self.setEditedSection(None)
        self.beginRemoveRows(parent, row, row + count - 1)
        for _ in range(count): section.removeChildAt(row)
        self.retainSections()
        self.endRemoveRows()
        return True

    @staticmethod
    def cloneSection(section):
        clone = section.clone()
        # Preserve the visibility policies on every nested group as well as
        # the layouts and layer references copied by the native clone method.
        def copyPolicies(source, target):
            if isinstance(source, QgsReportSectionFieldGroup):
                target.setHeaderVisibility(source.headerVisibility())
                target.setFooterVisibility(source.footerVisibility())
            for a, b in zip(source.childSections(), target.childSections()): copyPolicies(a, b)
        copyPolicies(section, clone)
        return clone

    def moveSection(self, section, parentSection, row):
        """Move using native deep copies: removeChildAt deletes its argument."""
        if section is self.mReport or section not in self.mSections or parentSection not in self.mSections: return None
        ancestor = parentSection
        while ancestor is not None:
            if ancestor is section: return None
            ancestor = ancestor.parentSection()
        sourceParent, sourceRow = section.parentSection(), section.row()
        if row < 0 or row > parentSection.childCount(): return None
        if sourceParent is parentSection and row in (sourceRow, sourceRow + 1): return section
        replacement = self.cloneSection(section)
        self.setEditedSection(None)
        self.beginResetModel()
        # Insert before removing, so a failed clone never discards the original.
        parentSection.insertChild(row, replacement)
        if sourceParent is parentSection and row <= sourceRow: sourceRow += 1
        sourceParent.removeChildAt(sourceRow)
        self.retainSections()
        self.endResetModel()
        return replacement

    def clearReport(self):
        self.beginResetModel()
        self.mReport = self.mEditedSection = None
        self.mSections.clear()
        self.endResetModel()
