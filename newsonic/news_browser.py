"""
news_browser.py

Uses Selenium to go to articles from news.google.com
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import atexit
import time

from listener import Listener


class NewsBrowser:
    def __init__(self):
        # Ensure media autoplays
        options = Options()
        options.add_argument('--autoplay-policy=no-user-gesture-required')

        # Create Selenium Chrome driver
        self.driver = webdriver.Chrome(chrome_options=options)
        atexit.register(self.close)
        self.articles = self.get_articles()

        print("!!!!!!!!!Ensure that the Selenium browser audio is being sent to Newsonsic!!!!!!!!!")

    def close(self):
        self.driver.close()

    def get_articles(self):
        # Navigate to news.google.com
        self.driver.get("https://news.google.com")
        return [e.get_attribute("href") for e in self.driver.find_elements_by_class_name("VDXfz")]

    def get_next_article(self):
        article_href = self.articles.pop(0)
        self.driver.get(article_href)
        print("Waiting 5s for page load...")
        time.sleep(5)


if __name__ == "__main__":
    b = NewsBrowser()
    l = Listener()
    b.get_next_article()

    def on_vad(timestamps, detections):
        if not True in detections:
            print("No audio, getting next article...")
            b.get_next_article()
            l.listen(10, callback=on_vad)
        else:
            l.extract_voice(timestamps, detections)
            print("Extracted voice.")


    l.listen(10, callback=on_vad)
