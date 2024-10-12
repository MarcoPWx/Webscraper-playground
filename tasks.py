from celery import Celery
from .sitemap_scraper import run_sitemap_scraper
# from .js_scraper import run_js_scraper (if needed for JS scraper)

app = Celery('WebScraper', broker='redis://redis:6379/0')

@app.task
def scrape_sitemap():
    """Task to run the sitemap-based scraper."""
    return run_sitemap_scraper()

# Add the JavaScript-based scraper task if needed
# @app.task
# def scrape_js():
#     """Task to run the JavaScript-based scraper."""
#     return run_js_scraper()
