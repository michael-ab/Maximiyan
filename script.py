import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import requests
from fake_useragent import UserAgent
from config import API_KEY, users

def solve_turnstile_captcha(sitekey, page_url, action, data, pagedata):
    """
    Solve Turnstile CAPTCHA using 2Captcha API.
    """
    try:
        print("Sending Turnstile CAPTCHA to 2Captcha...")
        create_task_payload = {
            "clientKey": API_KEY,
            "task": {
                "type": "TurnstileTaskProxyless",
                "websiteURL": page_url,
                "websiteKey": sitekey,
                "action": action,
                "data": data,
                "pagedata": pagedata,
                "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            },
        }
        response = requests.post("https://api.2captcha.com/createTask", json=create_task_payload)
        response_data = response.json()

        if response_data.get("errorId") == 0:
            task_id = response_data.get("taskId")
            print(f"CAPTCHA task created successfully. Task ID: {task_id}")
        else:
            error_message = response_data.get("errorDescription", "Unknown error")
            raise Exception(f"Error creating CAPTCHA task: {error_message}")

        # Poll for the solution
        solution_payload = {"clientKey": API_KEY, "taskId": task_id}
        start_time = time.time()

        timeout = 120  # seconds
        while time.time() - start_time < timeout:
            time.sleep(5)
            solution_response = requests.post("https://api.2captcha.com/getTaskResult", json=solution_payload)
            solution_data = solution_response.json()

            if solution_data.get("errorId") == 0:
                if solution_data.get("status") == "ready":
                    print("CAPTCHA Solved Successfully!")
                    return solution_data.get("solution", {}).get("token")
            else:
                error_message = solution_data.get("errorDescription", "Unknown error")
                raise Exception(f"Error fetching CAPTCHA solution: {error_message}")

            print("Solution not ready yet. Retrying...")

        raise TimeoutError("CAPTCHA solving timed out.")

    except Exception as e:
        print(f"Error solving CAPTCHA: {e}")
        return None

def login_session(email, password):
    """
    Handles a single login session in an isolated browser window.
    """
    driver = None
    try:
        # Use undetected-chromedriver
        options = uc.ChromeOptions()
        ua = UserAgent()
        user_agent = ua.random
        options.add_argument(f"user-agent={user_agent}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-infobars")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-extensions")

        # Set proxy
        # options.add_argument(f"--proxy-server={PROXY}")

        driver = uc.Chrome(options=options)
        url = "https://auth.billetterie.psg.fr/fr/login"

        # Open the login page
        driver.get(url)

        # Inject JavaScript to capture Turnstile parameters
        injection_script = """
        const i = setInterval(() => {
            if (window.turnstile) {
                clearInterval(i);
                window.turnstile.render = (a, b) => {
                    const params = {
                        action: b.action,
                        data: b.cData,
                        pagedata: b.chlPageData
                    };
                    console.log("Turnstile Parameters:", JSON.stringify(params));
                    window.extractedTurnstileParams = params; // Expose params globally
                    return "foo";
                };
            }
        }, 10);
        """
        driver.execute_script(injection_script)

        # Wait for Turnstile parameters to be captured
        time.sleep(5)

        params = driver.execute_script("return window.extractedTurnstileParams || null;")

        if not params:
            print(f"[{email}] Failed to extract Turnstile parameters.")
            return
        print(f"[{email}] Extracted Turnstile Parameters: {params}")

        # Solve the CAPTCHA using extracted parameters
        captcha_token = solve_turnstile_captcha(
            sitekey="0x4AAAAAAADnPIDROrmt1Wwj",
            page_url=url,
            action=params.get("action"),
            data=params.get("data"),
            pagedata=params.get("pagedata"),
        )

        if captcha_token:
            # Inject the CAPTCHA solution into the hidden input field
            try:
                captcha_element = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.ID, "cf-turnstile-response"))
                )
                driver.execute_script(
                    f'document.getElementById("cf-turnstile-response").value="{captcha_token}";'
                )
                print(f"[{email}] Successfully solved CAPTCHA.")
            except Exception as e:
                print(f"[{email}] Failed to inject CAPTCHA token: {e}")

        # Handle cookies
        try:
            agree_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.ID, "didomi-notice-agree-button"))
            )
            agree_button.click()
            print(f"[{email}] Clicked on 'Agree and close' button.")
        except Exception as e:
            print(f"[{email}] Failed to locate or click 'Agree and close' button: {e}")

        # Enter email and password
        try:
            email_field = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "user_login_identifier"))
            )
            email_field.send_keys(email)

            password_field = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "user_login_password"))
            )
            password_field.send_keys(password)
            print(f"[{email}] Entered email and password.")
        except Exception as e:
            print(f"[{email}] Failed to enter email or password: {e}")

        # Click the "Me connecter" button
        try:
            login_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[@type='submit' and .//span[text()='Me connecter']]")
                )
            )
            login_button.click()
            print(f"[{email}] Clicked on 'Me connecter' button.")
        except Exception as e:
            print(f"[{email}] Failed to locate or click 'Me connecter' button: {e}")

        # Optional wait to observe actions
        time.sleep(5)

        # Take a screenshot for debugging
        driver.save_screenshot(f"debug_screenshot_{email}.png")
        print(f"[{email}] Screenshot saved.")

    except Exception as e:
        print(f"[{email}] Encountered an error: {e}")

    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    for user in users:
        login_session(user["email"], user["password"])
    print("All sessions completed.")
