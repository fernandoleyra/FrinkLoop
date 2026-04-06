"""
Scraper project — starter scaffold.
Agents will implement the modules below based on the BRIEF.
"""

from scraper.crawler import Crawler
from scraper.extractor import Extractor
from scraper.pipeline import Pipeline


def main():
    crawler = Crawler()
    extractor = Extractor()
    pipeline = Pipeline(crawler=crawler, extractor=extractor)

    # Entry point — agents will implement the logic
    pipeline.run()


if __name__ == "__main__":
    main()
