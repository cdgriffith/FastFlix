// Package ffinstall holds the safety-critical helpers shared by the FastFlix installer and uninstaller:
// path validation, manifest-based file removal, registry cleanup, process detection and self-deletion.
package ffinstall

import (
	"bufio"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"unsafe"

	"golang.org/x/sys/windows"
	"golang.org/x/sys/windows/registry"
)

const (
	// ProductName is the registry / Start Menu / folder name.
	ProductName = "FastFlix"
	// ManifestName lists every file the installer extracted (relative paths, one per line).
	ManifestName = "install_manifest.txt"
	// UserConfigName is the portable-mode config. It is user data and is never deleted by an uninstall.
	UserConfigName = "fastflix.yaml"
)

// distEntries are the top-level entries of the distribution, used when an install has no manifest
// (installs made before manifests existed).
var distEntries = []string{
	"python", "lib", "FastFlix.exe", "uninstall.exe", "CHANGES", "build-licenses.txt", "build_version", "LICENSE",
	ManifestName,
}

// RegistryUninstallPaths are the Add/Remove Programs keys (64-bit view and the WOW6432Node view used by the
// old 32-bit NSIS installer).
var RegistryUninstallPaths = []string{
	`Software\Microsoft\Windows\CurrentVersion\Uninstall\` + ProductName,
	`Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\` + ProductName,
}

// RegistryAppPaths are the per-application keys (Install_Dir) in both registry views.
var RegistryAppPaths = []string{
	`SOFTWARE\` + ProductName,
	`SOFTWARE\WOW6432Node\` + ProductName,
}

// IsAdmin reports whether the current process token is elevated.
func IsAdmin() bool {
	return windows.GetCurrentProcessToken().IsElevated()
}

// ValidatePathString rejects strings that must never be handed to ShellExecute / batch files: empty paths,
// non-absolute paths, quotes, control characters and characters that are invalid in Windows paths.
// (No path is ever passed through cmd.exe for deletion; the batch script used for self-deletion escapes
// '%' itself, so '&', '^' and '%' are legal here.)
func ValidatePathString(p string) error {
	if strings.TrimSpace(p) == "" {
		return errors.New("empty path")
	}
	if !filepath.IsAbs(p) {
		return fmt.Errorf("path is not absolute: %q", p)
	}
	for _, r := range p {
		if r < 0x20 || strings.ContainsRune(`"<>|*?`, r) {
			return fmt.Errorf("path contains an illegal character: %q", p)
		}
	}
	return nil
}

// IsWithin reports whether child is parent itself or lies beneath it (separator-aware, case-insensitive).
func IsWithin(parent, child string) bool {
	p := filepath.Clean(parent)
	c := filepath.Clean(child)
	if len(c) < len(p) || !strings.EqualFold(c[:len(p)], p) {
		return false
	}
	return len(c) == len(p) || strings.HasSuffix(p, `\`) || c[len(p)] == filepath.Separator
}

// IsProtectedPath reports whether dir lies under Program Files (needs admin to modify).
func IsProtectedPath(dir string) bool {
	for _, env := range []string{"ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"} {
		if root := os.Getenv(env); root != "" && IsWithin(root, dir) {
			return true
		}
	}
	return false
}

// forbiddenRoots are directories that must never be removed (nor any of their parents).
func forbiddenRoots() []string {
	var roots []string
	for _, env := range []string{
		"ProgramFiles", "ProgramW6432", "ProgramFiles(x86)", "SystemRoot", "windir", "SystemDrive",
		"USERPROFILE", "LOCALAPPDATA", "APPDATA", "ProgramData", "PUBLIC", "TEMP", "TMP",
	} {
		if v := os.Getenv(env); v != "" {
			if env == "SystemDrive" {
				v += `\`
			}
			roots = append(roots, v)
		}
	}
	// Per-user "Programs" parent
	if la := os.Getenv("LOCALAPPDATA"); la != "" {
		roots = append(roots, filepath.Join(la, "Programs"))
	}
	return roots
}

// exists reports whether name exists in dir.
func exists(dir, name string) bool {
	_, err := os.Stat(filepath.Join(dir, name))
	return err == nil
}

// LooksInstalled reports whether dir is a FastFlix install: FastFlix.exe must exist AND at least one other
// install artifact (the manifest, uninstall.exe or the python runtime). A bare uninstall.exe or python folder
// is not proof of anything.
func LooksInstalled(dir string) bool {
	if !exists(dir, "FastFlix.exe") {
		return false
	}
	return exists(dir, ManifestName) || exists(dir, "uninstall.exe") || exists(dir, "python")
}

// SafeToRemove returns nil only if dir is plausibly a FastFlix install directory that is safe to delete from.
func SafeToRemove(dir string) error {
	if err := ValidatePathString(dir); err != nil {
		return err
	}
	clean := filepath.Clean(dir)
	if vol := filepath.VolumeName(clean); len(clean) <= len(vol)+1 {
		return fmt.Errorf("refusing to remove drive root: %q", dir)
	}
	for _, root := range forbiddenRoots() {
		// dir must not be one of the roots, nor an ancestor of one of them
		if IsWithin(clean, root) {
			return fmt.Errorf("refusing to remove protected location: %q", dir)
		}
	}
	if !LooksInstalled(clean) {
		return fmt.Errorf("%q does not contain a FastFlix installation", dir)
	}
	return nil
}

// ReadManifest returns the relative paths recorded by the installer, or nil if there is no manifest.
func ReadManifest(dir string) []string {
	f, err := os.Open(filepath.Join(dir, ManifestName))
	if err != nil {
		return nil
	}
	defer f.Close()
	var files []string
	sc := bufio.NewScanner(f)
	sc.Buffer(make([]byte, 0, 64*1024), 1024*1024)
	for sc.Scan() {
		if line := strings.TrimSpace(sc.Text()); line != "" {
			files = append(files, line)
		}
	}
	return files
}

// WriteManifest records the extracted files (relative paths) so an uninstall removes only what we installed.
func WriteManifest(dir string, files []string) error {
	return os.WriteFile(filepath.Join(dir, ManifestName), []byte(strings.Join(files, "\r\n")+"\r\n"), 0644)
}

// topLevelNames returns the distinct first path components of the given relative paths.
func topLevelNames(files []string) []string {
	seen := map[string]bool{}
	var out []string
	for _, f := range files {
		f = filepath.ToSlash(f)
		name := strings.SplitN(f, "/", 2)[0]
		if name == "" || name == "." || name == ".." || seen[strings.ToLower(name)] {
			continue
		}
		seen[strings.ToLower(name)] = true
		out = append(out, name)
	}
	return out
}

// RemoveOwned deletes the given top-level entries of dir (directories recursively), except self, then removes
// dir if (and only if) it is empty. Anything else in dir (portable fastflix.yaml, user files) is left alone.
func RemoveOwned(dir string, names []string, self string) error {
	var firstErr error
	for _, name := range names {
		p := filepath.Join(dir, name)
		if !IsWithin(dir, p) || strings.EqualFold(filepath.Clean(p), filepath.Clean(self)) {
			continue
		}
		if err := os.RemoveAll(p); err != nil && firstErr == nil {
			firstErr = err
		}
	}
	os.Remove(dir) // non-recursive: fails harmlessly while user files or self remain
	return firstErr
}

// RemoveInstalledFiles removes a FastFlix installation from dir without touching user files.
// With a manifest only the top-level entries it names are removed; without one, the known distribution
// entries are removed (or, for legacy PyInstaller/NSIS installs, everything except the portable config).
// self (the running uninstaller) is skipped so it can be deleted after exit.
func RemoveInstalledFiles(dir, self string) error {
	if err := SafeToRemove(dir); err != nil {
		return err
	}
	if files := ReadManifest(dir); files != nil {
		return RemoveOwned(dir, append(topLevelNames(files), ManifestName), self)
	}
	if _, err := os.Stat(filepath.Join(dir, "python")); err == nil {
		return RemoveOwned(dir, distEntries, self)
	}
	// Legacy one-folder install (old PyInstaller/NSIS): remove everything but user config. Because this deletes
	// the whole folder, demand much stronger evidence: the folder must be named FastFlix and hold both
	// FastFlix.exe and uninstall.exe.
	if !strings.EqualFold(filepath.Base(filepath.Clean(dir)), ProductName) ||
		!exists(dir, "FastFlix.exe") || !exists(dir, "uninstall.exe") {
		return fmt.Errorf("refusing to remove %q: not a recognizable legacy FastFlix install folder", dir)
	}
	entries, err := os.ReadDir(dir)
	if err != nil {
		return err
	}
	var names []string
	for _, e := range entries {
		if !strings.EqualFold(e.Name(), UserConfigName) {
			names = append(names, e.Name())
		}
	}
	return RemoveOwned(dir, names, self)
}

// RemoveExtracted cleans up after a failed extraction: removes the top-level entries named by files.
func RemoveExtracted(dir string, files []string) {
	RemoveOwned(dir, topLevelNames(files), "")
}

// CleanRegistry deletes FastFlix's Add/Remove Programs and application keys (both registry views) under root.
func CleanRegistry(root registry.Key) {
	for _, p := range RegistryUninstallPaths {
		registry.DeleteKey(root, p)
	}
	for _, p := range RegistryAppPaths {
		registry.DeleteKey(root, p)
	}
}

// ReadInstallDirFromRegistry looks for the install directory recorded by FastFlix (or the NSIS installer)
// under root, checking InstallLocation and Install_Dir in both the 64-bit and 32-bit registry views.
func ReadInstallDirFromRegistry(root registry.Key) string {
	for _, view := range []uint32{0, registry.WOW64_32KEY} {
		if k, err := registry.OpenKey(root, RegistryUninstallPaths[0], registry.QUERY_VALUE|view); err == nil {
			dir, _, _ := k.GetStringValue("InstallLocation")
			k.Close()
			if dir != "" {
				return dir
			}
		}
		if k, err := registry.OpenKey(root, RegistryAppPaths[0], registry.QUERY_VALUE|view); err == nil {
			dir, _, _ := k.GetStringValue("Install_Dir")
			k.Close()
			if dir != "" {
				return dir
			}
		}
	}
	return ""
}

// IsRunning reports whether FastFlix is running: FastFlix.exe by name, or an orphaned python.exe /
// pythonw.exe whose image lives inside one of dirs (the launcher's child keeps running if the launcher dies).
func IsRunning(dirs ...string) bool {
	snap, err := windows.CreateToolhelp32Snapshot(windows.TH32CS_SNAPPROCESS, 0)
	if err != nil {
		return false
	}
	defer windows.CloseHandle(snap)

	var pe windows.ProcessEntry32
	pe.Size = uint32(unsafe.Sizeof(pe))
	if windows.Process32First(snap, &pe) != nil {
		return false
	}
	for {
		name := windows.UTF16ToString(pe.ExeFile[:])
		if strings.EqualFold(name, "FastFlix.exe") {
			return true
		}
		if len(dirs) > 0 && (strings.EqualFold(name, "python.exe") || strings.EqualFold(name, "pythonw.exe")) {
			if img := processImagePath(pe.ProcessID); img != "" {
				for _, d := range dirs {
					if d != "" && IsWithin(d, img) {
						return true
					}
				}
			}
		}
		if windows.Process32Next(snap, &pe) != nil {
			break
		}
	}
	return false
}

func processImagePath(pid uint32) string {
	h, err := windows.OpenProcess(windows.PROCESS_QUERY_LIMITED_INFORMATION, false, pid)
	if err != nil {
		return ""
	}
	defer windows.CloseHandle(h)
	buf := make([]uint16, windows.MAX_LONG_PATH)
	size := uint32(len(buf))
	if windows.QueryFullProcessImageName(h, 0, &buf[0], &size) != nil {
		return ""
	}
	return windows.UTF16ToString(buf[:size])
}

// ScheduleSelfDelete deletes self and then (if empty) dir after the current process exits. It writes a temp
// .bat that retries until the exe is unlocked and then deletes itself, and runs it hidden and detached.
// The paths are passed through environment variables (UTF-16 in the process environment) rather than written
// into the script, so non-ASCII, '%' or '&' characters in them need no batch escaping or code page handling.
func ScheduleSelfDelete(self, dir string) error {
	if err := ValidatePathString(self); err != nil {
		return err
	}
	if err := ValidatePathString(dir); err != nil {
		return err
	}
	script := "@echo off\r\n" +
		"setlocal\r\n" +
		"set n=0\r\n" +
		":retry\r\n" +
		"set /a n+=1\r\n" +
		"ping 127.0.0.1 -n 2 >nul\r\n" +
		"del /f /q \"%FF_CLEANUP_SELF%\" >nul 2>&1\r\n" +
		"if exist \"%FF_CLEANUP_SELF%\" if %n% lss 60 goto retry\r\n" +
		"rmdir \"%FF_CLEANUP_DIR%\" >nul 2>&1\r\n" +
		"(goto) 2>nul & del \"%~f0\"\r\n"

	f, err := os.CreateTemp("", "fastflix-cleanup-*.bat")
	if err != nil {
		return err
	}
	bat := f.Name()
	if _, err := f.WriteString(script); err != nil {
		f.Close()
		os.Remove(bat)
		return err
	}
	f.Close()

	// CREATE_NO_WINDOW gives cmd a hidden console that ping inherits. DETACHED_PROCESS must not be used: with no
	// console at all, every console child (ping) would pop up its own visible window.
	const createNoWindow = 0x08000000
	cmdExe := filepath.Join(os.Getenv("SystemRoot"), "System32", "cmd.exe")
	cmd := exec.Command(cmdExe)
	cmd.SysProcAttr = &syscall.SysProcAttr{
		CmdLine:       `"` + cmdExe + `" /d /c ""` + bat + `""`,
		HideWindow:    true,
		CreationFlags: createNoWindow,
	}
	cmd.Env = append(os.Environ(), "FF_CLEANUP_SELF="+self, "FF_CLEANUP_DIR="+dir)
	if err := cmd.Start(); err != nil {
		os.Remove(bat)
		return err
	}
	return cmd.Process.Release()
}
