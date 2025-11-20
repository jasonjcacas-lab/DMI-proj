"""
Example script demonstrating the use of legacy_form_helpers for MVR automation.
This script shows how to use the helper functions to interact with legacy web forms.
"""

from playwright.sync_api import sync_playwright
from legacy_form_helpers import (
    set_select_dropdown_value,
    fill_text_input,
    click_submit_button,
    wait_for_element_ready
)


def run_mvr_example():
    """
    Main function that demonstrates the MVR automation flow.
    """
    with sync_playwright() as p:
        # Launch Chromium browser (not headless so you can see what's happening)
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # Navigate to the MVR portal
        # NOTE: Replace with your actual login URL
        login_url = "https://www.webmvr.com/login"  # Placeholder - update with actual URL
        page.goto(login_url)
        
        # ============================================
        # LOGIN STEPS (placeholder - implement your login logic here)
        # ============================================
        # Example:
        # fill_text_input(page, 'input[name="accountId"]', 'your_account_id')
        # fill_text_input(page, 'input[name="userId"]', 'your_user_id')
        # fill_text_input(page, 'input[name="password"]', 'your_password')
        # click_submit_button(page, 'button[type="submit"]')
        # page.wait_for_url("**/NewOrderMasterPage.jsp**")
        
        # Navigate to the MVR input page
        mvr_page_url = "https://www.webmvr.com/neworder/NewOrderMasterPage.jsp?Id=new"
        page.goto(mvr_page_url)
        
        # Wait for the page to be ready
        print("Waiting for page to load...")
        wait_for_element_ready(page, "#ddComboState", timeout=10000)
        print("Page ready!")
        
        # ============================================
        # STEP 1: Set the state dropdown value
        # ============================================
        print("\nStep 1: Setting state dropdown...")
        state_code = "TX"  # Example: Texas
        success = set_select_dropdown_value(page, "ddComboState", state_code)
        if success:
            print(f"✓ State dropdown set to: {state_code}")
        else:
            print(f"✗ Failed to set state dropdown")
            return
        
        # ============================================
        # STEP 2: Fill in driver information fields
        # ============================================
        print("\nStep 2: Filling driver information...")
        
        # Fill license number
        fill_text_input(page, 'input[name="license"]', "12345678")
        print("✓ License number filled")
        
        # Fill last name
        fill_text_input(page, 'input[name="lastName"]', "Smith")
        print("✓ Last name filled")
        
        # Fill first name
        fill_text_input(page, 'input[name="firstName"]', "John")
        print("✓ First name filled")
        
        # Fill date of birth (format: MM/DD/YYYY)
        fill_text_input(page, 'input[name="dob"]', "01/15/1980")
        print("✓ Date of birth filled")
        
        # ============================================
        # STEP 3: Click the submit button
        # ============================================
        print("\nStep 3: Clicking submit button...")
        # Example selector - adjust based on your page's actual button
        submit_selector = 'input[type="submit"][value="Run MVR"]'
        
        # Try alternative selectors if the first doesn't work
        alternative_selectors = [
            'input[type="submit"]',
            'button[type="submit"]',
            'input[value*="Run"]',
            'button:has-text("Run MVR")'
        ]
        
        clicked = False
        for sel in [submit_selector] + alternative_selectors:
            try:
                if click_submit_button(page, sel, no_wait_after=True):
                    print(f"✓ Submit button clicked (using selector: {sel})")
                    clicked = True
                    break
            except:
                continue
        
        if not clicked:
            print("✗ Could not find or click submit button")
        
        # ============================================
        # Keep browser open for a moment to see results
        # ============================================
        print("\nWaiting 5 seconds before closing browser...")
        page.wait_for_timeout(5000)
        
        # Close the browser
        browser.close()
        print("\nBrowser closed. Automation complete!")


if __name__ == "__main__":
    run_mvr_example()

