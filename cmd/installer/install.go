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
	"time"
	"unsafe"

	"github.com/cdgriffith/fastflix-installer/cmd/internal/ffinstall"
	"github.com/klauspost/compress/zstd"
	"golang.org/x/sys/windows/registry"
)

const (
	productName   = ffinstall.ProductName
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
// Returns the relative paths of the files that were extracted (also on error, for cleanup).
func extractTarZstd(data []byte, targetDir string, progressFn func(current, total int)) ([]string, error) {
	total := countArchiveEntries(data)
	if total == 0 {
		total = 1
	}

	decoder, err := zstd.NewReader(bytes.NewReader(data))
	if err != nil {
		return nil, fmt.Errorf("open zstd: %w", err)
	}
	defer decoder.Close()

	var files []string
	current := 0
	tr := tar.NewReader(decoder)
	for {
		header, err := tr.Next()
		if err == io.EOF {
			break
		}
		if err != nil {
			return files, fmt.Errorf("read tar: %w", err)
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
			files = append(files, filepath.ToSlash(header.Name))
			outFile, err := os.OpenFile(target, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, 0755)
			if err != nil {
				return files, fmt.Errorf("create %s: %w", header.Name, err)
			}
			_, err = io.Copy(outFile, tr)
			outFile.Close()
			if err != nil {
				return files, fmt.Errorf("extract %s: %w", header.Name, err)
			}
		}

		current++
		if progressFn != nil {
			progressFn(current, total)
		}
	}
	return files, nil
}

// installFiles extracts the embedded distribution into dir and records an install manifest so a later
// uninstall removes exactly these files. On failure everything extracted so far is removed again.
func installFiles(dir string, progressFn func(current, total int)) error {
	if err := os.MkdirAll(dir, 0755); err != nil {
		return err
	}
	files, err := extractTarZstd(distArchive, dir, progressFn)
	if err != nil {
		ffinstall.RemoveExtracted(dir, files)
		return err
	}
	if err := ffinstall.WriteManifest(dir, files); err != nil {
		ffinstall.RemoveExtracted(dir, files)
		return fmt.Errorf("write install manifest: %w", err)
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
	uKey, _, _ := registry.CreateKey(regRoot, ffinstall.RegistryUninstallPaths[0], registry.SET_VALUE)
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

	uKey, err := registry.OpenKey(regRoot, ffinstall.RegistryUninstallPaths[0], registry.SET_VALUE)
	if err == nil {
		uKey.SetDWordValue("EstimatedSize", uint32(totalKB))
		uKey.Close()
	}
}

// createShortcuts creates Start Menu shortcuts.
func createShortcuts(installDir, startMenu string) error {
	if err := os.MkdirAll(startMenu, 0755); err != nil {
		return err
	}
	return createShortcutFile(
		filepath.Join(startMenu, productName+".lnk"),
		filepath.Join(installDir, "FastFlix.exe"),
		installDir,
		"FastFlix Video Encoder",
	)
}

// createShortcutFile creates a .lnk shortcut via PowerShell. The paths are handed over through environment
// variables, never interpolated into the script, so quotes or other characters in a path cannot break it.
func createShortcutFile(lnkPath, targetPath, workDir, description string) error {
	script := `$ws = New-Object -ComObject WScript.Shell; ` +
		`$sc = $ws.CreateShortcut($env:FF_LNK); ` +
		`$sc.TargetPath = $env:FF_TARGET; ` +
		`$sc.WorkingDirectory = $env:FF_WORKDIR; ` +
		`$sc.Description = $env:FF_DESC; ` +
		`$sc.Save()`
	cmd := exec.Command("powershell", "-NoProfile", "-NonInteractive", "-Command", script)
	cmd.Env = append(os.Environ(),
		"FF_LNK="+lnkPath, "FF_TARGET="+targetPath, "FF_WORKDIR="+workDir, "FF_DESC="+description)
	cmd.SysProcAttr = &syscall.SysProcAttr{CreationFlags: 0x08000000}
	out, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("create shortcut %s: %v %s", lnkPath, err, strings.TrimSpace(string(out)))
	}
	if _, statErr := os.Stat(lnkPath); statErr != nil {
		return fmt.Errorf("shortcut %s was not created", lnkPath)
	}
	return nil
}

// existingInstall represents a single discovered FastFlix installation.
type existingInstall struct {
	RegRoot      registry.Key
	InstallDir   string
	UninstallStr string
	Version      string
}

// installNeedsAdmin reports whether removing inst requires elevation: it lives in Program Files or its
// registration is under HKLM (all-users).
func installNeedsAdmin(inst existingInstall) bool {
	return inst.RegRoot == registry.LOCAL_MACHINE ||
		(inst.InstallDir != "" && ffinstall.IsProtectedPath(inst.InstallDir))
}

// startMenuDirs returns the per-user and common Start Menu folders for FastFlix.
func startMenuDirs() (user, common string) {
	user = filepath.Join(os.Getenv("APPDATA"), "Microsoft", "Windows", "Start Menu", "Programs", productName)
	common = filepath.Join(os.Getenv("ProgramData"), "Microsoft", "Windows", "Start Menu", "Programs", productName)
	return
}

// cleanupInstallation removes a FastFlix installation: its files (user files such as a portable
// fastflix.yaml are preserved), Start Menu and desktop shortcuts, and registry keys.
// Installs in Program Files need admin; those are handled up-front by runElevatedUninstall.
func cleanupInstallation(inst existingInstall) {
	if inst.InstallDir != "" {
		if _, err := os.Stat(inst.InstallDir); err == nil {
			// Refuses (returns an error) for anything that is not clearly a FastFlix folder
			ffinstall.RemoveInstalledFiles(inst.InstallDir, "")
		}
	}

	userSM, commonSM := startMenuDirs()
	os.RemoveAll(userSM)
	os.RemoveAll(commonSM) // fails harmlessly without admin; the elevated step handles it

	os.Remove(filepath.Join(os.Getenv("USERPROFILE"), "Desktop", productName+".lnk"))
	os.Remove(filepath.Join(os.Getenv("PUBLIC"), "Desktop", productName+".lnk"))

	cleanAllRegistryKeys()
}

// cleanAllRegistryKeys removes all FastFlix registry keys from all known locations,
// including the WOW6432Node paths that the 32-bit NSIS installer wrote to.
func cleanAllRegistryKeys() {
	for _, root := range []registry.Key{registry.LOCAL_MACHINE, registry.CURRENT_USER} {
		ffinstall.CleanRegistry(root)
	}
}

// launchElevated starts the installer exe elevated (UAC) with the given arguments. Returns false if the
// user declined the prompt or ShellExecute failed.
func launchElevated(args string) bool {
	selfPath, err := os.Executable()
	if err != nil {
		return false
	}
	verb, _ := syscall.UTF16PtrFromString("runas")
	exe, _ := syscall.UTF16PtrFromString(selfPath)
	argPtr, _ := syscall.UTF16PtrFromString(args)
	cwd, _ := syscall.UTF16PtrFromString(filepath.Dir(selfPath))
	ret, _, _ := syscall.NewLazyDLL("shell32.dll").NewProc("ShellExecuteW").Call(0,
		uintptr(unsafe.Pointer(verb)), uintptr(unsafe.Pointer(exe)),
		uintptr(unsafe.Pointer(argPtr)), uintptr(unsafe.Pointer(cwd)), 0) // SW_HIDE
	return ret > 32
}

// elevatedUninstall removes the given (protected) install directories plus all HKLM keys and the common
// Start Menu entry in one elevated helper run. Returns false if elevation was refused or the helper failed.
func elevatedUninstall(dirs []string) (ok bool, detail string) {
	tempDir, err := os.MkdirTemp("", "fastflix-uninstall-*")
	if err != nil {
		return false, err.Error()
	}
	defer os.RemoveAll(tempDir)
	marker := filepath.Join(tempDir, ".done")

	args := `--elevated-uninstall --marker "` + marker + `"`
	for _, d := range dirs {
		if err := ffinstall.ValidatePathString(d); err != nil {
			return false, err.Error()
		}
		args += ` --dir "` + d + `"`
	}
	if !launchElevated(args) {
		return false, "elevation was declined"
	}
	result, done := waitForMarker(marker, 120, nil)
	if !done {
		return false, "timed out waiting for the elevated helper"
	}
	if strings.HasPrefix(result, "error") {
		return false, result
	}
	return true, ""
}

// waitForMarker polls for a marker file for up to maxSeconds and returns its contents.
func waitForMarker(marker string, maxSeconds int, tick func(i int)) (string, bool) {
	for i := 1; i <= maxSeconds*2; i++ {
		if data, err := os.ReadFile(marker); err == nil {
			return strings.TrimSpace(string(data)), true
		}
		if tick != nil {
			tick(i)
		}
		time.Sleep(500 * time.Millisecond)
	}
	return "", false
}

// fastflixRunning reports whether FastFlix (or an orphaned bundled python.exe) is running.
func fastflixRunning() bool {
	pf, _, _ := installPaths(modeAllUsers)
	local, _, _ := installPaths(modeUser)
	dirs := []string{pf, local}
	for _, inst := range state.existingInstalls {
		dirs = append(dirs, inst.InstallDir)
	}
	return ffinstall.IsRunning(dirs...)
}

// findAllExistingInstalls checks both registry and known disk paths for existing FastFlix installations.
// Returns all found installations (could be multiple: old NSIS in Program Files + user install).
func findAllExistingInstalls() []existingInstall {
	var results []existingInstall
	seen := map[string]bool{} // deduplicate by install dir (lowercased)

	// 1. Check registry: HKLM and HKCU, in both the 64-bit and the 32-bit (WOW6432Node) view, because the
	// old 32-bit NSIS installer wrote its keys to the 32-bit view and never set InstallLocation.
	for _, root := range []registry.Key{registry.LOCAL_MACHINE, registry.CURRENT_USER} {
		for _, view := range []uint32{0, registry.WOW64_32KEY} {
			uKey, err := registry.OpenKey(root, ffinstall.RegistryUninstallPaths[0], registry.QUERY_VALUE|view)
			if err != nil {
				continue
			}
			dir, _, _ := uKey.GetStringValue("InstallLocation")
			uninstall, _, _ := uKey.GetStringValue("UninstallString")
			version, _, _ := uKey.GetStringValue("DisplayVersion")
			uKey.Close()

			if dir == "" {
				// NSIS-style: Software\FastFlix\Install_Dir in the same view
				if appKey, err2 := registry.OpenKey(root, ffinstall.RegistryAppPaths[0], registry.QUERY_VALUE|view); err2 == nil {
					dir, _, _ = appKey.GetStringValue("Install_Dir")
					appKey.Close()
				}
			}
			if dir == "" && uninstall != "" {
				// Last resort: the directory of the uninstaller exe in UninstallString
				u := strings.TrimSpace(uninstall)
				if strings.HasPrefix(u, `"`) {
					if end := strings.Index(u[1:], `"`); end >= 0 {
						dir = filepath.Dir(u[1 : end+1])
					}
				}
			}

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
		// Install_Dir without an Uninstall key (view-aware)
		for _, view := range []uint32{0, registry.WOW64_32KEY} {
			if appKey, err := registry.OpenKey(root, ffinstall.RegistryAppPaths[0], registry.QUERY_VALUE|view); err == nil {
				dir, _, _ := appKey.GetStringValue("Install_Dir")
				appKey.Close()
				if dir != "" {
					dirKey := strings.ToLower(filepath.Clean(dir))
					if !seen[dirKey] {
						seen[dirKey] = true
						results = append(results, existingInstall{RegRoot: root, InstallDir: dir})
					}
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
		results = append(results, existingInstall{InstallDir: dir})
	}

	return results
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
