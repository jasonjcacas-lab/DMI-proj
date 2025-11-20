import os
import time

from Tabs.Splitter import (
    set_scan_mode,
    get_scan_mode,
    SCAN_MODE_QUICK,
    SCAN_MODE_ACCURACY,
    load_rules,
    RULES_PATH,
    begin_text_session,
    end_text_session,
    _suspect_pages,
    _page_cleaned,
    apply_rules_collect,
    assess_binder_scan_profile,
)


def run_once(pdf_path: str, mode: str, allow_ocr: bool):
    set_scan_mode(mode)
    mode_name = get_scan_mode()

    start = time.perf_counter()
    begin_text_session(pdf_path, allow_ocr=allow_ocr)
    try:
        if allow_ocr:
            for idx in _suspect_pages():
                _ = _page_cleaned(pdf_path, idx)
        apply_rules_collect(pdf_path, rules, session_paths=[])
    finally:
        end_text_session()
    elapsed = time.perf_counter() - start
    return mode_name, elapsed


if __name__ == "__main__":
    pdf_path = os.path.join("Bindocs", "Bindocs5.pdf")
    print(f"Profiling {pdf_path}")
    rules = load_rules(RULES_PATH)
    allow_ocr, skip_quick, stats = assess_binder_scan_profile(pdf_path, sample_limit=12)
    print(
        "[ScanProfile] allow_ocr={allow_ocr} skip_quick={skip_quick} reason={reason} "
        "sample={sample} low={low} med={med} high={high}".format(
            allow_ocr=allow_ocr,
            skip_quick=skip_quick,
            reason=stats.get("skip_reason"),
            sample=stats.get("sample_pages"),
            low=stats.get("low_pages"),
            med=stats.get("med_pages"),
            high=stats.get("high_pages"),
        )
    )
    modes = []
    if not skip_quick:
        modes.append((SCAN_MODE_QUICK, allow_ocr))
    else:
        print("Skipping quick run: binder flagged as scanned.")
    modes.append((SCAN_MODE_ACCURACY, True))
    for mode, allow in modes:
        name, elapsed = run_once(pdf_path, mode, allow)
        print(f"Mode={name}, allow_ocr={allow}, elapsed={elapsed:.2f}s")

