"""
MVR Runner Automation Core Module
Contains all Playwright automation functions for MVR Runner.
"""

import os
import sys
import random
from typing import Dict, Optional, Tuple

# Import optional dependencies
try:
    from playwright.sync_api import sync_playwright
except Exception:
    sync_playwright = None

try:
    from legacy_form_helpers import set_select_dropdown_value, fill_text_input
except Exception:
    set_select_dropdown_value = None
    fill_text_input = None

# Import shared utilities
import os
import sys
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

try:
    # Try relative imports first (when loaded as Tabs.MvrRunner_AutomationCore)
    from .MvrRunner_Shared import (
        _is_port_open,
        _is_chrome_running,
        _get_chrome_user_data_dir
    )
except (ImportError, ValueError):
    # Fallback for direct file execution
    from MvrRunner_Shared import (
        _is_port_open,
        _is_chrome_running,
        _get_chrome_user_data_dir
    )


def _ensure_playwright_browsers_installed(status_cb=None) -> None:
    """
    Make sure Playwright has installed browsers. If not, attempt a one-time install.
    """
    if sync_playwright is None:
        raise RuntimeError("playwright is not installed. Run: pip install playwright && playwright install")
    try:
        with sync_playwright() as p:
            # Try launching quickly; if missing browsers, it will throw
            browser = p.chromium.launch(headless=True)
            browser.close()
    except Exception:
        # Try to install browsers
        if status_cb:
            status_cb("Installing Playwright browsers (one-time)...")
        # Fallback: use Python API to install via CLI module
        import subprocess
        try:
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            raise RuntimeError(f"Failed to install Playwright browsers: {e}")


def _add_stealth_script(context):
    """Add stealth script to hide automation"""
    context.add_init_script("""
        // Remove webdriver property completely
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        
        // Override plugins to look more realistic
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
        
        // Override languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
        
        // Mock chrome object
        window.chrome = {
            runtime: {}
        };
        
        // Remove automation indicators
        delete navigator.__proto__.webdriver;
        
        // Override permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // Override getParameter to hide automation
        const originalGetParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) {
                return 'Intel Inc.';
            }
            if (parameter === 37446) {
                return 'Intel Iris OpenGL Engine';
            }
            return originalGetParameter.call(this, parameter);
        };
        
        // Override toString to hide automation
        const originalToString = Function.prototype.toString;
        Function.prototype.toString = function() {
            if (this === navigator.webdriver) {
                return 'function webdriver() { [native code] }';
            }
            return originalToString.call(this);
        };
    """)


def _launch_chrome_with_profile_for_mvr(p, status_cb):
    """Launch Chrome using the user's profile directory to access saved passwords and login sessions"""
    user_data_dir = _get_chrome_user_data_dir()
    
    if not user_data_dir:
        if status_cb:
            status_cb("Chrome profile not found. Will launch Chrome without saved passwords...")
        return None
    
    # Check if Chrome is already running - if so, we can't use the profile
    if _is_chrome_running():
        if status_cb:
            status_cb("Chrome is already running. Cannot use profile (would conflict).")
            status_cb("Close Chrome and try again, or use CDP connection with remote debugging.")
        return None
    
    if status_cb:
        status_cb(f"Using your Chrome profile: {user_data_dir}")
        status_cb("This will use your saved passwords and login sessions!")
    
    try:
        # Try method 1: launch_persistent_context (preferred for profile access)
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                channel="chrome",
                headless=False,
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="America/Los_Angeles",
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-site-isolation-trials",
                ],
                ignore_default_args=["--enable-automation"],  # Remove automation flag
            )
            _add_stealth_script(context)
            if status_cb:
                status_cb("✓ Chrome launched with your profile (persistent context) - saved passwords available!")
            return context
        except Exception as e1:
            if status_cb:
                status_cb(f"Persistent context failed: {str(e1)[:100]}")
                status_cb("Trying alternative method with user-data-dir argument...")
            
            # Method 2: Regular launch with user-data-dir argument (alternative approach)
            browser = p.chromium.launch(
                channel="chrome",
                headless=False,
                args=[
                    f"--user-data-dir={user_data_dir}",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-site-isolation-trials",
                ],
                ignore_default_args=["--enable-automation"],
            )
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="America/Los_Angeles",
            )
            _add_stealth_script(context)
            if status_cb:
                status_cb("✓ Chrome launched with your profile (user-data-dir) - saved passwords available!")
            return context
    except Exception as e:
        if status_cb:
            status_cb(f"Could not use Chrome profile: {str(e)[:100]}")
            status_cb("Will launch Chrome without profile...")
        return None


def _launch_chrome_with_profile(p, status_cb, url=None, field_to_selector=None, data=None):
    """Launch Chrome using the user's profile directory to access saved passwords"""
    user_data_dir = _get_chrome_user_data_dir()
    
    if user_data_dir:
        if status_cb:
            status_cb(f"Using your Chrome profile: {user_data_dir}")
        try:
            # Use launch_persistent_context to use the actual Chrome profile
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                channel="chrome",
                headless=False,
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="America/Los_Angeles",
            )
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                window.chrome = { runtime: {} };
            """)
            if url and field_to_selector and data:
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(url, wait_until="load")
                if status_cb:
                    status_cb("Filling form fields...")
                for field_name, selector in field_to_selector.items():
                    if selector and data.get(field_name):
                        try:
                            page.fill(selector, data[field_name])
                        except Exception:
                            pass
                if status_cb:
                    status_cb("Form filled. Please review and submit manually.")
            else:
                if status_cb:
                    status_cb("Chrome launched with your profile. You can now use saved passwords.")
            return context
        except Exception as e:
            if status_cb:
                status_cb(f"Could not use Chrome profile (Chrome may be running): {str(e)[:100]}")
                status_cb("Launching Chrome without profile...")
            # Fall through to regular launch
    else:
        if status_cb:
            status_cb("Chrome profile not found. Launching Chrome without saved passwords...")
    
    # Fallback: launch Chrome without profile
    browser = p.chromium.launch(headless=False, channel="chrome")
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        locale="en-US",
        timezone_id="America/Los_Angeles",
    )
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        window.chrome = { runtime: {} };
    """)
    if url and field_to_selector and data:
        page = context.new_page()
        page.goto(url, wait_until="load")
        if status_cb:
            status_cb("Filling form fields...")
        for field_name, selector in field_to_selector.items():
            if selector and data.get(field_name):
                try:
                    page.fill(selector, data[field_name])
                except Exception:
                    pass
        if status_cb:
            status_cb("Form filled. Please review and submit manually.")
    return context


def _fill_site_with_playwright(url: str, field_to_selector: Dict[str, str], data: Dict[str, str], status_cb=None, cdp_endpoint: Optional[str] = None) -> None:
    """
    Open Chromium and fill fields per provided CSS selectors.
    If cdp_endpoint is provided and reachable, attach to an existing Chrome via CDP.
    """
    if status_cb:
        status_cb("Starting browser...")
    with sync_playwright() as p:
        browser = None
        context = None
        if cdp_endpoint and _is_port_open("127.0.0.1", int(cdp_endpoint.rsplit(":", 1)[-1])):
            try:
                browser = p.chromium.connect_over_cdp(cdp_endpoint)
                # reuse an existing context if available; otherwise create one
                if browser.contexts:
                    context = browser.contexts[0]
                    # Add stealth script to existing context
                    try:
                        context.add_init_script("""
                            Object.defineProperty(navigator, 'webdriver', {
                                get: () => undefined
                            });
                            Object.defineProperty(navigator, 'plugins', {
                                get: () => [1, 2, 3, 4, 5]
                            });
                            Object.defineProperty(navigator, 'languages', {
                                get: () => ['en-US', 'en']
                            });
                            window.chrome = { runtime: {} };
                        """)
                    except:
                        pass  # If context already has pages, init script might fail
                else:
                    context = browser.new_context(
                        viewport={"width": 1280, "height": 720},
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        locale="en-US",
                        timezone_id="America/Los_Angeles",
                    )
                    context.add_init_script("""
                        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                        window.chrome = { runtime: {} };
                    """)
                if status_cb:
                    status_cb("Attached to existing Chrome via CDP.")
            except Exception:
                # fallback to launching - use system Chrome with your profile
                _launch_chrome_with_profile(p, status_cb)
                return  # _launch_chrome_with_profile handles everything
        else:
            # Use system Chrome with your profile (saved passwords and login sessions)
            _launch_chrome_with_profile(p, status_cb, url, field_to_selector, data)
            return  # _launch_chrome_with_profile handles everything
        page = context.new_page()
        page.goto(url, wait_until="load")
        if status_cb:
            status_cb("Page loaded. Filling fields...")
        for field, selector in field_to_selector.items():
            value = data.get(field, "")
            if not selector or not value:
                continue
            try:
                page.fill(selector, value, timeout=10000)
            except Exception as e:
                # Try click then type as fallback
                try:
                    page.click(selector, timeout=5000)
                    page.keyboard.type(value)
                except Exception as e2:
                    if status_cb:
                        status_cb(f"⚠ Warning: Could not fill {field} field: {str(e2)}")
                    pass
        if status_cb:
            status_cb("Done. Leaving browser open for review.")
        # keep browser open for user; do not close immediately


def _run_mvr_automation(url: str, field_to_selector: Dict[str, str], data: Dict[str, str], 
                        account_id: str, user_id: str, password: str, 
                        status_cb=None, cdp_endpoint: Optional[str] = None, skip_login: bool = False,
                        login_selectors: Optional[Dict[str, str]] = None, auto_click_recaptcha: bool = True) -> None:
    """
    Run MVR automation: login to site, then fill MVR fields.
    """
    if status_cb:
        status_cb("Starting browser...")
    with sync_playwright() as p:
        # Launch a fresh Playwright Chromium browser (blue icon)
        if status_cb:
            status_cb("Launching Chromium browser...")
        browser = p.chromium.launch(
            headless=False,
            channel="chrome",
            args=[
                "--disable-blink-features=AutomationControlled",
            ],
            ignore_default_args=["--enable-automation"],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="America/Los_Angeles",
        )
        _add_stealth_script(context)
        
        # Close the auto-created about:blank page if it exists
        if context.pages:
            try:
                blank_page = context.pages[0]
                if blank_page.url == "about:blank" or "about:blank" in blank_page.url:
                    blank_page.close()
            except:
                pass
        
        # Create a new page and navigate
        page = context.new_page()
        if status_cb:
            status_cb(f"Navigating to: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        if status_cb:
            status_cb(f"✓ Navigated to: {page.url}")
        
        # No wait - start immediately
        
        # Bring browser to front (Windows) - after navigation so page is loaded
        try:
            import ctypes
            from ctypes import wintypes
            
            # Bring browser to front using Playwright's method
            page.bring_to_front()
        except Exception as e:
            # Fallback: use Playwright's bring_to_front
            try:
                page.bring_to_front()
            except Exception:
                pass
        
        # Initialize skip_login and login_successful variables
        skip_login = False
        login_successful = False
        
        # Fast check if already logged in BEFORE attempting login
        try:
            current_url = page.url
            if "NewOrderMasterPage.jsp" in current_url:
                if status_cb:
                    status_cb("✓ Already logged in and on MVR page - skipping login")
                skip_login = True
                login_successful = True
                # Skip directly to field filling - no need to navigate or wait
                # This will be handled in the login_successful block below
        except Exception:
                pass
        
        # Login - only if not skipping
        if not skip_login:
            if status_cb:
                status_cb("Filling login credentials...")
            
            import random
            
            # Build selector lists - use custom selectors first if provided, then fall back to defaults
            default_selectors = {
                "account_id": [
                    "input[name='accountId']", "input[name='account_id']", "input[name='accountId']",
                    "input[id*='account' i]", "input[id*='Account']",
                    "#accountId", "#account-id", "#account_id",
                    "input[placeholder*='account' i]", "input[placeholder*='Account' i]",
                    "input[type='text'][name*='account' i]", "input[type='text'][id*='account' i]",
                ],
                "user_id": [
                    "input[name='username']", "input[name='userId']", "input[name='user_id']",
                    "input[name='userName']", "input[name='user_name']", "input[name='user']",
                    "input[id*='user' i]", "input[id*='User']",
                    "#username", "#userId", "#user_id", "#userName", "#user",
                    "input[placeholder*='user' i]", "input[placeholder*='User' i]",
                    "input[type='text'][name*='user' i]", "input[type='text'][id*='user' i]",
                ],
                "password": [
                    "input[name='password']", "input[type='password']",
                    "input[id*='password' i]", "input[id*='Password']",
                    "#password", "#pass",
                    "input[placeholder*='password' i]", "input[placeholder*='Password' i]",
                ],
            }
            
            # Build final selector lists - custom first, then defaults
            login_selector_lists = {}
            for field_name in ["account_id", "user_id", "password"]:
                selector_list = []
                # Add custom selector first if provided
                if login_selectors and login_selectors.get(field_name):
                    custom_sel = login_selectors[field_name].strip()
                    if custom_sel:
                        selector_list.append(custom_sel)
                # Add default selectors
                selector_list.extend(default_selectors[field_name])
                login_selector_lists[field_name] = selector_list
            
            # Quick scan for fields (only if no custom selectors provided)
            if not (login_selectors and any(login_selectors.values())):
                if status_cb:
                    status_cb("Quick scan for login fields...")
                try:
                    # Quick check for password field
                    if page.locator("input[type='password']").count() > 0:
                        login_selector_lists["password"].insert(0, "input[type='password']")
                except:
                    pass
            
            login_data = {
                "account_id": account_id,
                "user_id": user_id,
                "password": password,
            }
            
            # Humanized field filling - sequential typing with delays and mouse movements
            import random
            filled_fields = {}
            
            def find_field(selector_list):
                """Find the first visible field from a list of selectors"""
                for selector in selector_list:
                    try:
                        locator = page.locator(selector).first
                        if locator.is_visible(timeout=500):
                            return locator
                    except:
                        continue
                return None
            
            def human_type(locator, text, field_name):
                """Type text with minimal delays for speed"""
                try:
                    # Click the field first
                    locator.click(timeout=2000)
                    
                    # Clear existing value
                    locator.press("Control+a", timeout=500)
                    
                    # Type with minimal delay for speed
                    locator.type(text, delay=10)  # Minimal delay for speed
                    return True
                except Exception:
                    return False
            
            # Fill Account ID
            if account_id:
                account_locator = find_field(login_selector_lists["account_id"])
                if not account_locator:
                    # Fallback: try first text input
                    try:
                        account_locator = page.locator("input[type='text'], input:not([type])").first
                        if account_locator.is_visible(timeout=500):
                            pass
                        else:
                            account_locator = None
                    except:
                        account_locator = None
                
                if account_locator:
                    if human_type(account_locator, account_id, "account_id"):
                        filled_fields["account_id"] = True
            
            # Fill User ID
            if user_id:
                user_locator = find_field(login_selector_lists["user_id"])
                if not user_locator:
                    # Fallback: try second text input
                    try:
                        user_locator = page.locator("input[type='text'], input:not([type])").nth(1)
                        if user_locator.is_visible(timeout=500):
                            pass
                        else:
                            user_locator = None
                    except:
                        user_locator = None
                
                if user_locator:
                    if human_type(user_locator, user_id, "user_id"):
                        filled_fields["user_id"] = True
            
            # Fill Password
            if password:
                password_locator = find_field(login_selector_lists["password"])
                if not password_locator:
                    # Fallback: try password input
                    try:
                        password_locator = page.locator("input[type='password']").first
                        if password_locator.is_visible(timeout=500):
                            pass
                        else:
                            password_locator = None
                    except:
                        password_locator = None
                
                if password_locator:
                    if human_type(password_locator, password, "password"):
                        filled_fields["password"] = True
            
            # Report which fields were filled
            if status_cb:
                filled_count = len(filled_fields)
                if filled_count == 3:
                    status_cb("âœ“ All login fields filled")
                elif filled_count > 0:
                    status_cb(f"âš  Filled {filled_count} of 3 fields")
                else:
                    status_cb("âœ— Could not fill login fields - check selectors")
            
            # Automatically click "I'm not a robot" checkbox (if enabled)
            checkbox_verified = False
            checkbox_clicked = False
            
            if auto_click_recaptcha:
                if status_cb:
                    status_cb("Clicking 'I'm not a robot' checkbox...")
                
                # Wait a moment for reCAPTCHA to load
                page.wait_for_timeout(500)
                
                # Try to find and click the reCAPTCHA checkbox
                try:
                    # Method 1: Find checkbox in reCAPTCHA iframe
                    recaptcha_frames = page.frames
                    for frame in recaptcha_frames:
                        try:
                            frame_url = frame.url
                            if 'recaptcha' in frame_url.lower() or 'google.com/recaptcha' in frame_url.lower():
                                # Try to click the checkbox
                                checkbox = frame.locator("#recaptcha-anchor, .recaptcha-checkbox")
                                if checkbox.count() > 0:
                                    checkbox.first.click(timeout=2000)
                                    checkbox_clicked = True
                                    if status_cb:
                                        status_cb("✓ Clicked reCAPTCHA checkbox")
                                    page.wait_for_timeout(random.randint(300, 600))  # Wait for verification
                                    break
                        except:
                            continue
                    
                    # Method 2: Try clicking via iframe selector
                    if not checkbox_clicked:
                        try:
                            recaptcha_iframe = page.locator("iframe[src*='recaptcha'], iframe[title*='recaptcha']").first
                            if recaptcha_iframe.is_visible(timeout=2000):
                                # Click the iframe area (which should trigger the checkbox)
                                box = recaptcha_iframe.bounding_box()
                                if box:
                                    # Click near the center of the iframe (where checkbox usually is)
                                    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                                    checkbox_clicked = True
                                    if status_cb:
                                        status_cb("✓ Clicked reCAPTCHA checkbox (via iframe)")
                                    page.wait_for_timeout(random.randint(300, 600))
                        except:
                            pass
                    
                    # Method 3: Try JavaScript click
                    if not checkbox_clicked:
                        try:
                            page.evaluate("""
                                (function() {
                                    var frames = document.querySelectorAll('iframe[src*="recaptcha"]');
                                    for (var i = 0; i < frames.length; i++) {
                                        try {
                                            var frameDoc = frames[i].contentDocument || frames[i].contentWindow.document;
                                            var checkbox = frameDoc.querySelector('#recaptcha-anchor, .recaptcha-checkbox');
                                            if (checkbox) {
                                                checkbox.click();
                                                return true;
                                            }
                                        } catch(e) {}
                                    }
                                    return false;
                                })();
                            """)
                            checkbox_clicked = True
                            if status_cb:
                                status_cb("✓ Clicked reCAPTCHA checkbox (via JS)")
                            page.wait_for_timeout(random.randint(300, 600))
                        except:
                            pass
                    
                    if not checkbox_clicked:
                        if status_cb:
                            status_cb("âš  Could not auto-click checkbox - please click manually")
                except:
                    pass
            else:
                if status_cb:
                    status_cb("Auto-click reCAPTCHA disabled - please click 'I'm not a robot' manually")
                # Still wait a moment for user to manually click
                page.wait_for_timeout(500)
            
            # Check if challenge popup appears (image selection prompt)
            has_challenge = False
            try:
                challenge_iframes = page.locator("iframe[src*='bframe'], iframe[title*='recaptcha challenge' i]")
                if challenge_iframes.count() > 0:
                    try:
                        if challenge_iframes.first.is_visible(timeout=1000):
                            has_challenge = True
                    except:
                        pass
            except:
                pass
            
            # If challenge popup appears, wait for user to complete it
            if has_challenge:
                if status_cb:
                    status_cb("reCAPTCHA challenge detected - please complete image selection...")
            
            # Wait for checkbox to be verified (checkmark appears)
            if not has_challenge:
                page.wait_for_timeout(1000)  # Brief wait for auto-verification
            
            # Check more frequently if challenge is present (user is actively working on it)
            if has_challenge:
                check_interval = 0.5  # Check every 0.5 seconds when challenge is active
                max_wait_time = 300  # 5 minutes
            else:
                check_interval = 1.0  # Check every 1 second if no challenge
                max_wait_time = 10  # Only wait 10 seconds if no challenge (should auto-verify quickly)
            
            elapsed = 0
            
            if status_cb:
                if has_challenge:
                    status_cb("Waiting for reCAPTCHA verification (checkmark)...")
                else:
                    status_cb("Checking for reCAPTCHA checkmark...")
            
            while elapsed < max_wait_time and not checkbox_verified:
                page.wait_for_timeout(int(check_interval * 1000))
                elapsed += check_interval
                
                # Check if checkbox has checkmark (is verified)
                try:
                    # Method 1: Check reCAPTCHA checkbox in iframes for checkmark
                    recaptcha_frames = page.frames
                    for frame in recaptcha_frames:
                        try:
                            frame_url = frame.url
                            if 'recaptcha' in frame_url.lower() or 'google.com/recaptcha' in frame_url.lower():
                                # Check if checkbox has checkmark (verified state)
                                checked = frame.evaluate("""
                                    (function() {
                                        var cb = document.querySelector('#recaptcha-anchor');
                                        if (cb) {
                                            var ariaChecked = cb.getAttribute('aria-checked');
                                            var hasCheckedClass = cb.classList.contains('recaptcha-checkbox-checked');
                                            // Also check for checkmark icon
                                            var hasCheckmark = cb.querySelector('.recaptcha-checkbox-checkmark') !== null;
                                            return ariaChecked === 'true' || hasCheckedClass || hasCheckmark;
                                        }
                                        return false;
                                    })();
                                """)
                                if checked:
                                    checkbox_verified = True
                                    if status_cb:
                                        status_cb("âœ“ Checkmark detected! Clicking login button...")
                                    break
                        except:
                            continue
                    
                    # Method 2: Check for reCAPTCHA response token (most reliable)
                    if not checkbox_verified:
                        try:
                            token_result = page.evaluate("""
                                (function() {
                                    // Check for reCAPTCHA response token in textarea
                                    var textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                                    var hasTextareaToken = textarea && textarea.value && textarea.value.length > 0;
                                    
                                    // Check grecaptcha API
                                    var hasApiToken = false;
                                    if (typeof grecaptcha !== 'undefined') {
                                        try {
                                            var response = grecaptcha.getResponse();
                                            hasApiToken = response && response.length > 0;
                                        } catch(e) {}
                                    }
                                    
                                    return {
                                        verified: hasTextareaToken || hasApiToken,
                                        textareaToken: hasTextareaToken,
                                        apiToken: hasApiToken,
                                        tokenLength: textarea ? (textarea.value ? textarea.value.length : 0) : 0
                                    };
                                })();
                            """)
                            if token_result and token_result.get('verified'):
                                checkbox_verified = True
                                if status_cb:
                                    status_cb(f"âœ“ reCAPTCHA verified! Token length: {token_result.get('tokenLength', 0)}")
                        except:
                            pass
                    
                    if checkbox_verified:
                        break
                except:
                    pass
                
                # Also check if we've navigated away (login succeeded)
                try:
                    current_url = page.url
                    if url not in current_url:
                        checkbox_verified = True
                        if status_cb:
                            status_cb("Login detected, continuing...")
                        break
                except Exception:
                    pass
            
            # Always wait for checkmark before clicking login (both scenarios)
            # Scenario 1: No challenge - wait for auto-verification checkmark, then auto-click login
            # Scenario 2: Challenge appears - wait for user to complete and checkmark appears
            if not checkbox_verified:
                if status_cb:
                    status_cb("âš  Timeout waiting for checkmark - you may need to verify manually")
            
            # Initialize login_clicked variable (used later in the code)
            login_clicked = False
            
            # If no challenge appeared and checkbox is verified, automatically click login
            if checkbox_verified and not has_challenge:
                if status_cb:
                    status_cb("âœ“ No challenge detected - automatically clicking login button...")
                # Small delay before clicking (human behavior)
                page.wait_for_timeout(random.randint(200, 400))
                # Click login button automatically
                submit_selectors = [
                    "form[name='LoginMain'] button:has-text('LOGIN')",
                    "form[name='LoginMain'] button:has-text('Login')",
                    "form[name='LoginMain'] button[type='submit']",
                    "button:has-text('LOGIN')",
                    "button:has-text('LOG IN')",
                    "button[id*='login' i]",
                    "input[type='submit'][value*='LOGIN' i]",
                    "input[type='submit'][value*='Login' i]",
                ]
                
                for selector in submit_selectors:
                    try:
                        login_btn = page.locator(selector).first
                        if login_btn.is_visible(timeout=1000):
                            login_btn.click(timeout=2000)
                            login_clicked = True
                            if status_cb:
                                status_cb("✓ Login button clicked automatically")
                            break
                    except:
                        continue
                
                if not login_clicked:
                    if status_cb:
                        status_cb("⚠ Could not find login button - please click manually")
            
            # Only click login button if checkbox is verified (has checkmark) AND challenge appeared
            if checkbox_verified and has_challenge:
                if status_cb:
                    status_cb("âœ“ Checkmark detected! Waiting for reCAPTCHA to fully process...")
                
                # Wait for reCAPTCHA to fully process and any overlays/popups to clear
                # This is critical - reCAPTCHA can block clicks if not fully cleared
                max_wait_attempts = 10
                for attempt in range(max_wait_attempts):
                    page.wait_for_timeout(500)  # Check every 500ms
                    
                    # Check if reCAPTCHA challenge popup is still visible
                    challenge_still_visible = False
                    try:
                        # Check for challenge iframes
                        challenge_iframes = page.locator("iframe[title*='recaptcha challenge'], iframe[src*='bframe'], iframe[title*='recaptcha expires']")
                        if challenge_iframes.count() > 0:
                            for i in range(challenge_iframes.count()):
                                iframe = challenge_iframes.nth(i)
                                try:
                                    if iframe.is_visible(timeout=300):
                                        # Check if iframe is actually visible on screen (not hidden)
                                        box = iframe.bounding_box()
                                        if box and box['width'] > 0 and box['height'] > 0:
                                            # Check if it's positioned off-screen (hidden)
                                            if box['x'] > -10000 or box['y'] > -10000:
                                                continue  # It's hidden, skip
                                            challenge_still_visible = True
                                            break
                                except:
                                    pass
                        
                        # Also check for reCAPTCHA overlay divs
                        if not challenge_still_visible:
                            overlay_divs = page.locator("div[style*='z-index'][style*='2000000000'], div.g-recaptcha-bubble-arrow")
                            if overlay_divs.count() > 0:
                                for i in range(overlay_divs.count()):
                                    div = overlay_divs.nth(i)
                                    try:
                                        if div.is_visible(timeout=300):
                                            box = div.bounding_box()
                                            if box and box['width'] > 0 and box['height'] > 0:
                                                # Check opacity and visibility
                                                style = div.evaluate("el => window.getComputedStyle(el).opacity + '|' + window.getComputedStyle(el).visibility")
                                                if style and '0' not in style.split('|')[0] and 'hidden' not in style:
                                                    challenge_still_visible = True
                                                    break
                                    except:
                                        pass
                    except:
                        pass
                    
                    if not challenge_still_visible:
                        if status_cb and attempt > 0:
                            status_cb("reCAPTCHA cleared, proceeding to click login...")
                        break
                    elif attempt < max_wait_attempts - 1:
                        if status_cb:
                            status_cb(f"Waiting for reCAPTCHA to clear... ({attempt + 1}/{max_wait_attempts})")
                
                # Final wait to ensure everything is settled
                page.wait_for_timeout(1000)
                
                # CRITICAL: Verify reCAPTCHA token is actually present before clicking login
                if status_cb:
                    status_cb("Verifying reCAPTCHA token before login...")
                
                token_verified = False
                for verify_attempt in range(5):
                    try:
                        token_check = page.evaluate("""
                            (function() {
                                // Check textarea token
                                var textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                                var hasTextareaToken = textarea && textarea.value && textarea.value.length > 20; // Token should be at least 20 chars
                                
                                // Check grecaptcha API
                                var hasApiToken = false;
                                if (typeof grecaptcha !== 'undefined') {
                                    try {
                                        var response = grecaptcha.getResponse();
                                        hasApiToken = response && response.length > 20;
                                    } catch(e) {}
                                }
                                
                                return {
                                    verified: hasTextareaToken || hasApiToken,
                                    textareaToken: hasTextareaToken,
                                    apiToken: hasApiToken,
                                    tokenValue: textarea ? (textarea.value || '') : ''
                                };
                            })();
                        """)
                        
                        if token_check and token_check.get('verified'):
                            token_verified = True
                            if status_cb:
                                token_info = []
                                if token_check.get('textareaToken'):
                                    token_info.append("textarea token present")
                                if token_check.get('apiToken'):
                                    token_info.append("API token present")
                                status_cb(f"âœ“ reCAPTCHA token verified: {', '.join(token_info)}")
                            break
                        else:
                            if status_cb and verify_attempt < 4:
                                status_cb(f"Waiting for reCAPTCHA token... ({verify_attempt + 1}/5)")
                            page.wait_for_timeout(1000)
                    except:
                        page.wait_for_timeout(1000)
                
                if not token_verified:
                    if status_cb:
                        status_cb("âš  WARNING: reCAPTCHA token not verified!")
                        status_cb("Waiting additional 3 seconds for token...")
                    page.wait_for_timeout(3000)
                    # Check one more time
                    try:
                        final_check = page.evaluate("""
                            (function() {
                                var textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                                return textarea && textarea.value && textarea.value.length > 20;
                            })();
                        """)
                        if final_check:
                            token_verified = True
                            if status_cb:
                                status_cb("âœ“ reCAPTCHA token found on final check")
                    except:
                        pass
                
                # If token still not verified, ask user to click login manually
                if not token_verified:
                    if status_cb:
                        status_cb("âš  reCAPTCHA token not found - please click LOGIN button manually")
                        status_cb("Waiting for you to click LOGIN button in the browser...")
                        status_cb("The tool will continue automatically once you've logged in.")
                    
                    # Wait for user to click login manually - monitor for URL change
                    if status_cb:
                        status_cb("Monitoring for login completion...")
                    
                    login_url_base = url.split('?')[0].split('#')[0]
                    max_manual_wait = 120  # Wait up to 2 minutes for manual login
                    check_count = 0
                    manual_login_detected = False
                    
                    while check_count < max_manual_wait and not manual_login_detected:
                        page.wait_for_timeout(2000)  # Check every 2 seconds
                        check_count += 2
                        
                        try:
                            current_url = page.url
                            # If we've navigated away from login URL, login succeeded
                            if login_url_base not in current_url and url not in current_url:
                                manual_login_detected = True
                                if status_cb:
                                    status_cb("âœ“ Manual login detected! Continuing...")
                                break
                        except Exception:
                            pass
                    
                    if manual_login_detected:
                        # User manually logged in - set flags to proceed
                        login_clicked = True
                        checkbox_verified = True  # Assume verified since user completed it
                        if status_cb:
                            status_cb("âœ“ Manual login completed - proceeding to fill MVR fields...")
                    else:
                        if status_cb:
                            status_cb("âš  Timeout waiting for manual login - proceeding anyway...")
                        # Still set flags to proceed (user might have logged in)
                        login_clicked = True
                        checkbox_verified = True
                else:
                    if status_cb:
                        status_cb("Clicking login button automatically...")
                
                # Define submit_selectors outside the if block so it's always available
                submit_selectors = [
                    # Try form-specific selectors first (LoginMain form)
                    "form[name='LoginMain'] button:has-text('LOGIN')",
                    "form[name='LoginMain'] button:has-text('Login')",
                    "form[name='LoginMain'] input[value='LOGIN']",
                    "form[name='LoginMain'] input[value='Login']",
                    "form[name='LoginMain'] button[type='submit']",
                    "form[name='LoginMain'] input[type='submit']",
                    "form[name='LoginMain'] button",
                    "form[name='LoginMain'] input[type='button']",
                    # Try exact "LOGIN" text first (all caps)
                    "button:has-text('LOGIN')",
                    "button:has-text('LOG IN')",
                    "button:has-text('SIGN IN')",
                    # Try case-insensitive
                    "button:has-text('Login')",
                    "button:has-text('Sign In')",
                    "button:has-text('Log In')",
                    # Try by type
                    "button[type='submit']",
                    "input[type='submit']",
                    # Try by ID/class
                    "#login-button",
                    "#submit",
                    "#login",
                    "button[id*='login' i]",
                    "button[id*='submit' i]",
                    "button[class*='login' i]",
                    "button[class*='submit' i]",
                    "input[value*='Login' i]",
                    "input[value*='LOGIN' i]",
                    "input[value*='LOGIN']",
                    "input[value*='Sign In' i]",
                ]
                
                login_clicked = False
                login_button_found = False
                
                # Only try to auto-click if token was verified
                if token_verified:
                    # Debug: List all buttons on page to help identify login button
                    try:
                        all_buttons = page.evaluate("""
                            (function() {
                                var buttons = document.querySelectorAll('button, input[type="submit"], input[type="button"]');
                                var result = [];
                                for (var i = 0; i < buttons.length; i++) {
                                    var btn = buttons[i];
                                    if (btn.offsetParent !== null) {
                                        var rect = btn.getBoundingClientRect();
                                        result.push({
                                            text: (btn.textContent || btn.innerText || btn.value || '').trim(),
                                            id: btn.id || '',
                                            className: btn.className || '',
                                            type: btn.type || '',
                                            tagName: btn.tagName || '',
                                            x: Math.round(rect.left),
                                            y: Math.round(rect.top)
                                        });
                                    }
                                }
                                return result;
                            })();
                        """)
                        if status_cb and all_buttons:
                            # Show all buttons with their details
                            for btn in all_buttons:
                                btn_str = f"Text:'{btn['text']}' ID:'{btn['id']}' Class:'{btn['className'][:30]}'"
                                status_cb(f"Button: {btn_str}")
                    except Exception as e:
                        if status_cb:
                            status_cb(f"Debug error: {str(e)[:50]}")
                    
                    # Try Playwright selectors first
                    for selector in submit_selectors:
                        try:
                            login_btn = page.locator(selector).first
                            if login_btn.is_visible(timeout=2000):
                                # Check if button is enabled (not disabled)
                                is_enabled = True
                                try:
                                    is_enabled = login_btn.is_enabled(timeout=500)
                                except:
                                    pass
                                
                                if not is_enabled:
                                    if status_cb:
                                        status_cb(f"Login button found but disabled - waiting...")
                                    # Wait a bit more for button to become enabled
                                    page.wait_for_timeout(2000)
                                    # Check again
                                    try:
                                        is_enabled = login_btn.is_enabled(timeout=500)
                                    except:
                                        pass
                                
                                login_button_found = True
                                if status_cb:
                                    status_cb(f"Found login button: {selector} (enabled: {is_enabled})")
                                try:
                                    # Get button text for confirmation
                                    btn_text = login_btn.text_content()
                                    if status_cb:
                                        status_cb(f"Button text: '{btn_text}'")
                                    
                                    # Scroll into view and focus before clicking
                                    login_btn.scroll_into_view_if_needed()
                                    page.wait_for_timeout(200)
                                    
                                    # Check if button is covered by reCAPTCHA or another element
                                    try:
                                        # Get button's bounding box
                                        box = login_btn.bounding_box()
                                        if box:
                                            # Check if element at that position is the button or something else
                                            element_at_point = page.evaluate(f"""
                                                (function() {{
                                                    var x = {box['x'] + box['width']/2};
                                                    var y = {box['y'] + box['height']/2};
                                                    var elem = document.elementFromPoint(x, y);
                                                    if (elem) {{
                                                        var tag = elem.tagName;
                                                        var id = elem.id ? '#' + elem.id : '';
                                                        var cls = elem.className ? '.' + elem.className.split(' ')[0] : '';
                                                        var zIndex = window.getComputedStyle(elem).zIndex;
                                                        // Check if it's a reCAPTCHA overlay
                                                        var isRecaptcha = tag === 'IFRAME' && (elem.src.indexOf('recaptcha') !== -1 || elem.src.indexOf('bframe') !== -1);
                                                        var isOverlay = zIndex && parseInt(zIndex) > 1000000;
                                                        return tag + id + cls + (isRecaptcha ? ' [RECAPTCHA]' : '') + (isOverlay ? ' [HIGH-Z-INDEX:' + zIndex + ']' : '');
                                                    }}
                                                    return null;
                                                }})();
                                            """)
                                            if status_cb and element_at_point:
                                                if 'RECAPTCHA' in element_at_point or 'HIGH-Z-INDEX' in element_at_point:
                                                    status_cb(f"âš  Button may be blocked by: {element_at_point}")
                                                    # Try to hide reCAPTCHA overlays
                                                    try:
                                                        page.evaluate("""
                                                            (function() {
                                                                // Hide reCAPTCHA overlays that might be blocking
                                                                var overlays = document.querySelectorAll('div[style*="z-index"][style*="2000000000"], div.g-recaptcha-bubble-arrow');
                                                                for (var i = 0; i < overlays.length; i++) {
                                                                    var style = window.getComputedStyle(overlays[i]);
                                                                    if (style.opacity !== '0' && style.visibility !== 'hidden') {
                                                                        overlays[i].style.display = 'none';
                                                                    }
                                                                }
                                                            })();
                                                        """)
                                                        page.wait_for_timeout(500)
                                                        if status_cb:
                                                            status_cb("Attempted to hide reCAPTCHA overlays")
                                                    except:
                                                        pass
                                                else:
                                                    status_cb(f"Element at button position: {element_at_point}")
                                    except:
                                        pass
                                    
                                    login_btn.focus()
                                    page.wait_for_timeout(200)
                                    
                                    # Try multiple click methods
                                    try:
                                        if is_enabled:
                                            login_btn.click(timeout=2000)
                                        else:
                                            # Try force click if disabled
                                            login_btn.click(force=True, timeout=2000)
                                    except:
                                        # Try force click as fallback
                                        login_btn.click(force=True, timeout=2000)
                                    
                                    login_clicked = True
                                    if status_cb:
                                        status_cb("âœ“ Clicked login button (Playwright)")
                                    # Wait to ensure click registered
                                    page.wait_for_timeout(1000)
                                    break
                                except Exception as e:
                                    if status_cb:
                                        status_cb(f"Playwright click failed: {str(e)[:80]}")
                                    continue
                        except Exception as e:
                            if status_cb:
                                status_cb(f"Selector '{selector}' failed: {str(e)[:50]}")
                            continue
                
                # Fallback: Use JavaScript to find and click login button
                if not login_clicked:
                    try:
                        if status_cb:
                            status_cb("Trying JavaScript method to click login button...")
                        js_login = """
                        (function() {
                            // First, try to find button in LoginMain form
                            try {
                                var form = document.querySelector('form[name="LoginMain"]');
                                if (form) {
                                    var formButtons = form.querySelectorAll('button, input[type="submit"], input[type="button"]');
                                    for (var i = 0; i < formButtons.length; i++) {
                                        var btn = formButtons[i];
                                        if (btn.offsetParent === null) continue;
                                        var text = (btn.textContent || btn.innerText || btn.value || '').trim();
                                        if (text === 'LOGIN' || text === 'Login' || text.toUpperCase() === 'LOGIN') {
                                            console.log('Found LOGIN button in LoginMain form, clicking...');
                                            btn.scrollIntoView({behavior: 'smooth', block: 'center'});
                                            setTimeout(function() {
                                                btn.focus();
                                                btn.click();
                                                // Also try dispatchEvent as backup
                                                var clickEvent = new MouseEvent('click', {
                                                    bubbles: true,
                                                    cancelable: true,
                                                    view: window
                                                });
                                                btn.dispatchEvent(clickEvent);
                                            }, 200);
                                            return true;
                                        }
                                    }
                                    // If no button found with LOGIN text, try first submit button in form
                                    for (var i = 0; i < formButtons.length; i++) {
                                        var btn = formButtons[i];
                                        if (btn.offsetParent !== null && (btn.type === 'submit' || btn.tagName === 'BUTTON')) {
                                            console.log('Found submit button in LoginMain form, clicking...');
                                            btn.scrollIntoView({behavior: 'smooth', block: 'center'});
                                            setTimeout(function() {
                                                btn.focus();
                                                btn.click();
                                            }, 200);
                                            return true;
                                        }
                                    }
                                }
                            } catch(e) {
                                console.log('LoginMain form error:', e);
                            }
                            
                            // Fallback: try to find button with exact "LOGIN" text (all caps) anywhere on page
                            var buttons = document.querySelectorAll('button, input[type="submit"], input[type="button"]');
                            for (var i = 0; i < buttons.length; i++) {
                                var btn = buttons[i];
                                if (btn.offsetParent === null) continue;
                                var text = (btn.textContent || btn.innerText || btn.value || '').trim();
                                // Check for exact "LOGIN" match first (case-sensitive)
                                if (text === 'LOGIN' || text === 'LOG IN' || text.toUpperCase() === 'LOGIN') {
                                    console.log('Found LOGIN button, clicking...');
                                    btn.scrollIntoView({behavior: 'smooth', block: 'center'});
                                    setTimeout(function() {
                                        btn.focus();
                                        btn.click();
                                        // Also try dispatchEvent as backup
                                        var clickEvent = new MouseEvent('click', {
                                            bubbles: true,
                                            cancelable: true,
                                            view: window
                                        });
                                        btn.dispatchEvent(clickEvent);
                                    }, 200);
                                    return true;
                                }
                            }
                            
                            // Try querySelector with valid CSS selectors
                            var selectors = [
                                'button[type="submit"]',
                                'input[type="submit"]',
                                '#login-button',
                                '#submit',
                                '#login',
                                'button[id*="login" i]',
                                'button[id*="submit" i]',
                                'button[class*="login" i]',
                                'button[class*="submit" i]'
                            ];
                            
                            for (var i = 0; i < selectors.length; i++) {
                                try {
                                    var btn = document.querySelector(selectors[i]);
                                    if (btn && btn.offsetParent !== null) {
                                        btn.scrollIntoView({behavior: 'smooth', block: 'center'});
                                        btn.focus();
                                        setTimeout(function() { btn.click(); }, 100);
                                        return true;
                                    }
                                } catch(e) {}
                            }
                            
                            // Try finding by text content (case-insensitive)
                            buttons = document.querySelectorAll('button, input[type="submit"]');
                            for (var i = 0; i < buttons.length; i++) {
                                var btn = buttons[i];
                                if (btn.offsetParent === null) continue;
                                var text = (btn.textContent || btn.innerText || btn.value || '').toLowerCase();
                                if (text.indexOf('login') !== -1 || text.indexOf('sign in') !== -1 || text.indexOf('log in') !== -1) {
                                    btn.scrollIntoView({behavior: 'smooth', block: 'center'});
                                    btn.focus();
                                    setTimeout(function() { btn.click(); }, 100);
                                    return true;
                                }
                            }
                            
                            // Try to find button to the right of reCAPTCHA (position-based)
                            try {
                                var recaptcha = document.querySelector('iframe[src*="recaptcha"], div[class*="recaptcha"]');
                                if (recaptcha) {
                                    var recaptchaRect = recaptcha.getBoundingClientRect();
                                    buttons = document.querySelectorAll('button, input[type="submit"]');
                                    for (var i = 0; i < buttons.length; i++) {
                                        var btn = buttons[i];
                                        if (btn.offsetParent === null) continue;
                                        var btnRect = btn.getBoundingClientRect();
                                        // Check if button is to the right of reCAPTCHA (within reasonable distance)
                                        if (btnRect.left > recaptchaRect.right && 
                                            Math.abs(btnRect.top - recaptchaRect.top) < 100) {
                                            btn.scrollIntoView({behavior: 'smooth', block: 'center'});
                                            btn.focus();
                                            setTimeout(function() { btn.click(); }, 100);
                                            return true;
                                        }
                                    }
                                }
                            } catch(e) {}
                            
                            // Last resort: click first visible submit button
                            var submit = document.querySelector('button[type="submit"], input[type="submit"]');
                            if (submit && submit.offsetParent !== null) {
                                submit.scrollIntoView({behavior: 'smooth', block: 'center'});
                                submit.focus();
                                setTimeout(function() { submit.click(); }, 100);
                                return true;
                            }
                            
                            return false;
                        })();
                        """
                        result = page.evaluate(js_login)
                        if result:
                            login_clicked = True
                            if status_cb:
                                status_cb("âœ“ Clicked login button (JavaScript)")
                            # Wait to ensure click registered
                            page.wait_for_timeout(700)  # Wait for setTimeout(100) + processing
                        else:
                            if status_cb:
                                status_cb("âš  JavaScript could not find login button")
                    except Exception as e:
                        if status_cb:
                            status_cb(f"Login button JS error: {str(e)[:50]}")
                
                # If still not clicked and token was verified, try submitting the form directly
                if not login_clicked and token_verified:
                    try:
                        # Try to find and submit the LoginMain form directly
                        login_form = page.locator("form[name='LoginMain']").first
                        if login_form.is_visible(timeout=2000):
                            if status_cb:
                                status_cb("Found LoginMain form, trying to submit...")
                            # Try to find submit button in form
                            submit_btn = login_form.locator("button[type='submit'], input[type='submit'], button:has-text('LOGIN'), button:has-text('Login')").first
                            if submit_btn.is_visible(timeout=2000):
                                submit_btn.click(timeout=2000)
                                login_clicked = True
                                if status_cb:
                                    status_cb("âœ“ Clicked submit button in LoginMain form")
                            else:
                                # Submit form directly using JavaScript
                                try:
                                    login_form.evaluate("form => form.submit()")
                                    login_clicked = True
                                    if status_cb:
                                        status_cb("âœ“ Submitted LoginMain form directly")
                                except:
                                    # Try alternative form submission
                                    page.evaluate("""
                                        (function() {
                                            var form = document.querySelector('form[name="LoginMain"]');
                                            if (form) {
                                                form.submit();
                                                return true;
                                            }
                                            return false;
                                        })();
                                    """)
                                    login_clicked = True
                                    if status_cb:
                                        status_cb("âœ“ Submitted LoginMain form (alternative method)")
                    except Exception as e:
                        if status_cb:
                            status_cb(f"Form submit attempt: {str(e)[:50]}")
                
                if not login_clicked:
                    if status_cb:
                        if not login_button_found:
                            status_cb("âš  Could not find login button - please click it manually")
                        else:
                            status_cb("âš  Login button found but click failed - please click it manually")
            else:
                if status_cb:
                    status_cb("âš  Waiting for reCAPTCHA checkmark before clicking login...")
            
            # Wait for login to complete (only if we clicked login or user manually logged in)
            login_successful = False
            if checkbox_verified and login_clicked:
                if status_cb:
                    status_cb("Waiting for login to complete...")
                
                # IMMEDIATE check first (no wait) - login might be instant
                try:
                    current_url = page.url
                    if "NewOrderMasterPage.jsp" in current_url:
                        login_successful = True
                        if status_cb:
                            status_cb("✓ Login successful! (instant)")
                    else:
                        # Not ready yet - check frequently with minimal delay
                        login_url_base = url.split('?')[0].split('#')[0]
                        max_login_wait = 10  # Reduced to 10 seconds
                        check_count = 0
                        check_interval = 100  # Check every 100ms for faster detection (was 200ms)
                        
                        while check_count < (max_login_wait * 10) and not login_successful:  # 10 seconds * 10 = 100 checks
                            page.wait_for_timeout(check_interval)
                            check_count += 1
                            
                            try:
                                current_url = page.url
                                # If we've navigated away from login URL, login succeeded
                                # Also check if we're on the MVR input page
                                if "NewOrderMasterPage.jsp" in current_url:
                                    login_successful = True
                                    if status_cb:
                                        status_cb("✓ Login successful!")
                                    break
                                elif login_url_base not in current_url and url not in current_url:
                                    login_successful = True
                                    if status_cb:
                                        status_cb("✓ Login successful!")
                                    break
                            except Exception:
                                pass
                            if login_successful:
                                break
                except:
                    pass
                if not login_successful:
                    # Check one more time if we're on the MVR page
                    try:
                        current_url = page.url
                        if "NewOrderMasterPage.jsp" in current_url:
                            login_successful = True
                            if status_cb:
                                status_cb("âœ“ Already on MVR page - login successful!")
                        else:
                            if status_cb:
                                status_cb("âš  Login may not have completed - proceeding anyway...")
                            login_successful = True  # Proceed anyway
                    except:
                        if status_cb:
                            status_cb("âš  Login may not have completed - proceeding anyway...")
                        login_successful = True  # Proceed anyway
            elif checkbox_verified and not login_clicked:
                # Checkmark detected but login button wasn't clicked - wait for manual login
                if status_cb:
                    status_cb("âš  Waiting for manual login...")
                # Check frequently for manual login (every 500ms for 10 seconds)
                login_url_base = url.split('?')[0].split('#')[0]
                for _ in range(20):  # 20 checks * 500ms = 10 seconds
                    page.wait_for_timeout(500)
                    try:
                        current_url = page.url
                        if "NewOrderMasterPage.jsp" in current_url:
                            login_successful = True
                            if status_cb:
                                status_cb("✓ Manual login detected!")
                            break
                        elif login_url_base not in current_url and url not in current_url:
                            login_successful = True
                            if status_cb:
                                status_cb("✓ Manual login detected!")
                            break
                    except:
                        pass
                    if login_successful:
                        break
                
                if not login_successful:
                    login_successful = True  # Proceed anyway
            if status_cb:
                        status_cb("âš  Proceeding - please ensure you're logged in")
            else:
                # No checkmark - but if user manually logged in, proceed anyway
                # Check if we're already on a different page (user might have logged in manually)
                try:
                    current_url = page.url
                    if "NewOrderMasterPage.jsp" in current_url:
                        login_successful = True
                        if status_cb:
                            status_cb("âœ“ Already on MVR page - proceeding...")
                    else:
                        login_successful = False
                        if status_cb:
                            status_cb("âš  Cannot proceed - reCAPTCHA not verified")
                except:
                    login_successful = False
                    if status_cb:
                        status_cb("âš  Cannot proceed - reCAPTCHA not verified")
        else:
            # If skipping login, just navigate to the URL (should already be logged in)
            if status_cb:
                status_cb("Already logged in, navigating...")
            login_successful = True
        
        # Only fill MVR fields after successful login
        if login_successful:
            # Get the state selector immediately (no delay)
            state_selector = field_to_selector.get("state", "#ddComboState")
            if not state_selector:
                state_selector = "#ddComboState"  # Fallback to default
            
            # IMMEDIATE check: Try to detect if page is already ready (fastest path)
            page_ready = False
            try:
                # Instant check - if state dropdown already exists, we're ready NOW
                state_element = page.locator(state_selector).first
                if state_element.count() > 0:
                    page_ready = True
                    if status_cb:
                        status_cb("Page ready (instant) - starting immediately")
            except Exception:
                pass
            
            # Only navigate if not ready AND not on the right page
            if not page_ready:
                try:
                    current_url = page.url
                    mvr_page_url = "https://www.webmvr.com/neworder/NewOrderMasterPage.jsp?Id=new"
                    
                    # Check if we're already on the MVR input page
                    if "NewOrderMasterPage.jsp" not in current_url:
                        if status_cb:
                            status_cb(f"Navigating to MVR page...")
                        try:
                            # Use "commit" for fastest navigation - don't wait for DOM
                            # We'll check readiness immediately after
                            page.goto(mvr_page_url, wait_until="commit", timeout=30000)
                        except Exception as nav_err:
                            if status_cb:
                                status_cb(f"⚠ Navigation error: {str(nav_err)[:80]}")
            
                    # IMMEDIATE readiness check after navigation (or if already on page)
                    # Check multiple times quickly instead of one long wait
                    for quick_check in range(10):  # 10 quick checks
                        try:
                            state_element = page.locator(state_selector).first
                            if state_element.count() > 0:
                                page_ready = True
                                if status_cb:
                                    status_cb("Page ready - starting immediately")
                                break
                        except Exception:
                            pass
                        
                        if not page_ready:
                            # Very short wait between checks (50ms)
                            page.wait_for_timeout(50)
                    
                    # If still not ready, do one final wait with timeout
                    if not page_ready:
                        try:
                            page.wait_for_selector(state_selector, state="attached", timeout=2000)
                            page_ready = True
                            if status_cb:
                                status_cb("Page ready")
                        except Exception:
                            # Last resort: check for any form field
                            try:
                                page.wait_for_selector("select, input", state="attached", timeout=1000)
                                if status_cb:
                                    status_cb("Page ready (fallback)")
                            except Exception:
                                if status_cb:
                                    status_cb("⚠ Proceeding - page may still be loading")
                except Exception:
                    # If navigation/readiness check fails, proceed anyway
                    if status_cb:
                        status_cb("⚠ Navigation/readiness check failed - proceeding")
            
            # Helper function to fill searchable dropdown (click, type, select)
            def fill_dropdown(field_name: str, selector: str, value: str) -> bool:
                """Fill a dropdown - tries select_option() first for standard selects, then searchable dropdowns"""
                if not selector or not value:
                    return False
                
                value_upper = value.upper().strip()
                
                try:
                    # Wait for dropdown to be ready
                    dropdown_locator = page.locator(selector)
                    # Check if element exists first
                    element_count = dropdown_locator.count()
                    if element_count == 0:
                        if status_cb:
                            status_cb(f"⚠ {field_name} dropdown not found with selector: {selector}")
                        return False
                    
                    dropdown_locator.wait_for(state="attached", timeout=5000)
                    
                    if status_cb:
                        status_cb(f"Filling {field_name}: {value_upper}...")
                    
                    # FIRST: Try Playwright's select_option() for standard <select> elements
                    # This is the most reliable method for standard HTML selects (like OrderTypeCombo, ProductTypeCombo)
                    try:
                        # Try selecting by exact value first
                        dropdown_locator.select_option(value=value_upper, timeout=2000)
                        page.wait_for_timeout(100)  # Minimal wait
                        # Verify selection by checking the actual selected value
                        try:
                            selected_value = dropdown_locator.evaluate("el => el.value", timeout=500)
                            if value_upper == selected_value.upper():
                                if status_cb:
                                    status_cb(f"✓ {field_name}: {value_upper} (select_option)")
                                return True
                        except:
                            # If verification fails but no exception, assume success
                            if status_cb:
                                status_cb(f"✓ {field_name}: {value_upper} (select_option)")
                            return True
                    except Exception:
                        # select_option() by value failed, try selecting by label/text
                        try:
                            dropdown_locator.select_option(label=value_upper, timeout=2000)
                            page.wait_for_timeout(100)  # Minimal wait
                            if status_cb:
                                status_cb(f"✓ {field_name}: {value_upper} (select_option by label)")
                            return True
                        except Exception:
                            # select_option() didn't work, fall back to searchable dropdown method
                            pass
                    
                    # FALLBACK: Handle as searchable dropdown (click, type, select)
                    # Step 1: Click the dropdown to open it
                    dropdown_locator.click(timeout=3000)
                    page.wait_for_timeout(100)  # Minimal wait for dropdown to open
                    
                    # Step 2: Find the input/search field inside the dropdown and type into it
                    # Many dropdowns have a separate input field for filtering
                    input_found = False
                    input_selectors = [
                        f"{selector} input",
                        f"{selector} input[type='text']",
                        f"{selector} input[type='search']",
                        "input[role='combobox']",
                        "input[aria-autocomplete='list']",
                        ".dropdown-input",
                        ".select-input",
                        "input:focus",  # The currently focused input
                    ]
                    
                    input_locator = None
                    for input_sel in input_selectors:
                        try:
                            input_locator = page.locator(input_sel).first
                            if input_locator.is_visible(timeout=500):
                                input_found = True
                                break
                        except Exception:
                            continue
                
                    # If no separate input found, use the dropdown itself
                    if not input_found:
                        input_locator = dropdown_locator
                        dropdown_locator.focus(timeout=1000)
                    
                    # Clear any existing value first
                    try:
                        input_locator.press("Control+a", timeout=500)  # Select all
                        input_locator.press("Delete", timeout=500)  # Delete
                    except Exception:
                        try:
                            input_locator.clear(timeout=500)
                        except Exception:
                            pass
                    
                    # Type the abbreviation with minimal delay
                    input_locator.focus(timeout=1000)
                    page.keyboard.type(value_upper, delay=20)  # Reduced delay for speed
                    page.wait_for_timeout(200)  # Minimal wait for filtering to complete
                    
                    # Step 3: Select the filtered option using keyboard navigation
                    # After typing, the first matching option should already be highlighted
                    # Just press Enter to select it (don't press ArrowDown as it moves to next item)
                    try:
                        page.keyboard.press("Enter", delay=50)  # Select the highlighted option
                        page.wait_for_timeout(200)  # Minimal wait for selection to register
                        # Verify the selection was made by checking the dropdown value
                        try:
                            # Check if the value appears in the dropdown's text or value
                            current_value = dropdown_locator.input_value(timeout=1000)
                            if value_upper in current_value.upper() or current_value:
                                if status_cb:
                                    status_cb(f"✓ {field_name}: {value_upper}")
                                return True
                        except:
                            # Also try getting text content as fallback verification
                            try:
                                current_text = dropdown_locator.text_content(timeout=500)
                                if value_upper in current_text.upper() or current_text:
                                    if status_cb:
                                        status_cb(f"✓ {field_name}: {value_upper}")
                                    return True
                            except:
                                pass
                        # If we can't verify, assume success if no exception was raised
                        if status_cb:
                            status_cb(f"✓ {field_name}: {value_upper} (assumed success)")
                        return True
                    except Exception as e1:
                        # If keyboard navigation fails, try clicking the filtered option directly
                        try:
                            # Look for option elements or list items that contain the state abbreviation
                            # Try multiple selectors for different dropdown implementations
                            # Try exact match first, then partial match (e.g., "PW" in "Policy Writer (PW)")
                            option_selectors = [
                                f"{selector} option[value='{value_upper}']",  # Exact value match first
                                f"{selector} option:has-text('{value_upper}')",  # Exact text match
                                f"{selector} option:has-text('{value_upper}' i)",  # Case-insensitive
                                f"li:has-text('{value_upper}')",
                                f"li:has-text('{value_upper}' i)",  # Case-insensitive
                                f"[role='option']:has-text('{value_upper}')",
                                f"[role='option']:has-text('{value_upper}' i)",  # Case-insensitive
                                f"div[role='option']:has-text('{value_upper}')",
                                f"div[role='option']:has-text('{value_upper}' i)",  # Case-insensitive
                                f"*:has-text('{value_upper}'):visible",
                                f"*:has-text('{value_upper}' i):visible"  # Case-insensitive
                            ]
                            
                            for opt_sel in option_selectors:
                                try:
                                    option = page.locator(opt_sel).first
                                    if option.is_visible(timeout=500):
                                        option.click(timeout=2000)
                                        page.wait_for_timeout(100)  # Minimal wait
                                        if status_cb:
                                            status_cb(f"✓ {field_name}: {value_upper}")
                                        return True
                                except Exception:
                                    continue
                        except Exception as e2:
                            if status_cb:
                                status_cb(f"✗ {field_name}: Selection failed - {str(e2)[:30]}")
                            pass
                    
                    # If all else fails, try JavaScript helper
                    if set_select_dropdown_value:
                        element_id = selector.lstrip("#")
                        success = set_select_dropdown_value(page, element_id, value_upper)
                        if success:
                            if status_cb:
                                status_cb(f"✓ {field_name}: {value_upper} (JS)")
                            return True
                    
                    if status_cb:
                        status_cb(f"✗ {field_name}: Could not select {value_upper}")
                    return False
                    
                except Exception as e:
                    if status_cb:
                        status_cb(f"✗ {field_name} dropdown error: {str(e)[:50]}")
                    return False
            
            # Step 1: Fill state dropdown FIRST (required before other fields appear)
            state_selector = field_to_selector.get("state")
            state_value = data.get("state", "")
            if not state_selector or not state_selector.strip():
                # Use default if not configured
                state_selector = "#ddComboState"
                if status_cb:
                    status_cb(f"⚠ State selector not configured, using default: {state_selector}")
            
            # Debug: Show what state value we're using
            if status_cb:
                if state_value:
                    status_cb(f"Using extracted state value: '{state_value}'")
                else:
                    status_cb(f"⚠ No state value in data - state field is empty")
            
            if state_selector and state_value:
                if status_cb:
                    status_cb(f"Step 1: Filling state dropdown (selector: {state_selector}, value: {state_value})...")
                
                # Check if element exists before trying to fill
                try:
                    state_element = page.locator(state_selector).first
                    if state_element.count() == 0:
                        if status_cb:
                            status_cb(f"⚠ State dropdown not found with selector: {state_selector}")
                    else:
                        # For state dropdown, try to match full state name from dropdown options
                        state_value_to_use = state_value
                        try:
                            # Get all available options from the dropdown
                            available_options = page.evaluate(f"""
                                () => {{
                                    const dropdown = document.querySelector('{state_selector}');
                                    if (!dropdown || dropdown.tagName !== 'SELECT') return [];
                                    const opts = [];
                                    for (let i = 0; i < dropdown.options.length; i++) {{
                                        const opt = dropdown.options[i];
                                        if (opt.value && opt.value !== '' && opt.text.trim() !== '----- Select -----' && opt.text.trim() !== '------ Select ------') {{
                                            opts.push({{value: opt.value, text: opt.text.trim()}});
                                        }}
                                    }}
                                    return opts;
                                }}
                            """)
                            
                            if available_options:
                                state_abbr = state_value.upper().strip()
                                
                                # Mapping from abbreviations to full state names
                                abbrev_to_full = {
                                    "AL": "ALABAMA", "AK": "ALASKA", "AZ": "ARIZONA", "AR": "ARKANSAS", "CA": "CALIFORNIA",
                                    "CO": "COLORADO", "CT": "CONNECTICUT", "DE": "DELAWARE", "FL": "FLORIDA", "GA": "GEORGIA",
                                    "HI": "HAWAII", "ID": "IDAHO", "IL": "ILLINOIS", "IN": "INDIANA", "IA": "IOWA",
                                    "KS": "KANSAS", "KY": "KENTUCKY", "LA": "LOUISIANA", "ME": "MAINE", "MD": "MARYLAND",
                                    "MA": "MASSACHUSETTS", "MI": "MICHIGAN", "MN": "MINNESOTA", "MS": "MISSISSIPPI", "MO": "MISSOURI",
                                    "MT": "MONTANA", "NE": "NEBRASKA", "NV": "NEVADA", "NH": "NEW HAMPSHIRE", "NJ": "NEW JERSEY",
                                    "NM": "NEW MEXICO", "NY": "NEW YORK", "NC": "NORTH CAROLINA", "ND": "NORTH DAKOTA", "OH": "OHIO",
                                    "OK": "OKLAHOMA", "OR": "OREGON", "PA": "PENNSYLVANIA", "RI": "RHODE ISLAND", "SC": "SOUTH CAROLINA",
                                    "SD": "SOUTH DAKOTA", "TN": "TENNESSEE", "TX": "TEXAS", "UT": "UTAH", "VT": "VERMONT",
                                    "VA": "VIRGINIA", "WA": "WASHINGTON", "WV": "WEST VIRGINIA", "WI": "WISCONSIN", "WY": "WYOMING",
                                    "DC": "DISTRICT OF COLUMBIA"
                                }
                                
                                # If we have an abbreviation, try to find the full state name in dropdown options
                                if state_abbr in abbrev_to_full:
                                    full_state_name = abbrev_to_full[state_abbr]
                                    # Try to find matching option (case-insensitive, partial match)
                                    for opt in available_options:
                                        opt_text_upper = opt["text"].upper()
                                        # Check if option text contains the full state name or abbreviation
                                        if full_state_name in opt_text_upper or state_abbr in opt_text_upper:
                                            state_value_to_use = opt["text"]  # Use the exact text from dropdown
                                            if status_cb:
                                                status_cb(f"Found matching state option: '{state_value_to_use}'")
                                            break
                                
                                # If we already have a full state name, try to match it directly
                                if state_value_to_use == state_value:
                                    for opt in available_options:
                                        opt_text_upper = opt["text"].upper()
                                        state_value_upper = state_value.upper()
                                        # Check if option text matches (case-insensitive, partial match)
                                        if state_value_upper in opt_text_upper or opt_text_upper in state_value_upper:
                                            state_value_to_use = opt["text"]  # Use the exact text from dropdown
                                            if status_cb:
                                                status_cb(f"Found matching state option: '{state_value_to_use}'")
                                            break
                        except Exception as e:
                            # If getting options fails, just use the original value
                            if status_cb:
                                status_cb(f"Could not get dropdown options, using original value: {str(e)[:50]}")
                        
                        fill_dropdown("State", state_selector, state_value_to_use)
                        
                        # Minimal wait - just check if fields are ready quickly, don't block
                        if status_cb:
                            status_cb("Checking form readiness...")
                        try:
                            # Quick check - if fields are already there, great. If not, proceed anyway
                            page.wait_for_selector("input[name='license'], input[name='lastName'], input[name='firstName']", 
                                                  state="attached", timeout=500)  # Reduced timeout for speed
                            if status_cb:
                                status_cb("✓ Form fields ready")
                        except Exception:
                            # Fields not ready yet, but proceed anyway - they'll be ready by the time we need them
                            if status_cb:
                                status_cb("Form fields will be ready shortly...")
                except Exception as e:
                    if status_cb:
                        status_cb(f"⚠ Error locating state dropdown: {str(e)[:50]}")
            else:
                if status_cb:
                    status_cb(f"⚠ Skipping state - selector: '{state_selector}', value: '{state_value}'")
            
            # Step 2: Fill order_type dropdown IMMEDIATELY after state selection
            # Don't wait - let fill_dropdown handle retries internally for maximum speed
            order_type_selector = field_to_selector.get("order_type")
            if not order_type_selector or not order_type_selector.strip():
                # Use ID selector directly (faster than attribute selectors)
                order_type_selector = "#OrderTypeCombo"
                if status_cb:
                    status_cb(f"Using default Order Type selector: {order_type_selector}")
            else:
                if status_cb:
                    status_cb(f"Using configured Order Type selector: {order_type_selector}")
            
            if order_type_selector and order_type_selector.strip():
                if status_cb:
                    status_cb(f"Step 2: Filling order type dropdown (selector: {order_type_selector})...")
                
                # Check if element exists
                try:
                    order_type_element = page.locator(order_type_selector).first
                    if order_type_element.count() == 0:
                        if status_cb:
                            status_cb(f"⚠ Order Type dropdown not found with selector: {order_type_selector}")
                    else:
                        if status_cb:
                            status_cb(f"✓ Order Type dropdown found")
                except Exception as e:
                    if status_cb:
                        status_cb(f"⚠ Error locating Order Type dropdown: {str(e)[:50]}")
                
                # Check if "PW" option exists first before trying (faster than retrying)
                pw_exists = False
                try:
                    order_type_element = page.locator(order_type_selector).first
                    if order_type_element.count() > 0:
                        # Quick check if "PW" option exists
                        available_options = order_type_element.evaluate("""
                            (select) => {
                                const opts = [];
                                for (let i = 0; i < select.options.length; i++) {
                                    const opt = select.options[i];
                                    if (opt.text && opt.text.trim()) {
                                        opts.push(opt.text.trim().toUpperCase());
                                    }
                                }
                                return opts;
                            }
                        """)
                        if available_options:
                            # Check if any option contains "PW"
                            pw_exists = any("PW" in opt for opt in available_options)
                            if status_cb:
                                status_cb(f"Order Type options: {available_options[:5]}")
                                if pw_exists:
                                    status_cb("Found PW option, selecting...")
                                else:
                                    status_cb("PW option not found, will try DL...")
                except Exception:
                    pass  # If check fails, just try PW anyway
                
                pw_success = False
                if pw_exists:
                    # Only try PW if it exists, with minimal retries
                    max_retries = 2  # Reduced from 3
                    for attempt in range(max_retries):
                        pw_success = fill_dropdown("Order Type", order_type_selector, "PW")
                        if pw_success:
                            break
                        if attempt < max_retries - 1:
                            page.wait_for_timeout(50)  # Reduced wait
                else:
                    if status_cb:
                        status_cb("PW not found in options, trying DL...")
                
                # If "PW" not available or failed, try "DL" as fallback
                if not pw_success:
                    if status_cb and pw_exists:
                        status_cb("PW selection failed, trying DL...")
                    dl_success = False
                    max_retries = 2  # Reduced from 3
                    for attempt in range(max_retries):
                        dl_success = fill_dropdown("Order Type", order_type_selector, "DL")
                        if dl_success:
                            break
                        if attempt < max_retries - 1:
                            page.wait_for_timeout(50)  # Reduced wait
                    
                    if not dl_success:
                        if status_cb:
                            status_cb("⚠ Could not select Order Type (tried PW and DL)")
                
                # Minimal wait - just enough for selection to register
                page.wait_for_timeout(100)  # Reduced wait
                if status_cb:
                    status_cb("✓ Order Type dropdown complete")
            else:
                if status_cb:
                    status_cb("⚠ Skipping Order Type - no selector configured")
            
            # Step 3: Fill product dropdown with priority selection
            # Default selector based on inspection: ProductTypeCombo
            product_selector = field_to_selector.get("product")
            if not product_selector or not product_selector.strip():
                # Use ID selector directly (faster than attribute selectors)
                product_selector = "#ProductTypeCombo"
                if status_cb:
                    status_cb(f"Using default Product selector: {product_selector}")
            else:
                if status_cb:
                    status_cb(f"Using configured Product selector: {product_selector}")
            
            if product_selector and product_selector.strip():
                if status_cb:
                    status_cb(f"Step 3: Filling product dropdown (selector: {product_selector})...")
                
                # Check if element exists
                try:
                    product_element = page.locator(product_selector).first
                    if product_element.count() == 0:
                        if status_cb:
                            status_cb(f"⚠ Product dropdown not found with selector: {product_selector}")
                    else:
                        if status_cb:
                            status_cb(f"✓ Product dropdown found")
                except Exception as e:
                    if status_cb:
                        status_cb(f"⚠ Error locating Product dropdown: {str(e)[:50]}")
                
                # Get state abbreviation for product selection
                state_abbr = state_value.upper().strip() if state_value else ""
                
                # Helper function to get available options from dropdown
                def get_dropdown_options(sel: str) -> list:
                    """Get list of available option texts from dropdown"""
                    try:
                        options = page.evaluate(f"""
                            () => {{
                                const dropdown = document.querySelector('{sel}');
                                if (!dropdown) return [];
                                const opts = [];
                                if (dropdown.tagName === 'SELECT') {{
                                    for (let i = 0; i < dropdown.options.length; i++) {{
                                        const opt = dropdown.options[i];
                                        if (opt.value && opt.value !== '' && opt.text.trim() !== '----- Select -----' && opt.text.trim() !== '------ Select ------') {{
                                            opts.push(opt.text.trim());
                                        }}
                                    }}
                                }}
                                return opts;
                            }}
                        """)
                        return options if isinstance(options, list) else []
                    except Exception:
                        return []
                
                # Helper function to check if dropdown already has correct value selected
                def is_product_already_selected(sel: str, priority_options: list) -> Tuple[bool, str]:
                    """Check if product dropdown already has a matching priority option selected. Returns (is_selected, current_value)"""
                    try:
                        result = page.evaluate(f"""
                            () => {{
                                const dropdown = document.querySelector('{sel}');
                                if (!dropdown || dropdown.tagName !== 'SELECT') return {{selected: false, value: null}};
                                const selectedOption = dropdown.options[dropdown.selectedIndex];
                                if (!selectedOption || !selectedOption.value || selectedOption.value === '' || 
                                    selectedOption.text.trim() === '----- Select -----' || 
                                    selectedOption.text.trim() === '------ Select ------') {{
                                    return {{selected: false, value: null}};
                                }}
                                return {{selected: true, value: selectedOption.text.trim()}};
                            }}
                        """)
                        if result and result.get("selected") and result.get("value"):
                            current_value = result.get("value")
                            # Check if current value matches any priority option
                            for priority_option in priority_options:
                                if priority_option.upper() in current_value.upper():
                                    return (True, current_value)
                            # If only one option exists and it's selected, that's fine too
                            return (True, current_value)
                        return (False, None)
                    except Exception:
                        return (False, None)
                
                # Start selection immediately - fill_dropdown will retry if options aren't ready yet
                max_retries = 3
                product_selected = False
                
                # Priority list: try each option in order
                priority_options = []
                if state_abbr:
                    priority_options = [
                        f"{state_abbr} PolicyWatch 3Y FULL",
                        f"{state_abbr} PolicyWatch 3Y Instant",
                        f"{state_abbr} DL 3Y Instant"
                    ]
                
                # IMMEDIATE CHECK: See if dropdown already has correct value (fastest path)
                is_selected, current_value = is_product_already_selected(product_selector, priority_options)
                if is_selected and current_value:
                    if status_cb:
                        status_cb(f"✓ Product already selected: {current_value}")
                    product_selected = True
                else:
                    # Quick check: if there's only one option, select it immediately and skip all retry logic
                    try:
                        # Very quick check - don't wait long
                        page.wait_for_selector(product_selector, state="attached", timeout=500)  # Reduced from 2000 to 500
                        available_options = get_dropdown_options(product_selector)
                        if len(available_options) == 1:
                            # Only one option - select it immediately and move on
                            if status_cb:
                                status_cb(f"Only one product option, selecting: {available_options[0]}")
                            product_selected = fill_dropdown("Product", product_selector, available_options[0])
                            if product_selected:
                                # Skip all retry logic - we're done
                                pass
                    except:
                        # If quick check fails, fall through to retry logic
                        pass
                
                # Only do retry logic if we haven't selected yet
                if not product_selected:
                    # Try to get options and select based on priority
                    for attempt in range(max_retries):
                        try:
                            # Wait for dropdown to be populated (quick check)
                            page.wait_for_selector(product_selector, state="attached", timeout=1000)  # Reduced from 3000 to 1000
                            
                            # Get available options immediately (don't wait for multiple options - one is enough)
                            available_options = get_dropdown_options(product_selector)
                            
                            # If we have at least one valid option (not just placeholder), proceed
                            if len(available_options) == 0:
                                # Options not ready yet, wait briefly and retry
                                if attempt < max_retries - 1:
                                    page.wait_for_timeout(100)  # Reduced wait
                                    continue
                            
                            # Check again if it's already selected (in case it got populated between checks)
                            is_selected, current_value = is_product_already_selected(product_selector, priority_options)
                            if is_selected and current_value:
                                if status_cb:
                                    status_cb(f"✓ Product already selected: {current_value}")
                                product_selected = True
                                break
                            
                            # If only one option, check if it's already selected before trying to select it
                            if len(available_options) == 1:
                                # Double-check if it's already selected
                                is_selected, current_value = is_product_already_selected(product_selector, priority_options)
                                if is_selected:
                                    if status_cb:
                                        status_cb(f"✓ Product already selected: {available_options[0]}")
                                    product_selected = True
                                    break
                                
                                # If not already selected, select it
                                if status_cb:
                                    status_cb(f"Selecting product: {available_options[0]}")
                                product_selected = fill_dropdown("Product", product_selector, available_options[0])
                                if product_selected:
                                    break
                            
                            # If multiple options, try priority options in order
                            if len(available_options) > 1:
                                # Try priority options in order
                                for priority_option in priority_options:
                                    # Check if this option exists (case-insensitive, partial match)
                                    matching_option = None
                                    for opt in available_options:
                                        if priority_option.upper() in opt.upper():
                                            matching_option = opt
                                            break
                                    
                                    if matching_option:
                                        if status_cb:
                                            status_cb(f"Selecting: {matching_option}")
                                        product_selected = fill_dropdown("Product", product_selector, matching_option)
                                        if product_selected:
                                            break
                                
                                # If we found a match, break out of retry loop
                                if product_selected:
                                    break
                                
                                # If no priority match found, try to select first available option
                                if not product_selected and available_options:
                                    if status_cb:
                                        status_cb(f"No priority match found, selecting first option: {available_options[0]}")
                                    product_selected = fill_dropdown("Product", product_selector, available_options[0])
                                    if product_selected:
                                        break
                            
                            # If we got here and still not selected, retry
                            if not product_selected and attempt < max_retries - 1:
                                page.wait_for_timeout(100)  # Reduced wait
                        
                        except Exception as e:
                            # Only show error if it's the last attempt or if it's not a timeout (which is expected during retries)
                            error_str = str(e).lower()
                            is_timeout = "timeout" in error_str
                            if not is_timeout or attempt == max_retries - 1:
                                if status_cb:
                                    status_cb(f"⚠ Product dropdown error (attempt {attempt + 1}): {str(e)[:50]}")
                            if attempt < max_retries - 1:
                                page.wait_for_timeout(100)  # Reduced wait
                
                # Only show error if selection actually failed
                if not product_selected:
                    if status_cb:
                        status_cb("⚠ Could not select Product dropdown")
                else:
                    # Selection succeeded, no error message needed
                    pass
                
                # No wait needed - if selection succeeded, form is ready immediately
                # Only wait if we need to ensure form has updated (but we'll check that in Step 4)
                if status_cb:
                    status_cb("✓ Product dropdown complete")
            else:
                if status_cb:
                    status_cb("⚠ Skipping Product - no selector configured")
            
            # Step 4: Fill Purpose dropdown with "Insurance"
            # Wait a bit for form to be fully ready after Product dropdown
            page.wait_for_timeout(300)
            
            # Wait for JavaScript functions to complete (onload="retainProductType_Subproduct()")
            try:
                # Wait for the function to be defined and potentially executed
                page.wait_for_function("""
                    () => {
                        return typeof retainProductType_Subproduct === 'function' || 
                               document.querySelector('select[name="purposeCode"]') !== null;
                    }
                """, timeout=2000)
                if status_cb:
                    status_cb("✓ Page JavaScript functions ready")
            except Exception:
                pass  # Function might not be needed or already executed
            
            purpose_selector = field_to_selector.get("purpose")
            if not purpose_selector or not purpose_selector.strip():
                # Use name selector directly (based on inspection: name='purposeCode')
                purpose_selector = "select[name='purposeCode']"
                if status_cb:
                    status_cb(f"Using default Purpose selector: {purpose_selector}")
            else:
                if status_cb:
                    status_cb(f"Using configured Purpose selector: {purpose_selector}")
            
            if purpose_selector and purpose_selector.strip():
                if status_cb:
                    status_cb(f"Step 4: Filling Purpose dropdown (selector: {purpose_selector})...")
                
                # Wait for Purpose dropdown to be in DOM first, then visible
                try:
                    # First wait for it to be in the DOM (attached)
                    page.wait_for_selector(purpose_selector, timeout=5000, state="attached")
                    if status_cb:
                        status_cb(f"✓ Purpose dropdown found in DOM")
                    # Then wait for it to be visible
                    page.wait_for_selector(purpose_selector, timeout=3000, state="visible")
                    if status_cb:
                        status_cb(f"✓ Purpose dropdown is visible and ready")
                except Exception as e:
                    if status_cb:
                        status_cb(f"⚠ Purpose dropdown not ready: {str(e)[:60]}")
                    # Try to find it anyway - might be there but timing issue
                
                # Try direct selection by value first (we know from inspection: value='AA' for Insurance)
                purpose_success = False
                try:
                    # Try to find the dropdown - use multiple methods
                    purpose_element = None
                    
                    # Method 1: Try the configured selector
                    try:
                        purpose_element = page.locator(purpose_selector).first
                        if purpose_element.count() == 0:
                            purpose_element = None
                    except Exception:
                        purpose_element = None
                    
                    # Method 2: If selector failed, try finding by name attribute directly
                    if purpose_element is None or purpose_element.count() == 0:
                        if status_cb:
                            status_cb("Trying alternative method to find Purpose dropdown...")
                        try:
                            # Use JavaScript to find it
                            found_element = page.evaluate("""
                                () => {
                                    const select = document.querySelector('select[name="purposeCode"]');
                                    return select ? true : false;
                                }
                            """)
                            if found_element:
                                purpose_element = page.locator("select[name='purposeCode']").first
                                if status_cb:
                                    status_cb("✓ Found Purpose dropdown using JavaScript query")
                        except Exception:
                            pass
                    
                    # Method 3: Try finding all select.commonfont and check which one has "Insurance"
                    if purpose_element is None or (purpose_element.count() == 0):
                        if status_cb:
                            status_cb("Trying to find Purpose dropdown by checking all selects...")
                        try:
                            all_selects = page.locator("select.commonfont").all()
                            for select_elem in all_selects:
                                try:
                                    select_name = select_elem.evaluate("el => el.name", timeout=500)
                                    if select_name == "purposeCode":
                                        purpose_element = select_elem
                                        if status_cb:
                                            status_cb(f"✓ Found Purpose dropdown by checking select.commonfont elements")
                                        break
                                except Exception:
                                    continue
                        except Exception:
                            pass
                    
                    if purpose_element is None or purpose_element.count() == 0:
                        if status_cb:
                            status_cb(f"⚠ Could not find Purpose dropdown with any method")
                        # Debug: show what selects are available
                        try:
                            all_selects_info = page.evaluate("""
                                () => {
                                    const selects = document.querySelectorAll('select');
                                    const info = [];
                                    for (let i = 0; i < selects.length; i++) {
                                        const sel = selects[i];
                                        info.push({
                                            name: sel.name || '',
                                            id: sel.id || '',
                                            class: sel.className || '',
                                            visible: sel.offsetParent !== null
                                        });
                                    }
                                    return info;
                                }
                            """)
                            if status_cb and all_selects_info:
                                select_info_str = ", ".join([f"name='{s['name']}', id='{s['id']}', visible={s['visible']}" for s in all_selects_info[:5]])
                                status_cb(f"Available selects on page: {select_info_str}")
                        except Exception:
                            pass
                    
                    if purpose_element is not None and purpose_element.count() > 0:
                        # Wait for element to be attached and visible
                        purpose_element.wait_for(state="attached", timeout=2000)
                        purpose_element.wait_for(state="visible", timeout=2000)
                        
                        # Verify we have the correct element by checking its name attribute
                        element_name = purpose_element.evaluate("el => el.name", timeout=500)
                        if element_name != "purposeCode":
                            if status_cb:
                                status_cb(f"⚠ Wrong element! Expected name='purposeCode', got name='{element_name}' - skipping Purpose dropdown")
                            purpose_success = False
                        else:
                            # Verify element count
                            if purpose_element.count() > 0:
                                # Check if dropdown is disabled - if so, wait a bit
                                is_disabled = purpose_element.evaluate("el => el.disabled", timeout=500)
                                if is_disabled:
                                    if status_cb:
                                        status_cb("Purpose dropdown is disabled, waiting...")
                                    page.wait_for_timeout(500)
                                    # Check again
                                    is_disabled = purpose_element.evaluate("el => el.disabled", timeout=500)
                                    if is_disabled:
                                        if status_cb:
                                            status_cb("⚠ Purpose dropdown is still disabled")
                                
                                # Focus and click the dropdown first to ensure it's active
                                try:
                                    purpose_element.focus(timeout=1000)
                                    purpose_element.click(timeout=1000)
                                    page.wait_for_timeout(100)
                                except Exception:
                                    pass  # Click/focus might not be needed, but try it anyway
                                
                                if status_cb:
                                    status_cb("Attempting to select Insurance by value 'AA'...")
                                
                                # Method 1: Try selecting by value 'AA' directly (fastest method)
                                try:
                                    purpose_element.select_option(value="AA", timeout=3000)
                                    page.wait_for_timeout(200)  # Give it time to register
                                    # Verify selection
                                    selected_value = purpose_element.evaluate("el => el.value", timeout=500)
                                    selected_text = purpose_element.evaluate("el => el.options[el.selectedIndex].text.trim()", timeout=500)
                                    if selected_value == "AA":
                                        if status_cb:
                                            status_cb(f"✓ Purpose dropdown: Insurance (by value AA) - verified value={selected_value}, text={selected_text}")
                                        purpose_success = True
                                    else:
                                        if status_cb:
                                            status_cb(f"Value selection failed: expected AA, got {selected_value}, text={selected_text}")
                                except Exception as e1:
                                    if status_cb:
                                        status_cb(f"Method 1 (value AA) failed: {str(e1)[:100]}")
                                
                                # Method 2: Try by label "Insurance" (case-sensitive)
                                if not purpose_success:
                                    try:
                                        if status_cb:
                                            status_cb("Attempting to select Insurance by label...")
                                        purpose_element.select_option(label="Insurance", timeout=3000)
                                        page.wait_for_timeout(500)  # Longer wait for selection to register
                                        # Verify by checking both value and text - try multiple times
                                        selected_value = None
                                        selected_text = None
                                        for verify_attempt in range(3):
                                            try:
                                                selected_value = purpose_element.evaluate("el => el.value", timeout=500)
                                                selected_text = purpose_element.evaluate("el => el.options[el.selectedIndex].text.trim()", timeout=500)
                                                if selected_value == "AA" or (selected_text and "Insurance" in selected_text):
                                                    break
                                                if verify_attempt < 2:
                                                    page.wait_for_timeout(100)  # Wait a bit more and retry
                                            except Exception:
                                                if verify_attempt < 2:
                                                    page.wait_for_timeout(100)
                                        
                                        if selected_value == "AA" or (selected_text and "Insurance" in selected_text):
                                            if status_cb:
                                                status_cb(f"✓ Purpose dropdown: {selected_text} (by label) - verified value={selected_value}")
                                            purpose_success = True
                                        else:
                                            if status_cb:
                                                status_cb(f"Label selection verification failed: got value='{selected_value}', text='{selected_text}' - will try next method")
                                    except Exception as e2:
                                        if status_cb:
                                            status_cb(f"Method 2 (label) failed: {str(e2)[:100]}")
                                
                                # Method 3: Try finding by text and selecting by index
                                if not purpose_success:
                                    try:
                                        if status_cb:
                                            status_cb("Attempting to select Insurance by finding option index...")
                                        insurance_options = purpose_element.evaluate("""
                                            (select) => {
                                                const opts = [];
                                                for (let i = 0; i < select.options.length; i++) {
                                                    const opt = select.options[i];
                                                    const text = opt.text ? opt.text.trim() : '';
                                                    if (text === 'Insurance' || text.includes('Insurance')) {
                                                        opts.push({text: text, value: opt.value, index: i});
                                                        break;
                                                    }
                                                }
                                                return opts;
                                            }
                                        """)
                                        
                                        if insurance_options and len(insurance_options) > 0:
                                            insurance_opt = insurance_options[0]
                                            if status_cb:
                                                status_cb(f"Found Insurance option: value='{insurance_opt['value']}', index={insurance_opt['index']}")
                                            purpose_element.select_option(index=insurance_opt['index'], timeout=3000)
                                            page.wait_for_timeout(100)
                                            # Verify
                                            selected_index = purpose_element.evaluate("el => el.selectedIndex", timeout=500)
                                            if selected_index == insurance_opt['index']:
                                                if status_cb:
                                                    status_cb(f"✓ Purpose dropdown: {insurance_opt['text']} (by index)")
                                                purpose_success = True
                                            else:
                                                if status_cb:
                                                    status_cb(f"Index selection failed: expected index {insurance_opt['index']}, got {selected_index}")
                                        else:
                                            if status_cb:
                                                status_cb("⚠ Could not find 'Insurance' option in dropdown")
                                            # Debug: show all available options
                                            all_options = purpose_element.evaluate("""
                                                (select) => {
                                                    const opts = [];
                                                    for (let i = 0; i < select.options.length; i++) {
                                                        opts.push({text: select.options[i].text.trim(), value: select.options[i].value});
                                                    }
                                                    return opts;
                                                }
                                            """)
                                            if status_cb and all_options:
                                                status_cb(f"Available Purpose options: {[opt['text'] for opt in all_options[:10]]}")
                                    except Exception as e3:
                                        if status_cb:
                                            status_cb(f"Method 3 (index) failed: {str(e3)[:50]}")
                                
                                # Method 4: Try JavaScript direct assignment with all events
                                if not purpose_success:
                                    try:
                                        if status_cb:
                                            status_cb("Attempting to select Insurance via JavaScript with all events...")
                                        result = purpose_element.evaluate("""
                                            (select) => {
                                                // Find the Insurance option
                                                for (let i = 0; i < select.options.length; i++) {
                                                    const opt = select.options[i];
                                                    if (opt.value === 'AA' || (opt.text && opt.text.trim() === 'Insurance')) {
                                                        // Set selectedIndex
                                                        select.selectedIndex = i;
                                                        
                                                        // Trigger all possible events
                                                        select.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
                                                        select.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
                                                        select.dispatchEvent(new MouseEvent('change', { bubbles: true, cancelable: true }));
                                                        
                                                        // Also trigger on the option if possible
                                                        if (opt) {
                                                            opt.selected = true;
                                                        }
                                                        
                                                        // Return success info
                                                        return {success: true, value: select.value, text: select.options[select.selectedIndex].text.trim()};
                                                    }
                                                }
                                                return {success: false, value: select.value, text: ''};
                                            }
                                        """)
                                        page.wait_for_timeout(200)
                                        
                                        if result and result.get('success'):
                                            # Verify again from the page
                                            selected_value = purpose_element.evaluate("el => el.value", timeout=500)
                                            selected_text = purpose_element.evaluate("el => el.options[el.selectedIndex].text.trim()", timeout=500)
                                            if selected_value == "AA" or (selected_text and "Insurance" in selected_text):
                                                if status_cb:
                                                    status_cb(f"✓ Purpose dropdown: {selected_text} (via JavaScript) - value={selected_value}")
                                                purpose_success = True
                                            else:
                                                if status_cb:
                                                    status_cb(f"JavaScript selection failed: value={selected_value}, text={selected_text}, JS result={result}")
                                        else:
                                            # Check what we got
                                            selected_value = purpose_element.evaluate("el => el.value", timeout=500)
                                            selected_text = purpose_element.evaluate("el => el.options[el.selectedIndex].text.trim()", timeout=500)
                                            if status_cb:
                                                status_cb(f"JavaScript selection failed: value={selected_value}, text={selected_text}, JS result={result}")
                                    except Exception as e4:
                                        if status_cb:
                                            status_cb(f"Method 4 (JavaScript) failed: {str(e4)[:100]}")
                            else:
                                if status_cb:
                                    status_cb(f"⚠ Purpose dropdown element count is 0")
                except Exception as e:
                    if status_cb:
                        status_cb(f"Error accessing Purpose dropdown: {str(e)[:100]}")
                
                # If direct methods failed, use fill_dropdown with retries (same pattern as other dropdowns)
                if not purpose_success:
                    if status_cb:
                        status_cb("Trying fill_dropdown as fallback...")
                    max_retries = 3
                    for attempt in range(max_retries):
                        purpose_success = fill_dropdown("Purpose", purpose_selector, "Insurance")
                        if purpose_success:
                            break
                        if attempt < max_retries - 1:
                            if status_cb:
                                status_cb(f"Retry {attempt + 1}/{max_retries} for Purpose dropdown...")
                            page.wait_for_timeout(200)
                    
                    if purpose_success:
                        if status_cb:
                            status_cb("✓ Purpose dropdown: Insurance (via fill_dropdown)")
                        page.wait_for_timeout(100)
                    else:
                        # Final check - maybe it was selected but verification failed
                        try:
                            purpose_element = page.locator(purpose_selector).first
                            final_value = purpose_element.evaluate("el => el.value", timeout=500)
                            final_text = purpose_element.evaluate("el => el.options[el.selectedIndex].text.trim()", timeout=500)
                            if final_value == "AA" or (final_text and "Insurance" in final_text):
                                if status_cb:
                                    status_cb(f"✓ Purpose dropdown: {final_text} (final check - was already selected)")
                                purpose_success = True
                            else:
                                if status_cb:
                                    status_cb(f"⚠ Could not select Purpose: Insurance after all methods (final value={final_value}, text={final_text})")
                        except Exception:
                            if status_cb:
                                status_cb("⚠ Could not select Purpose: Insurance after all methods")
                else:
                    page.wait_for_timeout(100)
            else:
                if status_cb:
                    status_cb("⚠ Skipping Purpose - no selector configured")
            
            # IMPORTANT: Wait for all dropdowns to complete before filling input fields
            # This ensures the form is fully ready
            # No wait needed - if dropdowns completed successfully, form is ready immediately
            if status_cb:
                status_cb("Filling input fields (license, name, DOB)...")
            
            # Step 5: Fill all other fields (license, first name, last name, DOB)
            # These MUST come after all dropdowns are complete
            # Fill fields quickly with minimal delays
            
            for field, selector in field_to_selector.items():
                # Skip fields we've already handled
                if field in ("state", "order_type", "product", "purpose"):
                    continue
                
                value = data.get(field, "")
                # Clean DOB - remove underscores
                if field == "dob":
                    value = value.replace("_", "")
                
                if not selector:
                    if status_cb:
                        status_cb(f"⚠ Skipping {field} - no selector configured")
                    continue
                if not value:
                    if status_cb:
                        status_cb(f"⚠ Skipping {field} - no value to fill")
                    continue
                
                # Regular field handling - prioritize Playwright's native method
                # Special handling for DOB - need to click first and type character by character for auto-formatting
                # Special handling for first_name - if not found, skip it (don't block)
                filled = False
                
                # Check if field exists before trying to fill (especially for first_name)
                if field == "first_name":
                    try:
                        field_locator = page.locator(selector)
                        if field_locator.count() == 0:
                            if status_cb:
                                status_cb(f"⚠ First Name field not found - skipping")
                            continue
                    except Exception:
                        if status_cb:
                            status_cb(f"⚠ First Name field error - skipping")
                        continue
                
                try:
                    # For DOB field, click it first to make it visible/appear
                    if field == "dob":
                        try:
                            field_locator = page.locator(selector)
                            field_locator.click(timeout=5000)
                            # No wait - click should be enough, typing will trigger field activation
                            
                            # Type DOB character by character to trigger automatic slash insertion
                            # Remove any existing slashes from value (e.g., "01/01/1990" -> "01011990")
                            dob_digits = ''.join(c for c in value if c.isdigit())
                            if dob_digits:
                                # Type each digit with minimal delay to allow auto-formatting
                                for digit in dob_digits:
                                    page.keyboard.type(digit, delay=2)  # Minimal delay for speed
                                
                                filled = True
                                if status_cb:
                                    status_cb(f"✓ DOB: {value}")
                        except Exception as e:
                            if status_cb:
                                status_cb(f"⚠ DOB typing error: {str(e)[:50]}")
                            # Fall through to try regular fill method
                    
                    # For non-DOB fields, use regular fill method with reduced timeout
                    if not filled and field != "dob":
                        page.fill(selector, value, timeout=5000)  # Reduced timeout from 10000 to 5000
                        filled = True
                except Exception as e:
                    # If Playwright fails, try legacy helper as fallback
                    if fill_text_input:
                        try:
                            success = fill_text_input(page, selector, value, use_js=False)
                            if success:
                                filled = True
                        except Exception:
                            pass  # Legacy helper also failed, continue to next fallback
                    # Final fallback: click then type
                    if not filled:
                        try:
                            page.click(selector, timeout=3000)  # Reduced timeout from 5000 to 3000
                            # No wait after click - type immediately
                            if field == "dob":
                                # For DOB, type character by character even in fallback
                                dob_digits = ''.join(c for c in value if c.isdigit())
                                for digit in dob_digits:
                                    page.keyboard.type(digit, delay=2)  # Minimal delay for speed
                            else:
                                page.keyboard.type(value, delay=0)  # Type fast for other fields
                            filled = True
                        except Exception as e2:
                            if status_cb:
                                status_cb(f"⚠ Warning: Could not fill {field} field (selector: {selector}): {str(e2)}")
                            pass
            else:
                if status_cb:
                    status_cb("⚠ Cannot fill MVR fields - login was not successful")
        
        if status_cb:
            status_cb("Done. Browser will stay open - you can close it manually when done.")
        # Keep browser open - the context manager will keep it alive
        # Browser will close when the function exits (when user closes the app or stops automation)
        # For now, add a long wait to keep browser open
        try:
            # Wait to keep browser open (user can close manually)
            # The browser stays open as long as this function is running
            if status_cb:
                status_cb("Browser will remain open. Close it manually when finished.")
            page.wait_for_timeout(3600000)  # Wait up to 1 hour (keeps browser open)
        except Exception as e:
            # If page closes or error occurs, that's okay - don't propagate
            # Common exceptions: TargetClosedError, TimeoutError, etc.
            if status_cb:
                error_str = str(e).lower()
                if "target closed" not in error_str and "timeout" not in error_str:
                    # Only log unexpected errors, don't show popup
                    status_cb(f"Browser closed or error: {str(e)[:50]}")
            pass

