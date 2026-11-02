// FastFlix Installer
//
// Polished GUI installer drawn with raw Win32 calls and a dark theme.
// Supports per-user and all-users installation modes.
//
// Build (scripts/build_distribution.py --installer does all of this and injects the version):
//   cd cmd/installer && go-winres make && cd ../..
//   go build -ldflags="-s -w -H windowsgui -X main.Version=6.3.0 -X main.BuildDate=2026-01-01" -o FastFlix_installer.exe ./cmd/installer

package main

import (
	"os"
	"runtime"
	"strings"
	"syscall"
	"unsafe"

	"github.com/cdgriffith/fastflix-installer/cmd/internal/ffinstall"
	"golang.org/x/sys/windows/registry"
)

// Version and BuildDate are set at build time via -ldflags
var Version = "dev"
var BuildDate = "" // format: 2006-01-02

func main() {
	runtime.LockOSThread()

	// Single-instance check via named mutex (skipped for the silent elevated helpers)
	args := os.Args[1:]
	isHelper := containsArg(args, "--elevated-install") || containsArg(args, "--elevated-uninstall")
	if !isHelper {
		mutexName, _ := syscall.UTF16PtrFromString(`Global\FastFlixInstaller`)
		handle, _, err := kernel32DLL.NewProc("CreateMutexW").Call(0, 1, uintptr(unsafe.Pointer(mutexName)))
		if handle != 0 && err == syscall.ERROR_ALREADY_EXISTS {
			messageBox("FastFlix Installer", "The FastFlix installer is already running.", 0x40)
			return
		}
		// mutex handle stays open until process exits — no need to close it
	}

	// --elevated-install: silent elevated helper (extracts + registry + shortcuts)
	// Called by the GUI installer when "Install for all users" is clicked
	if containsArg(args, "--elevated-install") {
		runElevatedInstall(args)
		return
	}

	// --elevated-uninstall: silent elevated helper that removes protected (Program Files) installs
	if containsArg(args, "--elevated-uninstall") {
		runElevatedUninstall(args)
		return
	}

	// Default: show the installer GUI
	runInstallerGUI()
}

// runElevatedInstall does everything: extract embedded archive to dest, registry, shortcuts.
// Called as an elevated process — no UI. The outcome is reported only through the process exit code (see the
// exit* constants); the elevated process never writes to a path chosen by the unelevated caller.
func runElevatedInstall(args []string) {
	dst := getArgValue(args, "--dest")
	if dst == "" {
		os.Exit(exitError)
	}

	// Only ever install to the all-users location
	expected, regRoot, startMenu := installPaths(modeAllUsers)
	if !strings.EqualFold(strings.TrimRight(dst, `\`), expected) {
		os.Exit(exitBadLocation)
	}

	// Extract embedded archive directly to destination (includes uninstall.exe)
	if err := installFiles(dst, nil); err != nil {
		os.Exit(exitInstallFailed)
	}

	// Write HKLM registry + shortcuts
	writeRegistry(dst, regRoot)
	writeInstalledSize(dst, regRoot)
	if err := createShortcuts(dst, startMenu); err != nil {
		os.Exit(exitOKWithWarnings)
	}
	os.Exit(exitOK)
}

// runElevatedUninstall removes the given protected install directories (--dir, repeatable), then all HKLM
// keys and the common Start Menu / public desktop shortcuts. Elevated, no UI; reports via exit code.
func runElevatedUninstall(args []string) {
	problems := false
	for i, a := range args {
		if !strings.EqualFold(a, "--dir") || i+1 >= len(args) {
			continue
		}
		dir := args[i+1]
		if _, err := os.Stat(dir); err != nil {
			continue // already gone
		}
		// RemoveInstalledFiles validates the directory (SafeToRemove) and refuses anything that is not
		// clearly a FastFlix install, including the legacy delete-everything branch.
		if err := ffinstall.RemoveInstalledFiles(dir, ""); err != nil {
			problems = true
		}
	}

	ffinstall.CleanRegistry(registry.LOCAL_MACHINE)
	_, commonSM := startMenuDirs()
	os.RemoveAll(commonSM)
	os.Remove(publicDesktopShortcut())

	if problems {
		os.Exit(exitUninstallProbs)
	}
	os.Exit(exitOK)
}

func publicDesktopShortcut() string {
	return os.Getenv("PUBLIC") + `\Desktop\` + productName + ".lnk"
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
