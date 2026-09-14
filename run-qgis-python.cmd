@echo off
setlocal
if not defined OSGEO4W_ROOT set "OSGEO4W_ROOT=C:\OSGeo4W"
if not exist "%OSGEO4W_ROOT%\bin\python-qgis-ltr.bat" (
  echo Cannot find OSGeo4W python-qgis-ltr.bat. Set OSGEO4W_ROOT.
  exit /b 1
)
set "PYTHONPATH=%~dp0;%OSGEO4W_ROOT%\apps\qgis-ltr\python\plugins;%PYTHONPATH%"
call "%OSGEO4W_ROOT%\bin\python-qgis-ltr.bat" "%~dp0src\app\main.py" %*
exit /b %errorlevel%

