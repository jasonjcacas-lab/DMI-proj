# Help Request: Making Playwright `select_option()` Faster on Legacy Dropdown

## Goal

I need to programmatically select a value from a legacy `<select>` dropdown using Playwright (Python, sync API). Playwright's native `select_option()` works correctly but is extremely slow (15+ seconds), which is too slow for automation.

**Element**: `<select id="ddComboState" onchange="someLegacyFunction(this)">`

## Current Working (But Slow) Approach

```python
state_dropdown = page.locator("#ddComboState")
state_dropdown.wait_for(state="visible", timeout=5000)
state_dropdown.select_option(value="TX", timeout=2000)  # Works but takes 15+ seconds
```

This correctly triggers the page's JavaScript handlers, but the delay is unacceptable.

## Attempted Workaround (Doesn't Work)

I tried JavaScript DOM manipulation to speed it up, but while it sets the value instantly, it doesn't trigger the page's `onchange` handlers:

```python
js_code = f"""
const sel = document.getElementById('ddComboState');
sel.value = 'TX';
sel.onchange({{ target: sel }});  // Doesn't trigger page handlers
sel.dispatchEvent(new Event('change', {{ bubbles: true }}));
"""
page.evaluate(js_code)
```

## Why It's Slow

I suspect `select_option()` is waiting for:
- Network requests to complete (the dropdown triggers AJAX/refresh)
- Navigation events (page may partially reload)
- Default timeouts (30+ seconds for navigation)

## Questions

1. **How can I make `select_option()` faster?** Can I use `no_wait_after` or disable network wait?
2. **Is there a way to tell Playwright to not wait for network/navigation** after dropdown selection?
3. **Should I reduce `set_default_navigation_timeout()`** or use `force=True`?

## Environment

- Python 3.x, Playwright (sync API), Chromium
- Legacy JSP page (`https://www.webmvr.com`) that may refresh after dropdown selection
- The dropdown selection triggers a page refresh/partial reload

**Note**: The page's `onchange` handler must execute for the form to work correctly.

