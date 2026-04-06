package main

import (
	_ "embed"
	"encoding/json"
	"strings"
	"syscall"
)

//go:embed fastflix_dist.tar.zst
var distArchive []byte

//go:embed terms_translations.json
var termsTranslationsJSON string

//go:embed licenses.txt
var licensesFileText string

const mitLicense = `The MIT License

Copyright (c) 2019-2025 Chris Griffith

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.`

var termsAndLicensesText string

func init() {
	terms := loadTermsForLocale()

	// Use \r\n throughout for Windows EDIT control compatibility
	sep := "\r\n\r\n" + strings.Repeat("\u2550", 50) + "\r\n"

	termsAndLicensesText = terms +
		sep + "SOFTWARE LICENSE (MIT)\r\n" + strings.Repeat("\u2550", 50) + "\r\n\r\n" +
		strings.ReplaceAll(mitLicense, "\n", "\r\n") +
		sep + "THIRD-PARTY LICENSES\r\n" + strings.Repeat("\u2550", 50) + "\r\n\r\n" +
		strings.ReplaceAll(licensesFileText, "\n", "\r\n")
}

// loadTermsForLocale returns the terms text for the current system language.
// If the system language is not English and is supported, shows the translation
// followed by a divider and the English version.
func loadTermsForLocale() string {
	var translations map[string]string
	json.Unmarshal([]byte(termsTranslationsJSON), &translations)

	english := translations["eng"]
	if english == "" {
		english = "FastFlix Terms and Agreements\r\n\r\n(Terms text not available)"
	}

	langCode := detectSystemLanguage()

	if langCode != "eng" {
		if translated, ok := translations[langCode]; ok && translated != "" {
			divider := "\r\n\r\n" + strings.Repeat("\u2500", 50) + "\r\n\r\n"
			return translated + divider + english
		}
	}
	return english
}

// detectSystemLanguage uses GetUserDefaultUILanguage to detect the OS language
// and maps it to a FastFlix language code.
func detectSystemLanguage() string {
	kernel32 := syscall.NewLazyDLL("kernel32.dll")
	ret, _, _ := kernel32.NewProc("GetUserDefaultUILanguage").Call()
	primaryLang := int(ret) & 0x3FF

	switch primaryLang {
	case 0x07:
		return "deu" // German
	case 0x0C:
		return "fra" // French
	case 0x10:
		return "ita" // Italian
	case 0x0A:
		return "spa" // Spanish
	case 0x04:
		return "chs" // Chinese Simplified
	case 0x11:
		return "jpn" // Japanese
	case 0x19:
		return "rus" // Russian
	case 0x16:
		return "por" // Portuguese
	case 0x1D:
		return "swe" // Swedish
	case 0x15:
		return "pol" // Polish
	case 0x22:
		return "ukr" // Ukrainian
	case 0x12:
		return "kor" // Korean
	case 0x18:
		return "ron" // Romanian
	default:
		return "eng"
	}
}
