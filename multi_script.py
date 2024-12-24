import os
import random
import time
import logging
import threading
import itertools
from CloudflareBypasser import CloudflareBypasser
from DrissionPage import ChromiumPage, ChromiumOptions
from config import users, pushbullet_key
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cloudflare_bypass.log', mode='w')
    ]
)

def send_pushbullet_notification(api_key: str, body: str):
    """
    Sends a Pushbullet notification.

    :param api_key: Your Pushbullet API access token.
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

def get_unique_remote_debugging_port(port_generator) -> int:
    """
    Retrieves the next available remote debugging port.

    :param port_generator: An iterator that yields unique ports.
    :return: A unique remote debugging port number.
    """
    return next(port_generator)

def get_unique_user_data_dir(base_dir: str, user_email: str) -> str:
    """
    Generates a unique user data directory path for each user.

    :param base_dir: The base directory where user data directories are stored.
    :param user_email: The email of the user, used to name the directory uniquely.
    :return: Path to the unique user data directory.
    """
    sanitized_email = user_email.replace("@", "_at_").replace(".", "_")
    user_dir = os.path.join(base_dir, f"user_data_{sanitized_email}")
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

def get_chromium_options(browser_path: str, arguments: list, remote_debugging_port: int, user_data_dir: str) -> ChromiumOptions:
    """
    Configures and returns Chromium options.

    :param browser_path: Path to the Chromium browser executable.
    :param arguments: List of arguments for the Chromium browser.
    :param remote_debugging_port: Unique remote debugging port for this instance.
    :param user_data_dir: Unique user data directory for this instance.
    :return: Configured ChromiumOptions instance.
    """
    options = ChromiumOptions()
    options.set_argument(f"--remote-debugging-port={remote_debugging_port}")
    options.set_argument("--no-sandbox")
    options.set_argument("--disable-dev-shm-usage")
    options.set_argument('--auto-open-devtools-for-tabs')
    options.set_argument("--window-size=1200,800")
    options.set_argument(f"--user-data-dir={user_data_dir}")  # Ensure each instance has its own user data
    options.set_paths(browser_path=browser_path)
    for argument in arguments:
        options.set_argument(argument)
    return options

def buy_tickets(driver, email):
    """
    Attempts to purchase tickets for the given user.

    :param driver: The ChromiumPage driver instance.
    :param email: The user's email for logging purposes.
    """
    try:
        driver.get("https://billetterie.psg.fr/fr/acheter/billet-a-l-unite-rouge-et-bleu-paris-vs-manchester-city-2024-zd5w3rgn7obm/")
        logging.info(f"[{email}] Navigating to the PSG ticket page...")

        # Locate and click the "Achat rapide" link
        fast_buy_link = driver.ele("xpath://a[contains(@href, '/fr/acheter/billet-a-l-unite-rouge-et-bleu-paris-vs-manchester-city-2024-zd5w3rgn7obm/list')]")

        if fast_buy_link:
            fast_buy_link.click()
            logging.info(f"[{email}] Clicked on the 'Achat rapide' link.")
        else:
            logging.warning(f"[{email}] Could not find the 'Achat rapide' link.")
            return

        body = f"Ticket Purchase Attempt by {email}"
        send_pushbullet_notification(pushbullet_key, body)

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
                        logging.info(f"[{email}] Clicked the increment button once.")
                        increment_button.click()  # Click again
                        logging.info(f"[{email}] Clicked the increment button again.")
                        break
                    else:
                        logging.warning(f"[{email}] Could not find the increment button.")
                except Exception as e:
                    logging.error(f"[{email}] Error clicking button {i+1}: {e}")
        else:
            logging.warning(f"[{email}] No dropdown buttons found.")

        # Locate and click the "Ajouter au panier" button
        add_to_cart_button = driver.ele("xpath://button[span/span[text()='Ajouter au panier']]")

        if add_to_cart_button:
            add_to_cart_button.click()
            logging.info(f"[{email}] Clicked on the 'Ajouter au panier' button.")
        else:
            logging.warning(f"[{email}] Could not find the 'Ajouter au panier' button.")

        # Optionally, handle post-purchase steps or notifications here

    except Exception as e:
        logging.error(f"[{email}] An error occurred during ticket purchase: {e}")

def login_session(driver, email, password):
    """
    Handles a single login session in an isolated browser window.

    :param driver: The ChromiumPage driver instance.
    :param email: User's email.
    :param password: User's password.
    """
    # Handle cookies
    try:
        agree_button = driver.ele('@id:didomi-notice-agree-button')
        if agree_button:
            agree_button.click()
            logging.info(f"[{email}] Clicked on 'Agree and close' button.")
        else:
            logging.info(f"[{email}] 'Agree and close' button not found.")
    except Exception as e:
        logging.error(f"[{email}] Failed to locate or click 'Agree and close' button: {e}")

    # Enter email and password
    try:
        email_field = driver.ele('@id:user_login_identifier')
        if email_field:
            email_field.input(email)
        else:
            logging.warning(f"[{email}] Email field not found.")

        password_field = driver.ele('@id:user_login_password')
        if password_field:
            password_field.input(password)
        else:
            logging.warning(f"[{email}] Password field not found.")
        logging.info(f"[{email}] Entered email and password.")
    except Exception as e:
        logging.error(f"[{email}] Failed to enter email or password: {e}")

    # Click the "Me connecter" button using XPath
    try:
        login_button = driver.ele("xpath://button[@type='submit']//span[text()='Me connecter']", timeout=10)
        if login_button:
            login_button.click()
            logging.info(f"[{email}] Clicked on 'Me connecter' button.")
        else:
            logging.warning(f"[{email}] 'Me connecter' button not found.")
    except Exception as e:
        logging.error(f"[{email}] Failed to locate or click 'Me connecter' button: {e}")

def user_worker(user, browser_path, is_headless, arguments, port_generator, base_user_data_dir):
    """
    Handles the ticket purchasing process for a single user.

    :param user: A dictionary containing 'email' and 'password'.
    :param browser_path: Path to the Chromium browser executable.
    :param is_headless: Boolean indicating if the browser should run headlessly.
    :param arguments: List of arguments for the Chromium browser.
    :param port_generator: An iterator that yields unique remote debugging ports.
    :param base_user_data_dir: Base directory for user data directories.
    """
    email = user['email']
    # Assign a unique remote debugging port
    remote_debugging_port = get_unique_remote_debugging_port(port_generator)
    # Assign a unique user data directory
    user_data_dir = get_unique_user_data_dir(base_user_data_dir, email)

    # Configure Chromium options for this user
    options = get_chromium_options(browser_path, arguments, remote_debugging_port, user_data_dir)

    # Initialize the browser for this user
    driver = ChromiumPage(addr_or_opts=options)

    try:
        logging.info(f"[{email}] Navigating to the login page.")
        driver.get('https://auth.billetterie.psg.fr/fr/login')

        # Initialize Cloudflare bypasser
        cf_bypasser = CloudflareBypasser(driver)
        cf_bypasser.bypass()
        logging.info(f"[{email}] Cloudflare bypass completed.")

        # Perform login
        login_session(driver, user["email"], user["password"])
        logging.info(f"[{email}] Logged in successfully.")

        # Continuously attempt to buy tickets
        while True:
            buy_tickets(driver, email)
            sleep_time = random.randint(120, 180)
            logging.info(f"[{email}] Sleeping for {sleep_time} seconds.")
            time.sleep(sleep_time)

    except Exception as e:
        logging.error(f"[{email}] An error occurred: {e}")
    finally:
        logging.info(f"[{email}] Closing the browser.")
        driver.quit()

def main():
    # Determine if the browsers should run headlessly
    isHeadless = os.getenv('HEADLESS', 'false').lower() == 'true'

    # Handle virtual display if headless
    display = None
    if isHeadless:
        try:
            from pyvirtualdisplay import Display
            display = Display(visible=0, size=(1920, 1080))
            display.start()
            logging.info("Started virtual display for headless mode.")
        except ImportError:
            logging.error("pyvirtualdisplay is not installed. Install it or set HEADLESS=false.")
            return

    browser_path = os.getenv('CHROME_PATH', "/usr/bin/google-chrome")

    # Arguments to make the browser better for automation and less detectable.
    arguments = [
        "--no-first-run",
        "--force-color-profile=srgb",
        "--metrics-recording-only",
        "--password-store=basic",
        "--use-mock-keychain",
        "--export-tagged-pdf",
        "--no-default-browser-check",
        "--disable-background-mode",
        "--enable-features=NetworkService,NetworkServiceInProcess,LoadCryptoTokenExtension,PermuteTLSExtensions",
        "--disable-features=FlashDeprecationWarning,EnablePasswordsAccountStorage",
        "--deny-permission-prompts",
        "--disable-gpu",
        "--accept-lang=en-US",
    ]

    threads = []

    # Initialize a unique port generator starting from 9223 to avoid conflict with existing port 9222
    base_port = 9223
    port_generator = itertools.count(start=base_port)

    # Define a base directory for user data directories
    base_user_data_dir = os.path.abspath("user_data")
    os.makedirs(base_user_data_dir, exist_ok=True)

    # Start a separate thread for each user
    for user in users:
        thread = threading.Thread(
            target=user_worker,
            args=(user, browser_path, isHeadless, arguments, port_generator, base_user_data_dir),
            name=f"Thread-{user['email']}"
        )
        thread.start()
        threads.append(thread)
        logging.info(f"Started thread for user: {user['email']}")

    # Optionally, join threads if you want the main thread to wait for them
    for thread in threads:
        thread.join()
        logging.info(f"Thread {thread.name} has finished.")

    # Stop the virtual display if it was started
    if display:
        display.stop()
        logging.info("Stopped virtual display.")

if __name__ == '__main__':
    main()
