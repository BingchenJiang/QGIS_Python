from qgis.PyQt.QtCore import QDate
from .qgsdecorationtitledialog import QgsDecorationTitleDialog


class QgsDecorationCopyrightDialog(QgsDecorationTitleDialog):
    uiName = 'qgsdecorationcopyrightdialog.ui'
    helpAnchor = 'copyright-decoration'
    textWidgetName = 'txtCopyrightText'

    def defaultText(self):
        return f'© {self.mDeco.mApp.mProject.metadata().author()} {QDate.currentDate().year()}'
