from bs4 import BeautifulSoup
import time
import os.path
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

siteUrl = 'https://leetcode.com/problemset/all/' #LeetCode url to scrape
questionNameList = []
questionUrlList = []
questionDifficultyList = []
questionExampleList = []
questionRelatedTopics = []
questionDescriptionList = []
premium = []

def xcelSheet():
    """
    This function saves the fetched data to a data file.
    """
    excelFileName = 'LeetCode.xlsx' #Scraped data path
    sheetName = 'All Problems'

    df = pd.DataFrame({
        'Question Name': questionNameList,
        'Question Url': questionUrlList,
        'Premium' : premium,
        'Question Difficulty': questionDifficultyList,
        'Question Topics' : questionRelatedTopics,
        'Question Description': questionDescriptionList,
        'Question Examples' : questionExampleList
    })

    if os.path.exists(excelFileName):
        print("Appending to Excel sheet:")
        reader = pd.read_excel(excelFileName)
        writer = pd.ExcelWriter(excelFileName, engine='openpyxl', mode='a', if_sheet_exists="overlay")
        df.to_excel(writer, sheet_name= sheetName, index=False, header=False, startrow=len(reader) + 1)

    else:
        print("Creating Excel sheet:")
        writer = pd.ExcelWriter(excelFileName, engine='xlsxwriter')
        df.to_excel(writer, sheet_name= sheetName, index=False)

    writer.close()

    questionNameList.clear()
    questionUrlList.clear()
    questionDifficultyList.clear()
    questionExampleList.clear()
    questionRelatedTopics.clear()
    questionDescriptionList.clear()
    premium.clear()
    
    print("Finished writing to Excel sheet.")


def openBrowser(url):
    """
        This function opens the browser for the given url.

        :param url: Url to open
        :return: webdriver object
    """
    print("Opening the browser at ", url)
    options = webdriver.ChromeOptions()
    options.add_argument('--incognito')
    options.add_argument('--disable-search-engine-choice-screen')
    options.add_argument("--log-level=3")   
    #options.add_argument('--headless')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()),
                              options=options)
    driver.get(url)
    return driver


def closeBrowser(driver):
    """
        This function closes the browser.

        :param driver: driver to close
    """
    print("Closing the browser")
    driver.close()


def fetchQuestionDetails(questionName, questionUrl):
    """
        This function fetches the details of a question given the question name and its url.
        
        :param questionName: The question name to be scraped
        :param questionUrl: The url for the question to be scraped
    """
    sleepTime = 5
    print("Fetching Description details: ", questionUrl)
    browser2 = openBrowser(questionUrl)
    time.sleep(sleepTime)
    pageSource = browser2.page_source
    questionTitle = questionName.split(". ", 1)[1].strip() + " - LeetCode"
    questionTitle = ' '.join(questionTitle.split())

    WebDriverWait(browser2, 10).until(EC.title_contains(questionTitle))  # The webpage takes very long to load. Hence, we wait until some text i.e. the title loads.
    print(f"Problem : {questionName}")
        
    soup = BeautifulSoup(pageSource, 'html.parser')
    if (browser2.title == questionTitle):
        print("Parsing Question data:\n")
        descriptionBlock = soup.find('div', class_='elfjS')  # particular to our use case
        if descriptionBlock is not None:
            premium.append("No")

            #Fetching the question description
            items = descriptionBlock.find_all(recursive = False)
            description = ""
            for item in items:
                if "<img" not in item.contents:
                    description = description + str(item.text) 

            description = description.split("Example 1:", 1)[0]
            questionDescriptionList.append(description)
            
            #Fetching the I/O pairs
            questionExamples = descriptionBlock.find_all('pre') or descriptionBlock.find_all('div')
            print(f"Total {questionExamples.__len__()} example IO pairs fetched ")
            topicsList = []
            questionList = []
            for example in questionExamples:
                if 'Input' in example.text:
                    questionList.append(example.text)
            questionExampleList.append(questionList)
            
            #Fetching the related topics
            relatedTopicsBlock = soup.find('div', class_='mt-2 flex flex-wrap gap-1 pl-7')
            if relatedTopicsBlock is not None:
                relatedTopics = relatedTopicsBlock.find_all('a')
                for topic in relatedTopics:
                    topicsList.append(topic.text)
                questionRelatedTopics.append(topicsList)
            else:
                questionRelatedTopics.append([])
            print("Fetched question details for : ", questionName)

        else:
            premium.append("Yes")
            questionDescriptionList.append("")
            questionExampleList.append([])
            questionRelatedTopics.append([])

    else:
        print("Page does not exist or connection Failed, status code: ",
              soup.status_code)
    
    closeBrowser(browser2)
    return


def fetchPageData(pageUrl):
    """
        This function fetches the all question names and creates their urls for the given page.
        
        :param pageUrl: The paginated link containing questions
    """

    sleepTime = 10
    browser = openBrowser(pageUrl)
    time.sleep(sleepTime)
    pageSource = browser.page_source
    WebDriverWait(browser, 10).until(EC.title_contains("Problems - LeetCode"))  # The webpage takes very long to load. Hence, we wait until some text i.e. the title loads.
    print(f"title is: {browser.title}")

    soup = BeautifulSoup(pageSource, 'html.parser')
    if (browser.title == "Problems - LeetCode"):
        print("Parsing data: \n")
        questionBlock = soup.find_all('div', role='rowgroup')[2]
        questionList = questionBlock.find_all('div', role='row')
        print(len(questionBlock))
        for question in questionList:
            row = question.find_all('div', role='cell')
            questionName = row[1].find('a').text
            questionUrl = row[1].find('a')['href']
            questionUrl = 'https://leetcode.com' + questionUrl
            
            questionDifficulty = row[4].find('span').text
            questionNameList.append(questionName)
            questionUrlList.append(questionUrl)
            questionDifficultyList.append(questionDifficulty)

            fetchQuestionDetails(questionName, questionUrl)
            xcelSheet()
        print("Fetched all questions in the page: ", pageUrl)
        closeBrowser(browser)

    else:
        print("Page does not exist o connection Failed, status code: ",
              soup.status_code)
    return


def getQuestionPages():
    """
        This function fetches the all pages with questions in LeetCode and creates their urls.
    """
    try:
        browser = openBrowser(siteUrl)
        time.sleep(10)

        pageSource = browser.page_source
        print('hi', browser.title)
        WebDriverWait(browser, 10).until(EC.title_contains("Problems - LeetCode"))
        print("enter driver")
        soup = BeautifulSoup(pageSource, 'html.parser')
        
        if (browser.title == "Problems - LeetCode"):
            print("enter pages")
            # Fetching total number of pages
            totalPages = soup.find_all('button', class_="flex items-center justify-center px-3 h-8 rounded select-none focus:outline-none bg-fill-3 dark:bg-dark-fill-3 text-label-2 dark:text-dark-label-2 hover:bg-fill-2 dark:hover:bg-dark-fill-2")[-2]
            totalPages = int(totalPages.text)
            totalQuestions = 50 * totalPages # LeetCode displays 50 questions per page by default
            closeBrowser(browser)
            question_count =0

            # Fetching data from each page
            for page in range(61, totalPages + 1):
                print("Fetching Page : ", page)
                pageUrl = siteUrl + '?page=' + str(page)
                fetchPageData(pageUrl)
                question_count += questionNameList.__len__()
                xcelSheet()  # Writing to sheet for every page

            print("Finished fetching all pages with questions.")
            print(f"Total {question_count} questions fetched")
        else:
            print("Connection Failed")
            return

    except Exception as e:
        import traceback

        print("Error occurred, error: ", traceback.print_exc())
        return


if __name__ == "__main__":
    getQuestionPages()
    