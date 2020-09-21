; FastFlix.nsi
;

  !include "MUI2.nsh"
SetCompressor lzma

;--------------------------------

; The name of the installer
Name "FastFlix"

; The file to write
OutFile "FastFlix_installer.exe"

; Request application privileges for Windows Vista and higher
RequestExecutionLevel admin

; Build Unicode installer
Unicode True

; The default installation directory
InstallDir $PROGRAMFILES64\FastFlix

; Registry key to check for directory (so if you install again, it will
; overwrite the old one automatically)
InstallDirRegKey HKLM "Software\NSIS_FastFlix" "Install_Dir"

;--------------------------------

; Pages

  !insertmacro MUI_PAGE_COMPONENTS
  !insertmacro MUI_PAGE_DIRECTORY
  !insertmacro MUI_PAGE_INSTFILES

  !insertmacro MUI_UNPAGE_CONFIRM
  !insertmacro MUI_UNPAGE_INSTFILES

;Languages

  !insertmacro MUI_LANGUAGE "English"

;--------------------------------

; The stuff to install
Section "FastFlix (required)"

  SectionIn RO

  ; Set output path to the installation directory.
  SetOutPath $INSTDIR

  ; Put file there
  File /r "dist\FastFlix\*"

  ; Write the installation path into the registry
  WriteRegStr HKLM SOFTWARE\NSIS_FastFlix "Install_Dir" "$INSTDIR"

  ; Write the uninstall keys for Windows
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\FastFlix" "DisplayName" "FastFlix"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\FastFlix" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\FastFlix" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\FastFlix" "NoRepair" 1
  WriteUninstaller "$INSTDIR\uninstall.exe"

SectionEnd

; Optional section (can be disabled by the user)
Section "Start Menu Shortcuts"

  CreateDirectory "$SMPROGRAMS\FastFlix"
  CreateShortcut "$SMPROGRAMS\FastFlix\FastFlix.lnk" "$INSTDIR\FastFlix.exe"
  CreateShortcut "$SMPROGRAMS\FastFlix\Uninstall FastFlix.lnk" "$INSTDIR\uninstall.exe"

SectionEnd

; Uninstaller

Section "Uninstall"

  ; Remove registry keys
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\FastFlix"
  DeleteRegKey HKLM SOFTWARE\FastFlix

  ; Remove files and uninstaller
  Delete $INSTDIR\*

  ; Remove shortcuts, if any
  Delete "$SMPROGRAMS\FastFlix\*.lnk"

  ; Remove directories
  RMDir "$SMPROGRAMS\FastFlix"
  RMDir /r "$INSTDIR"
  RMDir "$INSTDIR"

SectionEnd
