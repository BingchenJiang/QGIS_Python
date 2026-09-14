@echo off
setlocal
if not defined OSGEO4W_ROOT set "OSGEO4W_ROOT=C:\OSGeo4W"
call "%OSGEO4W_ROOT%\bin\python-qgis-ltr.bat" -m PyQt5.uic.pyuic "%~dp0..\src\ui\qgisapp.ui" -o "%~dp0..\src\ui\ui_qgisapp.py"
if errorlevel 1 exit /b %errorlevel%
call "%OSGEO4W_ROOT%\bin\python-qgis-ltr.bat" -m PyQt5.uic.pyuic "%~dp0..\src\ui\qgsrastercalcdialogbase.ui" -o "%~dp0..\src\ui\ui_qgsrastercalcdialogbase.py"
exit /b %errorlevel%
