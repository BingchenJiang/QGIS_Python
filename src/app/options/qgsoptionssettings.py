"""Supported control names and settings keys transcribed from qgsoptions.cpp."""
PAGES = {
    '常规': [
        ('cbxHideSplash', '隐藏启动画面', 'qgis/hideSplash', False, 'bool'),
        ('cbxAttributeTableDocked', '属性表默认停靠', 'qgis/dockAttributeTable', False, 'bool'),
        ('mMessageTimeoutSpnBx', '消息显示时间（秒）', 'qgis/messageTimeout', 6, 'int'),
        ('mNativeColorDialogsChkBx', '系统颜色对话框', 'qgis/native_color_dialogs', False, 'bool'),
    ],
    '数据源与图层': [
        ('spinBoxAttrTableRowCache', '属性表缓存行数', 'qgis/attributeTableRowCache', 10000, 'int'),
        ('mCheckMonitorDirectories', '浏览器监视目录变化', 'qgis/monitorDirectoriesInBrowser', True, 'bool'),
        ('cbxLegendClassifiers', '显示分类字段', 'qgis/showLegendClassifiers', True, 'bool'),
        ('mNewLayersVisible', '新增图层默认可见', 'qgis/new_layers_visible', True, 'bool'),
        ('mMapTipsDelaySpinBox', '地图提示延迟（毫秒）', 'qgis/mapTipsDelay', 850, 'int'),
    ],
    '地图工具': [
        ('spinBoxIdentifyValue', '识别搜索半径（毫米）', 'Map/searchRadiusMM', 2.0, 'float'),
        ('mIdentifyHighlightBufferSpinBox', '识别高亮缓冲', 'Map/highlight/buffer', 0.5, 'float'),
        ('mIdentifyHighlightMinWidthSpinBox', '高亮最小宽度', 'Map/highlight/minWidth', 1.0, 'float'),
        ('mZoomFactor', '滚轮缩放倍数', 'qgis/zoom_factor', 2.0, 'float'),
        ('mMeasureDecimalPlaces', '测量小数位数', 'qgis/measure/decimalplaces', 3, 'int'),
        ('mMagnifierDefault', '默认放大倍率', 'qgis/magnifier_factor_default', 1.0, 'float'),
    ],
    '网络': [
        ('leUserAgent', 'User-Agent', 'qgis/networkAndProxy/userAgent', 'Mozilla/5.0 QGIS/33410', 'str'),
        ('mDefaultCapabilitiesExpirySpinBox', 'Capabilities 缓存（小时）', 'qgis/defaultCapabilitiesExpiry', 24, 'int'),
        ('mDefaultTileExpirySpinBox', '瓦片缓存（小时）', 'qgis/defaultTileExpiry', 24, 'int'),
        ('mDefaultTileMaxRetrySpinBox', '瓦片重试次数', 'qgis/defaultTileMaxRetry', 3, 'int'),
        ('grpProxy', '启用代理', 'proxy/proxyEnabled', False, 'bool'),
        ('leProxyHost', '代理主机', 'proxy/proxyHost', '', 'str'),
        ('leProxyPort', '代理端口', 'proxy/proxyPort', '', 'str'),
        ('mProxyTypeComboBox', '代理类型', 'proxy/proxyType', 'HttpProxy', ['DefaultProxy', 'Socks5Proxy', 'HttpProxy', 'HttpCachingProxy']),
        ('mCacheDirectory', '缓存目录', 'cache/directory', '', 'str'),
    ],
}
CORE_ENTRIES = [
    ('mDefaultZValueSpinBox', '默认 Z 值', 'settingsDigitizingDefaultZValue', 'float'),
    ('mDefaultMValueSpinBox', '默认 M 值', 'settingsDigitizingDefaultMValue', 'float'),
    ('mSnappingEnabledDefault', '新工程默认启用捕捉', 'settingsDigitizingDefaultSnapEnabled', 'bool'),
    ('mDefaultSnappingToleranceSpinBox', '默认捕捉容差', 'settingsDigitizingDefaultSnappingTolerance', 'float'),
    ('mSearchRadiusVertexEditSpinBox', '顶点编辑搜索半径', 'settingsDigitizingSearchRadiusVertexEdit', 'float'),
    ('mSnappingTooltipsCheckbox', '捕捉工具提示', 'settingsDigitizingSnapTooltip', 'bool'),
    ('chkDisableAttributeValuesDlg', '新增要素时不打开表单', 'settingsDigitizingDisableEnterAttributeValuesDialog', 'bool'),
    ('chkReuseLastValues', '重用上次属性值', 'settingsDigitizingReuseLastValues', 'bool'),
]
