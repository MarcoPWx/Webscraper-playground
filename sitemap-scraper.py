import requests
import xml.etree.ElementTree as ET
import json
import logging
import redis
from celery import Celery
from requests_cache import CachedSession

# Setup Celery
app = Celery('sitemap_scraper', broker='redis://redis:6379/0')

# Setup Redis and cache
cache = CachedSession('sitemap_cache', backend='redis', expire_after=3600)
r = redis.Redis(host='redis', port=6379, db=0)

# Set up logging
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@app.task
def fetch_sitemap(sitemap_url):
    """Fetch and parse the sitemap."""
    logging.info(f"Fetching sitemap: {sitemap_url}")
    response = cache.get(sitemap_url)
    
    if response.status_code == 200:
        logging.info("Sitemap fetched successfully.")
        return response.content
    else:
        logging.error(f"Failed to fetch sitemap. Status code: {response.status_code}")
        return None

def parse_sitemap(xml_content):
    """Parse sitemap XML and return list of URLs."""
    logging.info("Parsing sitemap XML...")
    root = ET.fromstring(xml_content)
    urls = []
    
    for url in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
        loc = url.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc').text
        urls.append(loc)
    
    logging.info(f"Found {len(urls)} URLs in the sitemap.")
    return urls

@app.task
def fetch_url_data(url):
    """Fetch the XML data of the URL."""
    xml_url = f"{url}/xml"
    logging.info(f"Fetching XML data from: {xml_url}")
    
    response = cache.get(xml_url)
    
    if response.status_code == 200:
        logging.info(f"Fetched XML for {url}")
        return response.content
    else:
        logging.error(f"Failed to fetch XML from {xml_url}. Status code: {response.status_code}")
        return None

def is_status_valid(xml_content):
    """Check if the status of the URL is 'Valid'."""
    root = ET.fromstring(xml_content)
    status = root.find('.//Status')
    
    if status is not None and status.text == 'Valid':
        logging.info("Status is 'Valid'.")
        return True
    else:
        logging.info("Status is not 'Valid'.")
        return False

def save_to_json(data, filename="valid_urls.json"):
    """Save the valid URL data to a JSON file."""
    logging.info(f"Saving data to {filename}")
    
    with open(filename, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)
    
    logging.info(f"Data saved successfully to {filename}")

@app.task
def scrape_sitemap(sitemap_url, limit=1):
    """Main scraping function to fetch sitemap, check URLs, and save valid data."""
    sitemap_content = fetch_sitemap(sitemap_url)
    
    if sitemap_content:
        urls = parse_sitemap(sitemap_content)
        
        valid_urls = []
        for idx, url in enumerate(urls):
            if idx >= limit:
                break  # Limiting the number of pages processed
            
            xml_content = fetch_url_data(url)
            
            if xml_content and is_status_valid(xml_content):
                valid_urls.append(url)  # Save the valid URL
        
        # Save valid URLs to a JSON file
        if valid_urls:
            save_to_json(valid_urls)
        else:
            logging.info("No valid URLs found.")
    else:
        logging.error("Could not retrieve sitemap.")

# Main execution point
if __name__ == "__main__":
    sitemap_url = ""
    
    # Limit the test to 1 page for now
    scrape_sitemap(sitemap_url, limit=1)
