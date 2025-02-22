; FastFlix.nsi
;

!include "MUI2.nsh"
!include LogicLib.nsh
!include "TextFunc.nsh"
!include "FileFunc.nsh"

;--------------------------------

!define PRODUCT_NAME      "FastFlix"
!define PRODUCT_AUTHOR    "Chris Griffith"
!define PRODUCT_COPYRIGHT "(c) Chris Griffith 2019-2025"

VIProductVersion "${PRODUCT_VERSION}"
VIFileVersion    "${PRODUCT_VERSION}"

; -------------------------------------------------------------------- Installer exe properties

VIAddVersionKey "ProductName"        "${PRODUCT_NAME}"
VIAddVersionKey "ProductVersion"     "${PRODUCT_VERSION}"
VIAddVersionKey "CompanyName"        "${PRODUCT_AUTHOR}"
VIAddVersionKey "LegalTrademarks"    "${PRODUCT_COPYRIGHT}"
VIAddVersionKey "LegalCopyright"     "${PRODUCT_COPYRIGHT}"
VIAddVersionKey "FileVersion"        "${PRODUCT_VERSION}"
VIAddVersionKey "FileDescription"    "${PRODUCT_NAME} installer"

VIAddVersionKey "InternalName"       "${PRODUCT_NAME}"


; The name of the installer
Name "${PRODUCT_NAME} ${VERSION}"

; The file to write
OutFile "FastFlix_installer.exe"

; Request application privileges for Windows Vista and higher
RequestExecutionLevel admin

; Build Unicode installer
Unicode True

SetCompressor lzma

; The default installation directory
InstallDir $PROGRAMFILES64\${PRODUCT_NAME}

; Registry key to check for directory (so if you install again, it will overwrite the old one automatically)
InstallDirRegKey HKLM "Software\${PRODUCT_NAME}" "Install_Dir"

;--------------------------------

; Pages

  !insertmacro MUI_PAGE_LICENSE "docs\build-licenses.txt"
  !insertmacro MUI_PAGE_COMPONENTS
  !insertmacro MUI_PAGE_DIRECTORY
  !insertmacro MUI_PAGE_INSTFILES

  !insertmacro MUI_UNPAGE_CONFIRM
  !insertmacro MUI_UNPAGE_INSTFILES
  !define MUI_FINISHPAGE_TEXT "$(LSTR05)"
  !insertmacro MUI_PAGE_FINISH
;Languages

  !insertmacro MUI_LANGUAGE "English"
  !insertmacro MUI_LANGUAGE "Italian"

  LangString LSTR01 1033  "Before proceeding with the installation of ${PRODUCT_NAME} you must uninstall the currently installed version.$\r$\n$\r$\nPlease ensure that ${PRODUCT_NAME} is not currently running!"
  LangString LSTR02 1033  "FastFlix (required)"
  LangString LSTR03 1033  "Start Menu Shortcuts"
  LangString LSTR04 1033  "Uninstall"
  LangString LSTR05 1033  "Thank you for installing ${PRODUCT_NAME}!"

  LangString LSTR01 1040  "Prima di procedere all'installazione di ${PRODUCT_NAME} è necessario disinstallare la versione attualmente installata.$\r$\n$\r$\nAssicurati che ${PRODUCT_NAME} non sia attualmente in esecuzione!"
  LangString LSTR02 1040  "FastFlix (richiesto)"
  LangString LSTR03 1040  "Collegamenti menu Start"
  LangString LSTR04 1040  "Disinstalla"
  LangString LSTR05 1040  "Grazie per aver installato ${PRODUCT_NAME}!"


;--------------------------------
Function .onInit
  ReadRegStr $0 HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\FastFlix" "UninstallString"
  ${If} $0 != ""
    Messagebox MB_OK|MB_ICONINFORMATION  "$(LSTR01)"
    ExecWait '$0 _?=$INSTDIR'
  ${EndIf}
FunctionEnd


; The stuff to install
Section "$(LSTR02)"

  SectionIn RO

  ; Set output path to the installation directory.
  SetOutPath $INSTDIR


  Delete "$INSTDIR\uninstall.exe"
  ; Put file there
  File /r "dist\${PRODUCT_NAME}\*"

  ; Write the installation path into the registry
  WriteRegStr HKLM SOFTWARE\${PRODUCT_NAME} "Install_Dir" "$INSTDIR"
  WriteRegStr HKLM SOFTWARE\${PRODUCT_NAME} "UninstallString" '"$INSTDIR\uninstall.exe"'

  ; Write the uninstall keys for Windows
  WriteRegStr   HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" "DisplayName" "${PRODUCT_NAME}"
  WriteRegStr   HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" "DisplayVersion" "${VERSION}"
  WriteRegStr   HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" "Publisher" "${PRODUCT_AUTHOR}"
  WriteRegStr   HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" "DisplayIcon" "$INSTDIR\FastFlix.exe"
  WriteRegStr   HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" "NoRepair" 1

  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0 #< conv to DWORD
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" "EstimatedSize" "$0"

  WriteUninstaller "$INSTDIR\uninstall.exe"

SectionEnd

; Optional section (can be disabled by the user)
Section "$(LSTR03)"

  CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
  CreateShortcut  "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk" "$INSTDIR\FastFlix.exe"
  CreateShortcut  "$SMPROGRAMS\${PRODUCT_NAME}\$(LSTR04) ${PRODUCT_NAME}.lnk" "$INSTDIR\uninstall.exe"

SectionEnd

; Uninstaller

Section "Uninstall"

  ; Remove registry keys
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
  DeleteRegKey HKLM SOFTWARE\${PRODUCT_NAME}

  ; Remove files
  Delete $INSTDIR\*

  ; Remove shortcuts, if any
  Delete "$SMPROGRAMS\${PRODUCT_NAME}\*.lnk"

  ; Remove directories
  RMDir "$SMPROGRAMS\${PRODUCT_NAME}"
  RMDir /r "$INSTDIR"
  RMDir "$INSTDIR"

  Delete "$INSTDIR\uninstall.exe"

SectionEnd
