# Trae Multi-Platform Download & Reverse Engineering Plan

**Goal:** Download the latest Trae IDE and SOLO installers for all platforms (macOS, Windows, Linux), extract and analyze their internals, compare cross-platform differences, and extend the existing reverse engineering analysis.

**Architecture:** Download installers from CDN → Extract app bundles → Analyze per-platform binaries (ai-agent, cli.js, main.js, product.json) → Compare cross-platform differences → Document findings in markdown reports.

**Tech Stack:** curl/wget for downloads, 7zip/patool for extraction, nm/strings/objdump for binary analysis, Python/Node for JS analysis

**Scope:** Large
**Risk:** Low (read-only analysis, no code changes)

**Risks:**
- Large download sizes (100-200MB each) may exceed disk space → monitor with df
- Windows .exe is NSIS installer, may need special extraction tools → use 7zip
- Linux .deb needs ar/dpkg for extraction → use standard tools
- Some CDN regions may be slow → use sg (Singapore) region URLs

**Autonomy Level:** Full

---

## Download Manifest (from API: `https://api-us-east.trae.ai/icube/api/v1/native/version/trae/latest`)

### TRAE IDE v2.3.30128

| Platform | Arch | URL (sg region) |
|----------|------|-----------------|
| macOS | arm64 (Apple Silicon) | `https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30128/darwin/Trae-darwin-arm64.dmg` |
| macOS | x64 (Intel) | `https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30128/darwin/Trae-darwin-x64.dmg` |
| Windows | x64 | `https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30128/win32/Trae-Setup-x64.exe` |
| Linux | x64 (.deb) | `https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30128/linux/Trae-linux-x64.deb` |
| Linux | x64 (.rpm) | `https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30128/linux/Trae-linux-x64.rpm` |
| Linux | x64 (.tar.gz) | `https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30128/linux/Trae-linux-x64.tar.gz` |
| Linux | arm64 (.deb) | `https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30128/linux/Trae-linux-arm64.deb` |
| Linux | arm64 (.rpm) | `https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30128/linux/Trae-linux-arm64.rpm` |
| Linux | arm64 (.tar.gz) | `https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30128/linux/Trae-linux-arm64.tar.gz` |

### TRAE SOLO v2.3.30125

| Platform | Arch | URL (sg region) |
|----------|------|-----------------|
| macOS | arm64 (Apple Silicon) | `https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30125/darwin/TRAE_SOLO-darwin-arm64.dmg` |
| macOS | x64 (Intel) | `https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30125/darwin/TRAE_SOLO-darwin-x64.dmg` |
| Windows | x64 | `https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30125/win32/TRAE_SOLO-Setup-x64.exe` |

### Mobile

| Platform | URL |
|----------|-----|
| iOS | `https://apps.apple.com/app/id6761401019` |
| Android | `https://play.google.com/store/apps/details?id=com.bytedance.trae.overseas` |
| Android APK | `https://lf-cdn.trae.ai/obj/trae-ai-sg/TRAE-overseas-release-0.0.2-20200-b22065ce-20260429.apk` |

---

### Task 1: Download All Trae IDE Installers

**Depends on:** None
**Files:**
- Create: `data/ide/darwin-arm64/Trae-darwin-arm64.dmg`
- Create: `data/ide/darwin-x64/Trae-darwin-x64.dmg`
- Create: `data/ide/win32-x64/Trae-Setup-x64.exe`
- Create: `data/ide/linux-x64/Trae-linux-x64.deb`
- Create: `data/ide/linux-x64/Trae-linux-x64.tar.gz`
- Create: `data/ide/linux-arm64/Trae-linux-arm64.deb`
- Create: `data/ide/linux-arm64/Trae-linux-arm64.tar.gz`

- [ ] **Step 1: Create directory structure for downloads**

```bash
mkdir -p data/ide/{darwin-arm64,darwin-x64,win32-x64,linux-x64,linux-arm64}
```

- [ ] **Step 2: Download macOS ARM64 DMG**

```bash
curl -L -o data/ide/darwin-arm64/Trae-darwin-arm64.dmg "https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30128/darwin/Trae-darwin-arm64.dmg"
```

Expected: File size > 100MB, exit code 0

- [ ] **Step 3: Download macOS Intel DMG**

```bash
curl -L -o data/ide/darwin-x64/Trae-darwin-x64.dmg "https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30128/darwin/Trae-darwin-x64.dmg"
```

Expected: File size > 100MB, exit code 0

- [ ] **Step 4: Download Windows x64 EXE**

```bash
curl -L -o data/ide/win32-x64/Trae-Setup-x64.exe "https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30128/win32/Trae-Setup-x64.exe"
```

Expected: File size > 80MB, exit code 0

- [ ] **Step 5: Download Linux x64 DEB**

```bash
curl -L -o data/ide/linux-x64/Trae-linux-x64.deb "https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30128/linux/Trae-linux-x64.deb"
```

Expected: File size > 80MB, exit code 0

- [ ] **Step 6: Download Linux x64 tar.gz**

```bash
curl -L -o data/ide/linux-x64/Trae-linux-x64.tar.gz "https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30128/linux/Trae-linux-x64.tar.gz"
```

Expected: File size > 80MB, exit code 0

- [ ] **Step 7: Download Linux arm64 DEB**

```bash
curl -L -o data/ide/linux-arm64/Trae-linux-arm64.deb "https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30128/linux/Trae-linux-arm64.deb"
```

Expected: File size > 80MB, exit code 0

- [ ] **Step 8: Download Linux arm64 tar.gz**

```bash
curl -L -o data/ide/linux-arm64/Trae-linux-arm64.tar.gz "https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30128/linux/Trae-linux-arm64.tar.gz"
```

Expected: File size > 80MB, exit code 0

- [ ] **Step 9: Verify all downloads**

Run: `ls -lh data/ide/*/*.{dmg,exe,deb,tar.gz} 2>/dev/null | wc -l && du -sh data/ide/`
Expected:
  - 7 files listed
  - Total size < 2GB

---

### Task 2: Download TRAE SOLO Installers

**Depends on:** None
**Files:**
- Create: `data/solo/darwin-arm64/TRAE_SOLO-darwin-arm64.dmg`
- Create: `data/solo/darwin-x64/TRAE_SOLO-darwin-x64.dmg`
- Create: `data/solo/win32-x64/TRAE_SOLO-Setup-x64.exe`
- Create: `data/mobile/TRAE-overseas-release.apk`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p data/solo/{darwin-arm64,darwin-x64,win32-x64} data/mobile
```

- [ ] **Step 2: Download SOLO macOS ARM64 DMG**

```bash
curl -L -o data/solo/darwin-arm64/TRAE_SOLO-darwin-arm64.dmg "https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30125/darwin/TRAE_SOLO-darwin-arm64.dmg"
```

Expected: File size > 100MB, exit code 0

- [ ] **Step 3: Download SOLO macOS Intel DMG**

```bash
curl -L -o data/solo/darwin-x64/TRAE_SOLO-darwin-x64.dmg "https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30125/darwin/TRAE_SOLO-darwin-x64.dmg"
```

Expected: File size > 100MB, exit code 0

- [ ] **Step 4: Download SOLO Windows x64 EXE**

```bash
curl -L -o data/solo/win32-x64/TRAE_SOLO-Setup-x64.exe "https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30125/win32/TRAE_SOLO-Setup-x64.exe"
```

Expected: File size > 80MB, exit code 0

- [ ] **Step 5: Download Android APK**

```bash
curl -L -o data/mobile/TRAE-overseas-release.apk "https://lf-cdn.trae.ai/obj/trae-ai-sg/TRAE-overseas-release-0.0.2-20200-b22065ce-20260429.apk"
```

Expected: File size > 30MB, exit code 0

- [ ] **Step 6: Verify all SOLO downloads**

Run: `ls -lh data/solo/*/*.{dmg,exe} data/mobile/*.apk 2>/dev/null`
Expected:
  - 4 files listed
  - All files > 10MB

---

### Task 3: Extract Linux tar.gz and Analyze App Structure

**Depends on:** Task 1
**Files:**
- Create: `data/ide/linux-x64/extracted/` (extracted app)
- Create: `analysis/linux-x64-structure.md`

- [ ] **Step 1: Extract Linux x64 tar.gz**

```bash
mkdir -p data/ide/linux-x64/extracted && tar -xzf data/ide/linux-x64/Trae-linux-x64.tar.gz -C data/ide/linux-x64/extracted/
```

Expected: Exit code 0, extracted directory contains Trae app

- [ ] **Step 2: Document Linux app structure**

```bash
find data/ide/linux-x64/extracted/ -maxdepth 4 -type f | head -100 > /tmp/linux-structure.txt
cat /tmp/linux-structure.txt
```

Expected: Output shows similar structure to macOS (Resources/app/out/, etc.)

- [ ] **Step 3: Extract product.json from Linux build**

```bash
cat data/ide/linux-x64/extracted/*/resources/app/product.json 2>/dev/null || cat data/ide/linux-x64/extracted/resources/app/product.json 2>/dev/null || find data/ide/linux-x64/extracted/ -name "product.json" -exec cat {} \;
```

Expected: JSON output with version info, update URL, extensions

- [ ] **Step 4: Extract package.json from Linux build**

```bash
find data/ide/linux-x64/extracted/ -name "package.json" -path "*/resources/app/*" -exec cat {} \; 2>/dev/null | head -100
```

Expected: JSON with Electron version, dependencies, etc.

- [ ] **Step 5: Analyze Linux ai-agent binary**

```bash
find data/ide/linux-x64/extracted/ -name "ai-agent" -type f | head -5
```

If found:
```bash
AI_AGENT=$(find data/ide/linux-x64/extracted/ -name "ai-agent" -type f | head -1)
file "$AI_AGENT"
nm -C "$AI_AGENT" 2>/dev/null | head -50
strings "$AI_AGENT" 2>/dev/null | head -100
```

Expected: ELF binary, Rust-compiled, similar architecture to macOS version

- [ ] **Step 6: Create Linux structure analysis report**

Create `analysis/linux-x64-structure.md` documenting:
- Directory structure
- Key files found (product.json, package.json, ai-agent, cli.js, main.js)
- Binary types (ELF x86_64 vs macOS Mach-O ARM64)
- Differences from macOS build

- [ ] **Step 7: Extract Linux arm64 tar.gz and compare**

```bash
mkdir -p data/ide/linux-arm64/extracted && tar -xzf data/ide/linux-arm64/Trae-linux-arm64.tar.gz -C data/ide/linux-arm64/extracted/
find data/ide/linux-arm64/extracted/ -name "ai-agent" -type f -exec file {} \;
```

Expected: ELF aarch64 binary

- [ ] **Step 8: 提交**

Run: `git add data/download-manifest.json analysis/linux-x64-structure.md && git commit -m "feat: add Linux Trae IDE extraction and structure analysis"`

---

### Task 4: Extract Windows EXE and Analyze App Structure

**Depends on:** Task 1
**Files:**
- Create: `data/ide/win32-x64/extracted/` (extracted app)
- Create: `analysis/win32-x64-structure.md`

- [ ] **Step 1: Install extraction tools**

```bash
pip install patool 2>/dev/null || apt-get install -y p7zip-full 2>/dev/null || echo "7zip already available or not needed"
which 7z 2>/dev/null || which 7za 2>/dev/null || echo "need 7zip"
```

Expected: At least one extraction tool available

- [ ] **Step 2: Extract Windows EXE (NSIS installer)**

```bash
mkdir -p data/ide/win32-x64/extracted
7z x data/ide/win32-x64/Trae-Setup-x64.exe -odata/ide/win32-x64/extracted/ -y 2>/dev/null || 7za x data/ide/win32-x64/Trae-Setup-x64.exe -odata/ide/win32-x64/extracted/ -y 2>/dev/null
```

Expected: Extracted directory with installer contents

- [ ] **Step 3: Document Windows app structure**

```bash
find data/ide/win32-x64/extracted/ -maxdepth 4 -type f | head -100
```

Expected: NSIS installer structure with app payload

- [ ] **Step 4: Find and extract product.json**

```bash
find data/ide/win32-x64/extracted/ -name "product.json" -exec cat {} \; 2>/dev/null
```

Expected: JSON with Windows-specific paths and config

- [ ] **Step 5: Analyze Windows ai-agent binary**

```bash
find data/ide/win32-x64/extracted/ -name "ai-agent*" -type f | head -5
find data/ide/win32-x64/extracted/ -name "ai-agent.exe" -o -name "ai-agent" | head -5
```

If found:
```bash
AI_AGENT=$(find data/ide/win32-x64/extracted/ -name "ai-agent*" -type f | head -1)
file "$AI_AGENT"
strings "$AI_AGENT" 2>/dev/null | head -100
```

Expected: PE32+ executable (Windows x64), Rust-compiled

- [ ] **Step 6: Create Windows structure analysis report**

Create `analysis/win32-x64-structure.md` documenting:
- NSIS installer structure
- Key files found
- Binary types (PE32+ vs ELF vs Mach-O)
- Windows-specific differences from macOS/Linux builds
- ai-agent binary comparison

- [ ] **Step 7: 提交**

Run: `git add analysis/win32-x64-structure.md && git commit -m "feat: add Windows Trae IDE extraction and structure analysis"`

---

### Task 5: Extract macOS DMG and Compare with Previous Analysis

**Depends on:** Task 1
**Files:**
- Create: `data/ide/darwin-arm64/extracted/` (extracted app)
- Create: `analysis/darwin-arm64-v2-comparison.md`

- [ ] **Step 1: Extract macOS ARM64 DMG**

```bash
mkdir -p data/ide/darwin-arm64/mount
sudo hdiutil attach data/ide/darwin-arm64/Trae-darwin-arm64.dmg -mountpoint data/ide/darwin-arm64/mount -readonly -nobrowse 2>/dev/null || echo "Cannot mount DMG on Linux, will use 7zip"
```

If on Linux (cannot mount DMG):
```bash
7z x data/ide/darwin-arm64/Trae-darwin-arm64.dmg -odata/ide/darwin-arm64/extracted/ -y 2>/dev/null || dmg2img data/ide/darwin-arm64/Trae-darwin-arm64.dmg data/ide/darwin-arm64/Trae.img 2>/dev/null
```

Expected: Extracted or mounted DMG contents

- [ ] **Step 2: Extract product.json from new macOS build**

```bash
find data/ide/darwin-arm64/ -name "product.json" -path "*/app/*" -exec cat {} \; 2>/dev/null | python3 -m json.tool > /tmp/new-product.json 2>/dev/null
cat /tmp/new-product.json
```

Expected: JSON with version 2.3.30128, update URLs, etc.

- [ ] **Step 3: Extract ai-agent binary and compare with existing analysis**

```bash
find data/ide/darwin-arm64/ -name "ai-agent" -type f | head -5
```

If found:
```bash
NEW_AI_AGENT=$(find data/ide/darwin-arm64/ -name "ai-agent" -type f | head -1)
file "$NEW_AI_AGENT"
strings "$NEW_AI_AGENT" | wc -l
strings "$NEW_AI_AGENT" | grep -i "icube_server_rs\|marscode\|claude\|deepseek" | head -20
```

Expected: Mach-O ARM64, Rust binary, similar to v1.98.2 but updated

- [ ] **Step 4: Compare versions — v1.98.2 (old) vs v2.3.30128 (new)**

```bash
# Old version: 1.98.2, Electron v34.2.0
# New version: 2.3.30128
# Key question: What changed in ai-agent? What new AI features were added?
echo "Old version: 1.98.2 (Electron 34.2.0)"
echo "New version: 2.3.30128"
echo "Checking for new strings in ai-agent..."
```

- [ ] **Step 5: Create macOS comparison analysis report**

Create `analysis/darwin-arm64-v2-comparison.md` documenting:
- Version changes (1.98.2 → 2.3.30128)
- New AI models referenced in ai-agent strings
- New tools/capabilities discovered
- Changes to product.json
- Any new security mechanisms

- [ ] **Step 6: 提交**

Run: `git add analysis/darwin-arm64-v2-comparison.md && git commit -m "feat: add macOS ARM64 v2.3.30128 comparison analysis"`

---

### Task 6: Cross-Platform Binary Comparison — ai-agent Analysis

**Depends on:** Task 3, Task 4, Task 5
**Files:**
- Create: `analysis/ai-agent-cross-platform.md`

- [ ] **Step 1: Find all ai-agent binaries across platforms**

```bash
echo "=== Linux x64 ==="
find data/ide/linux-x64/ -name "ai-agent" -type f -exec file {} \; -exec ls -lh {} \;

echo "=== Linux arm64 ==="
find data/ide/linux-arm64/ -name "ai-agent" -type f -exec file {} \; -exec ls -lh {} \;

echo "=== Windows x64 ==="
find data/ide/win32-x64/ -name "ai-agent*" -type f -exec file {} \; -exec ls -lh {} \;

echo "=== macOS ARM64 ==="
find data/ide/darwin-arm64/ -name "ai-agent" -type f -exec file {} \; -exec ls -lh {} \;
```

Expected: Binaries found for each platform: ELF x86_64, ELF aarch64, PE32+ x64, Mach-O ARM64

- [ ] **Step 2: Extract strings from each ai-agent binary and compare**

```bash
# Extract strings from each binary
for platform in "linux-x64" "linux-arm64" "win32-x64" "darwin-arm64"; do
  binary=$(find data/ide/$platform/ -name "ai-agent*" -type f 2>/dev/null | head -1)
  if [ -n "$binary" ]; then
    strings "$binary" > "data/ide/$platform/ai-agent-strings.txt" 2>/dev/null
    echo "$platform: $(wc -l < data/ide/$platform/ai-agent-strings.txt) strings"
  fi
done
```

Expected: Each binary has 100K+ strings, Rust-compiled

- [ ] **Step 3: Compare string sets across platforms**

```bash
# Find strings unique to each platform and shared across all
python3 << 'PYEOF'
import os

platforms = ["linux-x64", "linux-arm64", "win32-x64", "darwin-arm64"]
string_sets = {}

for p in platforms:
    path = f"data/ide/{p}/ai-agent-strings.txt"
    if os.path.exists(path):
        with open(path) as f:
            string_sets[p] = set(line.strip() for line in f if line.strip())
            print(f"{p}: {len(string_sets[p])} unique strings")

# Find common strings
if len(string_sets) >= 2:
    common = set.intersection(*string_sets.values())
    print(f"\nCommon across all: {len(common)} strings")

    # Find platform-unique strings
    for p in platforms:
        if p in string_sets:
            others = set.union(*[v for k, v in string_sets.items() if k != p])
            unique = string_sets[p] - others
            print(f"{p} unique: {len(unique)} strings")
            # Show some interesting unique strings
            interesting = [s for s in sorted(unique) if len(s) > 10 and ('/' in s or '::' in s or 'mod' in s.lower())]
            print(f"  Interesting unique: {interesting[:20]}")
PYEOF
```

Expected: Most strings shared (Rust code), some platform-specific (paths, library names)

- [ ] **Step 4: Compare exported symbols across platforms**

```bash
for platform in "linux-x64" "linux-arm64" "win32-x64" "darwin-arm64"; do
  binary=$(find data/ide/$platform/ -name "ai-agent*" -type f 2>/dev/null | head -1)
  if [ -n "$binary" ]; then
    echo "=== $platform exports ==="
    nm -D "$binary" 2>/dev/null | head -30 || objdump -T "$binary" 2>/dev/null | head -30 || echo "Cannot read symbols"
  fi
done
```

Expected: Similar export tables with crypto, sqlite, compression functions

- [ ] **Step 5: Search for AI model references across platforms**

```bash
for platform in "linux-x64" "linux-arm64" "win32-x64" "darwin-arm64"; do
  path="data/ide/$platform/ai-agent-strings.txt"
  if [ -f "$path" ]; then
    echo "=== $platform AI model references ==="
    grep -iE 'claude|gpt|deepseek|qwen|llama|model.*name|chat.*model|api.*key' "$path" | sort -u | head -20
  fi
done
```

Expected: Similar AI model references across platforms

- [ ] **Step 6: Create cross-platform comparison report**

Create `analysis/ai-agent-cross-platform.md` documenting:
- Binary format comparison (Mach-O vs ELF vs PE32+)
- Binary sizes across platforms
- String count and overlap analysis
- Platform-specific differences
- Exported function comparison
- AI model and feature comparison
- Security mechanism differences

- [ ] **Step 7: 提交**

Run: `git add analysis/ai-agent-cross-platform.md data/ide/*/ai-agent-strings.txt && git commit -m "feat: add ai-agent cross-platform binary comparison analysis"`

---

### Task 7: Analyze cli.js and main.js Across Platforms

**Depends on:** Task 3, Task 4, Task 5
**Files:**
- Create: `analysis/cli-js-cross-platform.md`
- Create: `analysis/main-js-cross-platform.md`

- [ ] **Step 1: Find cli.js and main.js across all platforms**

```bash
for platform in "linux-x64" "win32-x64" "darwin-arm64"; do
  echo "=== $platform ==="
  find data/ide/$platform/ -name "cli.js" -o -name "main.js" | head -10
done
```

Expected: cli.js and main.js in resources/app/out/ for each platform

- [ ] **Step 2: Compare cli.js files across platforms**

```bash
for platform in "linux-x64" "win32-x64" "darwin-arm64"; do
  cli=$(find data/ide/$platform/ -name "cli.js" -path "*/out/*" | head -1)
  if [ -n "$cli" ]; then
    echo "$platform: $(wc -l < "$cli") lines, $(wc -c < "$cli") bytes"
    md5sum "$cli"
  fi
done
```

Expected: Either identical files or minor platform-specific differences

- [ ] **Step 3: Diff cli.js between platforms**

```bash
CLI_LINUX=$(find data/ide/linux-x64/ -name "cli.js" -path "*/out/*" | head -1)
CLI_WIN=$(find data/ide/win32-x64/ -name "cli.js" -path "*/out/*" | head -1)
CLI_MAC=$(find data/ide/darwin-arm64/ -name "cli.js" -path "*/out/*" | head -1)

if [ -n "$CLI_LINUX" ] && [ -n "$CLI_WIN" ]; then
  diff <(md5sum "$CLI_LINUX") <(md5sum "$CLI_WIN") && echo "Linux vs Windows: IDENTICAL" || echo "Linux vs Windows: DIFFERENT"
fi
if [ -n "$CLI_LINUX" ] && [ -n "$CLI_MAC" ]; then
  diff <(md5sum "$CLI_LINUX") <(md5sum "$CLI_MAC") && echo "Linux vs macOS: IDENTICAL" || echo "Linux vs macOS: DIFFERENT"
fi
```

Expected: Likely identical (JavaScript is platform-agnostic)

- [ ] **Step 4: Search for platform-specific code paths in cli.js**

```bash
CLI_LINUX=$(find data/ide/linux-x64/ -name "cli.js" -path "*/out/*" | head -1)
if [ -n "$CLI_LINUX" ]; then
  grep -oP '"(win32|darwin|linux|mac|windows)[^"]*"' "$CLI_LINUX" | sort -u | head -20
  grep -oP "'(win32|darwin|linux|mac|windows)[^']*'" "$CLI_LINUX" | sort -u | head -20
fi
```

Expected: Platform detection and conditional code paths

- [ ] **Step 5: Create cli.js cross-platform analysis report**

Create `analysis/cli-js-cross-platform.md` documenting:
- Whether cli.js is identical across platforms
- Platform-specific code paths
- New modules or functions compared to v1.98.2
- Changes in CLI startup and command handling

- [ ] **Step 6: 提交**

Run: `git add analysis/cli-js-cross-platform.md analysis/main-js-cross-platform.md && git commit -m "feat: add cli.js and main.js cross-platform analysis"`

---

### Task 8: Analyze product.json and Extension System

**Depends on:** Task 3, Task 4, Task 5
**Files:**
- Create: `analysis/product-json-analysis.md`
- Create: `analysis/extensions-analysis.md`

- [ ] **Step 1: Collect and compare product.json from all platforms**

```bash
for platform in "linux-x64" "win32-x64" "darwin-arm64"; do
  pj=$(find data/ide/$platform/ -name "product.json" -path "*/app/*" | head -1)
  if [ -n "$pj" ]; then
    echo "=== $platform product.json ==="
    cat "$pj" | python3 -m json.tool 2>/dev/null | head -80
    echo ""
  fi
done
```

Expected: Nearly identical product.json with version, update URLs, extension IDs

- [ ] **Step 2: Extract and analyze built-in extensions**

```bash
for platform in "linux-x64"; do
  ext_dir=$(find data/ide/$platform/ -type d -name "extensions" -path "*/app/*" | head -1)
  if [ -n "$ext_dir" ]; then
    echo "=== Built-in extensions ==="
    ls -la "$ext_dir/"
    for ext in "$ext_dir"/*/; do
      name=$(basename "$ext")
      pkg=$(cat "$ext/package.json" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{d.get(\"name\",\"?\")} v{d.get(\"version\",\"?\")} - {d.get(\"description\",\"?\")[:80]}')" 2>/dev/null)
      echo "  $name: $pkg"
    done
  fi
done
```

Expected: 20+ built-in extensions including Python, C++, AI features

- [ ] **Step 3: Analyze extension marketplace and custom extension mechanism**

```bash
pj=$(find data/ide/linux-x64/ -name "product.json" -path "*/app/*" | head -1)
if [ -n "$pj" ]; then
  cat "$pj" | python3 -c "
import sys, json
d = json.load(sys.stdin)
keys = ['extensionsGallery', 'extensionRecommendations', 'extensionKeywords', 'aiExtension', 'keymapExtension', 'extensionEnabledApiProposals']
for k in keys:
    if k in d:
        print(f'{k}: {json.dumps(d[k], indent=2)[:500]}')
    else:
        # Search for any extension-related keys
        for dk in d:
            if 'extension' in dk.lower() or 'marketplace' in dk.lower() or 'gallery' in dk.lower():
                print(f'{dk}: {json.dumps(d[dk], indent=2)[:500]}')
" 2>/dev/null
fi
```

Expected: Custom extension gallery URL (likely ByteDance's own marketplace, not Microsoft's)

- [ ] **Step 4: Create product.json and extensions analysis report**

Create `analysis/product-json-analysis.md` documenting:
- product.json key fields and their values
- Comparison across platforms
- Extension gallery configuration (ByteDance vs Microsoft marketplace)
- Built-in extension list with descriptions
- Custom extension mechanism and security

- [ ] **Step 5: 提交**

Run: `git add analysis/product-json-analysis.md analysis/extensions-analysis.md && git commit -m "feat: add product.json and extensions system analysis"`

---

### Task 9: SOLO vs IDE — Structural Comparison

**Depends on:** Task 2, Task 3, Task 5
**Files:**
- Create: `analysis/solo-vs-ide-comparison.md`

- [ ] **Step 1: Extract SOLO macOS ARM64 DMG**

```bash
mkdir -p data/solo/darwin-arm64/extracted
7z x data/solo/darwin-arm64/TRAE_SOLO-darwin-arm64.dmg -odata/solo/darwin-arm64/extracted/ -y 2>/dev/null || echo "Will try dmg2img or other method"
```

Expected: Extracted SOLO app bundle

- [ ] **Step 2: Compare SOLO and IDE app structures**

```bash
echo "=== IDE structure ==="
find data/ide/darwin-arm64/ -maxdepth 5 -type d | head -50

echo "=== SOLO structure ==="
find data/solo/darwin-arm64/ -maxdepth 5 -type d | head -50
```

Expected: SOLO may have different directory structure, possibly a different Electron app

- [ ] **Step 3: Compare product.json between SOLO and IDE**

```bash
IDE_PJ=$(find data/ide/darwin-arm64/ -name "product.json" -path "*/app/*" | head -1)
SOLO_PJ=$(find data/solo/darwin-arm64/ -name "product.json" -path "*/app/*" | head -1)

echo "=== IDE product.json ==="
cat "$IDE_PJ" 2>/dev/null | python3 -m json.tool 2>/dev/null | head -30

echo "=== SOLO product.json ==="
cat "$SOLO_PJ" 2>/dev/null | python3 -m json.tool 2>/dev/null | head -30
```

Expected: Different product names, version numbers, possibly different AI features

- [ ] **Step 4: Check if SOLO has its own ai-agent binary**

```bash
find data/solo/ -name "ai-agent*" -type f | head -5
find data/solo/ -name "*.asar" -type f | head -5
```

Expected: SOLO may share or have its own ai-agent

- [ ] **Step 5: Create SOLO vs IDE comparison report**

Create `analysis/solo-vs-ide-comparison.md` documenting:
- Structural differences between SOLO and IDE
- product.json comparison
- Binary and module differences
- AI capability differences (SOLO is marketed as "Context Engineer")
- Whether SOLO is a separate app or a mode within IDE

- [ ] **Step 6: 提交**

Run: `git add analysis/solo-vs-ide-comparison.md && git commit -m "feat: add SOLO vs IDE structural comparison analysis"`

---

### Task 10: Generate Comprehensive Reverse Engineering Report

**Depends on:** Task 6, Task 7, Task 8, Task 9
**Files:**
- Create: `analysis/comprehensive-report.md`

- [ ] **Step 1: Compile all analysis into a comprehensive report**

Create `analysis/comprehensive-report.md` with sections:
1. **Executive Summary** — Key findings across all platforms
2. **Version Evolution** — Changes from v1.98.2 to v2.3.30128
3. **Architecture Overview** — Cross-platform Electron + Rust ai-agent architecture
4. **ai-agent Deep Analysis** — Cross-platform binary comparison, new features
5. **CLI and Main Process Analysis** — JavaScript layer comparison
6. **Extension System** — Custom marketplace, built-in extensions
7. **SOLO vs IDE** — Product differentiation analysis
8. **Security Analysis** — VBVirtualize, SQLCipher, AES-GCM across platforms
9. **AI/LLM Integration** — Models, tools, MCP support
10. **Network Communication** — API endpoints, WebSocket protocol
11. **Data Storage** — .icube directory, SQLite with SQLCipher
12. **Key Discoveries** — Leaked developer info, internal code names, architecture decisions

- [ ] **Step 2: Update project README.md with new findings**

- [ ] **Step 3: 提交**

Run: `git add analysis/comprehensive-report.md README.md && git commit -m "feat: add comprehensive reverse engineering report for Trae v2.3.30128"`

---

## Summary of Download URLs (SG Region — for quick reference)

**TRAE IDE v2.3.30128:**
- macOS ARM64: `https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30128/darwin/Trae-darwin-arm64.dmg`
- macOS Intel: `https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30128/darwin/Trae-darwin-x64.dmg`
- Windows x64: `https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30128/win32/Trae-Setup-x64.exe`
- Linux x64 deb: `https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30128/linux/Trae-linux-x64.deb`
- Linux x64 rpm: `https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30128/linux/Trae-linux-x64.rpm`
- Linux x64 tar.gz: `https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30128/linux/Trae-linux-x64.tar.gz`
- Linux arm64 deb: `https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30128/linux/Trae-linux-arm64.deb`
- Linux arm64 rpm: `https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30128/linux/Trae-linux-arm64.rpm`
- Linux arm64 tar.gz: `https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30128/linux/Trae-linux-arm64.tar.gz`

**TRAE SOLO v2.3.30125:**
- macOS ARM64: `https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30125/darwin/TRAE_SOLO-darwin-arm64.dmg`
- macOS Intel: `https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30125/darwin/TRAE_SOLO-darwin-x64.dmg`
- Windows x64: `https://lf-cdn.trae.ai/obj/trae-ai-sg/pkg/app/releases/stable/2.3.30125/win32/TRAE_SOLO-Setup-x64.exe`

**Android APK:** `https://lf-cdn.trae.ai/obj/trae-ai-sg/TRAE-overseas-release-0.0.2-20200-b22065ce-20260429.apk`
