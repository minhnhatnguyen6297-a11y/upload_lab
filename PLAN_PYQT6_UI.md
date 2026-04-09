# Kế hoạch Thiết kế lại UI - PyQt6

## 1. Mục tiêu

Thay thế UI Tkinter hiện tại bằng giao diện PyQt6 hiện đại, chuyên nghiệp hơn, với UX tốt hơn cho tool Upload Nam Định.

**Tool hiện tại:** Batch scan → Extract contract → Upload Playwright (3 tabs Tkinter) # Bỏ tab 2, chuyển tên tab thành tiếng việt, batch scan thành "Quét hồ sơ", upload playwright thành "Upload hồ sơ"
**Mục tiêu:** Giữ chức năng y hệt, nhưng:
- Giao diện sạch, professional
- Responsive design
- Feedback tốt hơn cho user
- Dark/Light theme support (optional)

---

## 2. Cấu trúc dự án

```
./
├── ui_app_pyqt6.py              # File UI chính (thay thế ui_runner.py)
├── ui/
│   ├── __init__.py
│   ├── main_window.py            # MainWindow class
│   ├── tabs/
│   │   ├── __init__.py
│   │   ├── batch_scan_tab.py    # Tab Batch Scan
│   │   ├── extract_tab.py       # Tab Extract 1 File
│   │   └── upload_tab.py        # Tab Upload Playwright
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── file_browser.py      # File/Folder browser widget
│   │   ├── progress_panel.py    # Progress display widget
│   │   ├── log_viewer.py        # Log text viewer widget
│   │   └── table_widget.py      # Custom table for records
│   ├── styles/
│   │   ├── __init__.py
│   │   └── stylesheets.py       # QSS stylesheets (colors, fonts, etc)
│   └── threads/
│       ├── __init__.py
│       ├── batch_scan_worker.py # Thread worker cho batch scan
│       ├── extract_worker.py    # Thread worker cho extract
│       └── upload_worker.py     # Thread worker cho upload
├── bootstrap_ui_pyqt6.py        # Bootstrap script (thay thế bootstrap_ui.py)
├── run_ui_pyqt6.bat             # Batch file launcher (thay thế run_ui.bat)
└── requirements.txt             # Thêm PyQt6>=6.4.0
```

---

## 3. Công nghệ & Dependencies

### Framework
- **PyQt6 >= 6.4.0**: GUI framework
- **Python 3.8+**: Compatibility

### Dependencies hiện tại (giữ nguyên)
- python-docx==1.1.2
- pywin32
- python-dotenv
- playwright
- openpyxl

### Thêm mới
- PyQt6>=6.4.0

---

## 4. Tính năng UI

### ✅ Đã hoàn tất
- Title: "Batch Scan & Upload Tool - Nam Định" ✅
- Window size: 1280x900 (resizable, min 1024x700) ✅
- Status bar: Show current operation, ready status ✅
- 2 tabs (bỏ Extract tab) ✅
- Tiếng Việt: "Quét hồ sơ" + "Upload hồ sơ" ✅

### 4.2 Tab 1: Batch Scan Folder ✅
**Bố cục:**
- Group Box 1: Folder Selection
  - Input: Folder path (read-only display + button Browse)
  - Button: Browse Folder
  
- Group Box 2: Options
  - Input: Modified Since date (YYYY-MM-DD format, placeholder)
  - Checkbox: Full Rescan
  
- Group Box 3: Actions
  - Button: Run Batch Scan
  - Button: Convert .doc → .docx (1 time) 
  # bỏ chức năng này
  # thêm nút chỉnh số để chỉnh độ sâu của folder quét (mặc định hiện tại là 3)
- Group Box 4: Progress (collapsible)
  - Progress bar: File processing progress
  - Status text: "Processing X/Y files | candidates=A | success=B | failed=C"
  - Detail text: Current file, last outcome
  - Speed: Files/sec, ETA time
  # ghi trạng thái bằng tiếng việt
- Group Box 5: Results
  - Manifest path display
  - Output folder display
  - Summary stats

### 4.3 Tab 2: Extract Single File
# bỏ tab này
**Bố cục:**
- Group Box 1: File Selection
  - Input: File path (read-only + button Browse)
  - Button: Browse File (.doc/.docx)
  
- Group Box 2: Actions
  - Button: Extract Single File
  
- Group Box 3: Results
  - Output path display
  - Contract number (nếu có)

### 4.4 Tab 3: Upload Playwright
**Bố cục:**
- Group Box 1: Manifest Selection
  - Input: Manifest path + Button Browse
  
- Group Box 2: Web Contract Comparison
  - Input: Excel export file + Button Browse
  - Date range: From / To
  - Button: Download from Web
  
- Group Box 3: Actions
  - Button: Refresh Queue
  - Button: Start Dry-run
  - Button: Stop
  - Button: Finalize Selected
  
- Group Box 4: Queue Table
  - Columns: Record ID | Contract No | Status | Missing Fields | Source File
  - Selection mode: Multi-select
  - Double-click: Open source file
  
- Group Box 5: Duplicate Records
  - Same columns as above (read-only)
  - Show records that already exist on website

- Group Box 6: Status
  - Status text: Run ID, pending count, duplicates
  - Capability status: Playwright ready?
  - Comparison status: Web comparison loaded?

---

## 5. Log Viewer (dưới cùng - toàn tab)
- Text editor (read-only)
- Auto-scroll to bottom
- Syntax highlight cho [TAG] messages (colors)
- Buttons: Clear Log | Copy Log | Save Log to File

---

## 6. Design Details

### Color Scheme
- Background: #F5F5F5 (light gray)
- Primary: #0b5394 (blue) - for status/info
- Error: #a61c00 (red)
- Success: #38761d (green)
- Warning: #7f6000 (orange)
- Text: #333333 (dark gray)

### Typography
- Font: Segoe UI (Windows native)
- Title: 14pt bold
- Body: 10pt regular
- Monospace (log): 9pt Courier New

### Spacing & Layout
- Padding: 12px standard
- Button height: 32px
- Input height: 28px
- Group box margins: 8px
- Tab padding: 12px

### Icons (optional)
- Browse folder: 📁
- Browse file: 📄
- Play/Start: ▶️
- Stop: ⏹️
- Refresh: 🔄

---

## 7. Implementation Steps

### Phase 1: Foundation
1. ✓ Add PyQt6 to requirements.txt
2. Create `ui/` package structure
3. Create bootstrap script for PyQt6 setup
4. Create main_window.py with basic 3-tab layout

### Phase 2: Components
5. Create file browser widget (for folder/file selection)
6. Create progress panel widget (progress bar + stats)
7. Create log viewer widget (text area with styling)
8. Create table widget (for records)
9. Create stylesheets (QSS files)

### Phase 3: Tab Implementation
10. Implement Batch Scan tab (UI only)
11. Implement Extract tab (UI only)
12. Implement Upload tab (UI only)

### Phase 4: Worker Threads
13. Create batch_scan_worker.py (threading)
14. Create extract_worker.py (threading)
15. Create upload_worker.py (threading)

### Phase 5: Integration
16. Connect batch scan button → run_batch_scan()
17. Connect extract button → extract()
18. Connect upload button → NamDinhUploaderSession
19. Wire log callbacks from workers → log viewer

### Phase 6: Polish
20. Test all tabs + interactions
21. Test progress updates during operations
22. Test error handling
23. Test on Windows (various DPI scales)
24. Update bootstrap_ui.py for PyQt6
25. Update run_ui.bat

---

## 8. Key Implementation Details

### Worker Threads Pattern
- Each long-running task (batch scan, extract, upload) runs in separate thread
- Thread emits Qt signals with progress/log data
- Main thread updates UI based on signals
- No blocking calls in main thread

### Log Display
- Accumulate log messages in queue from worker threads
- Display in QTextEdit with color-coded tags
- [BATCH], [EXTRACT], [UPLOAD], [ERROR] = different colors
- Auto-scroll to bottom

### File Selection
- Custom widget: Show path + Browse button
- Use QFileDialog for file/folder selection
- Remember last used folder (QSettings)

### Progress Display
- Progress bar: 0-100%
- Status text: Multi-line label
- Detail text: Current file being processed
- Speed/ETA: Calculated and updated

### Table Display (Upload Tab)
- Sortable columns
- Multi-select rows
- Context menu: Open source file
- Double-click: Open file explorer

---

## 9. Compatibility & Migration

### Backward Compatibility
- All business logic stays in existing Python files:
  - batch_scan.py
  - extract_contract.py
  - playwright_uploader.py
- UI only changes → completely new files
- Old `ui_runner.py` → deprecated (keep as fallback?)

### Migration Path
1. Keep old `run_ui.bat` (Tkinter)
2. Add new `run_ui_pyqt6.bat` (PyQt6)
3. Once PyQt6 is stable, replace old one

---

## 10. Testing Plan

### Unit Tests
- Test each widget separately (if needed)
- Test worker threads with mock data

### Integration Tests
- Test all 3 tabs with actual functions
- Test worker thread communication
- Test log display

### Manual Testing
- Run on Windows 10/11
- Test file dialogs
- Test progress updates
- Test error messages
- Test table interactions (sort, select, double-click)

---

## 11. Quy ước Coding

- All UI files use type hints (Python 3.8+)
- All worker signals must be properly typed
- Log messages must have [TAG] prefix
- Use QSettings for saving user preferences
- Use QMessageBox for dialogs (info, warning, error)
- Use QFileDialog for file/folder selection

---

## 12. Known Limitations / Future Work

- No dark mode in MVP (can add with stylesheet switching)
- No drag-drop file selection (use browse buttons)
- Icons are emoji only (can use QIcon later if needed)
- No keyboard shortcuts in MVP

---

## Summary of Changes

| Item | Current | New |
|------|---------|-----|
| Framework | Tkinter | PyQt6 |
| Main entry | `ui_runner.py` | `ui_app_pyqt6.py` |
| Bootstrap | `bootstrap_ui.py` | `bootstrap_ui_pyqt6.py` |
| Launcher | `run_ui.bat` | `run_ui_pyqt6.bat` |
| Structure | Single file | Package-based |
| Thread model | Same (queue-based) | Same (Qt signals) |
| Dependencies | Add PyQt6 | PyQt6>=6.4.0 |

---

## Approval Checklist

- [ ] Bố cục & tính năng được phê duyệt
- [ ] Design colors & typography được phê duyệt
- [ ] Component breakdown được phê duyệt
- [ ] Implementation steps được phê duyệt
- [ ] Ready to start Phase 1?
