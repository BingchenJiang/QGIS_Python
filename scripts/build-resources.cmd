@echo off
setlocal
if not defined OSGEO4W_ROOT set "OSGEO4W_ROOT=C:\OSGeo4W"
call "%OSGEO4W_ROOT%\bin\python-qgis-ltr.bat" -m PyQt5.pyrcc_main "%~dp0..\images\images.qrc" -o "%~dp0..\images\images_rc.py"
exit /b %errorlevel%
