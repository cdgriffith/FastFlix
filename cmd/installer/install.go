package main

import (
	"archive/tar"
	"bytes"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"unsafe"

	"github.com/klauspost/compress/zstd"
	"golang.org/x/sys/windows/registry"
)

const (
	productName   = "FastFlix"
	productAuthor = "Chris Griffith"
)

// installMode determines where to install and which registry root to use.
type installMode int

const (
	modeUser     installMode = iota // Install for current user only
	modeAllUsers                    // Install for all users (admin required)
)

// installPaths returns the install directory, registry root, and Start Menu path for the given mode.
func installPaths(mode installMode) (installDir string, regRoot registry.Key, startMenu string) {
	switch mode {
	case modeUser:
		installDir = filepath.Join(os.Getenv("LOCALAPPDATA"), "Programs", productName)
		regRoot = registry.CURRENT_USER
		startMenu = filepath.Join(os.Getenv("APPDATA"), "Microsoft", "Windows", "Start Menu", "Programs", productName)
	case modeAllUsers:
		installDir = filepath.Join(os.Getenv("ProgramFiles"), productName)
		regRoot = registry.LOCAL_MACHINE
		startMenu = filepath.Join(os.Getenv("ProgramData"), "Microsoft", "Windows", "Start Menu", "Programs", productName)
	}
	return
}

// countArchiveEntries counts the number of file entries in the tar.zst archive.
func countArchiveEntries(data []byte) int {
	decoder, err := zstd.NewReader(bytes.NewReader(data))
	if err != nil {
		return 0
	}
	defer decoder.Close()

	count := 0
	tr := tar.NewReader(decoder)
	for {
		_, err := tr.Next()
		if err != nil {
			break
		}
		count++
	}
	return count
}

// extractTarZstd decompresses a tar.zst archive to the target directory.
// Calls progressFn(current, total) after each file is extracted.
func extractTarZstd(data []byte, targetDir string, progressFn func(current, total int)) error {
	total := countArchiveEntries(data)
	if total == 0 {
		total = 1
	}

	decoder, err := zstd.NewReader(bytes.NewReader(data))
	if err != nil {
		return fmt.Errorf("open zstd: %w", err)
	}
	defer decoder.Close()

	current := 0
	tr := tar.NewReader(decoder)
	for {
		header, err := tr.Next()
		if err == io.EOF {
			break
		}
		if err != nil {
			return fmt.Errorf("read tar: %w", err)
		}

		target := filepath.Join(targetDir, header.Name)

		// Prevent path traversal
		if !strings.HasPrefix(filepath.Clean(target), filepath.Clean(targetDir)+string(os.PathSeparator)) {
			continue
		}

		switch header.Typeflag {
		case tar.TypeDir:
			os.MkdirAll(target, 0755)
		case tar.TypeReg:
			os.MkdirAll(filepath.Dir(target), 0755)
			outFile, err := os.OpenFile(target, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, 0755)
			if err != nil {
				return fmt.Errorf("create %s: %w", header.Name, err)
			}
			_, err = io.Copy(outFile, tr)
			outFile.Close()
			if err != nil {
				return fmt.Errorf("extract %s: %w", header.Name, err)
			}
		}

		current++
		if progressFn != nil {
			progressFn(current, total)
		}
	}
	return nil
}

// writeRegistry creates registry entries for the installation.
func writeRegistry(installDir string, regRoot registry.Key) {
	// Application registry key
	appKey, _, _ := registry.CreateKey(regRoot, `SOFTWARE\`+productName, registry.SET_VALUE)
	if appKey != 0 {
		appKey.SetStringValue("Install_Dir", installDir)
		appKey.Close()
	}

	// Determine uninstall flag based on mode
	uninstallFlag := "--user"
	if regRoot == registry.LOCAL_MACHINE {
		uninstallFlag = "--allusers"
	}

	// Uninstall registry key
	uninstallKeyPath := `Software\Microsoft\Windows\CurrentVersion\Uninstall\` + productName
	uKey, _, _ := registry.CreateKey(regRoot, uninstallKeyPath, registry.SET_VALUE)
	if uKey != 0 {
		uKey.SetStringValue("DisplayName", productName)
		uKey.SetStringValue("DisplayVersion", Version)
		uKey.SetStringValue("Publisher", productAuthor)
		uKey.SetStringValue("DisplayIcon", filepath.Join(installDir, "FastFlix.exe"))
		uKey.SetStringValue("UninstallString", `"`+filepath.Join(installDir, "uninstall.exe")+`" --uninstall `+uninstallFlag)
		uKey.SetStringValue("InstallLocation", installDir)
		uKey.SetDWordValue("NoModify", 1)
		uKey.SetDWordValue("NoRepair", 1)
		uKey.Close()
	}
}

// writeInstalledSize calculates and writes the EstimatedSize registry value.
func writeInstalledSize(installDir string, regRoot registry.Key) {
	var totalKB int64
	filepath.Walk(installDir, func(path string, info os.FileInfo, err error) error {
		if err == nil && !info.IsDir() {
			totalKB += info.Size() / 1024
		}
		return nil
	})

	uKey, err := registry.OpenKey(regRoot,
		`Software\Microsoft\Windows\CurrentVersion\Uninstall\`+productName,
		registry.SET_VALUE)
	if err == nil {
		uKey.SetDWordValue("EstimatedSize", uint32(totalKB))
		uKey.Close()
	}
}

// createShortcuts creates Start Menu shortcuts.
func createShortcuts(installDir, startMenu string) {
	os.MkdirAll(startMenu, 0755)

	createShortcutFile(
		filepath.Join(startMenu, productName+".lnk"),
		filepath.Join(installDir, "FastFlix.exe"),
		installDir,
		"FastFlix Video Encoder",
	)
}

// createShortcutFile creates a .lnk shortcut via PowerShell.
func createShortcutFile(lnkPath, targetPath, workDir, description string) {
	script := fmt.Sprintf(
		`$ws = New-Object -ComObject WScript.Shell; `+
			`$sc = $ws.CreateShortcut('%s'); `+
			`$sc.TargetPath = '%s'; `+
			`$sc.WorkingDirectory = '%s'; `+
			`$sc.Description = '%s'; `+
			`$sc.Save()`,
		lnkPath, targetPath, workDir, description,
	)
	cmd := exec.Command("powershell", "-NoProfile", "-Command", script)
	cmd.SysProcAttr = &syscall.SysProcAttr{CreationFlags: 0x08000000}
	cmd.Run()
}

// copyFile copies a file from src to dst.
func copyFile(src, dst string) error {
	data, err := os.ReadFile(src)
	if err != nil {
		return err
	}
	return os.WriteFile(dst, data, 0755)
}

// isAdmin checks if the current process has admin privileges.
func isAdmin() bool {
	_, err := os.Open("\\\\.\\PHYSICALDRIVE0")
	return err == nil
}

// relaunchAsAdmin re-launches with admin privileges and the given extra args.
func relaunchAsAdmin(extraArgs ...string) {
	verb, _ := syscall.UTF16PtrFromString("runas")
	exe, _ := syscall.UTF16PtrFromString(os.Args[0])

	args := strings.Join(extraArgs, " ")
	argPtr, _ := syscall.UTF16PtrFromString(args)
	cwd, _ := syscall.UTF16PtrFromString(".")

	shell32 := syscall.NewLazyDLL("shell32.dll")
	shellExecute := shell32.NewProc("ShellExecuteW")
	shellExecute.Call(0, uintptr(unsafe.Pointer(verb)), uintptr(unsafe.Pointer(exe)),
		uintptr(unsafe.Pointer(argPtr)), uintptr(unsafe.Pointer(cwd)), 1)
}

// existingInstall represents a single discovered FastFlix installation.
type existingInstall struct {
	RegRoot      registry.Key
	InstallDir   string
	UninstallStr string
	Version      string
}

// cleanupInstallation performs a thorough removal of a FastFlix installation.
// Handles both old NSIS installs and new Go installer installs, removing:
// - The install directory itself (elevates via UAC if in Program Files)
// - Start Menu shortcuts (all known locations)
// - Registry keys (both HKLM and HKCU)
// - Desktop shortcuts if any
// Returns true if elevation was needed and launched (caller should wait for re-run).
func cleanupInstallation(inst existingInstall) bool {
	elevated := false

	// 1. Remove the install directory
	if inst.InstallDir != "" {
		err := os.RemoveAll(inst.InstallDir)
		if err != nil && isProtectedPath(inst.InstallDir) && !isAdmin() {
			// Need admin to delete from Program Files — elevate
			elevated = true
			elevatedCleanup(inst.InstallDir)
		}
	}

	// 2. Remove Start Menu shortcuts from ALL possible locations
	startMenuPaths := []string{
		// Common (all-users) Start Menu — old NSIS installer uses this
		filepath.Join(os.Getenv("ProgramData"), "Microsoft", "Windows", "Start Menu", "Programs", productName),
		// User Start Menu — new Go installer user-mode uses this
		filepath.Join(os.Getenv("APPDATA"), "Microsoft", "Windows", "Start Menu", "Programs", productName),
	}
	for _, sm := range startMenuPaths {
		if _, err := os.Stat(sm); err == nil {
			err2 := os.RemoveAll(sm)
			if err2 != nil && !isAdmin() {
				elevatedDelete(sm)
			}
		}
	}

	// 3. Remove Desktop shortcuts if present
	desktopPaths := []string{
		filepath.Join(os.Getenv("USERPROFILE"), "Desktop", productName+".lnk"),
		filepath.Join(os.Getenv("PUBLIC"), "Desktop", productName+".lnk"),
	}
	for _, d := range desktopPaths {
		os.Remove(d)
	}

	// 4. Remove ALL registry keys (both roots, all paths including WOW6432Node)
	cleanAllRegistryKeys()

	return elevated
}

// isProtectedPath checks if a path is under Program Files or another admin-protected location.
func isProtectedPath(dir string) bool {
	dirLower := strings.ToLower(filepath.Clean(dir))
	protectedRoots := []string{
		strings.ToLower(os.Getenv("ProgramFiles")),
		strings.ToLower(os.Getenv("ProgramW6432")),
	}
	programFilesX86 := os.Getenv("ProgramFiles(x86)")
	if programFilesX86 != "" {
		protectedRoots = append(protectedRoots, strings.ToLower(programFilesX86))
	}
	for _, root := range protectedRoots {
		if root != "" && strings.HasPrefix(dirLower, root) {
			return true
		}
	}
	return false
}

// elevatedCleanup runs an elevated cmd.exe to remove a directory that requires admin access.
// Triggers a UAC prompt.
func elevatedCleanup(dir string) {
	// Use cmd /c rmdir /s /q via ShellExecute with "runas" verb
	verb, _ := syscall.UTF16PtrFromString("runas")
	exe, _ := syscall.UTF16PtrFromString("cmd.exe")
	args, _ := syscall.UTF16PtrFromString(`/c rmdir /s /q "` + dir + `"`)
	cwd, _ := syscall.UTF16PtrFromString(".")

	shell32 := syscall.NewLazyDLL("shell32.dll")
	shellExecute := shell32.NewProc("ShellExecuteW")
	shellExecute.Call(0, uintptr(unsafe.Pointer(verb)), uintptr(unsafe.Pointer(exe)),
		uintptr(unsafe.Pointer(args)), uintptr(unsafe.Pointer(cwd)), 0) // SW_HIDE
}

// elevatedDelete runs an elevated cmd.exe to remove a file/directory that requires admin access.
func elevatedDelete(path string) {
	info, err := os.Stat(path)
	if err != nil {
		return
	}
	verb, _ := syscall.UTF16PtrFromString("runas")
	exe, _ := syscall.UTF16PtrFromString("cmd.exe")
	var cmdArgs string
	if info.IsDir() {
		cmdArgs = `/c rmdir /s /q "` + path + `"`
	} else {
		cmdArgs = `/c del /f /q "` + path + `"`
	}
	args, _ := syscall.UTF16PtrFromString(cmdArgs)
	cwd, _ := syscall.UTF16PtrFromString(".")

	shell32 := syscall.NewLazyDLL("shell32.dll")
	shellExecute := shell32.NewProc("ShellExecuteW")
	shellExecute.Call(0, uintptr(unsafe.Pointer(verb)), uintptr(unsafe.Pointer(exe)),
		uintptr(unsafe.Pointer(args)), uintptr(unsafe.Pointer(cwd)), 0) // SW_HIDE
}

// cleanAllRegistryKeys removes all FastFlix registry keys from all known locations,
// including the WOW6432Node path that 32-bit NSIS installers write to.
func cleanAllRegistryKeys() {
	regPaths := []string{
		`Software\Microsoft\Windows\CurrentVersion\Uninstall\` + productName,
		`Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\` + productName,
		`SOFTWARE\` + productName,
	}
	for _, root := range []registry.Key{registry.LOCAL_MACHINE, registry.CURRENT_USER} {
		for _, p := range regPaths {
			registry.DeleteKey(root, p)
		}
	}
}

// findAllExistingInstalls checks both registry and known disk paths for existing FastFlix installations.
// Returns all found installations (could be multiple: old NSIS in Program Files + user install).
func findAllExistingInstalls() []existingInstall {
	var results []existingInstall
	seen := map[string]bool{} // deduplicate by install dir (lowercased)

	// 1. Check registry (both HKLM and HKCU, including WOW6432Node for 32-bit NSIS installs)
	uninstallPaths := []string{
		`Software\Microsoft\Windows\CurrentVersion\Uninstall\` + productName,
		`Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\` + productName,
	}
	for _, root := range []registry.Key{registry.LOCAL_MACHINE, registry.CURRENT_USER} {
		for _, regPath := range uninstallPaths {
			uKey, err := registry.OpenKey(root, regPath, registry.QUERY_VALUE)
			if err != nil {
				continue
			}
			dir, _, _ := uKey.GetStringValue("InstallLocation")
			if dir == "" {
				// Try the old NSIS-style key
				appKey, err2 := registry.OpenKey(root, `SOFTWARE\`+productName, registry.QUERY_VALUE)
				if err2 == nil {
					dir, _, _ = appKey.GetStringValue("Install_Dir")
					appKey.Close()
				}
			}
			uninstall, _, _ := uKey.GetStringValue("UninstallString")
			version, _, _ := uKey.GetStringValue("DisplayVersion")
			uKey.Close()

			if dir != "" || uninstall != "" {
				dirKey := strings.ToLower(filepath.Clean(dir))
				if !seen[dirKey] {
					seen[dirKey] = true
					results = append(results, existingInstall{
						RegRoot:      root,
						InstallDir:   dir,
						UninstallStr: uninstall,
						Version:      version,
					})
				}
			}
		}
	}

	// 2. Check known disk paths even if registry keys are missing
	// (handles installs where registry was cleaned up or never written)
	knownPaths := []string{
		filepath.Join(os.Getenv("ProgramFiles"), productName),
		filepath.Join(os.Getenv("LOCALAPPDATA"), "Programs", productName),
	}
	for _, dir := range knownPaths {
		dirKey := strings.ToLower(filepath.Clean(dir))
		if seen[dirKey] {
			continue
		}
		// Check if FastFlix.exe exists at this path
		exePath := filepath.Join(dir, "FastFlix.exe")
		if _, err := os.Stat(exePath); err != nil {
			continue
		}
		seen[dirKey] = true
		// Check for uninstaller
		uninstallStr := ""
		uninstallExe := filepath.Join(dir, "uninstall.exe")
		if _, err := os.Stat(uninstallExe); err == nil {
			uninstallStr = `"` + uninstallExe + `" --uninstall`
		}
		results = append(results, existingInstall{
			InstallDir:   dir,
			UninstallStr: uninstallStr,
		})
	}

	return results
}
