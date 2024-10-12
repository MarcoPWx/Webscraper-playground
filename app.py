from celery import Celery

app = Celery('WebScraper')
app.config_from_object('WebScraper.celeryconfig')

# Ensure all tasks are imported
app.autodiscover_tasks(['WebScraper.tasks'])

# Explicitly export the celery_app
celery_app = app

if __name__ == '__main__':
    app.start()
