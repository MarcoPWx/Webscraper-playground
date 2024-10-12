# Scalable WebScraper

This project is a scalable web scraper built with Celery, Redis, and Selenium. It's designed to scrape data from specified web pages, with support for parallel processing, robust error handling, and rate limiting.

## Project Structure

```
Scalable-WebScraper/
├── webscraper/
│   ├── __init__.py
│   └── app.py
├── docker-compose.yml
├── Dockerfile
├── dockerfile.flower
├── requirements.txt
└── README.md
```

## Prerequisites

- Docker
- Docker Compose

## Setup and Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/Scalable-WebScraper.git
   cd Scalable-WebScraper
   ```

2. Build and start the Docker containers or choose to scale:
   ```
   docker-compose up --build
   docker-compose up --scale scraper=3
   ```

This command will start three services:
- Redis: Message broker and result backend
- Scraper: Celery worker running the scraping tasks
- Flower: Web-based tool for monitoring Celery tasks

## Usage

### Running Scraper Tasks

To run scraper tasks, you need to execute commands inside the Scraper container. Here's how:

1. Find the container ID of the Scraper service:
   ```
   docker ps
   ```

2. Open a bash shell in the Scraper container:
   ```
   docker exec -it <container_id> bash
   ```

3. Once inside the container, start a Python shell:
   ```
   python
   ```

4. In the Python shell, import the Celery app:
   ```python
   from WebScraper.app import celery_app
   ```

This will allow you to start scraping tasks asynchronously. You can monitor their progress in the Flower dashboard.

### Available Tasks

- `example_task`: A simple example task that returns a test message.
- `scrape_all_pages`: Scrapes multiple pages of a website for specific data.
- `scrape_page_data`: Scrapes data from a specific page URL.
- `scrape_item_details`: Scrapes details for a specific item.
- `scrape_and_save_data`: Scrapes data and saves it to a local file.
- `get_item_data`: Retrieves data from an API for a specific item.
- `run_full_scrape`: Runs a full scrape of multiple pages in parallel and processes found items.
- `scrape_page_range`: Scrapes a specific range of pages for data.
- `test_single_page_scrape`: Scrapes the first page and retrieves data for the first item found.
- `scrape_multiple_pages`: Scrapes a set number of pages and retrieves their data.

### Using send_task

You can use `send_task` to queue tasks:

```python
from WebScraper.app import celery_app

# To run the tasks
celery_app.send_task('scrape_all_pages', args=['https://example.com/data', 5])
```

This method will queue the tasks for execution by Celery workers.

### Scaling Celery Workers

To scale the number of Celery workers:

1. In your terminal, use the following command:
   ```
   docker-compose up -d --scale scraper=3
   ```
   This will start 3 instances of the scraper service, each running a Celery worker.

2. You can adjust the number (3 in this example) to any value based on your needs and system resources.

3. To scale down, use a lower number:
   ```
   docker-compose up -d --scale scraper=1
   ```

4. You can verify the number of running workers in the Flower dashboard or by running:
   ```
   docker-compose ps
   ```

Scaling workers allows for parallel processing of tasks, potentially increasing the overall scraping speed. However, be mindful of rate limiting and the target website's terms of service when scaling up.

## Rate Limiting and Error Handling

This scraper implements several mechanisms to ensure responsible and robust scraping:

### Rate Limiting

To avoid overwhelming the target website and to comply with ethical scraping practices, the scraper implements rate limiting:

1. **Global Rate Limit**: The scraper enforces a global rate limit across all workers. This is configured in the `config.py` file:

   ```python
   RATE_LIMIT = "10/m"  # 10 requests per minute
   ```

2. **Per-Task Rate Limit**: Individual tasks can have their own rate limits. For example:

   ```python
   @celery.task(rate_limit="2/m")
   def scrape_single_page(url):
       # ...
   ```

### Backoff Mechanism

To handle temporary errors and avoid getting blocked, the scraper uses an exponential backoff strategy:

1. The `@backoff.on_exception` decorator is applied to functions that make requests:

   ```python
   @backoff.on_exception(backoff.expo,
                         (requests.exceptions.RequestException, selenium.common.exceptions.WebDriverException),
                         max_tries=5)
   def make_request(url):
       # ...
   ```

2. This will retry the request with increasing delays between attempts, up to a maximum number of tries.

### Error Handling

The scraper includes comprehensive error handling to manage various scenarios:

1. **Network Errors**: Handled by the backoff mechanism and retries.
2. **Parsing Errors**: Logged and skipped to allow continued operation.
3. **Authentication Errors**: Trigger an immediate stop and alert.

### Logging

Detailed logs are maintained to track the scraper's operation:

1. **Info Logs**: Record successful operations and general flow.
2. **Warning Logs**: Note potential issues that don't stop execution.
3. **Error Logs**: Document failures and exceptions.

Logs can be viewed in the Docker container:

```bash
docker exec -it scalable_webscraper_scraper_1 cat /app/logs/scraper.log
```

### Monitoring and Adjusting

1. Use the Flower dashboard to monitor task execution and identify bottlenecks.
2. Adjust rate limits and backoff settings in `config.py` based on observed performance and target website behavior.
3. Regularly review logs to ensure the scraper operates within acceptable parameters.

Remember to always respect the target website's terms of service and robots.txt file. Adjust your scraping behavior accordingly to maintain ethical and responsible web scraping practices.

## Contributing

Please read CONTRIBUTING.md for details on our code of conduct, and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the LICENSE.md file for details
