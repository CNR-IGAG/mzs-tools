@echo off
setlocal

REM Set installer URL and local path
set "QGIS_URL=https://qgis.org/downloads/QGIS-OSGeo4W-3.44.3-1.msi"
set "QGIS_MSI=%SystemDrive%\OEM\QGIS-OSGeo4W-3.44.3-1.msi"

REM JRE installer URL and local path - % needs to be escaped as %% !!!
set "JRE_URL=https://github.com/adoptium/temurin25-binaries/releases/download/jdk-25%%2B36/OpenJDK25U-jre_x64_windows_hotspot_25_36.msi"
set "JRE_MSI=%SystemDrive%\OEM\OpenJDK25U-jre_x64_windows_hotspot_25_36.msi"

REM Download QGIS installer if not already present
if not exist "%QGIS_MSI%" (
    curl.exe -L -o "%QGIS_MSI%" "%QGIS_URL%"
)

REM Download JRE installer if not already present
if not exist "%JRE_MSI%" (
    curl.exe -L -o "%JRE_MSI%" "%JRE_URL%"
)

REM Install QGIS silently
msiexec /i "%QGIS_MSI%" /qn /norestart
REM del "%QGIS_MSI%"

REM Install JRE silently https://adoptium.net/installation/windows/
msiexec /i "%JRE_MSI%" ADDLOCAL=FeatureMain,FeatureEnvironment,FeatureJarFileRunWith,FeatureJavaHome /quiet /norestart

REM map network drive for shared folder
net use Z: \\host.lan\Data

REM create plugin symbolic link inside QGIS default profile
if not exist "%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\" (
    mkdir "%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins"
)
mklink /D "%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\mzs_tools" "Z:\GIT\mzs-tools\mzs_tools"
endlocal
