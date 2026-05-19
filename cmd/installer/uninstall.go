package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"unsafe"

	"golang.org/x/sys/windows/registry"
)

// runUninstall performs the uninstallation for the given mode.
// Pass --silent in os.Args to skip confirmation dialogs (used when called from installer).
func runUninstall(mode installMode) {
	silent := containsArg(os.Args[1:], "--silent") || containsArg(os.Args[1:], "/S")

	regRoot := registry.CURRENT_USER
	if mode == modeAllUsers {
		if !isAdmin() {
			args := []string{"--uninstall", "--allusers"}
			if silent {
				args = append(args, "--silent")
			}
			relaunchAsAdmin(args...)
			os.Exit(0)
		}
		regRoot = registry.LOCAL_MACHINE
	}

	// Find install directory from registry
	installDir := ""
	appKey, err := registry.OpenKey(regRoot, `SOFTWARE\`+productName, registry.QUERY_VALUE)
	if err == nil {
		installDir, _, _ = appKey.GetStringValue("Install_Dir")
		appKey.Close()
	}

	if installDir == "" {
		if !silent {
			messageBox("Uninstall Error", productName+" installation not found.", 0x10)
		}
		return
	}

	if !silent {
		ret := messageBox("Uninstall "+productName,
			fmt.Sprintf("Remove %s from:\n%s\n\nContinue?", productName, installDir),
			0x01|0x40)
		if ret != 1 {
			return
		}
	}

	// Determine Start Menu path
	startMenu := filepath.Join(os.Getenv("APPDATA"), "Microsoft", "Windows", "Start Menu", "Programs", productName)
	if mode == modeAllUsers {
		startMenu = filepath.Join(os.Getenv("ProgramData"), "Microsoft", "Windows", "Start Menu", "Programs", productName)
	}

	// Remove Start Menu shortcuts
	os.RemoveAll(startMenu)

	// Remove registry keys
	registry.DeleteKey(regRoot, `Software\Microsoft\Windows\CurrentVersion\Uninstall\`+productName)
	registry.DeleteKey(regRoot, `SOFTWARE\`+productName)

	// Remove installation directory
	selfPath, _ := os.Executable()
	cleanInstallDir := filepath.Clean(installDir)
	cleanSelfPath := filepath.Clean(selfPath)

	// Check if we're running from inside the install directory
	runningFromInstallDir := strings.HasPrefix(strings.ToLower(cleanSelfPath), strings.ToLower(cleanInstallDir))

	if runningFromInstallDir {
		// Delete everything except our own exe, then schedule self-deletion
		filepath.Walk(cleanInstallDir, func(path string, info os.FileInfo, err error) error {
			if err != nil {
				return nil
			}
			cleanPath := filepath.Clean(path)
			if cleanPath == cleanSelfPath || cleanPath == cleanInstallDir {
				return nil
			}
			if info.IsDir() {
				os.RemoveAll(path)
				return filepath.SkipDir
			}
			os.Remove(path)
			return nil
		})

		// Schedule self-deletion after exit
		delCmd := fmt.Sprintf(
			`ping 127.0.0.1 -n 4 >nul & del /f /q "%s" & rmdir /s /q "%s"`,
			cleanSelfPath, cleanInstallDir)
		cmd := exec.Command("cmd", "/c", delCmd)
		cmd.SysProcAttr = &syscall.SysProcAttr{CreationFlags: 0x08000000}
		cmd.Start()
	} else {
		// We're the installer exe, not inside the install dir — just remove it
		os.RemoveAll(cleanInstallDir)
	}

	if !silent {
		messageBox("Uninstall Complete", productName+" has been removed.", 0x40)
	}
}

// runExistingUninstaller runs the uninstaller from a previous installation.
func runExistingUninstaller(uninstallStr string) {
	// Clean the uninstall string (may have quotes and flags)
	uninstallStr = strings.TrimSpace(uninstallStr)

	// Parse the command — it might be: "C:\path\uninstall.exe" --uninstall --user
	var exe string
	var args []string

	if strings.HasPrefix(uninstallStr, `"`) {
		// Quoted path
		end := strings.Index(uninstallStr[1:], `"`)
		if end >= 0 {
			exe = uninstallStr[1 : end+1]
			remaining := strings.TrimSpace(uninstallStr[end+2:])
			if remaining != "" {
				args = strings.Fields(remaining)
			}
		}
	} else {
		parts := strings.Fields(uninstallStr)
		if len(parts) > 0 {
			exe = parts[0]
			args = parts[1:]
		}
	}

	if exe == "" {
		return
	}

	// Add silent flags so the uninstaller doesn't show UI
	hasFlag := func(flag string) bool {
		for _, a := range args {
			if strings.EqualFold(a, flag) {
				return true
			}
		}
		return false
	}
	// NSIS uses /S, our Go uninstaller uses --silent
	if !hasFlag("/S") {
		args = append(args, "/S")
	}
	if !hasFlag("--silent") {
		args = append(args, "--silent")
	}

	cmd := exec.Command(exe, args...)
	cmd.SysProcAttr = &syscall.SysProcAttr{CreationFlags: 0x08000000} // CREATE_NO_WINDOW
	cmd.Run()
}

// messageBox shows a Windows message box and returns the button clicked.
func messageBox(title, msg string, flags uintptr) int {
	user32 := syscall.NewLazyDLL("user32.dll")
	proc := user32.NewProc("MessageBoxW")
	titlePtr, _ := syscall.UTF16PtrFromString(title)
	msgPtr, _ := syscall.UTF16PtrFromString(msg)
	ret, _, _ := proc.Call(0,
		uintptr(unsafe.Pointer(msgPtr)),
		uintptr(unsafe.Pointer(titlePtr)),
		flags)
	return int(ret)
}
