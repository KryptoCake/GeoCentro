import os
import time
from selenium import webdriver
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

def run_task():
    """
    This task uses Selenium to download the full HTML content from the INETER seismology page
    and saves it to a local file, overwriting it each time.
    It uses webdriver-manager to automatically handle the chromedriver.
    """
    # Path to save the resulting HTML file
    output_html_path = os.path.join(os.path.dirname(__file__), '..', 'lista_de_sismos.html')
    url = 'https://webserver2.ineter.gob.ni/geofisica/sis/events/sismos.php'

    print(f"    - Starting Selenium task to download HTML from: {url}")

    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--window-size=1920x1080')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    driver = None
    try:
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        print("    - Chrome WebDriver started.")
        
        driver.get(url)
        
        # Wait a few seconds for any dynamic content to load
        time.sleep(5)
        
        print("    - Page loaded. Getting page source...")
        html_content = driver.page_source
        
        with open(output_html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        print(f"    - Success! HTML content saved to: {output_html_path}")

    except Exception as e:
        print(f"    [!] An error occurred during the Selenium task: {e}")
    finally:
        if driver:
            driver.quit()
            print("    - Chrome WebDriver closed.")
