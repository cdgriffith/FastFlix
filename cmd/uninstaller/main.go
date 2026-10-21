// FastFlix Standalone Uninstaller
//
// Dark-themed GUI that only knows how to uninstall FastFlix from its own directory.
// Registered with Windows Add/Remove Programs. Does NOT contain installer functionality.
//
// Build:
//   cd cmd/uninstaller && go-winres make && cd ../..
//   go build -ldflags="-s -w -H windowsgui" -o uninstall.exe ./cmd/uninstaller
//   (scripts/build_distribution.py does all of this and injects the version)

package main

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"syscall"
	"unsafe"

	"github.com/cdgriffith/fastflix-installer/cmd/internal/ffinstall"
	"golang.org/x/sys/windows/registry"
)

const productName = ffinstall.ProductName

// Version is set at build time via -ldflags="-X main.Version=..."
var Version = "dev"

// Win32 API
var (
	user32   = syscall.NewLazyDLL("user32.dll")
	kernel32 = syscall.NewLazyDLL("kernel32.dll")
	gdi32    = syscall.NewLazyDLL("gdi32.dll")
	dwmapi   = syscall.NewLazyDLL("dwmapi.dll")
	comctl32 = syscall.NewLazyDLL("comctl32.dll")
)

// State
var st struct {
	hwnd       syscall.Handle
	hInst      syscall.Handle
	hBgBrush   syscall.Handle
	hIcon      syscall.Handle
	hTitleFont syscall.Handle
	hFont      syscall.Handle
	hSmFont    syscall.Handle

	hUninstBtn syscall.Handle
	hCloseBtn  syscall.Handle
	hStatus    syscall.Handle
	hProgress  syscall.Handle
	hProgLabel syscall.Handle

	installDir string
	selfPath   string
	regRoot    registry.Key // registry root that owns this install (HKLM for all-users, HKCU for per-user)
	regOwned   bool         // true if that root's keys actually point at installDir
	allUsers   bool
	winW, winH int
	iconSz     int
	silent     bool
}

// Colors
const (
	clrBg     = 0x00333333
	clrText   = 0x00E6E6E6
	clrSub    = 0x00A0A0A0
	clrBtn    = 0x004848CC // red
	clrBtnDis = 0x00444466
	clrBtnCls = 0x00F0D030 // cyan close
	clrBtnTxt = 0x00FFFFFF
	clrRed    = 0x003C3CDC
	clrDarkBg = 0x00222222
)

// Control IDs
const (
	idUninstall = 101
	idClose     = 102
	idStatus    = 103
	idProgress  = 104
	idProgLabel = 105
)

type rect struct{ Left, Top, Right, Bottom int32 }
type paintStruct struct {
	HDC       syscall.Handle
	Erase     int32
	RcPaint   rect
	Restore   int32
	IncUpdate int32
	Reserved  [32]byte
}
type msg struct {
	Hwnd    syscall.Handle
	Message uint32
	WParam  uintptr
	LParam  uintptr
	Time    uint32
	Pt      struct{ X, Y int32 }
}
type drawItemStruct struct {
	CtlType, CtlID, ItemID, ItemAction, ItemState uint32
	HwndItem, HDC                                 syscall.Handle
	RcItem                                        rect
	ItemData                                      uintptr
}
type wndClassExW struct {
	Size       uint32
	Style      uint32
	WndProc    uintptr
	ClsExtra   int32
	WndExtra   int32
	Instance   syscall.Handle
	Icon       syscall.Handle
	Cursor     syscall.Handle
	Background syscall.Handle
	MenuName   *uint16
	ClassName  *uint16
	IconSm     syscall.Handle
}

func utf16P(s string) *uint16 { p, _ := syscall.UTF16PtrFromString(s); return p }

func main() {
	runtime.LockOSThread()
	args := os.Args[1:]
	st.silent = containsArg(args, "--silent") || containsArg(args, "/S")

	var err error
	st.selfPath, err = os.Executable()
	if err != nil {
		os.Exit(1)
	}
	st.installDir = filepath.Dir(st.selfPath)

	// Verify FastFlix install
	if _, err := os.Stat(filepath.Join(st.installDir, "python")); err != nil {
		if _, err2 := os.Stat(filepath.Join(st.installDir, "FastFlix.exe")); err2 != nil {
			if !st.silent {
				msgBox("FastFlix Uninstaller",
					"No FastFlix installation found in:\n"+st.installDir+"\n\nIt may have already been removed.", 0x40)
			}
			os.Exit(0)
		}
	}

	st.regRoot, st.regOwned = detectRegRoot(st.installDir, args)
	st.allUsers = st.regRoot == registry.LOCAL_MACHINE || ffinstall.IsProtectedPath(st.installDir)

	// All-users installs (HKLM / Program Files) need admin, in silent mode as well
	if st.allUsers && !ffinstall.IsAdmin() {
		relaunchElevated(st.selfPath, args)
		return
	}

	// Silent mode — never remove files out from under a running FastFlix
	if st.silent {
		if isRunning() {
			os.Exit(1)
		}
		doUninstall()
		return
	}

	// Show GUI
	showGUI()
}

// detectRegRoot finds which registry root registered the install living in dir. owned is false when no
// registry key points at dir (the registry is then left untouched).
func detectRegRoot(dir string, args []string) (root registry.Key, owned bool) {
	for _, r := range []registry.Key{registry.CURRENT_USER, registry.LOCAL_MACHINE} {
		if d := ffinstall.ReadInstallDirFromRegistry(r); d != "" && strings.EqualFold(filepath.Clean(d), filepath.Clean(dir)) {
			return r, true
		}
	}
	if containsArg(args, "--allusers") || ffinstall.IsProtectedPath(dir) {
		return registry.LOCAL_MACHINE, false
	}
	return registry.CURRENT_USER, false
}

func showGUI() {
	hInst, _, _ := kernel32.NewProc("GetModuleHandleW").Call(0)
	st.hInst = syscall.Handle(hInst)

	screenW, _, _ := user32.NewProc("GetSystemMetrics").Call(0)
	screenH, _, _ := user32.NewProc("GetSystemMetrics").Call(1)
	st.winW = int(screenW) * 20 / 100
	if st.winW < 400 {
		st.winW = 400
	}
	st.winH = st.winW * 150 / 100
	if st.winH > int(screenH)*85/100 {
		st.winH = int(screenH) * 85 / 100
	}
	st.iconSz = st.winW * 30 / 100
	if st.iconSz > 256 {
		st.iconSz = 256
	}

	ret, _, _ := gdi32.NewProc("CreateSolidBrush").Call(clrBg)
	st.hBgBrush = syscall.Handle(ret)

	titlePt := st.winW * 54 / 660
	normalPt := st.winW * 24 / 660
	smallPt := st.winW * 20 / 660
	st.hTitleFont = mkFont("Segoe UI", titlePt, true)
	st.hFont = mkFont("Segoe UI", normalPt, false)
	st.hSmFont = mkFont("Segoe UI", smallPt, false)

	ret, _, _ = user32.NewProc("LoadImageW").Call(hInst, 1, 1, uintptr(st.iconSz), uintptr(st.iconSz), 0)
	st.hIcon = syscall.Handle(ret)

	cls := utf16P("FastFlixUninstaller")
	cur, _, _ := user32.NewProc("LoadCursorW").Call(0, 32512)
	wc := wndClassExW{
		Size: uint32(unsafe.Sizeof(wndClassExW{})), Style: 3,
		WndProc: syscall.NewCallback(wndProc), Instance: st.hInst,
		Icon: st.hIcon, Cursor: syscall.Handle(cur), Background: st.hBgBrush,
		ClassName: cls, IconSm: st.hIcon,
	}
	user32.NewProc("RegisterClassExW").Call(uintptr(unsafe.Pointer(&wc)))

	px := (int(screenW) - st.winW) / 2
	py := (int(screenH) - st.winH) / 2
	hwnd, _, _ := user32.NewProc("CreateWindowExW").Call(0x02000000,
		uintptr(unsafe.Pointer(cls)), uintptr(unsafe.Pointer(utf16P("FastFlix Uninstaller"))),
		0x00800000, // WS_BORDER
		uintptr(px), uintptr(py), uintptr(st.winW), uintptr(st.winH), 0, 0, hInst, 0)
	st.hwnd = syscall.Handle(hwnd)

	var dark int32 = 1
	dwmapi.NewProc("DwmSetWindowAttribute").Call(hwnd, 20, uintptr(unsafe.Pointer(&dark)), 4)
	if st.hIcon != 0 {
		user32.NewProc("SendMessageW").Call(hwnd, 0x0080, 0, uintptr(st.hIcon))
		user32.NewProc("SendMessageW").Call(hwnd, 0x0080, 1, uintptr(st.hIcon))
	}

	createControls(hwnd, hInst)

	// Check if running on startup
	if isRunning() {
		setText(st.hStatus, "\u26D4  FastFlix is running, please close it first")
		user32.NewProc("ShowWindow").Call(uintptr(st.hStatus), 5)
		user32.NewProc("EnableWindow").Call(uintptr(st.hUninstBtn), 0)
		inval(st.hUninstBtn)
	}

	// Timer to check process every 10s
	user32.NewProc("SetTimer").Call(hwnd, 1, 10000, 0)

	user32.NewProc("ShowWindow").Call(hwnd, 5)
	user32.NewProc("UpdateWindow").Call(hwnd)

	var m msg
	for {
		r, _, _ := user32.NewProc("GetMessageW").Call(uintptr(unsafe.Pointer(&m)), 0, 0, 0)
		if r == 0 {
			break
		}
		user32.NewProc("TranslateMessage").Call(uintptr(unsafe.Pointer(&m)))
		user32.NewProc("DispatchMessageW").Call(uintptr(unsafe.Pointer(&m)))
	}
}

func createControls(hwnd, hInst uintptr) {
	cx := int32(st.winW)
	pad := cx * 9 / 100
	btnW := cx - pad*2
	btnH := int32(st.winH) * 7 / 100
	ctlH := int32(st.winH) * 4 / 100

	// Uninstall button at ~58%
	y := int32(st.winH) * 58 / 100
	st.hUninstBtn = mkCtl("BUTTON", "Uninstall FastFlix", 0x50000000|0x0000000B,
		pad, y, btnW, btnH, idUninstall, hwnd, hInst) // WS_CHILD|WS_VISIBLE|BS_OWNERDRAW

	y += btnH + ctlH/2
	// Location info
	loc := locationLabel()
	mkStatic(loc, 0x50000000|0x01, pad, y, btnW, ctlH, hwnd, hInst) // SS_CENTER

	y += ctlH + ctlH/2
	// Status (hidden)
	st.hStatus = mkCtl("STATIC", "", 0x40000000|0x01, pad, y, btnW, ctlH*2, idStatus, hwnd, hInst)
	setFont(st.hStatus, st.hFont)

	// Progress (hidden)
	progY := int32(st.winH) * 58 / 100
	progH := int32(st.winH) * 3 / 100
	st.hProgress = mkCtl("STATIC", "", 0x40000000|0x0000000D, pad, progY, btnW, progH, idProgress, hwnd, hInst) // SS_OWNERDRAW
	st.hProgLabel = mkCtl("STATIC", "", 0x40000000|0x01, pad, progY+progH+progH/2, btnW, ctlH, idProgLabel, hwnd, hInst)
	setFont(st.hProgLabel, st.hFont)

	// Close button at bottom
	closW := cx * 20 / 100
	closH := int32(st.winH) * 4 / 100
	closY := int32(st.winH) - closH - int32(st.winH)*8/100
	st.hCloseBtn = mkCtl("BUTTON", "Close", 0x50000000|0x00010000|0x0000000B,
		(cx-closW)/2, closY, closW, closH, idClose, hwnd, hInst)
}

func locationLabel() string {
	dirLower := strings.ToLower(st.installDir)
	loc := st.installDir
	if strings.Contains(dirLower, "program files") {
		loc = "Program Files"
	} else if strings.Contains(dirLower, "appdata") {
		loc = "Local Apps"
	}
	return "Installed in " + loc
}

func wndProc(hwnd syscall.Handle, m uint32, wParam, lParam uintptr) uintptr {
	switch m {
	case 0x000F: // WM_PAINT
		paint(hwnd)
		return 0
	case 0x0138: // WM_CTLCOLORSTATIC
		hdc := syscall.Handle(wParam)
		ctl := syscall.Handle(lParam)
		gdi32.NewProc("SetTextColor").Call(uintptr(hdc), clrText)
		gdi32.NewProc("SetBkMode").Call(uintptr(hdc), 1)
		if ctl == st.hStatus {
			gdi32.NewProc("SetTextColor").Call(uintptr(hdc), clrRed)
		}
		return uintptr(st.hBgBrush)
	case 0x0135: // WM_CTLCOLORBTN
		return uintptr(st.hBgBrush)
	case 0x002B: // WM_DRAWITEM
		dis := *(**drawItemStruct)(unsafe.Pointer(&lParam))
		if dis.HwndItem == st.hProgress {
			drawProgress(dis)
		} else {
			drawBtn(dis)
		}
		return 1
	case 0x0111: // WM_COMMAND
		id := int(wParam & 0xFFFF)
		if id == idClose {
			user32.NewProc("PostQuitMessage").Call(0)
		}
		if id == idUninstall {
			go onUninstall()
		}
		return 0
	case 0x0113: // WM_TIMER
		checkProc()
		return 0
	case 0x0010: // WM_CLOSE
		user32.NewProc("DestroyWindow").Call(uintptr(hwnd))
		return 0
	case 0x0002: // WM_DESTROY
		user32.NewProc("PostQuitMessage").Call(0)
		return 0
	}
	r, _, _ := user32.NewProc("DefWindowProcW").Call(uintptr(hwnd), uintptr(m), wParam, lParam)
	return r
}

func paint(hwnd syscall.Handle) {
	var ps paintStruct
	hdc, _, _ := user32.NewProc("BeginPaint").Call(uintptr(hwnd), uintptr(unsafe.Pointer(&ps)))
	var rc rect
	user32.NewProc("GetClientRect").Call(uintptr(hwnd), uintptr(unsafe.Pointer(&rc)))
	user32.NewProc("FillRect").Call(hdc, uintptr(unsafe.Pointer(&rc)), uintptr(st.hBgBrush))

	if st.hIcon != 0 {
		ix := (int32(st.winW) - int32(st.iconSz)) / 2
		user32.NewProc("DrawIconEx").Call(hdc, uintptr(ix), uintptr(int32(st.winH)*16/100),
			uintptr(st.hIcon), uintptr(st.iconSz), uintptr(st.iconSz), 0, 0, 3)
	}

	gdi32.NewProc("SetBkMode").Call(hdc, 1)
	iconBot := int32(st.winH)*16/100 + int32(st.iconSz) + int32(st.winH)*4/100

	gdi32.NewProc("SetTextColor").Call(hdc, clrText)
	gdi32.NewProc("SelectObject").Call(hdc, uintptr(st.hTitleFont))
	tH := int32(st.winH) * 7 / 100
	tr := rect{0, iconBot, int32(st.winW), iconBot + tH}
	user32.NewProc("DrawTextW").Call(hdc, uintptr(unsafe.Pointer(utf16P("FastFlix"))),
		uintptr(len("FastFlix")), uintptr(unsafe.Pointer(&tr)), 0x21) // DT_CENTER|DT_SINGLELINE

	gdi32.NewProc("SetTextColor").Call(hdc, clrSub)
	gdi32.NewProc("SelectObject").Call(hdc, uintptr(st.hFont))
	vr := rect{0, iconBot + tH, int32(st.winW), iconBot + tH + int32(st.winH)*4/100}
	txt := "Uninstaller " + Version
	user32.NewProc("DrawTextW").Call(hdc, uintptr(unsafe.Pointer(utf16P(txt))),
		uintptr(len(txt)), uintptr(unsafe.Pointer(&vr)), 0x21)

	user32.NewProc("EndPaint").Call(uintptr(hwnd), uintptr(unsafe.Pointer(&ps)))
}

var progressVal int

func drawBtn(dis *drawItemStruct) {
	hdc := uintptr(dis.HDC)
	rc := dis.RcItem
	disabled := dis.ItemState&0x0004 != 0
	isClose := dis.HwndItem == st.hCloseBtn

	bg := uintptr(clrBtn)
	txt := uintptr(clrBtnTxt)
	if isClose {
		bg = clrBtnCls
		txt = 0x00202020
	}
	if disabled {
		bg = clrBtnDis
		txt = clrSub
	}

	// Clear + rounded rect
	user32.NewProc("FillRect").Call(hdc, uintptr(unsafe.Pointer(&rc)), uintptr(st.hBgBrush))
	cornerR := (rc.Bottom - rc.Top) / 4
	br, _, _ := gdi32.NewProc("CreateSolidBrush").Call(bg)
	np, _, _ := gdi32.NewProc("CreatePen").Call(5, 0, 0)
	ob, _, _ := gdi32.NewProc("SelectObject").Call(hdc, br)
	op, _, _ := gdi32.NewProc("SelectObject").Call(hdc, np)
	gdi32.NewProc("RoundRect").Call(hdc, uintptr(rc.Left), uintptr(rc.Top), uintptr(rc.Right), uintptr(rc.Bottom), uintptr(cornerR), uintptr(cornerR))
	gdi32.NewProc("SelectObject").Call(hdc, ob)
	gdi32.NewProc("SelectObject").Call(hdc, op)
	gdi32.NewProc("DeleteObject").Call(br)
	gdi32.NewProc("DeleteObject").Call(np)

	gdi32.NewProc("SetBkMode").Call(hdc, 1)
	gdi32.NewProc("SetTextColor").Call(hdc, txt)
	gdi32.NewProc("SelectObject").Call(hdc, uintptr(st.hFont))
	buf := make([]uint16, 256)
	user32.NewProc("GetWindowTextW").Call(uintptr(dis.HwndItem), uintptr(unsafe.Pointer(&buf[0])), 256)
	t := syscall.UTF16ToString(buf)
	user32.NewProc("DrawTextW").Call(hdc, uintptr(unsafe.Pointer(utf16P(t))),
		uintptr(len(t)), uintptr(unsafe.Pointer(&rc)), 0x25) // DT_CENTER|DT_SINGLELINE|DT_VCENTER
}

func drawProgress(dis *drawItemStruct) {
	hdc := uintptr(dis.HDC)
	rc := dis.RcItem
	cornerR := (rc.Bottom - rc.Top) / 3
	bg, _, _ := gdi32.NewProc("CreateSolidBrush").Call(clrDarkBg)
	np, _, _ := gdi32.NewProc("CreatePen").Call(5, 0, 0)
	ob, _, _ := gdi32.NewProc("SelectObject").Call(hdc, bg)
	op, _, _ := gdi32.NewProc("SelectObject").Call(hdc, np)
	gdi32.NewProc("RoundRect").Call(hdc, uintptr(rc.Left), uintptr(rc.Top), uintptr(rc.Right), uintptr(rc.Bottom), uintptr(cornerR), uintptr(cornerR))
	if progressVal > 0 {
		fillW := (rc.Right - rc.Left) * int32(progressVal) / 100
		if fillW < cornerR*2 {
			fillW = cornerR * 2
		}
		fb, _, _ := gdi32.NewProc("CreateSolidBrush").Call(clrBtnCls)
		gdi32.NewProc("SelectObject").Call(hdc, fb)
		gdi32.NewProc("RoundRect").Call(hdc, uintptr(rc.Left), uintptr(rc.Top), uintptr(rc.Left+fillW), uintptr(rc.Bottom), uintptr(cornerR), uintptr(cornerR))
		gdi32.NewProc("DeleteObject").Call(fb)
	}
	gdi32.NewProc("SelectObject").Call(hdc, ob)
	gdi32.NewProc("SelectObject").Call(hdc, op)
	gdi32.NewProc("DeleteObject").Call(bg)
	gdi32.NewProc("DeleteObject").Call(np)
}

func onUninstall() {
	if isRunning() {
		setText(st.hStatus, "\u26D4  FastFlix is running, please close it first")
		user32.NewProc("ShowWindow").Call(uintptr(st.hStatus), 5)
		user32.NewProc("EnableWindow").Call(uintptr(st.hUninstBtn), 0)
		inval(st.hUninstBtn)
		return
	}

	// Switch to progress view
	user32.NewProc("ShowWindow").Call(uintptr(st.hUninstBtn), 0)
	user32.NewProc("ShowWindow").Call(uintptr(st.hCloseBtn), 0)
	user32.NewProc("ShowWindow").Call(uintptr(st.hStatus), 0)
	user32.NewProc("ShowWindow").Call(uintptr(st.hProgress), 5)
	user32.NewProc("ShowWindow").Call(uintptr(st.hProgLabel), 5)
	setText(st.hProgLabel, "Uninstalling...")

	doUninstall()

	setProgress(100)
	if _, err := os.Stat(filepath.Join(st.installDir, ffinstall.UserConfigName)); err == nil {
		setText(st.hProgLabel, "FastFlix has been removed (settings file kept).")
	} else {
		setText(st.hProgLabel, "FastFlix has been removed.")
	}

	// Show close button again
	user32.NewProc("ShowWindow").Call(uintptr(st.hCloseBtn), 5)
}

func doUninstall() {
	setProgress(10)

	// Shortcuts: only the ones belonging to the kind of install being removed
	if st.regRoot == registry.LOCAL_MACHINE {
		os.RemoveAll(filepath.Join(os.Getenv("ProgramData"), "Microsoft", "Windows", "Start Menu", "Programs", productName))
		os.Remove(filepath.Join(os.Getenv("PUBLIC"), "Desktop", productName+".lnk"))
	} else {
		os.RemoveAll(filepath.Join(os.Getenv("APPDATA"), "Microsoft", "Windows", "Start Menu", "Programs", productName))
		os.Remove(filepath.Join(os.Getenv("USERPROFILE"), "Desktop", productName+".lnk"))
	}

	setProgress(30)

	// Registry: only the root that registered this install (and only if it really points at this directory)
	if st.regOwned {
		ffinstall.CleanRegistry(st.regRoot)
	}

	setProgress(50)

	// Remove the files the installer put here. User files (portable fastflix.yaml etc.) are left alone and
	// the folder is only removed if it ends up empty. The running uninstaller removes itself after exit.
	ffinstall.RemoveInstalledFiles(st.installDir, st.selfPath)

	setProgress(90)

	ffinstall.ScheduleSelfDelete(st.selfPath, st.installDir)
}

func checkProc() {
	running := isRunning()
	if running {
		setText(st.hStatus, "\u26D4  FastFlix is running, please close it first")
		user32.NewProc("ShowWindow").Call(uintptr(st.hStatus), 5)
		user32.NewProc("EnableWindow").Call(uintptr(st.hUninstBtn), 0)
	} else {
		user32.NewProc("ShowWindow").Call(uintptr(st.hStatus), 0)
		user32.NewProc("EnableWindow").Call(uintptr(st.hUninstBtn), 1)
	}
	inval(st.hUninstBtn)
}

// Helpers

func setProgress(pct int) {
	progressVal = pct
	inval(st.hProgress)
}

func setText(h syscall.Handle, s string) {
	user32.NewProc("SetWindowTextW").Call(uintptr(h), uintptr(unsafe.Pointer(utf16P(s))))
}
func setFont(h, f syscall.Handle) {
	user32.NewProc("SendMessageW").Call(uintptr(h), 0x0030, uintptr(f), 1)
}
func inval(h syscall.Handle) {
	user32.NewProc("InvalidateRect").Call(uintptr(h), 0, 1)
}
func mkFont(fam string, sz int, bold bool) syscall.Handle {
	w := int32(400)
	if bold {
		w = 700
	}
	h, _, _ := gdi32.NewProc("CreateFontW").Call(uintptr(uint32(-sz)), 0, 0, 0, uintptr(w), 0, 0, 0, 1, 0, 0, 5, 0, uintptr(unsafe.Pointer(utf16P(fam))))
	return syscall.Handle(h)
}
func mkCtl(cls, txt string, style uint32, x, y, w, h int32, id int, parent, hInst uintptr) syscall.Handle {
	r, _, _ := user32.NewProc("CreateWindowExW").Call(0, uintptr(unsafe.Pointer(utf16P(cls))), uintptr(unsafe.Pointer(utf16P(txt))), uintptr(style), uintptr(x), uintptr(y), uintptr(w), uintptr(h), parent, uintptr(id), hInst, 0)
	return syscall.Handle(r)
}
func mkStatic(txt string, style uint32, x, y, w, h int32, parent, hInst uintptr) syscall.Handle {
	r := mkCtl("STATIC", txt, style, x, y, w, h, 0, parent, hInst)
	setFont(r, st.hSmFont)
	return r
}

func containsArg(a []string, f string) bool {
	for _, v := range a {
		if strings.EqualFold(v, f) {
			return true
		}
	}
	return false
}
func isRunning() bool { return ffinstall.IsRunning(st.installDir) }

func relaunchElevated(self string, args []string) {
	v, _ := syscall.UTF16PtrFromString("runas")
	e, _ := syscall.UTF16PtrFromString(self)
	a, _ := syscall.UTF16PtrFromString(strings.Join(args, " "))
	c, _ := syscall.UTF16PtrFromString(filepath.Dir(self))
	syscall.NewLazyDLL("shell32.dll").NewProc("ShellExecuteW").Call(0, uintptr(unsafe.Pointer(v)), uintptr(unsafe.Pointer(e)), uintptr(unsafe.Pointer(a)), uintptr(unsafe.Pointer(c)), 1)
}

func msgBox(title, msg string, flags uintptr) int {
	t, _ := syscall.UTF16PtrFromString(title)
	m, _ := syscall.UTF16PtrFromString(msg)
	ret, _, _ := user32.NewProc("MessageBoxW").Call(0, uintptr(unsafe.Pointer(m)), uintptr(unsafe.Pointer(t)), flags)
	return int(ret)
}
