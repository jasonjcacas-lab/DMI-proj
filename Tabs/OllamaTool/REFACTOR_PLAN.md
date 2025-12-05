# OllamaTool Refactoring Plan

## Current State
- **File**: `Tabs/OllamaTool/main.py`
- **Size**: 3,947 lines
- **Problem**: Too large, hard to maintain, mixes concerns

## Proposed Modular Structure

### 1. `config.py` (~150 lines)
**Purpose**: Settings, paths, and configuration
- Import checks and availability flags
- Path constants
- Default settings
- `_load_settings()`, `_save_settings()`, `_ensure_dir()`

### 2. `ollama_api.py` (~200 lines)
**Purpose**: Ollama API communication
- `_check_ollama_connection()`
- `_get_available_models()`
- `_chat_with_ollama()`

### 3. `ocr_engines.py` (~600 lines)
**Purpose**: OCR functionality
- `_extract_text_with_tesseract()`
- `_extract_text_with_easyocr()`
- `_extract_text_with_ollama_vision()`
- `_ocr_specific_pages()`
- `_format_ocr_results_as_table()`
- `_clean_ocr_text()`

### 4. `pdf_processing.py` (~500 lines)
**Purpose**: PDF and document processing
- `_detect_pdf_type()`
- `_extract_page_as_image()`
- `extract_tables_from_pdf()`
- `format_table_as_text()`
- `extract_text_from_document()`

### 5. `table_detection.py` (~150 lines)
**Purpose**: Table structure detection
- `_detect_table_with_opencv()`

### 6. `ui.py` (~2500 lines)
**Purpose**: UI and main application logic
- `build_tab()` - Main GUI builder
- All UI event handlers
- Clipboard image processing
- MVR extraction with AI
- Document processing workflows

### 7. `main.py` (~50 lines)
**Purpose**: Entry point - imports and exports
- Imports from all modules
- Exports `build_tab()` for `__init__.py`

## Benefits
1. **Maintainability**: Each module has a single responsibility
2. **Testability**: Easier to test individual components
3. **Readability**: Smaller files are easier to understand
4. **Reusability**: Modules can be imported independently
5. **Collaboration**: Multiple developers can work on different modules

## Migration Strategy
1. Create new module files
2. Move functions to appropriate modules
3. Update imports in `main.py`
4. Test thoroughly
5. Update `__init__.py` if needed

## Estimated File Sizes After Split
- `config.py`: ~150 lines
- `ollama_api.py`: ~200 lines
- `ocr_engines.py`: ~600 lines
- `pdf_processing.py`: ~500 lines
- `table_detection.py`: ~150 lines
- `ui.py`: ~2500 lines
- `main.py`: ~50 lines
- **Total**: ~4,150 lines (slight increase due to imports, but much better organized)

