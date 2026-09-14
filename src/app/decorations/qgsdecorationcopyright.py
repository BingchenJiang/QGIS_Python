from .qgsdecorationtitle import QgsDecorationTitle
from .qgsdecorationitem import QgsDecorationItem


class QgsDecorationCopyright(QgsDecorationTitle):
    configurationName = 'CopyrightLabel'
    defaultPlacement = QgsDecorationItem.BottomRight
    hasBackground = False

    def createDialog(self):
        from .qgsdecorationcopyrightdialog import QgsDecorationCopyrightDialog
        return QgsDecorationCopyrightDialog(self, self.mApp)
