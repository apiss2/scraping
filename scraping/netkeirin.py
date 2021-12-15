import time
import re

import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select

from .base import SeleniumScraperBase


class NetkeirinSeleniumScraperBase(SeleniumScraperBase):
    def __init__(self, base_url, executable_path, visible=False, wait_time=10):
        super().__init__(executable_path, visible, wait_time)
        self.base_url = base_url

    def visit_page(self, race_id):
        self.driver.get(self.base_url.format(race_id))


class OddsScraper(NetkeirinSeleniumScraperBase):
    '''
    オッズをスクレイピングするクラス
    '''

    def __init__(self, excutable_path, visible, wait_time):
        super().__init__(
            base_url='https://keirin.netkeiba.com/race/odds/?race_id={}',
            executable_path=excutable_path, visible=visible, wait_time=wait_time)

    def odds_is_exist(self):
        elements = self.driver.find_elements_by_xpath(
            '//*[@id="root-app"]/div[1]/div[1]/div[1]/nav/ul/li[1]')
        if len(elements) > 0:
            return True
        else:
            return False

    def get_wakuren_odds_table(self):
        # 枠連
        raise NotImplementedError()

    def get_2shafuku_odds_table(self):
        # 2車複
        self._click_element(
            By.XPATH, '//*[@id="root-app"]/div[1]/div[1]/div[1]/nav/ul/li[4]/button')
        self._click_element(
            By.XPATH, '//*[@id="root-app"]/div[1]/div[1]/div[2]/nav/ul/li[2]/button')
        element = self._get_element(
            By.XPATH, '//*[@id="root-app"]/div[1]/article/div[1]')
        dfs = pd.read_html(element.get_attribute('outerHTML'))
        target_df = dfs[2].copy().iloc[:, :-1]
        target_df.columns = [i + 1 for i in range(len(target_df))]
        target_df['Second'] = [i + 2 for i in range(len(target_df))]
        df_list = list()
        for first in range(1, len(target_df) + 1):
            tmp = target_df[['Second', first]].copy().rename(
                columns={first: 'Odds'})
            tmp['First'] = first
            df_list.append(tmp[['First', 'Second', 'Odds']])
        shafuku_df = pd.concat(df_list).dropna().reset_index(drop=True)
        return shafuku_df

    def get_wide_odds_table(self):
        # ワイド
        raise NotImplementedError

    def get_2shatan_odds_table(self):
        # 2車単
        self._click_element(
            By.XPATH, '//*[@id="root-app"]/div[1]/div[1]/div[1]/nav/ul/li[2]/button')
        self._click_element(
            By.XPATH, '//*[@id="root-app"]/div[1]/div[1]/div[2]/nav/ul/li[2]/button')
        element = self._get_element(
            By.XPATH, '//*[@id="root-app"]/div[1]/article/div[1]')
        dfs = pd.read_html(element.get_attribute('outerHTML'))
        target_df = dfs[2].copy()
        target_df.columns = [i + 1 for i in range(len(target_df))]
        target_df['Second'] = [i + 1 for i in range(len(target_df))]
        df_list = list()
        for first in range(1, len(target_df) + 1):
            tmp = target_df[['Second', first]].copy().rename(
                columns={first: 'Odds'})
            tmp['First'] = first
            df_list.append(tmp[['First', 'Second', 'Odds']])
        shatan_df = pd.concat(df_list).dropna().reset_index(drop=True)
        return shatan_df

    def get_3renpuku_odds_table(self, sleep_time=0.2):
        # 3連複
        self._click_element(
            By.XPATH, '//*[@id="root-app"]/div[1]/div[1]/div[1]/nav/ul/li[3]/button')
        self._click_element(
            By.XPATH, '//*[@id="root-app"]/div[1]/div[1]/div[2]/nav/ul/li[2]/button')
        element = self.driver.find_element_by_xpath('//*[@id="entry_axis"]')
        select = Select(element)
        renpuku_list = list()
        for first in range(1, select.options.__len__() + 1):
            select.select_by_value(f'{first - 1}')
            time.sleep(0.5)
            element = self._get_element(
                By.XPATH, '//*[@id="root-app"]/div[1]/article/div[2]/div')
            dfs = pd.read_html(element.get_attribute('outerHTML'))
            target_df = dfs[2].copy().iloc[:, :-1]
            third_list = [int(i) for i in list(dfs[1].columns[1][3:])]
            second_list = [int(re.search(r'\d', i).group())
                           for i in target_df.columns]
            target_df.columns = second_list
            target_df.index = third_list
            target_df['First'] = first
            tmp_list = list()
            for i in second_list:
                tmp = target_df[['First', i]].rename(columns={i: 'Odds'})
                tmp['Second'] = i
                tmp_list.append(tmp)
            target_df = pd.concat(tmp_list).reset_index().rename(
                columns={'index': 'Third'})
            target_df = target_df[[
                'First', 'Second', 'Third', 'Odds']].dropna()
            renpuku_list.append(target_df)
        renpuku_df = pd.concat(renpuku_list).reset_index(drop=True)
        values = renpuku_df.iloc[:, :3].values
        values.sort()
        renpuku_df.iloc[:, :3] = values
        renpuku_df = renpuku_df.drop_duplicates().reset_index(drop=True)
        return renpuku_df

    def get_3rentan_odds_table(self):
        # 3連単
        self._click_element(
            By.XPATH, '//*[@id="root-app"]/div[1]/div[1]/div[1]/nav/ul/li[1]/button')
        self._click_element(
            By.XPATH, '//*[@id="root-app"]/div[1]/div[1]/div[2]/nav/ul/li[2]/button')
        element = self.driver.find_element_by_xpath('//*[@id="entry_axis"]')
        select = Select(element)
        rentan_list = list()
        for first in range(1, select.options.__len__() + 1):
            select.select_by_value(f'{first - 1}')
            time.sleep(0.5)
            element = self._get_element(
                By.XPATH, '//*[@id="root-app"]/div[1]/article/div[2]/div')
            dfs = pd.read_html(element.get_attribute('outerHTML'))
            target_df = dfs[2].copy()
            uma_list = [int(i) for i in list(dfs[1].columns[1][3:])]
            target_df.columns = uma_list
            target_df.index = uma_list
            target_df['First'] = first
            tmp_list = list()
            for i in uma_list:
                tmp = target_df[['First', i]].rename(columns={i: 'Odds'})
                tmp['Second'] = i
                tmp_list.append(tmp)
            target_df = pd.concat(tmp_list).reset_index().rename(
                columns={'index': 'Third'})
            target_df = target_df[[
                'First', 'Second', 'Third', 'Odds']].dropna()
            rentan_list.append(target_df)
        rentan_df = pd.concat(rentan_list).reset_index(drop=True)
        return rentan_df


class PrizeScraper(NetkeirinSeleniumScraperBase):
    '''
    払い戻し金額をスクレイピングするクラス
    '''
    # TODO: SoupScraperBaseで実装可能か検討

    def __init__(self, excutable_path, visible, wait_time):
        super().__init__(
            base_url='https://keirin.netkeiba.com/race/result/?race_id={}',
            executable_path=excutable_path, visible=visible, wait_time=wait_time)

    def get_prize_table(self):
        element = self._get_element(
            By.XPATH, '//*[@id="RaceResult"]/div[1]/div/div[1]/div[7]/table')
        dfs = pd.read_html(element.get_attribute('outerHTML'))
        tmp = dfs[0]
        tmp.columns = ['ticket_type', 'combination', 'price', 'none']
        return tmp.iloc[:, :3]
