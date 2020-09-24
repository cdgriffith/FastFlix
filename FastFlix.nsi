; FastFlix.nsi
;

!include "MUI2.nsh"
!include LogicLib.nsh
;--------------------------------

; The name of the installer
Name "FastFlix"

; The file to write
OutFile "FastFlix_installer.exe"

; Request application privileges for Windows Vista and higher
RequestExecutionLevel admin

; Build Unicode installer
Unicode True

SetCompressor lzma

; The default installation directory
InstallDir $PROGRAMFILES64\FastFlix

; Registry key to check for directory (so if you install again, it will overwrite the old one automatically)
InstallDirRegKey HKLM "Software\FastFlix" "Install_Dir"

;--------------------------------

; Pages

  !insertmacro MUI_PAGE_COMPONENTS
  !insertmacro MUI_PAGE_DIRECTORY
  !insertmacro MUI_PAGE_INSTFILES

  !insertmacro MUI_UNPAGE_CONFIRM
  !insertmacro MUI_UNPAGE_INSTFILES
  !define MUI_FINISHPAGE_RUN
  !define MUI_FINISHPAGE_RUN_TEXT "Start FastFlix"
  !define MUI_FINISHPAGE_RUN_FUNCTION "LaunchLink"
  !insertmacro MUI_PAGE_FINISH


;Languages

  !insertmacro MUI_LANGUAGE "English"

;--------------------------------
Function .onInit
  ReadRegStr $0 HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\FastFlix" "UninstallString"
  ${If} $0 != ""
    Messagebox MB_OK|MB_ICONINFORMATION  "You will now be prompted to first uninstall the previous version of FastFlix"
    ExecWait '$0 _?=$INSTDIR'
  ${EndIf}
FunctionEnd


; The stuff to install
Section "FastFlix (required)"

  SectionIn RO

  ; Set output path to the installation directory.
  SetOutPath $INSTDIR

  Delete "$INSTDIR\uninstall.exe"
  ; Put file there
  File /r "dist\FastFlix\*"

  ; Write the installation path into the registry
  WriteRegStr HKLM SOFTWARE\FastFlix "Install_Dir" "$INSTDIR"
  WriteRegStr HKLM SOFTWARE\FastFlix "UninstallString" '"$INSTDIR\uninstall.exe"'

  ; Write the uninstall keys for Windows
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\FastFlix" "DisplayName" "FastFlix"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\FastFlix" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\FastFlix" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\FastFlix" "NoRepair" 1
  WriteUninstaller "$INSTDIR\uninstall.exe"

SectionEnd

Function LaunchLink
  ExecShell "" "$INSTDIR\FastFlix.exe"
FunctionEnd

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

  ; Remove files
  Delete $INSTDIR\*

  ; Remove shortcuts, if any
  Delete "$SMPROGRAMS\FastFlix\*.lnk"

  ; Remove directories
  RMDir "$SMPROGRAMS\FastFlix"
  RMDir /r "$INSTDIR"
  RMDir "$INSTDIR"

  Delete "$INSTDIR\uninstall.exe"

SectionEnd
