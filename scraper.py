import time
import os
import traceback
import pandas as pd
import logging
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(message)s')


class LeetCodeScraper:
    EXCEL_FILE_NAME = 'LeetCode.xlsx'
    SHEET_NAME = 'All Problems'
    SLEEP_TIME = 5

    def __init__(self, site_url='https://leetcode.com/problemset/all/'):
        self.site_url = site_url
        self.data = {
            'Question Name': [],
            'Question Url': [],
            'Premium': [],
            'Question Difficulty': [],
            'Question Topics': [],
            'Question Description': [],
            'Question Examples Count': [],
            'Question Examples': []
        }

    def save_to_excel(self):
        """Saves the collected data to an Excel file."""
        df = pd.DataFrame(self.data)
        if os.path.exists(self.EXCEL_FILE_NAME):
            logging.warning("Appending to Excel sheet")
            with pd.ExcelWriter(self.EXCEL_FILE_NAME, engine='openpyxl', mode='a', if_sheet_exists="overlay") as writer:
                df.to_excel(writer, sheet_name=self.SHEET_NAME, index=False, header=False,startrow=writer.sheets[self.SHEET_NAME].max_row)
        else:
            logging.warning("Creating Excel sheet")
            with pd.ExcelWriter(self.EXCEL_FILE_NAME, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name=self.SHEET_NAME, index=False)

        for key in self.data:
            self.data[key].clear()
        logging.warning("Finished writing to Excel sheet.")

    def open_browser(self, url):
        """Initializes and returns a Selenium web driver for the given url."""
        logging.warning(f"Opening browser at {url}")
        options = webdriver.ChromeOptions()
        options.add_argument('--incognito')
        options.add_argument('--disable-search-engine-choice-screen')
        options.add_argument("--log-level=3")
        # options.add_argument('--headless')

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(url)
        return driver


    def close_browser(self, driver):
        """Closes the web driver instance."""
        logging.warning("Closing the browser")
        driver.quit()

    def fetch_question_details(self, question_name, question_url):
        """Fetches and stores details of a question by scraping its page."""
        logging.warning(f"Fetching question details for: {question_name}")
        browser = self.open_browser(question_url)
        time.sleep(self.SLEEP_TIME)
        try:
            page_source = browser.page_source
            question_title = question_name.split(". ", 1)[1].strip() + " - LeetCode"
            question_title = ' '.join(question_title.split())
            WebDriverWait(browser, 10).until(EC.title_contains(question_title))
            logging.warning(f"Problem : {question_name}")
            soup = BeautifulSoup(page_source, 'html.parser')
            logging.warning(f"Parsing Question data:")

            description_block = soup.find('div', class_='elfjS')
            if description_block:
                self.data['Premium'].append("No")
                self.data['Question Description'].append(self._extract_description(description_block))
                self.data['Question Examples'].append(self._extract_examples(description_block))
                self.data['Question Examples Count'].append(len(self._extract_examples(description_block)))
                self.data['Question Topics'].append(self._extract_topics(soup))
                logging.warning(f"Fetched question details for : {question_name}")
            else:
                logging.warning(f"{question_name} is a premium question")
                self.data['Premium'].append("Yes")
                self.data['Question Description'].append("")
                self.data['Question Examples Count'].append(0)
                self.data['Question Examples'].append([])
                self.data['Question Topics'].append([])

        except Exception as e:
            logging.error(f"Error fetching details for {question_name}: {e}")
        finally:
            self.close_browser(browser)

    def _extract_description(self, description_block):
        """Extracts and returns the question description."""
        items = description_block.find_all(recursive=False)
        description = "".join(str(item.text) for item in items if "<img" not in item.contents)
        return description.split("Example 1:", 1)[0]

    def _extract_examples(self, description_block):
        """Extracts and returns example input-output pairs."""
        question_examples = description_block.find_all('div')
        examples = [example.text for example in question_examples if 'Input' in example.text]
        if len(examples) == 0:
            question_examples = description_block.find_all('pre')
            examples = [example.text for example in question_examples if 'Input' in example.text]
        logging.warning(f"Total {len(examples)} example IO pairs fetched")
        return examples

    def _extract_topics(self, soup):
        """Extracts and returns related topics of the question."""
        related_topics_block = soup.find('div', class_='mt-2 flex flex-wrap gap-1 pl-7')
        topics = [topic.text for topic in related_topics_block.find_all('a')] if related_topics_block else []
        return topics

    def fetch_page_data(self, page_url):
        """Fetches questions from a specific page and stores the data."""
        logging.warning(f"Fetching page data from: {page_url}")
        browser = self.open_browser(page_url)
        time.sleep(self.SLEEP_TIME)

        try:
            WebDriverWait(browser, 10).until(EC.title_contains("Problems - LeetCode"))
            logging.warning(f"title is: {browser.title}")
            soup = BeautifulSoup(browser.page_source, 'html.parser')
            logging.warning("Parsing data: ")
            question_block = soup.find_all('div', role='rowgroup')[2]
            questions = question_block.find_all('div', role='row')

            for question in questions:
                row = question.find_all('div', role='cell')
                question_name = row[1].find('a').text
                question_url = 'https://leetcode.com' + row[1].find('a')['href']
                question_difficulty = row[4].find('span').text

                self.data['Question Name'].append(question_name if question_name else "")
                self.data['Question Url'].append(question_url if question_url else "")
                self.data['Question Difficulty'].append(question_difficulty if question_difficulty else "")
                self.fetch_question_details(question_name, question_url)
                self.save_to_excel()

            logging.warning(f"Fetched all questions in the page: {page_url}")
        except Exception as e:
            logging.error(f"Error fetching page data: {e}")
        finally:
            self.close_browser(browser)

    def get_all_pages(self):
        """Fetches data from all pages with questions on LeetCode."""
        try:
            url = self.site_url
            browser = self.open_browser(url)
            time.sleep(self.SLEEP_TIME)

            WebDriverWait(browser, 10).until(EC.title_contains("Problems - LeetCode"))
            soup = BeautifulSoup(browser.page_source, 'html.parser')
            total_pages = int(soup.find_all('button', class_="flex items-center justify-center px-3 h-8 rounded select-none focus:outline-none bg-fill-3 dark:bg-dark-fill-3 text-label-2 dark:text-dark-label-2 hover:bg-fill-2 dark:hover:bg-dark-fill-2")[-2].text)
            self.close_browser(browser)

            for page in range(1, total_pages + 1):
                logging.warning(f"Fetching Page : {page}")
                page_url = f"{self.site_url}?page={page}"
                self.fetch_page_data(page_url)

            logging.warning("Completed fetching data from all pages")

        except Exception as e:
            logging.error("An error occurred while fetching all pages")
            traceback.print_exc()


if __name__ == "__main__":
    scraper = LeetCodeScraper()
    scraper.get_all_pages()
