// FastFlix Installer
//
// Polished GUI installer using lxn/walk with dark theme.
// Supports per-user and all-users installation modes.
//
// Build:
//   go build -ldflags="-s -w -H windowsgui -X main.Version=6.3.0" -o FastFlix_installer.exe ./cmd/installer

package main

import (
	"os"
	"os/exec"
	"runtime"
	"strings"
	"syscall"
	"unsafe"
)

// Version and BuildDate are set at build time via -ldflags
var Version = "dev"
var BuildDate = "" // format: 2006-01-02

func main() {
	runtime.LockOSThread()

	// Single-instance check via named mutex (skip for elevated helpers and uninstall mode)
	args := os.Args[1:]
	isHelper := containsArg(args, "--elevated-install") || containsArg(args, "--elevated-copy") || containsArg(args, "--uninstall")
	if !isHelper {
		mutexName, _ := syscall.UTF16PtrFromString("Global\\FastFlixInstaller")
		handle, _, err := kernel32DLL.NewProc("CreateMutexW").Call(0, 1, uintptr(unsafe.Pointer(mutexName)))
		if handle != 0 && err == syscall.ERROR_ALREADY_EXISTS {
			messageBox("FastFlix Installer", "The FastFlix installer is already running.", 0x40)
			return
		}
		// mutex handle stays open until process exits — no need to close it
	}

	// Handle command-line flags

	// --elevated-install: silent elevated helper (extracts + registry + shortcuts)
	// Called by the GUI installer when "Install for all users" is clicked
	if containsArg(args, "--elevated-install") {
		runElevatedInstall(args)
		return
	}

	// Legacy --elevated-copy for backwards compat
	if containsArg(args, "--elevated-copy") {
		runElevatedCopy(args)
		return
	}

	// Default: show the installer GUI
	runInstallerGUI()
}

// runElevatedCopy is a silent elevated helper that copies an already-extracted
// distribution from a temp directory to Program Files and writes HKLM registry.
// Called with: --elevated-copy --source <tempdir> --dest <installdir>
func runElevatedCopy(args []string) {
	src := getArgValue(args, "--source")
	dst := getArgValue(args, "--dest")
	if src == "" || dst == "" {
		os.Exit(1)
	}

	// Copy files from temp to Program Files
	os.MkdirAll(dst, 0755)
	// Use robocopy for reliable admin copy
	cmd := exec.Command("robocopy", src, dst, "/E", "/NFL", "/NDL", "/NJH", "/NJS", "/nc", "/ns", "/np")
	cmd.SysProcAttr = &syscall.SysProcAttr{CreationFlags: 0x08000000}
	cmd.Run()
	// robocopy returns non-zero on success (1=files copied), only 8+ is error

	// Write HKLM registry
	_, regRoot, startMenu := installPaths(modeAllUsers)
	writeRegistry(dst, regRoot)
	writeInstalledSize(dst, regRoot)
	createShortcuts(dst, startMenu)

	// Write success marker
	os.WriteFile(src+`\.done`, []byte("ok"), 0644)
}

// runElevatedInstall does everything: extract embedded archive to dest, registry, shortcuts.
// Called as an elevated process — no UI, writes a marker file when done.
func runElevatedInstall(args []string) {
	dst := getArgValue(args, "--dest")
	marker := getArgValue(args, "--marker")
	if dst == "" {
		os.Exit(1)
	}

	// Extract embedded archive directly to destination (includes uninstall.exe)
	os.MkdirAll(dst, 0755)
	extractTarZstd(distArchive, dst, nil)

	// Write HKLM registry + shortcuts
	_, regRoot, startMenu := installPaths(modeAllUsers)
	writeRegistry(dst, regRoot)
	writeInstalledSize(dst, regRoot)
	createShortcuts(dst, startMenu)

	// Write completion marker
	if marker != "" {
		os.WriteFile(marker, []byte("ok"), 0644)
	}
}

func getArgValue(args []string, key string) string {
	for i, a := range args {
		if strings.EqualFold(a, key) && i+1 < len(args) {
			return args[i+1]
		}
	}
	return ""
}

func containsArg(args []string, flag string) bool {
	for _, a := range args {
		if strings.EqualFold(a, flag) {
			return true
		}
	}
	return false
}
