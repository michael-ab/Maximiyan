import os
import random
import time
import logging
from CloudflareBypasser import CloudflareBypasser
from DrissionPage import ChromiumPage, ChromiumOptions
from config import users, pushbullet_key
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cloudflare_bypass.log', mode='w')
    ]
)

def send_pushbullet_notification(api_key: str, body: str):
    """
    Sends a Pushbullet notification.

    :param api_key: Your Pushbullet API access token.
    :param title: Title of the notification.
    :param body: Body content of the notification.
    """
    try:
        url = "https://api.pushbullet.com/v2/pushes"
        headers = {
            "Access-Token": api_key,
            "Content-Type": "application/json"
        }
        data = {
            "type": "note",
            "body": body
        }
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            logging.info("Success: Pushbullet notification sent.")
        else:
            logging.error(f"Failed to send Pushbullet notification. Status Code: {response.status_code}, Response: {response.text}")
    except Exception as e:
        logging.error(f"Exception occurred while sending Pushbullet notification: {e}")

def get_chromium_options(browser_path: str, arguments: list) -> ChromiumOptions:
    """
    Configures and returns Chromium options.

    :param browser_path: Path to the Chromium browser executable.
    :param arguments: List of arguments for the Chromium browser.
    :return: Configured ChromiumOptions instance.
    """
    options = ChromiumOptions()
    options.set_argument("--remote-debugging-port=9222")
    options.set_argument("--no-sandbox")
    options.set_argument("--disable-dev-shm-usage")
    options.set_argument('--auto-open-devtools-for-tabs', 'true')
    options.set_argument("--window-size=1200,1000")
    options.set_paths(browser_path=browser_path)
    for argument in arguments:
        options.set_argument(argument)
    return options

def buy_tickets(driver):
    # Navigate to the PSG ticket purchase page
    driver.get("https://billetterie.psg.fr/fr/acheter/billet-a-l-unite-rouge-et-bleu-paris-vs-manchester-city-2024-zd5w3rgn7obm/")
    print("Navigating to the PSG ticket page...")

    # Locate and click the "Achat rapide" link
    fast_buy_link = driver.ele("xpath://a[contains(@href, '/fr/acheter/billet-a-l-unite-rouge-et-bleu-paris-vs-manchester-city-2024-zd5w3rgn7obm/list')]")
    body = "Ticket Purchase Successful"
    send_pushbullet_notification(pushbullet_key, body)
    if fast_buy_link:
        fast_buy_link.click()
        print("Clicked on the 'Achat rapide' link.")
    else:
        print("Could not find the 'Achat rapide' link.")
        return

    # Locate all the buttons with the class 'dropdownArrows' and click each one
    buttons = driver.eles("xpath://button[contains(@class, 'dropdownArrows')]")
    if buttons:
        for i, button in enumerate(buttons):
            try:
                button.click()
                # Locate the first button with class 'qtyButtonIncrement' and click it twice
                increment_button = driver.ele("xpath://button[contains(@class, 'qtyButtonIncrement')]")
                if increment_button:
                    increment_button.click()  # Click once
                    print("Clicked the increment button once.")
                    increment_button.click()  # Click again
                    print("Clicked the increment button again.")
                    break
                else:
                    print("Could not find the increment button.")
            except Exception as e:
                print(f"Error clicking button {i+1}: {e}")
    else:
        print("No buttons found.")

    # Locate and click the "Ajouter au panier" button
    add_to_cart_button = driver.ele("xpath://button[span/span[text()='Ajouter au panier']]")

    if add_to_cart_button:
        add_to_cart_button.click()
        print("Clicked on the 'Ajouter au panier' button.")
    else:
        print("Could not find the 'Ajouter au panier' button.")

    # Wait for dynamic content to load
    subject = "Ticket Purchase Successful"
    body = f"User {report_email} has successfully completed the ticket purchase."
    send_email(subject, body)
    time.sleep(20000)

def login_session(driver, email, password):
    """
    Handles a single login session in an isolated browser window.
    """
    # Handle cookies
    try:
        agree_button = driver.ele('@id:didomi-notice-agree-button')
        if agree_button:
            agree_button.click()
            print(f"[{email}] Clicked on 'Agree and close' button.")
        else:
            print(f"[{email}] 'Agree and close' button not found.")
    except Exception as e:
        print(f"[{email}] Failed to locate or click 'Agree and close' button: {e}")

    # Enter email and password
    try:
        email_field = driver.ele('@id:user_login_identifier')
        if email_field:
            email_field.input(email)

        password_field = driver.ele('@id:user_login_password')
        if password_field:
            password_field.input(password)
        print(f"[{email}] Entered email and password.")
    except Exception as e:
        print(f"[{email}] Failed to enter email or password: {e}")

    # Click the "Me connecter" button using XPath
    try:
        login_button = driver.ele("xpath://button[@type='submit']//span[text()='Me connecter']", timeout=10)
        if login_button:
            login_button.click()
            print(f"[{email}] Clicked on 'Me connecter' button.")
        else:
            print(f"[{email}] 'Me connecter' button not found.")
    except Exception as e:
        print(f"[{email}] Failed to locate or click 'Me connecter' button: {e}")

def main():
    # Chromium Browser Path
    isHeadless = os.getenv('HEADLESS', 'false').lower() == 'true'

    if isHeadless:
        from pyvirtualdisplay import Display

        display = Display(visible=0, size=(1920, 1080))
        display.start()

    browser_path = os.getenv('CHROME_PATH', "/usr/bin/google-chrome")

    # Arguments to make the browser better for automation and less detectable.
    arguments = [
        "-no-first-run",
        "-force-color-profile=srgb",
        "-metrics-recording-only",
        "-password-store=basic",
        "-use-mock-keychain",
        "-export-tagged-pdf",
        "-no-default-browser-check",
        "-disable-background-mode",
        "-enable-features=NetworkService,NetworkServiceInProcess,LoadCryptoTokenExtension,PermuteTLSExtensions",
        "-disable-features=FlashDeprecationWarning,EnablePasswordsAccountStorage",
        "-deny-permission-prompts",
        "-disable-gpu",
        "-accept-lang=en-US",
    ]

    options = get_chromium_options(browser_path, arguments)

    # Initialize the browser
    driver = ChromiumPage(addr_or_opts=options)
    try:
        logging.info('Navigating to the demo page.')
        driver.get('https://auth.billetterie.psg.fr/fr/login')

        # Where the bypass starts
        logging.info('Starting Cloudflare bypass.')
        cf_bypasser = CloudflareBypasser(driver)

        cf_bypasser.bypass()

        for user in users:
            login_session(driver, user["email"], user["password"])
            while True:
                buy_tickets(driver)
                time.sleep(random.randint(2,4))

    except Exception as e:
        logging.error("An error occurred: %s", str(e))
    finally:
        logging.info('Closing the browser.')
        driver.quit()
        if isHeadless:
            display.stop()

if __name__ == '__main__':
    main()
