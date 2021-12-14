from abc import ABC, abstractmethod

import requests
from bs4 import BeautifulSoup
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.support.expected_conditions import (
    visibility_of_all_elements_located, visibility_of_element_located)
from selenium.webdriver.support.ui import WebDriverWait


class SeleniumScraperBase(ABC):
    '''
    動的なサイトをスクレイピングする場合は、このクラスを継承。
    '''
    def __init__(self, executable_path, visible=False, wait_time=10):
        self.option = ChromeOptions()
        if not visible:
            self.option.add_argument('--headless')
        self.driver = Chrome(executable_path=executable_path, options=self.option)
        self.driver.implicitly_wait(wait_time)
        self.wait = WebDriverWait(self.driver, wait_time)

    def __del__(self):
        self.driver.close()

    @abstractmethod
    def visit_page(self):
        pass

    def __get_element(self, by, text):
        return self.wait.until(visibility_of_element_located((by, text)))

    def __get_elements(self, by, text):
        return self.wait.until(visibility_of_all_elements_located((by, text)))

    def __click_element(self, by, text):
        self.__get_element(by, text).click()


class SoupScraperBase(ABC):
    '''
    静的なサイトをスクレイピングする場合は、このクラスを継承。
    '''

    @abstractmethod
    def get_soup(self):
        pass

    def __get_soup(self, url):
        html = requests.get(url)
        html.encoding = "EUC-JP"
        soup = BeautifulSoup(html.text, "html.parser")
        return soup

    def __get_element(self, soup, tag, by, text):
        attrs = {by: text} if by is not None else {}
        return soup.find(tag, attrs=attrs)

    def __get_elements(self, soup, tag, by=None, text=None):
        attrs = {by: text} if by is not None else {}
        return soup.find_all(tag, attrs=attrs)
