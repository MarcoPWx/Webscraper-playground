from celery import shared_task, chain, group
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import logging
import time
import os
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

# Define rate limit: 1 request per 5 seconds
RATE_LIMIT = 5

def get_chrome_options():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.binary_location = os.environ.get("CHROME_BIN", "/usr/bin/google-chrome-stable")
    return chrome_options

@shared_task(name='example_task')
def example_task():
    return "Hello, this is an example task!"

@shared_task(name='scrape_all_pages')
def scrape_all_pages(base_url, max_pages=5):
    """Scrape multiple pages for item numbers and details."""
    all_item_info = []
    for page in range(1, max_pages + 1):
        page_url = f"{base_url}&page={page}"
        logging.info(f"Scraping page {page} - {page_url}")
        item_info = scrape_item_numbers(page_url)
        all_item_info.extend(item_info)
        logging.info(f"Extracted info: {item_info}")
        time.sleep(RATE_LIMIT)  # Rate limiting
    
    return all_item_info

@shared_task(name='scrape_item_numbers')
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def scrape_item_numbers(url):
    """Scrape item numbers from a given page."""
    logging.info(f"Scraping {url}...")

    chrome_options = get_chrome_options()
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get(url)

    time.sleep(2)  # Give some time for the page to load

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    item_info = []

    # Find all item entries
    item_entries = soup.find_all('div', class_='item-entry')

    for item in item_entries:
        status_container = item.find('div', class_='status-container')
        if status_container and 'ACTIVE' in status_container.get_text():
            short_name = item.find('div', class_='item-short-name').get_text(strip=True)
            item_number = short_name.split(" ")[2]
            item_date = short_name.split("from")[-1].strip()
            item_year = item_date.split('/')[-1]

            item_info.append({
                'item_number': item_number,
                'item_year': item_year,
            })

    driver.quit()
    return item_info

@shared_task(name='scrape_item_details')
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def scrape_item_details(item_number, item_year):
    """Scrape details for a given item number."""
    logging.info(f"Scraping details for item {item_number}...")

    url = f"https://www.example.com/item/{item_year}/{item_number}/xml"
    chrome_options = get_chrome_options()
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get(url)

    time.sleep(2)  # Give some time for the page to load    

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    details = {}

    # Extract details from the page
    details_container = soup.find('div', class_='details-container')
    if details_container:
        details['title'] = details_container.find('h1').get_text(strip=True)    

    driver.quit()
    return details

@shared_task(name='scrape_and_save_item_xml')
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def scrape_and_save_item_xml(item_number, item_year):
    """Scrape item XML and save it to a file."""
    url = f"https://www.example.com/api/document/{item_year}/{item_number}/xml"
    logging.info(f"Scraping XML for item {item_number}/{item_year} from {url}")

    chrome_options = get_chrome_options()
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        driver.get(url)
        time.sleep(2)  # Give some time for JavaScript to execute

        # Find the pre element containing the XML
        xml_element = driver.find_element_by_tag_name('pre')
        xml_content = xml_element.text

        # Create a directory to store XML files if it doesn't exist
        os.makedirs('item_xml_files', exist_ok=True)
        
        # Save XML content to a file
        filename = f"item_xml_files/ITEM_{item_number}_{item_year}.xml"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        
        logging.info(f"Saved XML for item {item_number} to {filename}")
        
        return {"xml_filename": filename}
    except Exception as e:
        logging.error(f"Failed to get XML for item {item_number}/{item_year}. Error: {str(e)}")
        return None
    finally:
        driver.quit()

@shared_task(name='run_full_scrape')
def run_full_scrape(base_url, max_pages=1000, chunk_size=10):
    """Run the full scraping process in parallel."""
    logging.info(f"Starting full scrape of {base_url} for {max_pages} pages")
    
    # Create groups of tasks
    task_groups = []
    for i in range(0, max_pages, chunk_size):
        start_page = i + 1
        end_page = min(i + chunk_size, max_pages)
        task_groups.append(scrape_page_range.s(base_url, start_page, end_page))
    
    # Execute all groups in parallel
    results = group(task_groups).apply_async()
    
    # Wait for all tasks to complete and collect results
    all_results = results.get()
    
    # Flatten the results
    all_item_info = [item for sublist in all_results for item in sublist]
    
    # Process each item number
    final_results = []
    for item in all_item_info:
        item_number = item['item_number']
        item_year = item['item_year']
        
        # Scrape details
        details = scrape_item_details(item_number, item_year)
        
        # Scrape and save XML
        xml_result = scrape_and_save_item_xml(item_number, item_year)
        
        final_results.append({
            'item_number': item_number,
            'item_year': item_year,
            'details': details,
            'xml_filename': xml_result['xml_filename'] if xml_result else None
        })
        
        time.sleep(RATE_LIMIT)  # Rate limiting
    
    logging.info(f"Completed full scrape. Processed {len(final_results)} item numbers.")
    return final_results

@shared_task(name='scrape_page_range')
def scrape_page_range(base_url, start_page, end_page):
    """Scrape a range of pages for item numbers and details."""
    all_item_info = []
    for page in range(start_page, end_page + 1):
        page_url = f"{base_url}&page={page}"
        logging.info(f"Scraping page {page} - {page_url}")
        item_info = scrape_item_numbers(page_url)
        all_item_info.extend(item_info)
        logging.info(f"Extracted info from page {page}: {item_info}")
        time.sleep(RATE_LIMIT)  # Rate limiting
    
    return all_item_info

@shared_task(name='scrape_ten_pages')
def scrape_ten_pages(base_url):
    """Scrape 10 pages and get XML for each item number found."""
    logging.info(f"Starting scrape of 10 pages from {base_url}")
    
    all_item_info = []
    for page in range(1, 11):
        page_url = f"{base_url}&page={page}"
        logging.info(f"Scraping page {page} - {page_url}")
        item_info = scrape_item_numbers(page_url)
        all_item_info.extend(item_info)
        logging.info(f"Extracted info from page {page}: {item_info}")
        time.sleep(RATE_LIMIT)  # Rate limiting
    
    results = []
    for item in all_item_info:
        item_number = item['item_number']
        item_year = item['item_year']
        
        # Get XML content
        xml_result = scrape_and_save_item_xml(item_number, item_year)
        
        if xml_result:
            results.append({
                'item_number': item_number,
                'item_year': item_year,
                'xml_filename': xml_result['xml_filename']
            })
        else:
            logging.warning(f"Failed to get XML for item {item_number}/{item_year}")
        
        time.sleep(RATE_LIMIT)  # Rate limiting
    
    logging.info(f"Completed scrape of 10 pages. Processed {len(results)} item numbers.")
    return results