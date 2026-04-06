// FastFlix Launcher
//
// Native Go binary that launches FastFlix via Python's embeddable distribution.
// Replaces PyInstaller to avoid antivirus false positives caused by the
// PyInstaller bootloader's temp-extraction behavior.
//
// Build: go build -ldflags="-s -w" -o FastFlix.exe ./cmd/launcher

package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"unsafe"
)

// Version is set at build time via -ldflags="-X main.Version=6.3.0"
var Version = "dev"

func main() {
	// Resolve install directory from the launcher's own location
	exePath, err := os.Executable()
	if err != nil {
		fatal("Cannot resolve executable path: %v", err)
	}
	installDir := filepath.Dir(exePath)

	// Handle CLI flags
	if len(os.Args) > 1 {
		switch os.Args[1] {
		case "--version":
			fmt.Printf("FastFlix %s\n", Version)
			os.Exit(0)
		case "--test":
			// Pass --test through to Python for startup validation
			runPython(installDir, "python.exe", true)
			return
		case "--help":
			fmt.Printf("FastFlix %s\n", Version)
			fmt.Println("Usage: FastFlix.exe [--version] [--test] [--help]")
			os.Exit(0)
		}
	}

	// Normal launch: use python.exe (console visible for log output)
	runPython(installDir, "python.exe", false)
}

func runPython(installDir, pythonBin string, passArgs bool) {
	pythonDir := filepath.Join(installDir, "python")
	libDir := filepath.Join(installDir, "lib")
	pythonExe := filepath.Join(pythonDir, pythonBin)

	// Verify Python exists
	if _, err := os.Stat(pythonExe); os.IsNotExist(err) {
		fatal("Python not found at %s\nPlease reinstall FastFlix.", pythonExe)
	}

	// Build environment
	env := os.Environ()
	env = setEnv(env, "PYTHONHOME", pythonDir)
	env = setEnv(env, "PYTHONPATH", libDir)
	env = setEnv(env, "FASTFLIX_BUNDLED", "1")

	// Detect portable mode: fastflix.yaml next to the launcher
	portableConfig := filepath.Join(installDir, "fastflix.yaml")
	if _, err := os.Stat(portableConfig); err == nil {
		env = setEnv(env, "FASTFLIX_PORTABLE", "1")
	}

	// Prepend python/ and lib/PySide6/ to PATH for DLL discovery
	currentPath := os.Getenv("PATH")
	pyside6Dir := filepath.Join(libDir, "PySide6")
	newPath := pythonDir + ";" + pyside6Dir + ";" + currentPath
	env = setEnv(env, "PATH", newPath)

	// Set QT_PLUGIN_PATH so PySide6 finds its plugins
	env = setEnv(env, "QT_PLUGIN_PATH", filepath.Join(pyside6Dir, "plugins"))

	// Build command: python -m fastflix [args...]
	args := []string{pythonExe, "-m", "fastflix"}
	if passArgs && len(os.Args) > 1 {
		args = append(args, os.Args[1:]...)
	}

	// Set working directory to install dir so base_path resolves correctly
	cmd := exec.Command(args[0], args[1:]...)
	cmd.Dir = installDir
	cmd.Env = env
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin

	if err := cmd.Run(); err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			os.Exit(exitErr.ExitCode())
		}
		fatal("Failed to start FastFlix: %v", err)
	}
}

// setEnv sets or replaces an environment variable in the env slice.
func setEnv(env []string, key, value string) []string {
	prefix := key + "="
	for i, e := range env {
		if strings.HasPrefix(strings.ToUpper(e), strings.ToUpper(prefix)) {
			env[i] = prefix + value
			return env
		}
	}
	return append(env, prefix+value)
}

func fatal(format string, args ...any) {
	msg := fmt.Sprintf(format, args...)
	// Try to show a Windows message box since we may not have a console
	showMessageBox(msg)
	os.Exit(1)
}

func showMessageBox(msg string) {
	user32 := syscall.NewLazyDLL("user32.dll")
	messageBoxW := user32.NewProc("MessageBoxW")

	title, _ := syscall.UTF16PtrFromString("FastFlix Error")
	text, _ := syscall.UTF16PtrFromString(msg)

	const MB_OK = 0x00000000
	const MB_ICONERROR = 0x00000010
	// MessageBoxW(hWnd, lpText, lpCaption, uType)
	messageBoxW.Call(
		0, // NULL hWnd
		uintptr(unsafe.Pointer(text)),
		uintptr(unsafe.Pointer(title)),
		uintptr(MB_OK|MB_ICONERROR),
	)
}
