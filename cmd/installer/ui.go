package main

import (
	"fmt"
	"math"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"syscall"
	"time"
	"unsafe"

	"golang.org/x/sys/windows/registry"
)

// Win32 API bindings
var (
	user32DLL   = syscall.NewLazyDLL("user32.dll")
	kernel32DLL = syscall.NewLazyDLL("kernel32.dll")
	gdi32DLL    = syscall.NewLazyDLL("gdi32.dll")
	dwmapiDLL   = syscall.NewLazyDLL("dwmapi.dll")
	comctl32DLL = syscall.NewLazyDLL("comctl32.dll")

	registerClassExW      = user32DLL.NewProc("RegisterClassExW")
	createWindowExW       = user32DLL.NewProc("CreateWindowExW")
	showWindow            = user32DLL.NewProc("ShowWindow")
	updateWindow          = user32DLL.NewProc("UpdateWindow")
	getMessageW           = user32DLL.NewProc("GetMessageW")
	translateMessage      = user32DLL.NewProc("TranslateMessage")
	dispatchMessageW      = user32DLL.NewProc("DispatchMessageW")
	defWindowProcW        = user32DLL.NewProc("DefWindowProcW")
	postQuitMessage       = user32DLL.NewProc("PostQuitMessage")
	sendMessageW          = user32DLL.NewProc("SendMessageW")
	enableWindow          = user32DLL.NewProc("EnableWindow")
	setTimer              = user32DLL.NewProc("SetTimer")
	destroyWindow         = user32DLL.NewProc("DestroyWindow")
	getSystemMetrics      = user32DLL.NewProc("GetSystemMetrics")
	invalidateRect        = user32DLL.NewProc("InvalidateRect")
	loadImageW            = user32DLL.NewProc("LoadImageW")
	loadIconW             = user32DLL.NewProc("LoadIconW")
	drawIconEx            = user32DLL.NewProc("DrawIconEx")
	beginPaint            = user32DLL.NewProc("BeginPaint")
	endPaint              = user32DLL.NewProc("EndPaint")
	fillRectProc          = user32DLL.NewProc("FillRect")
	setWindowTextW        = user32DLL.NewProc("SetWindowTextW")
	getClientRectProc     = user32DLL.NewProc("GetClientRect")
	getWindowTextW        = user32DLL.NewProc("GetWindowTextW")
	isWindowProc          = user32DLL.NewProc("IsWindow")
	setForegroundWindow   = user32DLL.NewProc("SetForegroundWindow")

	createSolidBrush      = gdi32DLL.NewProc("CreateSolidBrush")
	createFontW           = gdi32DLL.NewProc("CreateFontW")
	selectObject          = gdi32DLL.NewProc("SelectObject")
	setTextColor          = gdi32DLL.NewProc("SetTextColor")
	setBkMode             = gdi32DLL.NewProc("SetBkMode")
	drawTextW             = user32DLL.NewProc("DrawTextW")
	deleteObject          = gdi32DLL.NewProc("DeleteObject")

	initCommonControlsEx  = comctl32DLL.NewProc("InitCommonControlsEx")
	dwmSetWindowAttribute = dwmapiDLL.NewProc("DwmSetWindowAttribute")
	getModuleHandleW      = kernel32DLL.NewProc("GetModuleHandleW")
)

// Win32 constants
const (
	wsOverlapped   = 0x00000000
	wsCaption      = 0x00C00000
	wsSysMenu      = 0x00080000
	wsMinimizeBox  = 0x00020000
	wsVisible      = 0x10000000
	wsChild        = 0x40000000
	wsTabStop      = 0x00010000
	wsExComposited = 0x02000000
	wsVScroll      = 0x00200000
	wsBorder       = 0x00800000

	bsAutoCheckBox = 0x00000003
	bsOwnerDraw    = 0x0000000B
	ssCenter       = 0x00000001
	ssNotify       = 0x00000100
	ssOwnerDraw    = 0x0000000D
	pbsSmooth      = 0x01
	esMultiline    = 0x0004
	esReadOnly     = 0x0800
	esAutoVScroll  = 0x0040

	wmDestroy        = 0x0002
	wmPaint          = 0x000F
	wmClose          = 0x0010
	wmSetText        = 0x000C
	wmSetFont        = 0x0030
	wmSetIcon        = 0x0080
	wmCommand        = 0x0111
	wmTimer          = 0x0113
	wmCtlColorStatic = 0x0138
	wmCtlColorBtn    = 0x0135
	wmCtlColorEdit   = 0x0133
	wmDrawItem       = 0x002B

	bmGetCheck   = 0x00F0
	bstChecked   = 0x0001
	pbmSetRange  = 0x0406
	pbmSetPos    = 0x0402
	emSetMargins = 0x00D3

	bnClicked   = 0
	smCXScreen  = 0
	smCYScreen  = 1
	swShow      = 5
	swHide      = 0
	transparent = 1
	imageIcon   = 1

	dtCenter     = 0x00000001
	dtSingleLine = 0x00000020
	dtVCenter    = 0x00000004
)

// Control IDs
const (
	idcAgree     = 101
	idcTerms     = 102
	idcUninstall = 103
	idcUser      = 104
	idcAll       = 105
	idcWarning   = 106
	idcProgress  = 107
	idcProgLabel = 108
	idcLaunch    = 109
	idcInstInfo  = 110
	idcClose     = 111
	idcAd        = 112
	idcAdLink    = 113
	idtCountdown = 2
	idtProcCheck = 1
	idcDlgEdit   = 201
	idcDlgClose  = 202
)

// Colors (COLORREF = 0x00BBGGRR)
const (
	clrBg       = 0x00333333
	clrText     = 0x00E6E6E6
	clrSubtext  = 0x00A0A0A0
	clrAccent   = 0x00F0AA46 // #46AAF0 in BGR (cyan)
	clrRed      = 0x003C3CDC
	clrBtnBg    = 0x00F0D030 // bright cyan #30D0F0 in BGR
	clrBtnText  = 0x00202020 // dark text on bright buttons
	clrBtnDis   = 0x00555555
	clrBtnRed   = 0x004848CC
	clrBtnRedDis = 0x00444466
	clrEditBg   = 0x003A3A3A
)

// Window dimensions — computed at runtime from screen size
var (
	winWidth  int
	winHeight int
	iconSz    int
)

type wndState struct {
	hwnd      syscall.Handle
	hInstance syscall.Handle
	hBgBrush  syscall.Handle
	hEditBrush syscall.Handle

	hTitleFont  syscall.Handle
	hNormalFont syscall.Handle
	hSmallFont  syscall.Handle
	hIcon       syscall.Handle
	hShieldIcon syscall.Handle

	hAgree        syscall.Handle
	hTerms        syscall.Handle
	hUninstallBtn syscall.Handle
	hUserBtn      syscall.Handle
	hAllBtn       syscall.Handle
	hWarning      syscall.Handle
	hProgress     syscall.Handle
	hProgLabel    syscall.Handle
	hLaunchBtn    syscall.Handle
	hCloseBtn     syscall.Handle
	hAdText       syscall.Handle
	hAdLink       syscall.Handle
	hAdPromo      syscall.Handle
	countdown     int // seconds remaining before Launch button enables
	hInstallInfo  syscall.Handle // label showing where previous versions were found

	processRunning  bool
	installing      bool
	agreeChecked    bool   // owner-drawn checkbox state
	termsLinkX      int32    // X position where "Terms and Conditions" text starts (for hit-test)
	installedDir    string   // set after install completes, for launch button
	progressValue   int      // 0-100 progress percentage
	uninstallNeedsAdmin bool // true if any existing install is in Program Files
	existingInstalls []existingInstall // all detected installs (for info display)
	existingFound   bool
	existingVersion string
	existingDir     string
	previousRemoved bool
}

var state wndState

// Win32 struct types
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

type paintStruct struct {
	HDC      syscall.Handle
	Erase    int32
	RcPaint  rect
	Restore  int32
	IncUpdate int32
	Reserved [32]byte
}

type rect struct{ Left, Top, Right, Bottom int32 }

type msg struct {
	Hwnd    syscall.Handle
	Message uint32
	WParam  uintptr
	LParam  uintptr
	Time    uint32
	Pt      struct{ X, Y int32 }
}

type drawItemStruct struct {
	CtlType    uint32
	CtlID      uint32
	ItemID     uint32
	ItemAction uint32
	ItemState  uint32
	HwndItem   syscall.Handle
	HDC        syscall.Handle
	RcItem     rect
	ItemData   uintptr
}

type initCommonControlsExStruct struct {
	Size uint32
	ICC  uint32
}

func utf16Ptr(s string) *uint16 {
	p, _ := syscall.UTF16PtrFromString(s)
	return p
}

func runInstallerGUI() {
	runtime.LockOSThread()

	icc := initCommonControlsExStruct{Size: 8, ICC: 0x00000020}
	initCommonControlsEx.Call(uintptr(unsafe.Pointer(&icc)))

	hInst, _, _ := getModuleHandleW.Call(0)
	state.hInstance = syscall.Handle(hInst)

	// Compute window size relative to screen (width ~20% of screen)
	screenW, _, _ := getSystemMetrics.Call(smCXScreen)
	screenH, _, _ := getSystemMetrics.Call(smCYScreen)
	winWidth = int(screenW) * 20 / 100
	if winWidth < 400 {
		winWidth = 400
	}
	winHeight = winWidth * 150 / 100 // 1.5:1 aspect ratio (tall)
	if winHeight > int(screenH)*85/100 {
		winHeight = int(screenH) * 85 / 100
	}
	iconSz = winWidth * 30 / 100 // Icon is ~30% of window width
	if iconSz > 256 {
		iconSz = 256
	}

	// Brushes
	ret, _, _ := createSolidBrush.Call(clrBg)
	state.hBgBrush = syscall.Handle(ret)
	ret, _, _ = createSolidBrush.Call(clrEditBg)
	state.hEditBrush = syscall.Handle(ret)

	// Fonts — scale with window width
	titlePt := winWidth * 54 / 660
	normalPt := winWidth * 24 / 660
	smallPt := winWidth * 20 / 660
	state.hTitleFont = makeFont("Segoe UI", titlePt, true)
	state.hNormalFont = makeFont("Segoe UI", normalPt, false)
	state.hSmallFont = makeFont("Segoe UI", smallPt, false)

	// App icon
	ret, _, _ = loadImageW.Call(hInst, uintptr(1), imageIcon, uintptr(iconSz), uintptr(iconSz), 0)
	state.hIcon = syscall.Handle(ret)

	// UAC shield icon — try multiple methods
	ret, _, _ = loadImageW.Call(0, uintptr(106), imageIcon, 0, 0, 0x00008000) // OIC_SHIELD=106, LR_SHARED
	if ret == 0 {
		ret, _, _ = loadIconW.Call(0, uintptr(32518)) // IDI_SHIELD fallback
	}
	state.hShieldIcon = syscall.Handle(ret)

	// Register window class
	className := utf16Ptr("FastFlixInstaller")
	cursor, _, _ := user32DLL.NewProc("LoadCursorW").Call(0, uintptr(32512))

	wc := wndClassExW{
		Size:       uint32(unsafe.Sizeof(wndClassExW{})),
		Style:      0x0003,
		WndProc:    syscall.NewCallback(wndProc),
		Instance:   state.hInstance,
		Icon:       state.hIcon,
		Cursor:     syscall.Handle(cursor),
		Background: state.hBgBrush,
		ClassName:  className,
		IconSm:     state.hIcon,
	}
	registerClassExW.Call(uintptr(unsafe.Pointer(&wc)))

	posX := (int(screenW) - winWidth) / 2
	posY := (int(screenH) - winHeight) / 2

	hwnd, _, _ := createWindowExW.Call(
		wsExComposited,
		uintptr(unsafe.Pointer(className)),
		uintptr(unsafe.Pointer(utf16Ptr("FastFlix Installer"))),
		0x00800000, // WS_BORDER only — no title bar, no system menu
		uintptr(posX), uintptr(posY), uintptr(winWidth), uintptr(winHeight),
		0, 0, hInst, 0,
	)
	state.hwnd = syscall.Handle(hwnd)

	// Dark title bar
	var dark int32 = 1
	dwmSetWindowAttribute.Call(hwnd, 20, uintptr(unsafe.Pointer(&dark)), 4)

	// Window icon
	if state.hIcon != 0 {
		sendMessageW.Call(hwnd, wmSetIcon, 0, uintptr(state.hIcon))
		sendMessageW.Call(hwnd, wmSetIcon, 1, uintptr(state.hIcon))
	}

	// Detect existing installs and process state BEFORE creating controls
	detectExistingInstall()
	state.processRunning = isProcessRunning("FastFlix.exe")

	createControls(hwnd, hInst)

	// Check process every 10 seconds
	setTimer.Call(hwnd, idtProcCheck, 10000, 0)

	showWindow.Call(hwnd, swShow)
	updateWindow.Call(hwnd)

	// Message loop
	var m msg
	for {
		r, _, _ := getMessageW.Call(uintptr(unsafe.Pointer(&m)), 0, 0, 0)
		if r == 0 {
			break
		}
		translateMessage.Call(uintptr(unsafe.Pointer(&m)))
		dispatchMessageW.Call(uintptr(unsafe.Pointer(&m)))
	}
}

const bsAutoRadioButton = 0x00000009

func createControls(hwnd, hInst uintptr) {
	cx := int32(winWidth)
	pad := cx * 9 / 100       // ~9% padding on each side
	btnW := cx - pad*2
	btnH := int32(winHeight) * 7 / 100 // button height ~7% of window

	// --- Checkbox + Terms link as a single owner-drawn button ---
	// This eliminates the gap between "the" and "Terms" since we draw it all ourselves
	y := int32(winHeight) * 50 / 100
	agreeW := cx * 65 / 100
	agreeX := (cx - agreeW) / 2
	ctlH := int32(winHeight) * 4 / 100

	// Hide agree checkbox if we need to uninstall first
	agreeStyle := uint32(wsChild | wsTabStop | bsOwnerDraw)
	if !state.existingFound {
		agreeStyle |= wsVisible
	}
	state.hAgree = createCtl("BUTTON", "",
		agreeStyle,
		agreeX, y, agreeW, ctlH, idcAgree, hwnd, hInst)

	// Terms link is hidden — clicks on the "Terms and Conditions" part of the
	// owner-drawn button are detected in WM_LBUTTONUP by hit-testing
	state.hTerms = 0 // no separate control

	y += int32(winHeight) * 8 / 100

	// Uninstall button
	uninstallText := "Uninstall previous version"
	if len(state.existingInstalls) > 1 {
		uninstallText = "Uninstall previous versions"
	}
	uninstallStyle := uint32(wsChild | wsTabStop | bsOwnerDraw)
	if state.existingFound {
		uninstallStyle |= wsVisible
	}
	state.hUninstallBtn = createCtl("BUTTON", uninstallText, uninstallStyle,
		pad, y, btnW, btnH, idcUninstall, hwnd, hInst)
	if state.processRunning {
		enableWindow.Call(uintptr(state.hUninstallBtn), 0)
	}

	// Remember where the uninstall button is for placing install buttons at the same Y
	uninstallY := y

	y += btnH + ctlH/4

	// Info label showing where previous installs were found (only if existing)
	infoStyle := uint32(wsChild | ssCenter)
	if state.existingFound {
		infoStyle |= wsVisible
	}
	infoH := ctlH * int32(len(state.existingInstalls))
	if infoH < ctlH {
		infoH = ctlH
	}
	state.hInstallInfo = createCtl("STATIC", buildInstallInfoText(),
		infoStyle, pad, y, btnW, infoH, idcInstInfo, hwnd, hInst)
	setFont(state.hInstallInfo, state.hSmallFont)

	// Install buttons — placed at same Y as uninstall button (they swap visibility)
	installY := uninstallY
	installStyle := uint32(wsChild | wsTabStop | bsOwnerDraw)
	if !state.existingFound {
		installStyle |= wsVisible
	}

	state.hUserBtn = createCtl("BUTTON", "Install for just me", installStyle,
		pad, installY, btnW, btnH, idcUser, hwnd, hInst)
	enableWindow.Call(uintptr(state.hUserBtn), 0)

	installY += btnH + btnH*20/100

	state.hAllBtn = createCtl("BUTTON", "Install for all users", installStyle,
		pad, installY, btnW, btnH, idcAll, hwnd, hInst)
	enableWindow.Call(uintptr(state.hAllBtn), 0)

	y = installY + btnH + btnH*40/100

	// Warning label (below buttons area)
	warningStyle := uint32(wsChild | ssCenter)
	if state.processRunning {
		warningStyle |= wsVisible
	}
	warnH := int32(winHeight) * 5 / 100
	state.hWarning = createCtl("STATIC",
		"\u26D4  FastFlix is currently running, please close it to continue",
		warningStyle, pad/2, y, cx-pad, warnH, idcWarning, hwnd, hInst)
	setFont(state.hWarning, state.hNormalFont)

	// --- Install progress + ad area (all hidden until install starts) ---
	// Progress bar right below the title/version area (~48%)
	progY := int32(winHeight) * 53 / 100
	progH := int32(winHeight) * 3 / 100
	labelH := int32(winHeight) * 4 / 100

	state.hProgress = createCtl("STATIC", "",
		wsChild|ssOwnerDraw, pad, progY, btnW, progH, idcProgress, hwnd, hInst)

	state.hProgLabel = createCtl("STATIC", "",
		wsChild|ssCenter, pad, progY+progH+labelH/4, btnW, labelH, idcProgLabel, hwnd, hInst)
	setFont(state.hProgLabel, state.hNormalFont)

	// Ad text below progress (hidden until install starts)
	adY := progY + progH + labelH + labelH
	adH := int32(winHeight) * 8 / 100
	state.hAdText = createCtl("STATIC",
		"Please check out my new project",
		wsChild|ssCenter, pad, adY, btnW, adH, idcAd, hwnd, hInst)
	setFont(state.hAdText, state.hNormalFont)

	state.hAdLink = createCtl("STATIC", "Beautiphoto",
		wsChild|ssCenter|ssNotify, pad, adY+adH, btnW, ctlH, idcAdLink, hwnd, hInst)
	setFont(state.hAdLink, state.hNormalFont)

	adPromoY := adY + adH + ctlH + ctlH/4
	adPromoH := int32(winHeight) * 4 / 100
	state.hAdPromo = createCtl("STATIC", "Use Promo code FastFlix0626 for half off for a year!",
		wsChild|ssCenter, pad, adPromoY, btnW, adPromoH, 0, hwnd, hInst)
	setFont(state.hAdPromo, state.hSmallFont)

	// Launch button near bottom (hidden until install completes)
	launchY := int32(winHeight) - btnH - int32(winHeight)*12/100
	state.hLaunchBtn = createCtl("BUTTON", "Launch FastFlix (8)",
		wsChild|wsTabStop|bsOwnerDraw,
		pad, launchY, btnW, btnH, idcLaunch, hwnd, hInst)

	// Close button — small, centered at bottom, visible during uninstall/install screens
	closeBtnW := cx * 20 / 100
	closeBtnH := int32(winHeight) * 4 / 100
	closeY := int32(winHeight) - closeBtnH - int32(winHeight)*13/100
	state.hCloseBtn = createCtl("BUTTON", "Close",
		wsChild|wsVisible|wsTabStop|bsOwnerDraw,
		(cx-closeBtnW)/2, closeY, closeBtnW, closeBtnH, idcClose, hwnd, hInst)
}

func createCtl(class, text string, style uint32, x, y, w, h int32, id int, parent, hInst uintptr) syscall.Handle {
	h2, _, _ := createWindowExW.Call(0,
		uintptr(unsafe.Pointer(utf16Ptr(class))),
		uintptr(unsafe.Pointer(utf16Ptr(text))),
		uintptr(style),
		uintptr(x), uintptr(y), uintptr(w), uintptr(h),
		parent, uintptr(id), hInst, 0)
	return syscall.Handle(h2)
}

func setFont(hwnd, hFont syscall.Handle) {
	sendMessageW.Call(uintptr(hwnd), wmSetFont, uintptr(hFont), 1)
}

func makeFont(family string, size int, bold bool) syscall.Handle {
	weight := int32(400)
	if bold {
		weight = 700
	}
	h, _, _ := createFontW.Call(uintptr(uint32(-size)), 0, 0, 0,
		uintptr(weight), 0, 0, 0, 1, 0, 0, 5, 0,
		uintptr(unsafe.Pointer(utf16Ptr(family))))
	return syscall.Handle(h)
}

func setText(hwnd syscall.Handle, text string) {
	setWindowTextW.Call(uintptr(hwnd), uintptr(unsafe.Pointer(utf16Ptr(text))))
}

func sleepMs(ms uint32) {
	kernel32DLL.NewProc("Sleep").Call(uintptr(ms))
}

// --- Window procedure ---

func wndProc(hwnd syscall.Handle, m uint32, wParam, lParam uintptr) uintptr {
	switch m {
	case wmPaint:
		paintWindow(hwnd)
		return 0
	case wmCtlColorStatic:
		hdc := syscall.Handle(wParam)
		ctl := syscall.Handle(lParam)
		setTextColor.Call(uintptr(hdc), clrText)
		setBkMode.Call(uintptr(hdc), transparent)
		if ctl == state.hAdLink {
			setTextColor.Call(uintptr(hdc), clrAccent)
		}
		if ctl == state.hWarning {
			setTextColor.Call(uintptr(hdc), clrRed)
		}
		return uintptr(state.hBgBrush)
	case wmCtlColorBtn:
		return uintptr(state.hBgBrush)
	case wmDrawItem:
		dis := (*drawItemStruct)(unsafe.Pointer(lParam))
		if dis.HwndItem == state.hProgress {
			drawProgressBar(dis)
		} else {
			drawButton(dis)
		}
		return 1
	case wmCommand:
		handleCommand(int(wParam&0xFFFF), int((wParam>>16)&0xFFFF))
		return 0
	case 0x0020: // WM_SETCURSOR
		// Show hand cursor over clickable links
		ctl := syscall.Handle(wParam)
		if ctl == state.hAdLink {
			hand, _, _ := user32DLL.NewProc("LoadCursorW").Call(0, 32649) // IDC_HAND
			user32DLL.NewProc("SetCursor").Call(hand)
			return 1
		}
	case wmTimer:
		if int(wParam) == idtProcCheck {
			checkProcessTimer()
		}
		if int(wParam) == idtCountdown {
			state.countdown--
			if state.countdown <= 0 {
				// Enable the launch button
				user32DLL.NewProc("KillTimer").Call(uintptr(hwnd), idtCountdown)
				setText(state.hLaunchBtn, "Launch FastFlix")
				enableWindow.Call(uintptr(state.hLaunchBtn), 1)
				invalidateRect.Call(uintptr(state.hLaunchBtn), 0, 1)
			} else {
				setText(state.hLaunchBtn, fmt.Sprintf("Launch FastFlix (%d)", state.countdown))
				invalidateRect.Call(uintptr(state.hLaunchBtn), 0, 1)
			}
		}
		return 0
	case wmClose:
		destroyWindow.Call(uintptr(hwnd))
		return 0
	case wmDestroy:
		postQuitMessage.Call(0)
		return 0
	}
	ret, _, _ := defWindowProcW.Call(uintptr(hwnd), uintptr(m), wParam, lParam)
	return ret
}

func paintWindow(hwnd syscall.Handle) {
	var ps paintStruct
	hdc, _, _ := beginPaint.Call(uintptr(hwnd), uintptr(unsafe.Pointer(&ps)))

	var rc rect
	getClientRectProc.Call(uintptr(hwnd), uintptr(unsafe.Pointer(&rc)))
	fillRectProc.Call(hdc, uintptr(unsafe.Pointer(&rc)), uintptr(state.hBgBrush))

	// Icon centered at top (~16% of window height margin)
	iconTop := int32(winHeight) * 16 / 100
	if state.hIcon != 0 {
		iconX := (int32(winWidth) - int32(iconSz)) / 2
		drawIconEx.Call(hdc, uintptr(iconX), uintptr(iconTop), uintptr(state.hIcon),
			uintptr(iconSz), uintptr(iconSz), 0, 0, 3)
	}

	setBkMode.Call(hdc, transparent)

	// "FastFlix" title — gap below icon (~4% of window height)
	titleGap := int32(winHeight) * 4 / 100
	titleY := iconTop + int32(iconSz) + titleGap
	setTextColor.Call(hdc, clrText)
	selectObject.Call(hdc, uintptr(state.hTitleFont))
	titleH := int32(winHeight) * 7 / 100
	titleR := rect{0, titleY, int32(winWidth), titleY + titleH}
	drawTextW.Call(hdc, uintptr(unsafe.Pointer(utf16Ptr("FastFlix"))),
		uintptr(len("FastFlix")), uintptr(unsafe.Pointer(&titleR)), dtCenter|dtSingleLine)

	// Version — tight below title
	setTextColor.Call(hdc, clrSubtext)
	selectObject.Call(hdc, uintptr(state.hNormalFont))
	ver := "version " + Version
	verY := titleY + titleH - int32(winHeight)*1/100
	verH := int32(winHeight) * 4 / 100
	verR := rect{0, verY, int32(winWidth), verY + verH}
	drawTextW.Call(hdc, uintptr(unsafe.Pointer(utf16Ptr(ver))),
		uintptr(len(ver)), uintptr(unsafe.Pointer(&verR)), dtCenter|dtSingleLine)

	endPaint.Call(uintptr(hwnd), uintptr(unsafe.Pointer(&ps)))
}

var (
	procEllipse   = gdi32DLL.NewProc("Ellipse")
	procCreatePen = gdi32DLL.NewProc("CreatePen")
	procRoundRect = gdi32DLL.NewProc("RoundRect")
)

func drawButton(dis *drawItemStruct) {
	hdc := dis.HDC
	rc := dis.RcItem
	disabled := dis.ItemState&0x0004 != 0
	isUninstall := dis.HwndItem == state.hUninstallBtn
	isAllUsers := dis.HwndItem == state.hAllBtn
	showShield := (isAllUsers || (isUninstall && state.uninstallNeedsAdmin)) && state.hShieldIcon != 0
	isAgree := dis.HwndItem == state.hAgree

	// --- Special drawing for the agree checkbox ---
	if isAgree {
		drawAgreeCheckbox(uintptr(hdc), rc)
		return
	}

	bgColor := uintptr(clrBtnBg)
	txtColor := uintptr(clrBtnText)
	if isUninstall {
		bgColor = clrBtnRed
		txtColor = clrText
		if disabled {
			bgColor = clrBtnRedDis
			txtColor = clrSubtext
		}
	} else if disabled {
		bgColor = clrBtnDis
		txtColor = clrSubtext
	}

	// Clear button area with window bg (so rounded corners don't show square artifacts)
	fillRectProc.Call(uintptr(hdc), uintptr(unsafe.Pointer(&rc)), uintptr(state.hBgBrush))

	// Rounded rectangle background
	cornerR := (rc.Bottom - rc.Top) / 4 // corner radius = 25% of button height
	brush, _, _ := createSolidBrush.Call(bgColor)
	// Need a null pen so RoundRect doesn't draw an outline
	nullPen, _, _ := procCreatePen.Call(5, 0, 0) // PS_NULL
	oldBrush, _, _ := selectObject.Call(uintptr(hdc), brush)
	oldPen2, _, _ := selectObject.Call(uintptr(hdc), nullPen)
	procRoundRect.Call(uintptr(hdc),
		uintptr(rc.Left), uintptr(rc.Top), uintptr(rc.Right), uintptr(rc.Bottom),
		uintptr(cornerR), uintptr(cornerR))
	selectObject.Call(uintptr(hdc), oldBrush)
	selectObject.Call(uintptr(hdc), oldPen2)
	deleteObject.Call(brush)
	deleteObject.Call(nullPen)

	setBkMode.Call(uintptr(hdc), transparent)
	setTextColor.Call(uintptr(hdc), txtColor)
	selectObject.Call(uintptr(hdc), uintptr(state.hNormalFont))

	buf := make([]uint16, 256)
	getWindowTextW.Call(uintptr(dis.HwndItem), uintptr(unsafe.Pointer(&buf[0])), 256)
	text := syscall.UTF16ToString(buf)

	// Shield icon size relative to button height
	shieldSz := (rc.Bottom - rc.Top) * 40 / 100
	if shieldSz < 16 {
		shieldSz = 16
	}
	if showShield {
		// Measure text width to place shield right beside it
		var measureR rect
		drawTextW.Call(uintptr(hdc), uintptr(unsafe.Pointer(utf16Ptr(text))),
			uintptr(len(text)), uintptr(unsafe.Pointer(&measureR)),
			dtSingleLine|0x00000400) // DT_CALCRECT

		// Total width = text + gap + shield, centered in button
		gap := shieldSz / 3
		totalW := measureR.Right + gap + shieldSz
		startX := rc.Left + (rc.Right-rc.Left-totalW)/2

		// Draw text
		textRc := rect{startX, rc.Top, startX + measureR.Right, rc.Bottom}
		drawTextW.Call(uintptr(hdc), uintptr(unsafe.Pointer(utf16Ptr(text))),
			uintptr(len(text)), uintptr(unsafe.Pointer(&textRc)), dtSingleLine|dtVCenter)

		// Draw shield right after text
		shieldX := startX + measureR.Right + gap
		shieldY := rc.Top + (rc.Bottom-rc.Top-shieldSz)/2
		drawIconEx.Call(uintptr(hdc), uintptr(shieldX), uintptr(shieldY),
			uintptr(state.hShieldIcon), uintptr(shieldSz), uintptr(shieldSz), 0, 0, 3)
	} else {
		drawTextW.Call(uintptr(hdc), uintptr(unsafe.Pointer(utf16Ptr(text))),
			uintptr(len(text)), uintptr(unsafe.Pointer(&rc)), dtCenter|dtSingleLine|dtVCenter)
	}
}

func drawAgreeCheckbox(hdc uintptr, rc rect) {
	h := rc.Bottom - rc.Top
	// Fill background
	fillRectProc.Call(hdc, uintptr(unsafe.Pointer(&rc)), uintptr(state.hBgBrush))

	setBkMode.Call(hdc, transparent)
	selectObject.Call(hdc, uintptr(state.hNormalFont))

	// Draw circle (radio indicator) — scaled to row height
	circleR := h * 25 / 100 // radius (compact)
	circleCX := rc.Left + circleR + h*15/100
	circleCY := rc.Top + h/2

	// Circle outline — 3px thick for visibility
	penWidth := uintptr(3)
	if circleR > 12 {
		penWidth = 4
	}
	pen, _, _ := procCreatePen.Call(0, penWidth, clrAccent) // PS_SOLID, thick, accent color
	oldPen, _, _ := selectObject.Call(hdc, pen)
	if state.agreeChecked {
		// Filled circle
		br, _, _ := createSolidBrush.Call(clrAccent)
		oldBr, _, _ := selectObject.Call(hdc, br)
		procEllipse.Call(hdc,
			uintptr(circleCX-circleR), uintptr(circleCY-circleR),
			uintptr(circleCX+circleR), uintptr(circleCY+circleR))
		selectObject.Call(hdc, oldBr)
		deleteObject.Call(br)
	} else {
		// Empty circle
		nullBrush, _, _ := gdi32DLL.NewProc("GetStockObject").Call(5) // HOLLOW_BRUSH
		oldBr, _, _ := selectObject.Call(hdc, nullBrush)
		procEllipse.Call(hdc,
			uintptr(circleCX-circleR), uintptr(circleCY-circleR),
			uintptr(circleCX+circleR), uintptr(circleCY+circleR))
		selectObject.Call(hdc, oldBr)
	}
	selectObject.Call(hdc, oldPen)
	deleteObject.Call(pen)

	// Text starts after circle
	textX := circleCX + circleR + h*15/100

	// "I Agree to the " in normal text color
	setTextColor.Call(hdc, clrText)
	agreeStr := "I Agree to the "
	agreeR := rect{textX, rc.Top, rc.Right, rc.Bottom}
	drawTextW.Call(hdc, uintptr(unsafe.Pointer(utf16Ptr(agreeStr))),
		uintptr(len(agreeStr)), uintptr(unsafe.Pointer(&agreeR)), dtSingleLine|dtVCenter)

	// Measure "I Agree to the " width to position the link text
	var measureR rect
	drawTextW.Call(hdc, uintptr(unsafe.Pointer(utf16Ptr(agreeStr))),
		uintptr(len(agreeStr)), uintptr(unsafe.Pointer(&measureR)), dtSingleLine|0x00000400) // DT_CALCRECT

	// "Terms and Conditions" in accent color — immediately after
	termsX := textX + measureR.Right
	setTextColor.Call(hdc, clrAccent)
	termsStr := "Terms and Conditions"
	termsR := rect{termsX, rc.Top, rc.Right, rc.Bottom}
	drawTextW.Call(hdc, uintptr(unsafe.Pointer(utf16Ptr(termsStr))),
		uintptr(len(termsStr)), uintptr(unsafe.Pointer(&termsR)), dtSingleLine|dtVCenter)

	// Store the terms link X boundary for hit-testing
	state.termsLinkX = termsX
}

func drawProgressBar(dis *drawItemStruct) {
	hdc := uintptr(dis.HDC)
	rc := dis.RcItem
	cornerR := (rc.Bottom - rc.Top) / 3

	// Dark background track
	bgBrush, _, _ := createSolidBrush.Call(0x00222222) // very dark gray
	nullPen, _, _ := procCreatePen.Call(5, 0, 0)       // PS_NULL
	oldBr, _, _ := selectObject.Call(hdc, bgBrush)
	oldPn, _, _ := selectObject.Call(hdc, nullPen)
	procRoundRect.Call(hdc,
		uintptr(rc.Left), uintptr(rc.Top), uintptr(rc.Right), uintptr(rc.Bottom),
		uintptr(cornerR), uintptr(cornerR))

	// Filled portion
	if state.progressValue > 0 {
		fillW := (rc.Right - rc.Left) * int32(state.progressValue) / 100
		if fillW < cornerR*2 {
			fillW = cornerR * 2 // minimum width for rounded rect to look right
		}
		fillBrush, _, _ := createSolidBrush.Call(clrBtnBg) // accent color
		selectObject.Call(hdc, fillBrush)
		procRoundRect.Call(hdc,
			uintptr(rc.Left), uintptr(rc.Top), uintptr(rc.Left+fillW), uintptr(rc.Bottom),
			uintptr(cornerR), uintptr(cornerR))
		deleteObject.Call(fillBrush)
	}

	selectObject.Call(hdc, oldBr)
	selectObject.Call(hdc, oldPn)
	deleteObject.Call(bgBrush)
	deleteObject.Call(nullPen)
}

func setProgress(pct int) {
	state.progressValue = pct
	invalidateRect.Call(uintptr(state.hProgress), 0, 1)
}

// --- Command handling ---

func handleCommand(id, notif int) {
	switch id {
	case idcAgree:
		// Toggle agree state and check if they clicked on the "Terms" portion
		state.agreeChecked = !state.agreeChecked
		invalidateRect.Call(uintptr(state.hAgree), 0, 1)
		// Get cursor position to check if they clicked on the link text
		var pt struct{ X, Y int32 }
		user32DLL.NewProc("GetCursorPos").Call(uintptr(unsafe.Pointer(&pt)))
		user32DLL.NewProc("ScreenToClient").Call(uintptr(state.hAgree), uintptr(unsafe.Pointer(&pt)))
		if state.termsLinkX > 0 {
			// Account for the agree button's position in the parent
			var agreeRect rect
			user32DLL.NewProc("GetWindowRect").Call(uintptr(state.hAgree), uintptr(unsafe.Pointer(&agreeRect)))
			var parentRect rect
			user32DLL.NewProc("GetWindowRect").Call(uintptr(state.hwnd), uintptr(unsafe.Pointer(&parentRect)))
			localTermsX := state.termsLinkX - (agreeRect.Left - parentRect.Left)
			if pt.X >= localTermsX {
				// Clicked on "Terms and Conditions" — open dialog
				// Undo the toggle since this was a link click, not an agree click
				state.agreeChecked = !state.agreeChecked
				invalidateRect.Call(uintptr(state.hAgree), 0, 1)
				showScrollableDialog("Terms and Conditions", termsAndLicensesText)
			}
		}
		updateButtonState()
	case idcUninstall:
		if notif == bnClicked {
			go onUninstallClicked() // Run in goroutine to keep UI responsive
		}
	case idcUser:
		if notif == bnClicked {
			go doInstallFromGUI(modeUser)
		}
	case idcAll:
		if notif == bnClicked {
			go doInstallForAllUsers()
		}
	case idcAdLink:
		if notif == 0 { // STN_CLICKED
			url, _ := syscall.UTF16PtrFromString("https://beautiphoto.com")
			open, _ := syscall.UTF16PtrFromString("open")
			syscall.NewLazyDLL("shell32.dll").NewProc("ShellExecuteW").Call(
				0, uintptr(unsafe.Pointer(open)), uintptr(unsafe.Pointer(url)), 0, 0, 1)
		}
	case idcClose:
		postQuitMessage.Call(0)
	case idcLaunch:
		// Accept any notification — owner-drawn buttons may send different codes
		exePath := filepath.Join(state.installedDir, "FastFlix.exe")
		if state.installedDir == "" {
			messageBox("Error", "Install directory not set", 0x10)
			return
		}
		if _, err := os.Stat(exePath); err != nil {
			messageBox("Error", "FastFlix.exe not found at:\n"+exePath, 0x10)
			return
		}
		// Launch via cmd.exe /c start "" "path" to get a fully detached process with console
		cmd := fmt.Sprintf(`/c start "" "%s"`, exePath)
		cmdPtr, _ := syscall.UTF16PtrFromString(cmd)
		exeCmd, _ := syscall.UTF16PtrFromString("cmd.exe")
		dirPtr, _ := syscall.UTF16PtrFromString(state.installedDir)
		shell32 := syscall.NewLazyDLL("shell32.dll")
		shell32.NewProc("ShellExecuteW").Call(
			0, 0, // NULL verb = "open"
			uintptr(unsafe.Pointer(exeCmd)),
			uintptr(unsafe.Pointer(cmdPtr)),
			uintptr(unsafe.Pointer(dirPtr)),
			0) // SW_HIDE for the cmd, FastFlix opens its own window
		postQuitMessage.Call(0)
	}
}

func updateButtonState() {
	agreed := state.agreeChecked

	// Uninstall button
	if state.existingFound && !state.previousRemoved {
		can := agreed && !state.processRunning && !state.installing
		e := uintptr(0)
		if can {
			e = 1
		}
		enableWindow.Call(uintptr(state.hUninstallBtn), e)
		invalidateRect.Call(uintptr(state.hUninstallBtn), 0, 1)
	}

	// Install buttons
	canInstall := agreed && !state.processRunning && !state.installing && !state.existingFound
	e := uintptr(0)
	if canInstall {
		e = 1
	}
	enableWindow.Call(uintptr(state.hUserBtn), e)
	enableWindow.Call(uintptr(state.hAllBtn), e)
	invalidateRect.Call(uintptr(state.hUserBtn), 0, 1)
	invalidateRect.Call(uintptr(state.hAllBtn), 0, 1)
}

func onUninstallClicked() {
	// Re-check if FastFlix is running right now
	if isProcessRunning("FastFlix.exe") {
		state.processRunning = true
		showWindow.Call(uintptr(state.hWarning), swShow)
		enableWindow.Call(uintptr(state.hUninstallBtn), 0)
		invalidateRect.Call(uintptr(state.hUninstallBtn), 0, 1)
		messageBox("FastFlix Running",
			"FastFlix is currently running.\n\nPlease close FastFlix before uninstalling.", 0x30)
		return
	}

	enableWindow.Call(uintptr(state.hUninstallBtn), 0)
	setText(state.hUninstallBtn, "Uninstalling...")
	invalidateRect.Call(uintptr(state.hUninstallBtn), 0, 1)

	installs := findAllExistingInstalls()

	// Check upfront if ANY install is in a protected path — request UAC once
	needsAdmin := false
	for _, inst := range installs {
		if inst.InstallDir != "" && isProtectedPath(inst.InstallDir) {
			needsAdmin = true
			break
		}
	}
	if needsAdmin && !isAdmin() {
		// Build a single elevated cmd that removes all protected directories + registry + shortcuts
		var cmds []string
		for _, inst := range installs {
			if inst.InstallDir != "" && isProtectedPath(inst.InstallDir) {
				cmds = append(cmds, fmt.Sprintf(`rmdir /s /q "%s"`, inst.InstallDir))
			}
		}
		// Also remove common Start Menu
		commonSM := filepath.Join(os.Getenv("ProgramData"), "Microsoft", "Windows", "Start Menu", "Programs", productName)
		cmds = append(cmds, fmt.Sprintf(`rmdir /s /q "%s"`, commonSM))
		// Also clean HKLM registry keys via reg.exe
		cmds = append(cmds, fmt.Sprintf(`reg delete "HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall\%s" /f`, productName))
		cmds = append(cmds, fmt.Sprintf(`reg delete "HKLM\SOFTWARE\%s" /f`, productName))

		cmdStr := strings.Join(cmds, " & ")
		verb, _ := syscall.UTF16PtrFromString("runas")
		exe, _ := syscall.UTF16PtrFromString("cmd.exe")
		argPtr, _ := syscall.UTF16PtrFromString("/c " + cmdStr)
		cwdPtr, _ := syscall.UTF16PtrFromString(".")
		shell32 := syscall.NewLazyDLL("shell32.dll")
		retUAC, _, _ := shell32.NewProc("ShellExecuteW").Call(0,
			uintptr(unsafe.Pointer(verb)), uintptr(unsafe.Pointer(exe)),
			uintptr(unsafe.Pointer(argPtr)), uintptr(unsafe.Pointer(cwdPtr)), 0)

		if retUAC <= 32 {
			// User cancelled UAC — show error and stay on uninstall page
			messageBox("Administrator Access Required",
				"The previous installation is in a protected location (Program Files).\n\nAdministrator access is required to remove it. Please click Uninstall again and accept the permission prompt.",
				0x30)
			resetUninstallButton()
			return
		}

		setText(state.hUninstallBtn, "Removing (elevated)...")
		invalidateRect.Call(uintptr(state.hUninstallBtn), 0, 1)

		// Give the elevated process time to start before polling
		sleepMs(3000)

		// Wait for protected directories to disappear (up to 60 seconds)
		for i := 0; i < 60; i++ {
			allGone := true
			for _, inst := range installs {
				if inst.InstallDir != "" && isProtectedPath(inst.InstallDir) {
					if _, err := os.Stat(inst.InstallDir); err == nil {
						allGone = false
					}
				}
			}
			if allGone {
				break
			}
			sleepMs(1000)
		}
		// Extra wait for registry cleanup to complete
		sleepMs(2000)
	}

	// Clean up all installs directly — we don't call existing uninstallers
	// because they may be old installer builds that show UI or hit mutex issues.
	// cleanupInstallation handles: dirs, shortcuts, desktop icons, registry.
	for _, inst := range installs {
		cleanupInstallation(inst)
	}

	// For protected paths that were removed by elevated cmd, also verify
	// the directory is actually gone before checking registry
	for _, inst := range installs {
		if inst.InstallDir != "" && isProtectedPath(inst.InstallDir) {
			// If directory is gone, the elevated cleanup succeeded
			if _, err := os.Stat(inst.InstallDir); err != nil {
				// Dir is gone — also clean any remaining Start Menu shortcuts we can access
				userSM := filepath.Join(os.Getenv("APPDATA"), "Microsoft", "Windows", "Start Menu", "Programs", productName)
				os.RemoveAll(userSM)
			}
		}
	}

	// Final verify — only transition if installs are actually gone
	remaining := findAllExistingInstalls()
	if len(remaining) > 0 {
		// Try one more cleanup pass
		for _, inst := range remaining {
			cleanupInstallation(inst)
		}
		remaining = findAllExistingInstalls()
	}

	if len(remaining) > 0 {
		// Check if it's just orphaned registry (dirs actually gone) vs real remaining files
		var realRemaining []string
		for _, inst := range remaining {
			if inst.InstallDir != "" {
				if _, err := os.Stat(inst.InstallDir); err == nil {
					// Directory still exists on disk
					realRemaining = append(realRemaining, inst.InstallDir)
				}
			}
		}

		if len(realRemaining) > 0 {
			// Directories still exist — show error
			msg := "The following could not be fully removed:\n\n" + strings.Join(realRemaining, "\n")
			msg += "\n\nThis may require administrator permissions or the files may be in use."
			msg += "\nPlease try again or remove manually."
			messageBox("Uninstall Incomplete", msg, 0x30)
			resetUninstallButton()
			return
		}
		// Dirs are gone but registry lingers — clean it up and continue
		for _, root := range []registry.Key{registry.LOCAL_MACHINE, registry.CURRENT_USER} {
			registry.DeleteKey(root, `Software\Microsoft\Windows\CurrentVersion\Uninstall\`+productName)
			registry.DeleteKey(root, `SOFTWARE\`+productName)
		}
	}

	// Uninstall succeeded — show agree checkbox + install buttons
	state.previousRemoved = true
	state.existingFound = false
	showWindow.Call(uintptr(state.hUninstallBtn), swHide)
	showWindow.Call(uintptr(state.hInstallInfo), swHide)
	showWindow.Call(uintptr(state.hAgree), swShow)
	showWindow.Call(uintptr(state.hUserBtn), swShow)
	showWindow.Call(uintptr(state.hAllBtn), swShow)
	updateButtonState()
}

// shouldShowAd returns true while the Beautiphoto promo is active (through 2026-06-30).
func shouldShowAd() bool {
	promoEnd := time.Date(2026, 7, 1, 0, 0, 0, 0, time.Local)
	return time.Now().Before(promoEnd)
}

// showAdDuringInstall shows the ad text as soon as install begins (while progress bar is visible).
func showAdDuringInstall() {
	if shouldShowAd() {
		showWindow.Call(uintptr(state.hAdText), swShow)
		showWindow.Call(uintptr(state.hAdLink), swShow)
		showWindow.Call(uintptr(state.hAdPromo), swShow)
	}
}

// showPostInstallScreen hides progress, shows launch button with countdown.
func showPostInstallScreen() {
	// Hide progress bar and label
	showWindow.Call(uintptr(state.hProgress), swHide)
	showWindow.Call(uintptr(state.hProgLabel), swHide)

	showAd := shouldShowAd()
	// Ad should already be visible from showAdDuringInstall, but ensure it
	if showAd {
		showWindow.Call(uintptr(state.hAdText), swShow)
		showWindow.Call(uintptr(state.hAdLink), swShow)
		showWindow.Call(uintptr(state.hAdPromo), swShow)
	}

	// Show launch button with countdown
	state.countdown = 8
	if !showAd {
		state.countdown = 0
	}

	showWindow.Call(uintptr(state.hLaunchBtn), swShow)
	if state.countdown > 0 {
		setText(state.hLaunchBtn, fmt.Sprintf("Launch FastFlix (%d)", state.countdown))
		enableWindow.Call(uintptr(state.hLaunchBtn), 0)
		invalidateRect.Call(uintptr(state.hLaunchBtn), 0, 1)
		setTimer.Call(uintptr(state.hwnd), idtCountdown, 1000, 0)
	} else {
		setText(state.hLaunchBtn, "Launch FastFlix")
		enableWindow.Call(uintptr(state.hLaunchBtn), 1)
	}
}

func resetUninstallButton() {
	resetText := "Uninstall previous version"
	if len(state.existingInstalls) > 1 {
		resetText = "Uninstall previous versions"
	}
	setText(state.hUninstallBtn, resetText)
	enableWindow.Call(uintptr(state.hUninstallBtn), 1)
	invalidateRect.Call(uintptr(state.hUninstallBtn), 0, 1)
}

func checkProcessTimer() {
	running := isProcessRunning("FastFlix.exe")
	if running != state.processRunning {
		state.processRunning = running
		if running {
			showWindow.Call(uintptr(state.hWarning), swShow)
		} else {
			showWindow.Call(uintptr(state.hWarning), swHide)
		}
		updateButtonState()
	}
}

func detectExistingInstall() {
	installs := findAllExistingInstalls()
	if len(installs) == 0 {
		return
	}

	// Filter: only keep installs where the directory has a real FastFlix install
	// (not just a leftover uninstall.exe from incomplete self-deletion)
	var real []existingInstall
	for _, inst := range installs {
		if inst.InstallDir != "" {
			ffExe := filepath.Join(inst.InstallDir, "FastFlix.exe")
			pythonDir := filepath.Join(inst.InstallDir, "python")
			if _, err := os.Stat(ffExe); err == nil {
				real = append(real, inst)
			} else if _, err := os.Stat(pythonDir); err == nil {
				real = append(real, inst)
			}
			// Dir with only uninstall.exe is a leftover — clean it up
			if _, err := os.Stat(inst.InstallDir); err == nil {
				if _, err2 := os.Stat(ffExe); err2 != nil {
					if _, err3 := os.Stat(pythonDir); err3 != nil {
						os.RemoveAll(inst.InstallDir)
					}
				}
			}
		}
	}

	// If all were orphaned registry keys (dirs gone), clean them up silently
	if len(real) == 0 {
		cleanAllRegistryKeys()
		return // No actual installs on disk — skip uninstall screen
	}

	state.existingFound = true
	state.existingInstalls = real
	state.existingDir = real[0].InstallDir
	for _, inst := range real {
		if inst.Version != "" {
			state.existingVersion = inst.Version
			break
		}
	}
	for _, inst := range real {
		if inst.InstallDir != "" && isProtectedPath(inst.InstallDir) {
			state.uninstallNeedsAdmin = true
			break
		}
	}
}

// buildInstallInfoText creates a human-readable summary of where previous installs were found.
func buildInstallInfoText() string {
	var lines []string
	programFiles := strings.ToLower(os.Getenv("ProgramFiles"))
	localAppData := strings.ToLower(os.Getenv("LOCALAPPDATA"))

	for _, inst := range state.existingInstalls {
		ver := inst.Version
		if ver == "" {
			ver = "unknown version"
		}
		dirLower := strings.ToLower(inst.InstallDir)
		location := inst.InstallDir
		if programFiles != "" && strings.HasPrefix(dirLower, programFiles) {
			location = "Program Files"
		} else if localAppData != "" && strings.HasPrefix(dirLower, localAppData) {
			location = "Local Apps"
		}
		lines = append(lines, fmt.Sprintf("%s found in %s", ver, location))
	}
	return strings.Join(lines, "\n")
}

func doInstallFromGUI(mode installMode) {
	state.installing = true
	updateButtonState()

	// Hide controls, show progress
	for _, h := range []syscall.Handle{state.hAgree, state.hUserBtn, state.hAllBtn, state.hWarning, state.hUninstallBtn, state.hInstallInfo, state.hCloseBtn} {
		showWindow.Call(uintptr(h), swHide)
	}
	showWindow.Call(uintptr(state.hProgress), swShow)
	showWindow.Call(uintptr(state.hProgLabel), swShow)
	setText(state.hProgLabel, "Installing...")
	showAdDuringInstall()

	installDir, regRoot, startMenu := installPaths(mode)
	os.MkdirAll(installDir, 0755)

	lastPct := -1
	err := extractTarZstd(distArchive, installDir, func(current, total int) {
		pct := (current * 95) / total // 0-95% for extraction
		if pct != lastPct {           // only update on actual change
			lastPct = pct
			setProgress(pct)
			setText(state.hProgLabel, fmt.Sprintf("Installing... %d%%", pct))
		}
	})
	if err != nil {
		messageBox("Installation Failed", "Failed to extract files:\n"+err.Error(), 0x10)
		postQuitMessage.Call(0)
		return
	}

	setText(state.hProgLabel, "Finalizing...")
	setProgress(95)

	writeRegistry(installDir, regRoot)
	writeInstalledSize(installDir, regRoot)
	createShortcuts(installDir, startMenu)

	setProgress(100)
	setText(state.hProgLabel, "Installation complete!")

	state.installedDir = installDir
	showPostInstallScreen()
}

// doInstallForAllUsers triggers UAC immediately, then the elevated process does everything.
// The GUI stays visible and polls for completion.
func doInstallForAllUsers() {
	state.installing = true
	updateButtonState()

	installDir, _, _ := installPaths(modeAllUsers)
	selfPath, _ := os.Executable()

	// Create a temp dir for the done marker
	tempDir, err := os.MkdirTemp("", "fastflix-install-*")
	if err != nil {
		messageBox("Installation Failed", "Failed to create temp directory:\n"+err.Error(), 0x10)
		return
	}
	doneMarker := filepath.Join(tempDir, ".done")

	// Trigger UAC IMMEDIATELY — elevated process does extract + registry + shortcuts
	verb, _ := syscall.UTF16PtrFromString("runas")
	exe, _ := syscall.UTF16PtrFromString(selfPath)
	cmdArgs := fmt.Sprintf(`--elevated-install --dest "%s" --marker "%s"`, installDir, doneMarker)
	argPtr, _ := syscall.UTF16PtrFromString(cmdArgs)
	cwd, _ := syscall.UTF16PtrFromString(".")

	shell32 := syscall.NewLazyDLL("shell32.dll")
	shellExec := shell32.NewProc("ShellExecuteW")
	ret, _, _ := shellExec.Call(0, uintptr(unsafe.Pointer(verb)), uintptr(unsafe.Pointer(exe)),
		uintptr(unsafe.Pointer(argPtr)), uintptr(unsafe.Pointer(cwd)), 0)
	if ret <= 32 {
		// User cancelled UAC or error
		os.RemoveAll(tempDir)
		state.installing = false
		updateButtonState()
		return
	}

	// UAC accepted — now show progress
	for _, h := range []syscall.Handle{state.hAgree, state.hUserBtn, state.hAllBtn, state.hWarning, state.hUninstallBtn, state.hInstallInfo, state.hCloseBtn} {
		showWindow.Call(uintptr(h), swHide)
	}
	showWindow.Call(uintptr(state.hProgress), swShow)
	showWindow.Call(uintptr(state.hProgLabel), swShow)
	setText(state.hProgLabel, "Installing to Program Files...")
	showAdDuringInstall()

	// Poll for completion with smooth animated progress
	// Uses an ease-out curve: fast at start, slows as it approaches 95%
	for i := 1; i <= 600; i++ { // up to 5 minutes (500ms intervals)
		if _, err := os.Stat(doneMarker); err == nil {
			break
		}
		// Ease-out: progress = 95 * (1 - e^(-i/30))
		// At i=15 (~7.5s): ~35%, i=30 (~15s): ~55%, i=60 (~30s): ~76%, i=90 (~45s): ~86%
		progress := 95.0 * (1.0 - math.Exp(-float64(i)/30.0))
		pct := int(progress)
		if pct > 95 {
			pct = 95
		}
		setProgress(pct)
		setText(state.hProgLabel, fmt.Sprintf("Installing to Program Files... %d%%", pct))
		sleepMs(500)
	}

	os.RemoveAll(tempDir)

	setProgress(100)
	setText(state.hProgLabel, "Installation complete!")

	state.installedDir = installDir
	showPostInstallScreen()
}

// --- Scrollable text dialog ---

var dlgState struct {
	hEdit  syscall.Handle
	hClose syscall.Handle
}

func showScrollableDialog(title, content string) {
	hInst := state.hInstance
	className := utf16Ptr("FastFlixDialog")
	cursor, _, _ := user32DLL.NewProc("LoadCursorW").Call(0, uintptr(32512))

	wc := wndClassExW{
		Size:       uint32(unsafe.Sizeof(wndClassExW{})),
		Style:      0x0003,
		WndProc:    syscall.NewCallback(dialogWndProc),
		Instance:   hInst,
		Cursor:     syscall.Handle(cursor),
		Background: state.hBgBrush,
		ClassName:  className,
	}
	registerClassExW.Call(uintptr(unsafe.Pointer(&wc)))

	screenW, _, _ := getSystemMetrics.Call(smCXScreen)
	screenH, _, _ := getSystemMetrics.Call(smCYScreen)
	// Dialog: 35% of screen width, 50% of screen height
	dlgW := int32(screenW) * 35 / 100
	dlgH := int32(screenH) * 50 / 100
	if dlgW < 500 {
		dlgW = 500
	}
	if dlgH < 400 {
		dlgH = 400
	}
	posX := (int(screenW) - int(dlgW)) / 2
	posY := (int(screenH) - int(dlgH)) / 2
	dlgPad := dlgW * 2 / 100 // 2% padding

	hwnd, _, _ := createWindowExW.Call(0,
		uintptr(unsafe.Pointer(className)),
		uintptr(unsafe.Pointer(utf16Ptr(title))),
		wsOverlapped|wsCaption|wsSysMenu,
		uintptr(posX), uintptr(posY), uintptr(dlgW), uintptr(dlgH),
		uintptr(state.hwnd), 0, uintptr(hInst), 0)

	var dark int32 = 1
	dwmSetWindowAttribute.Call(hwnd, 20, uintptr(unsafe.Pointer(&dark)), 4)

	// Edit control fills most of the dialog
	btnH := dlgH * 7 / 100
	editH := dlgH - dlgPad*2 - btnH - dlgPad*3
	dlgState.hEdit = createCtl("EDIT", "",
		wsChild|wsVisible|wsVScroll|wsBorder|esMultiline|esReadOnly|esAutoVScroll|wsTabStop,
		dlgPad, dlgPad, dlgW-dlgPad*2-16, editH, idcDlgEdit, hwnd, uintptr(hInst))
	setFont(dlgState.hEdit, state.hSmallFont)
	editMargin := dlgW * 2 / 100
	sendMessageW.Call(uintptr(dlgState.hEdit), emSetMargins, 3, uintptr(editMargin|(editMargin<<16)))
	sendMessageW.Call(uintptr(dlgState.hEdit), wmSetText, 0, uintptr(unsafe.Pointer(utf16Ptr(content))))

	// Close button centered at bottom
	closeBtnW := dlgW * 25 / 100
	dlgState.hClose = createCtl("BUTTON", "Close",
		wsChild|wsVisible|wsTabStop|bsOwnerDraw,
		(dlgW-closeBtnW)/2, dlgPad+editH+dlgPad, closeBtnW, btnH, idcDlgClose, hwnd, uintptr(hInst))

	showWindow.Call(hwnd, swShow)
	updateWindow.Call(hwnd)
	enableWindow.Call(uintptr(state.hwnd), 0)

	var m msg
	for {
		r, _, _ := getMessageW.Call(uintptr(unsafe.Pointer(&m)), 0, 0, 0)
		if r == 0 {
			break
		}
		alive, _, _ := isWindowProc.Call(hwnd)
		if alive == 0 {
			break
		}
		translateMessage.Call(uintptr(unsafe.Pointer(&m)))
		dispatchMessageW.Call(uintptr(unsafe.Pointer(&m)))
	}

	enableWindow.Call(uintptr(state.hwnd), 1)
	setForegroundWindow.Call(uintptr(state.hwnd))
}

func dialogWndProc(hwnd syscall.Handle, m uint32, wParam, lParam uintptr) uintptr {
	switch m {
	case wmCtlColorStatic, wmCtlColorEdit:
		hdc := syscall.Handle(wParam)
		setTextColor.Call(uintptr(hdc), clrText)
		// IMPORTANT: Use OPAQUE mode for EDIT controls, not TRANSPARENT.
		// TRANSPARENT causes garbled text as redraws paint over previous text.
		setBkMode.Call(uintptr(hdc), 2) // OPAQUE
		gdi32DLL.NewProc("SetBkColor").Call(uintptr(hdc), clrEditBg)
		return uintptr(state.hEditBrush)
	case wmDrawItem:
		drawButton((*drawItemStruct)(unsafe.Pointer(lParam)))
		return 1
	case wmCommand:
		if int(wParam&0xFFFF) == idcDlgClose {
			destroyWindow.Call(uintptr(hwnd))
			return 0
		}
	case wmClose:
		destroyWindow.Call(uintptr(hwnd))
		return 0
	case wmDestroy:
		postQuitMessage.Call(0)
		return 0
	}
	ret, _, _ := defWindowProcW.Call(uintptr(hwnd), uintptr(m), wParam, lParam)
	return ret
}
