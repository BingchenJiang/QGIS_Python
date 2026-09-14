"""Designer constructor adapter for the native QGIS provider connection combo."""
from qgis.gui import QgsProviderConnectionComboBox as _QgsProviderConnectionComboBox


class QgsProviderConnectionComboBox(_QgsProviderConnectionComboBox):
    def __init__(self, parent=None):
        # The C++ QWidget-only Designer constructor is SIP_SKIP in 3.34.
        super().__init__('spatialite', parent)
