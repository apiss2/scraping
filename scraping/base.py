from abc import ABC

import requests
from bs4 import BeautifulSoup
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.support.expected_conditions import (
    visibility_of_all_elements_located, visibility_of_element_located)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.select import Select


class SeleniumScraperBase(ABC):
    '''
    動的なサイトをスクレイピングする場合は、このクラスを継承。
    '''

    def __init__(self, executable_path, visible=False, wait_time=10):
        self.option = ChromeOptions()
        if not visible:
            self.option.add_argument('--headless')
        self.driver = Chrome(
            executable_path=executable_path, options=self.option)
        self.driver.implicitly_wait(wait_time)
        self.wait = WebDriverWait(self.driver, wait_time)

    def __del__(self):
        self.driver.close()

    def _visit_page(self, url):
        self.driver.get(url)

    def _get_element(self, by, text):
        return self.wait.until(visibility_of_element_located((by, text)))

    def _get_elements(self, by, text):
        return self.wait.until(visibility_of_all_elements_located((by, text)))

    def _click(self, element):
        self.driver.execute_script("arguments[0].scrollIntoView(false);", element)
        element.click()

    def _select(self, element, idx):
        select = Select(element)
        select.select_by_index(idx)


class SoupScraperBase(ABC):
    '''
    静的なサイトをスクレイピングする場合は、このクラスを継承。
    '''
    def __init__(self, login_url: str = None, login_info: dict = None):
        self.login = False
        if (login_info is not None) and (login_url is not None):
            self.login = True
            self.session = requests.session()
            self.session.post(login_url, data=login_info)

    def _get_soup(self, url, encoding=None):
        if self.login:
            html = self.session.get(url)
        else:
            html = requests.get(url)
        if encoding is not None:
            html.encoding = encoding
        content = html.content if self.login else html.text
        soup = BeautifulSoup(content, "html.parser")
        return soup

    def _get_element(self, soup, tag, by, text):
        attrs = {by: text} if by is not None else {}
        return soup.find(tag, attrs=attrs)

    def _get_elements(self, soup, tag, by=None, text=None):
        attrs = {by: text} if by is not None else {}
        return soup.find_all(tag, attrs=attrs)
