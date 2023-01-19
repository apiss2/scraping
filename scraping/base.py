from abc import ABC
from typing import List

import requests
from bs4 import BeautifulSoup
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.support.expected_conditions import (
    visibility_of_all_elements_located, visibility_of_element_located)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.select import Select
from selenium.webdriver.remote.webelement import WebElement

class SeleniumScraperBase(ABC):
    '''
    動的なサイトをスクレイピングする場合は、このクラスを継承。
    '''

    def __init__(self, executable_path: str, visible : bool = False, wait_time: float = 10):
        """
        Parameters
        ----------
        executable_path : str
            chrome driverまでのパス
        visible : bool, default False
            ブラウザを起動して動作させるかのフラグ
        wait_time : float, default 10
            タイムアウトまでの時間
        """
        self.option = ChromeOptions()
        if not visible:
            self.option.add_argument('--headless')
        self.option.add_experimental_option(
            'excludeSwitches', ['enable-logging'])
        self.option.use_chromium = True
        self.driver = Chrome(
            executable_path=executable_path, options=self.option)
        self.driver.implicitly_wait(wait_time)
        self.wait = WebDriverWait(self.driver, wait_time)

    def __del__(self):
        self.driver.close()

    def _visit_page(self, url) -> None:
        self.driver.get(url)

    def _get_element(self, by, text) -> WebElement:
        return self.wait.until(visibility_of_element_located((by, text)))

    def _get_elements(self, by, text) -> List[WebElement]:
        return self.wait.until(visibility_of_all_elements_located((by, text)))

    def _click(self, element) -> None:
        self.driver.execute_script("arguments[0].scrollIntoView(false);", element)
        element.click()

    def _select(self, element, idx) -> None:
        select = Select(element)
        select.select_by_index(idx)


class SoupScraperBase(ABC):
    '''
    静的なサイトをスクレイピングする場合は、このクラスを継承。
    '''
    def __init__(self, login_url: str = None, login_info: dict = None):
        """
        Parameters
        ----------
        login_url : str, optional
            _description_, by default None
        login_info : dict, optional
            _description_, by default None
        """
        self.login = False
        if (login_info is not None) and (login_url is not None):
            self.login = True
            self.session = requests.session()
            self.session.post(login_url, data=login_info)

    def _get_soup(self, url: str, encoding: str = None):
        if self.login:
            html = self.session.get(url)
        else:
            html = requests.get(url)
        if encoding is not None:
            html.encoding = encoding
        content = html.content if self.login else html.text
        soup = BeautifulSoup(content, "html.parser")
        return soup

    def _get_element(self, soup: BeautifulSoup, tag: str, by: str = None, text: str = None) -> BeautifulSoup:
        attrs = {by: text} if by is not None else {}
        return soup.find(tag, attrs=attrs)

    def _get_elements(self, soup: BeautifulSoup, tag: str, by: str = None, text: str = None) -> List[BeautifulSoup]:
        attrs = {by: text} if by is not None else {}
        return soup.find_all(tag, attrs=attrs)
