package ffinstall

import (
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestIsWithin(t *testing.T) {
	cases := []struct {
		parent, child string
		want          bool
	}{
		{`C:\Program Files`, `C:\Program Files\FastFlix`, true},
		{`C:\Program Files`, `c:\program files`, true},
		{`C:\Program Files`, `C:\Program Files (x86)\FastFlix`, false}, // prefix without separator
		{`C:\Program Files`, `C:\Program FilesEvil`, false},
		{`C:\`, `C:\Users`, true},
	}
	for _, c := range cases {
		if got := IsWithin(c.parent, c.child); got != c.want {
			t.Errorf("IsWithin(%q, %q) = %v, want %v", c.parent, c.child, got, c.want)
		}
	}
}

func TestValidatePathString(t *testing.T) {
	for _, bad := range []string{"", "relative\\dir", `C:\a"b`, "C:\\a\nb", `C:\a|b`} {
		if ValidatePathString(bad) == nil {
			t.Errorf("expected %q to be rejected", bad)
		}
	}
	if err := ValidatePathString(`C:\Users\Tom & Jerry\FastFlix`); err != nil {
		t.Errorf("unexpected rejection: %v", err)
	}
}

func TestSafeToRemoveRefusesRootsAndUnmarked(t *testing.T) {
	for _, dir := range []string{`C:\`, os.Getenv("ProgramFiles"), os.Getenv("USERPROFILE"), os.Getenv("LOCALAPPDATA"), `C:\Users`} {
		if dir == "" {
			continue
		}
		if SafeToRemove(dir) == nil {
			t.Errorf("SafeToRemove(%q) should refuse", dir)
		}
	}
	empty := t.TempDir()
	if SafeToRemove(empty) == nil {
		t.Error("directory without a FastFlix marker should be refused")
	}
}

func TestRemoveInstalledFilesKeepsUserFiles(t *testing.T) {
	dir := filepath.Join(t.TempDir(), "FastFlix")
	must := func(err error) {
		t.Helper()
		if err != nil {
			t.Fatal(err)
		}
	}
	must(os.MkdirAll(filepath.Join(dir, "python"), 0755))
	must(os.MkdirAll(filepath.Join(dir, "lib", "pkg", "__pycache__"), 0755))
	must(os.WriteFile(filepath.Join(dir, "python", "python.exe"), []byte("x"), 0644))
	must(os.WriteFile(filepath.Join(dir, "lib", "pkg", "__pycache__", "m.pyc"), []byte("x"), 0644)) // runtime litter
	must(os.WriteFile(filepath.Join(dir, "FastFlix.exe"), []byte("x"), 0644))
	must(os.WriteFile(filepath.Join(dir, "uninstall.exe"), []byte("x"), 0644))
	must(os.WriteFile(filepath.Join(dir, UserConfigName), []byte("cfg"), 0644))
	must(WriteManifest(dir, []string{"python/python.exe", "lib/pkg/__init__.py", "FastFlix.exe", "uninstall.exe"}))

	self := filepath.Join(dir, "uninstall.exe")
	must(RemoveInstalledFiles(dir, self))

	for _, gone := range []string{"python", "lib", "FastFlix.exe", ManifestName} {
		if _, err := os.Stat(filepath.Join(dir, gone)); err == nil {
			t.Errorf("%s should have been removed", gone)
		}
	}
	for _, kept := range []string{UserConfigName, "uninstall.exe"} {
		if _, err := os.Stat(filepath.Join(dir, kept)); err != nil {
			t.Errorf("%s should have been kept: %v", kept, err)
		}
	}
}

func writeFiles(t *testing.T, dir string, files ...string) {
	t.Helper()
	for _, f := range files {
		p := filepath.Join(dir, f)
		if filepath.Ext(f) == "" && f == "python" {
			if err := os.MkdirAll(p, 0755); err != nil {
				t.Fatal(err)
			}
			continue
		}
		if err := os.MkdirAll(filepath.Dir(p), 0755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(p, []byte("x"), 0644); err != nil {
			t.Fatal(err)
		}
	}
}

func TestLooksInstalledRequiresFastFlixExe(t *testing.T) {
	cases := []struct {
		name  string
		files []string
		want  bool
	}{
		{"only uninstall.exe", []string{"uninstall.exe"}, false},
		{"only python", []string{"python"}, false},
		{"only FastFlix.exe", []string{"FastFlix.exe"}, false},
		{"exe + uninstall", []string{"FastFlix.exe", "uninstall.exe"}, true},
		{"exe + python", []string{"FastFlix.exe", "python"}, true},
		{"exe + manifest", []string{"FastFlix.exe", ManifestName}, true},
	}
	for _, c := range cases {
		dir := t.TempDir()
		writeFiles(t, dir, c.files...)
		if got := LooksInstalled(dir); got != c.want {
			t.Errorf("%s: LooksInstalled = %v, want %v", c.name, got, c.want)
		}
	}
}

func TestRemoveInstalledFilesRefusesWeakEvidence(t *testing.T) {
	for _, files := range [][]string{{"uninstall.exe", "a.txt"}, {"python", "a.txt"}} {
		dir := filepath.Join(t.TempDir(), "FastFlix")
		writeFiles(t, dir, files...)
		if RemoveInstalledFiles(dir, "") == nil {
			t.Errorf("%v: should be refused", files)
		}
		if !exists(dir, "a.txt") {
			t.Errorf("%v: user file was deleted", files)
		}
	}
}

func TestRemoveInstalledFilesLegacyBranch(t *testing.T) {
	// Wrong folder name: refused, nothing deleted
	bad := filepath.Join(t.TempDir(), "Documents")
	writeFiles(t, bad, "FastFlix.exe", "uninstall.exe", "precious.docx")
	if RemoveInstalledFiles(bad, "") == nil {
		t.Error("legacy removal should be refused when the folder is not named FastFlix")
	}
	if !exists(bad, "precious.docx") || !exists(bad, "FastFlix.exe") {
		t.Error("refused legacy removal must not delete anything")
	}

	// FastFlix.exe without uninstall.exe (named correctly): refused
	noUn := filepath.Join(t.TempDir(), "FastFlix")
	writeFiles(t, noUn, "FastFlix.exe", "other.dll")
	if LooksInstalled(noUn) {
		t.Fatal("exe alone should not look installed")
	}
	if RemoveInstalledFiles(noUn, "") == nil {
		t.Error("legacy removal should be refused without uninstall.exe")
	}

	// Proper legacy install: everything but fastflix.yaml goes
	good := filepath.Join(t.TempDir(), "fastflix")
	writeFiles(t, good, "FastFlix.exe", "uninstall.exe", "old.dll", UserConfigName)
	if err := RemoveInstalledFiles(good, ""); err != nil {
		t.Fatal(err)
	}
	if exists(good, "old.dll") || exists(good, "FastFlix.exe") {
		t.Error("legacy files should have been removed")
	}
	if !exists(good, UserConfigName) {
		t.Error("fastflix.yaml should have been kept")
	}
}

func TestScheduleSelfDelete(t *testing.T) {
	for _, name := range []string{"FastFlix", "FastFlix José", "Fast & Flix", "Fast 100%"} {
		t.Run(name, func(t *testing.T) { testScheduleSelfDelete(t, name) })
	}
}

func testScheduleSelfDelete(t *testing.T, name string) {
	dir := filepath.Join(t.TempDir(), name)
	if err := os.MkdirAll(dir, 0755); err != nil {
		t.Fatal(err)
	}
	self := filepath.Join(dir, "uninstall.exe")
	if err := os.WriteFile(self, []byte("x"), 0644); err != nil {
		t.Fatal(err)
	}
	if err := ScheduleSelfDelete(self, dir); err != nil {
		t.Fatal(err)
	}
	deadline := time.Now().Add(20 * time.Second)
	for time.Now().Before(deadline) {
		if _, err := os.Stat(dir); err != nil {
			return
		}
		time.Sleep(500 * time.Millisecond)
	}
	t.Fatal("self-delete batch did not remove the file and folder")
}
