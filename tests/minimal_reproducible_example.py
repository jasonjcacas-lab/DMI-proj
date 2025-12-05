"""
Minimal Reproducible Example: Legacy Dropdown Selection Issue

This script demonstrates the problem with selecting values from a legacy dropdown
using Playwright. The dropdown has an inline onchange handler that doesn't seem
to be triggered properly.

To use this:
1. Install Playwright: pip install playwright
2. Install browsers: playwright install chromium
3. Update the URL and credentials below
4. Run: python minimal_reproducible_example.py
"""

from playwright.sync_api import sync_playwright
import time

def set_select_dropdown_value_js(page, element_id: str, value: str) -> bool:
    """
    Attempts to set dropdown value using JavaScript DOM manipulation.
    This is the approach that's not working reliably.
    """
    value_escaped = value.replace("'", "\\'")
    
    js_code = f"""
    (function() {{
        const elementId = '{element_id}';
        const targetValue = '{value_escaped}'.toUpperCase().trim();
        
        const sel = document.getElementById(elementId);
        if (!sel) {{
            return {{success: false, error: 'Element not found: ' + elementId}};
        }}
        
        // Find matching option
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
            return {{
                success: false, 
                error: 'Value not found in options',
                availableOptions: Array.from(sel.options).slice(0, 5).map(o => o.value + ':' + o.text)
            }};
        }}
        
        // Set the value
        sel.value = foundValue;
        
        // Fire legacy onchange handler
        if (typeof sel.onchange === 'function') {{
            try {{
                const eventObj = {{
                    target: sel,
                    currentTarget: sel,
                    type: 'change'
                }};
                sel.onchange(eventObj);
            }} catch (e) {{
                console.error('Error calling onchange:', e);
            }}
        }}
        
        // Dispatch standard events
        const changeEvent = new Event('change', {{ bubbles: true, cancelable: true }});
        sel.dispatchEvent(changeEvent);
        
        const inputEvent = new Event('input', {{ bubbles: true, cancelable: true }});
        sel.dispatchEvent(inputEvent);
        
        // Verify
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
            print(f"❌ Error: {error_msg}")
            if 'availableOptions' in result:
                print(f"   Available options (first 5): {result['availableOptions']}")
        return success
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False


def test_playwright_native(page, selector: str, value: str):
    """
    Test using Playwright's native select_option() method.
    This works but is slow.
    """
    print(f"\n📋 Testing Playwright native select_option()...")
    try:
        start_time = time.time()
        dropdown = page.locator(selector)
        dropdown.wait_for(state="visible", timeout=5000)
        dropdown.select_option(value=value, timeout=2000)
        elapsed = time.time() - start_time
        print(f"✅ Success! Took {elapsed:.2f} seconds")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_javascript_manipulation(page, element_id: str, value: str):
    """
    Test using JavaScript DOM manipulation.
    This is fast but doesn't seem to trigger page handlers.
    """
    print(f"\n📋 Testing JavaScript DOM manipulation...")
    try:
        start_time = time.time()
        # Wait for element
        page.wait_for_selector(f"#{element_id}", state="attached", timeout=5000)
        
        # Set value using JS
        success = set_select_dropdown_value_js(page, element_id, value)
        elapsed = time.time() - start_time
        
        if success:
            print(f"✅ Value set! Took {elapsed:.2f} seconds")
            
            # Verify the value is still set after a moment
            time.sleep(0.5)
            verify_js = f"""
            (function() {{
                const sel = document.getElementById('{element_id}');
                return sel ? sel.value : null;
            }})();
            """
            current_value = page.evaluate(verify_js)
            print(f"   Current value: {current_value}")
            
            # Check if page reacted (e.g., other fields appeared)
            # This is where we'd check if the page's JavaScript handlers ran
            print(f"   ⚠️  Note: Value is set, but page may not have reacted")
            
        return success
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def main():
    """
    Main test function.
    Update these values for your specific case:
    """
    # CONFIGURATION - Update these for your case
    LOGIN_URL = "https://www.webmvr.com/login.jsp"
    FORM_URL = "https://www.webmvr.com/neworder/NewOrderMasterPage.jsp?Id=new"
    USERNAME = "your_username"  # Update this
    PASSWORD = "your_password"  # Update this
    DROPDOWN_ID = "ddComboState"
    DROPDOWN_SELECTOR = "#ddComboState"
    STATE_VALUE = "TX"  # State to select
    
    print("=" * 60)
    print("Legacy Dropdown Selection Test")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        try:
            # Navigate to login page
            print(f"\n🌐 Navigating to login page...")
            page.goto(LOGIN_URL, wait_until="commit")
            
            # Manual login (you'll need to complete this)
            print(f"⏸️  Please log in manually...")
            print(f"   Waiting for navigation to form page...")
            page.wait_for_url(FORM_URL, timeout=60000)
            print(f"✅ Logged in!")
            
            # Wait for dropdown to be ready
            print(f"\n⏳ Waiting for dropdown to be ready...")
            page.wait_for_selector(DROPDOWN_SELECTOR, state="attached", timeout=10000)
            print(f"✅ Dropdown is ready")
            
            # Test both approaches
            print(f"\n{'=' * 60}")
            print(f"Testing with state value: {STATE_VALUE}")
            print(f"{'=' * 60}")
            
            # Test 1: Playwright native (slow but works)
            test_playwright_native(page, DROPDOWN_SELECTOR, STATE_VALUE)
            
            # Reset dropdown for next test
            time.sleep(1)
            page.evaluate(f"document.getElementById('{DROPDOWN_ID}').value = '';")
            time.sleep(0.5)
            
            # Test 2: JavaScript manipulation (fast but may not work)
            test_javascript_manipulation(page, DROPDOWN_ID, STATE_VALUE)
            
            # Keep browser open for inspection
            print(f"\n⏸️  Browser will remain open for 10 seconds for inspection...")
            time.sleep(10)
            
        except Exception as e:
            print(f"\n❌ Error during test: {e}")
            import traceback
            traceback.print_exc()
        finally:
            browser.close()
    
    print(f"\n{'=' * 60}")
    print("Test complete!")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()

