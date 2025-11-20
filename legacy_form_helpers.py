"""
Helper functions for interacting with legacy web forms using Playwright.
These functions use direct DOM manipulation for maximum compatibility with older JavaScript frameworks.
"""

from playwright.sync_api import Page
from typing import Optional


def set_select_dropdown_value(page: Page, element_id: str, value: str) -> bool:
    """
    Sets the value of a <select> dropdown by direct DOM manipulation.
    
    This function:
    1. Finds the select element by ID
    2. Searches for matching option by value or text
    3. Sets its .value property directly
    4. Fires the legacy onchange handler if it exists
    5. Otherwise dispatches a standard change event
    
    Args:
        page: Playwright Page object
        element_id: The ID of the <select> element (e.g., 'ddComboState')
        value: The value to set (e.g., 'TX' for Texas)
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Escape value for JavaScript
    value_escaped = value.replace("'", "\\'")
    
    js_code = f"""
    (function() {{
        const elementId = '{element_id}';
        const targetValue = '{value_escaped}'.toUpperCase().trim();
        
        const sel = document.getElementById(elementId);
        if (!sel) {{
            return {{success: false, error: 'Element not found: ' + elementId}};
        }}
        
        // First, try to find the option by value or text
        let foundOption = null;
        let foundValue = null;
        
        for (let i = 0; i < sel.options.length; i++) {{
            const opt = sel.options[i];
            const optValue = (opt.value || '').toUpperCase().trim();
            const optText = (opt.text || '').toUpperCase().trim();
            
            if (optValue === targetValue || optText === targetValue) {{
                foundOption = opt;
                foundValue = opt.value;
                break;
            }}
        }}
        
        if (!foundOption) {{
            // If no exact match, try setting the value directly anyway
            // Some dropdowns might accept the value even if it's not in options yet
            try {{
                sel.value = targetValue;
                if (sel.value === targetValue || sel.value.toUpperCase().trim() === targetValue) {{
                    foundValue = sel.value;
                }} else {{
                    return {{
                        success: false, 
                        error: 'Value not found in options',
                        availableOptions: Array.from(sel.options).slice(0, 5).map(o => o.value + ':' + o.text)
                    }};
                }}
            }} catch (e) {{
                return {{
                    success: false,
                    error: 'Could not set value: ' + e.message,
                    availableOptions: Array.from(sel.options).slice(0, 5).map(o => o.value + ':' + o.text)
                }};
            }}
        }} else {{
            // Set the value using the found option
            sel.value = foundValue;
        }}
        
        // Fire the legacy onchange handler - try multiple approaches
        // 1. If there's an inline onchange attribute, execute it directly
        const onchangeAttr = sel.getAttribute('onchange');
        if (onchangeAttr) {{
            try {{
                // Execute inline handler with 'this' bound to the select element
                // This handles cases like onchange="someFunction(this)"
                (function() {{
                    eval(onchangeAttr);
                }}).call(sel);
            }} catch (e) {{
                console.error('Error executing inline onchange:', e);
            }}
        }}
        
        // 2. Also try calling the onchange property if it's a function
        if (typeof sel.onchange === 'function') {{
            try {{
                sel.onchange.call(sel, {{ target: sel, currentTarget: sel, type: 'change' }});
            }} catch (e) {{
                console.error('Error calling onchange property:', e);
            }}
        }}
        
        // 3. Dispatch standard events (some frameworks listen to these)
        const changeEvent = new Event('change', {{ bubbles: true, cancelable: true }});
        sel.dispatchEvent(changeEvent);
        
        const inputEvent = new Event('input', {{ bubbles: true, cancelable: true }});
        sel.dispatchEvent(inputEvent);
        
        // 4. Also try firing as if user clicked (some legacy code expects this)
        const clickEvent = new MouseEvent('click', {{ bubbles: true, cancelable: true }});
        sel.dispatchEvent(clickEvent);
        
        // Verify the value was set
        const finalValue = sel.value;
        const success = finalValue && (
            finalValue.toUpperCase().trim() === targetValue || 
            finalValue === targetValue
        );
        
        return {{
            success: success,
            currentValue: finalValue,
            targetValue: targetValue,
            foundValue: foundValue
        }};
    }})();
    """
    
    try:
        result = page.evaluate(js_code)
        success = result.get('success', False)
        if not success:
            error_msg = result.get('error', 'Unknown error')
            print(f"Error setting dropdown value: {error_msg}")
            if 'availableOptions' in result:
                print(f"Available options (first 5): {result['availableOptions']}")
        return success
    except Exception as e:
        print(f"Exception setting dropdown value: {e}")
        return False


def fill_text_input(page: Page, selector: str, value: str, use_js: bool = False) -> bool:
    """
    Fills in a text <input> field on the page.
    
    By default, this uses Playwright's .fill() method which is reliable and fast.
    If use_js=True, it uses direct DOM manipulation via page.evaluate.
    
    Args:
        page: Playwright Page object
        selector: CSS selector for the input field (e.g., 'input[name="license"]')
        value: The value to fill in
        use_js: If True, use JavaScript DOM manipulation instead of .fill()
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if use_js:
            # Use JavaScript to set the value directly
            js_code = f"""
            (function() {{
                const el = document.querySelector('{selector}');
                if (!el) {{
                    return {{success: false, error: 'Element not found'}};
                }}
                
                // Set the value
                el.value = '{value}';
                
                // Trigger input and change events
                const inputEvent = new Event('input', {{ bubbles: true }});
                el.dispatchEvent(inputEvent);
                
                const changeEvent = new Event('change', {{ bubbles: true }});
                el.dispatchEvent(changeEvent);
                
                return {{success: true, value: el.value}};
            }})();
            """
            result = page.evaluate(js_code)
            return result.get('success', False)
        else:
            # Use Playwright's native fill method
            page.fill(selector, value, timeout=5000)
            return True
    except Exception as e:
        print(f"Error filling input field: {e}")
        return False


def click_submit_button(page: Page, selector: str, no_wait_after: bool = True) -> bool:
    """
    Clicks a submit button on the page.
    
    This function uses a simple CSS selector to find and click the button.
    By default, it uses no_wait_after=True to avoid waiting for slow legacy page events.
    
    Args:
        page: Playwright Page object
        selector: CSS selector for the submit button (e.g., 'input[type="submit"][value="Run MVR"]')
        no_wait_after: If True, don't wait for navigation after click (useful for slow legacy pages)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        page.click(selector, timeout=5000, no_wait_after=no_wait_after)
        return True
    except Exception as e:
        print(f"Error clicking submit button: {e}")
        return False


def wait_for_element_ready(page: Page, selector: str, timeout: int = 10000) -> bool:
    """
    Waits for an element to be ready in the DOM.
    
    This is a helper function to ensure elements exist before interacting with them.
    
    Args:
        page: Playwright Page object
        selector: CSS selector for the element
        timeout: Maximum time to wait in milliseconds
    
    Returns:
        bool: True if element is ready, False if timeout
    """
    try:
        page.wait_for_selector(selector, state="attached", timeout=timeout)
        return True
    except Exception:
        return False

