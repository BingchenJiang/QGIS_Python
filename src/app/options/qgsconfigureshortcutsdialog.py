from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QAction, QTableWidget, QTableWidgetItem, QKeySequenceEdit, QDialogButtonBox
from qgis.core import QgsSettings

class QgsConfigureShortcutsDialog(QDialog):
    def __init__(self, app):
        super().__init__(app)
        self.mApp = app
        self.setWindowTitle('配置快捷键')
        self.resize(720, 600)
        layout = QVBoxLayout(self)
        actions = [a for a in app.findChildren(QAction) if a.objectName() in app.mImplementedActions]
        table = QTableWidget(len(actions), 2)
        table.setHorizontalHeaderLabels(['动作', '快捷键'])
        self.mEditors = []
        for row, action in enumerate(actions):
            table.setItem(row, 0, QTableWidgetItem(action.text()))
            editor = QKeySequenceEdit(action.shortcut())
            table.setCellWidget(row, 1, editor)
            self.mEditors.append((action, editor))
        table.resizeColumnToContents(0)
        layout.addWidget(table)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(self.apply)
        buttons.rejected.connect(self.reject)

    def apply(self):
        settings = QgsSettings()
        used = {}
        for action, editor in self.mEditors:
            key = editor.keySequence().toString()
            if key and key in used:
                self.mApp.mMessageBar.pushWarning('快捷键重复', f'{action.text()} / {used[key]}: {key}')
                return
            if key: used[key] = action.text()
        for action, editor in self.mEditors:
            action.setShortcut(editor.keySequence())
            settings.setValue('PythonDesktop/shortcuts/' + action.objectName(), editor.keySequence().toString())
        self.accept()
