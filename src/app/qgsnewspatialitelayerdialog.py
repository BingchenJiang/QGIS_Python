"""Python port of qgsnewspatialitelayerdialog.cpp using the native provider."""
from pathlib import Path
from contextlib import closing
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QMessageBox, QTreeWidgetItem
from qgis.core import (QgsApplication, QgsProject, QgsProviderRegistry, QgsDataSourceUri,
                       QgsCoordinateReferenceSystem, QgsVectorLayer, QgsWkbTypes)
from qgis.gui import QgsGui, QgsProjectionSelectionDialog, QgsHelp
from qgis.utils import spatialite_connect


class QgsNewSpatialiteLayerDialog(QDialog):
    def __init__(self, parent=None, defaultCrs=None):
        super().__init__(parent)
        uic.loadUi(str(Path(__file__).resolve().parents[1] / 'ui/qgsnewspatialitelayerdialogbase.ui'), self)
        QgsGui.enableAutoGeometryRestore(self)
        self.mNewLayer = None
        self.mCrs = defaultCrs or QgsProject.instance().crs()
        self.leSRID.setText(self.mCrs.userFriendlyIdentifier())
        self.leGeometryColumn.setText('geometry')
        for name in ('NoGeometry', 'Point', 'LineString', 'Polygon', 'MultiPoint', 'MultiLineString', 'MultiPolygon'):
            self.mGeometryTypeBox.addItem(QgsWkbTypes.translatedDisplayString(getattr(QgsWkbTypes, name)), '' if name == 'NoGeometry' else name.upper())
        self.mGeometryTypeBox.setCurrentIndex(-1)
        for name, sqlType in [('文本', 'text'), ('整数', 'integer'), ('小数', 'real'), ('日期', 'date'), ('日期时间', 'timestamp')]:
            self.mTypeBox.addItem(name, sqlType)
        self.mDatabaseComboBox.setProvider('spatialite')
        self.mAddAttributeButton.setIcon(QgsApplication.getThemeIcon('/mActionNewAttribute.svg'))
        self.mRemoveAttributeButton.setIcon(QgsApplication.getThemeIcon('/mActionDeleteAttribute.svg'))
        self.mAddAttributeButton.clicked.connect(self.mAddAttributeButton_clicked)
        self.mRemoveAttributeButton.clicked.connect(self.mRemoveAttributeButton_clicked)
        self.mNameEdit.textChanged.connect(self.checkOk)
        self.mAttributeView.itemSelectionChanged.connect(self.checkOk)
        self.leLayerName.textChanged.connect(self.checkOk)
        self.leGeometryColumn.textChanged.connect(self.checkOk)
        self.checkBoxPrimaryKey.toggled.connect(self.checkOk)
        self.mDatabaseComboBox.connectionChanged.connect(self.checkOk)
        self.mGeometryTypeBox.currentIndexChanged.connect(self.mGeometryTypeBox_currentIndexChanged)
        self.pbnFindSRID.clicked.connect(self.pbnFindSRID_clicked)
        self.toolButtonNewDatabase.clicked.connect(self.createDb)
        self.toolButtonNewDatabase.setToolTip('选择现有数据库以添加图层，或输入新路径创建数据库；不会替换已有数据库。')
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.helpRequested.connect(lambda: QgsHelp.openHelp('managing_data_source/create_layers.html#creating-a-new-spatialite-layer'))
        self.mGeometryTypeBox_currentIndexChanged(-1)

    @staticmethod
    def quotedIdentifier(value): return '"' + value.replace('"', '""') + '"'

    def fields(self):
        return [(self.mAttributeView.topLevelItem(i).text(0), self.mAttributeView.topLevelItem(i).text(1))
                for i in range(self.mAttributeView.topLevelItemCount())]

    def selectedType(self): return self.mGeometryTypeBox.currentData() or ''
    def selectedZM(self): return 'XY' + ('Z' if self.mGeometryWithZCheckBox.isChecked() else '') + ('M' if self.mGeometryWithMCheckBox.isChecked() else '')

    def checkOk(self, *args):
        names = {name.casefold() for name, _ in self.fields()}
        reserved = {'pkuid'} if self.checkBoxPrimaryKey.isChecked() else set()
        if self.selectedType(): reserved.add(self.leGeometryColumn.text().strip().casefold())
        fieldName = self.mNameEdit.text().strip()
        self.mAddAttributeButton.setEnabled(bool(fieldName and fieldName.casefold() not in names | reserved))
        self.mRemoveAttributeButton.setEnabled(bool(self.mAttributeView.selectedItems()))
        valid = bool(self.leLayerName.text().strip() and self.mDatabaseComboBox.currentConnectionUri()
                     and self.mGeometryTypeBox.currentIndex() >= 0
                     and (self.checkBoxPrimaryKey.isChecked() or names) and not names.intersection(reserved))
        if self.selectedType(): valid = valid and bool(self.leGeometryColumn.text().strip()) and self.mCrs.isValid()
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(valid)

    def mGeometryTypeBox_currentIndexChanged(self, index):
        for widget in (self.pbnFindSRID, self.leSRID, self.leGeometryColumn, self.mGeometryWithZCheckBox, self.mGeometryWithMCheckBox):
            widget.setEnabled(index > 0)
        self.checkOk()

    def mAddAttributeButton_clicked(self):
        if not self.mAddAttributeButton.isEnabled(): return
        self.mAttributeView.addTopLevelItem(QTreeWidgetItem([self.mNameEdit.text().strip(), self.mTypeBox.currentData()]))
        self.mNameEdit.clear()
        self.checkOk()

    def mRemoveAttributeButton_clicked(self):
        for item in self.mAttributeView.selectedItems(): self.mAttributeView.takeTopLevelItem(self.mAttributeView.indexOfTopLevelItem(item))
        self.checkOk()

    def pbnFindSRID_clicked(self):
        dialog = QgsProjectionSelectionDialog(self)
        dialog.setCrs(self.mCrs)
        if dialog.exec_():
            self.mCrs = dialog.crs()
            self.leSRID.setText(self.mCrs.userFriendlyIdentifier())
            self.checkOk()

    def createDb(self):
        path, _ = QFileDialog.getSaveFileName(self, '新建或选择 SpatiaLite 数据库', '', 'SpatiaLite (*.sqlite *.db *.sqlite3 *.db3 *.s3db)', options=QFileDialog.DontConfirmOverwrite)
        if not path: return
        if not Path(path).suffix: path += '.sqlite'
        try: self.createDatabase(path)
        except Exception as error: QMessageBox.warning(self, 'SpatiaLite 数据库', str(error))

    def createDatabase(self, path):
        path = str(Path(path).resolve())
        existed = Path(path).exists()
        with closing(spatialite_connect(path)) as connection:
            if not existed:
                if connection.execute('SELECT InitSpatialMetaData(1)').fetchone()[0] != 1:
                    raise RuntimeError('无法初始化 SpatiaLite 元数据')
            elif not connection.execute("SELECT 1 FROM sqlite_master WHERE name='geometry_columns'").fetchone():
                raise ValueError('该文件不是已初始化的 SpatiaLite 数据库')
        uri = QgsDataSourceUri()
        uri.setDatabase(path)
        metadata = QgsProviderRegistry.instance().providerMetadata('spatialite')
        nativeConnection = metadata.createConnection(uri.uri(), {})
        # Reuse an existing connection to this path without replacing another one.
        connections = metadata.connections()
        name = Path(path).name
        for existingName, existing in connections.items():
            if Path(QgsDataSourceUri(existing.uri()).database()).resolve() == Path(path):
                name = existingName
                break
        else:
            base, suffix = name, 2
            while name in connections:
                name = f'{base} ({suffix})'
                suffix += 1
        metadata.saveConnection(nativeConnection, name)
        self.mDatabaseComboBox.setConnection(name)
        self.checkOk()
        return name

    def createLayer(self):
        self.checkOk()
        if not self.buttonBox.button(QDialogButtonBox.Ok).isEnabled(): raise ValueError('请检查数据库、图层名称、几何类型和字段')
        uri = QgsDataSourceUri(self.mDatabaseComboBox.currentConnectionUri())
        if not Path(uri.database()).is_file(): raise ValueError('数据库文件不存在')
        name = self.leLayerName.text().strip()
        geometryColumn = self.leGeometryColumn.text().strip() if self.selectedType() else ''
        columns = ['pkuid INTEGER PRIMARY KEY AUTOINCREMENT'] if self.checkBoxPrimaryKey.isChecked() else []
        for field, sqlType in self.fields():
            if sqlType not in ('text', 'integer', 'real', 'date', 'timestamp'): raise ValueError('不支持的字段类型')
            columns.append(self.quotedIdentifier(field) + ' ' + sqlType)
        with closing(spatialite_connect(uri.database())) as connection:
            try:
                connection.execute('BEGIN')
                connection.execute('CREATE TABLE ' + self.quotedIdentifier(name) + '(' + ','.join(columns) + ')')
                if geometryColumn:
                    authority = self.mCrs.authid().split(':')
                    epsg = len(authority) == 2 and authority[0].upper() == 'EPSG' and authority[1].isdigit()
                    srid = int(authority[1]) if epsg else connection.execute('SELECT MAX(100000, COALESCE(MAX(srid), 0)) + 1 FROM spatial_ref_sys').fetchone()[0]
                    if not connection.execute('SELECT 1 FROM spatial_ref_sys WHERE srid=?', (srid,)).fetchone():
                        connection.execute('INSERT INTO spatial_ref_sys (srid,auth_name,auth_srid,ref_sys_name,proj4text,srtext) VALUES (?,?,?,?,?,?)',
                                           (srid, 'EPSG' if epsg else 'NONE', srid, self.mCrs.description(), self.mCrs.toProj(), self.mCrs.toWkt()))
                    if connection.execute('SELECT AddGeometryColumn(?,?,?,?,?)', (name, geometryColumn, srid, self.selectedType(), self.selectedZM())).fetchone()[0] != 1:
                        raise RuntimeError('创建几何字段失败')
                    if connection.execute('SELECT CreateSpatialIndex(?,?)', (name, geometryColumn)).fetchone()[0] != 1:
                        raise RuntimeError('创建空间索引失败')
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        uri.setDataSource('', name, geometryColumn, '', 'pkuid' if self.checkBoxPrimaryKey.isChecked() else '')
        layer = QgsVectorLayer(uri.uri(), name, 'spatialite')
        if not layer.isValid(): raise RuntimeError('表已创建，但 SpatiaLite 提供者无法加载该图层')
        self.mNewLayer = layer
        return layer

    def apply(self):
        try:
            layer = self.createLayer()
        except Exception as error:
            QMessageBox.warning(self, '创建 SpatiaLite 图层失败', str(error))
            return False
        QgsProject.instance().addMapLayer(layer)
        return True

    def accept(self):
        if self.mNameEdit.text().strip() and QMessageBox.question(self, '未添加字段', '字段输入框中还有未添加的字段，是否忽略它并继续？', QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes: return
        if self.apply(): super().accept()
