import datetime
import re
import time

import pandas as pd
from dateutil import relativedelta
from tqdm import tqdm

from .base import SoupScraperBase


class BoarRaceSoupScraperBase(SoupScraperBase):
    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.soup = None

    def get_soup(self, infos: list):
        self.soup = self._get_soup(self.base_url.format(*infos))
        return self.soup

    def page_is_exists(self):
        return 'システムエラー' not in self.soup.title.text


class JcdScraper(BoarRaceSoupScraperBase):
    def __init__(self):
        super().__init__('https://www.boatrace.jp/owpc/pc/race/index?jcd=01&hd={}')

    def get_Jcd_list_from_date(self, today: datetime.date) -> list:
        date = f'{today.year:04}{today.month:02}{today.day:02}'
        self.get_soup([date])
        # ページが存在しない場合にはNone
        if not self.page_is_exists():
            return None
        # レース一覧からレースが開催されているレース場IDを取得
        rows = self.soup.find_all('table')[0].find_all('tr')
        jcd_list = list()
        for row in rows[1:]:
            contents = row.find_all('td')[4]
            url_text = contents.find('a')['href']
            jcd = re.search('jcd=\d\d', url_text)[0][-2:]
            jcd_list.append({'date': date, 'jcd': jcd})
        return jcd_list

    def get_monthly_Jcd_list(self, year, month, sleep_time, leave=True) -> list:
        today = datetime.date(year, month, 1)
        jcd_dict_list = list()
        for _ in tqdm(range(31), leave=leave):
            jcd_list = self.get_Jcd_list_from_date(today)
            if jcd_list is None:
                continue
            jcd_dict_list += jcd_list
            today = today + relativedelta.relativedelta(days=1)
            time.sleep(sleep_time)
        return jcd_dict_list


class ResultScraper(object):
    def __init__(self):
        self.base_url = 'https://www.boatrace.jp/owpc/pc/race/raceresult?rno={}&jcd={}&hd={}'

    def get_result(self, race_number, jcd, hold_date):
        tables = pd.read_html(self.base_url.format(race_number, jcd, hold_date))
        if len(tables)==0:
            return None
        result_df = self._reshape_result_df(tables[1])
        return_df = self._reshape_return_df(tables[3])
        return result_df, return_df

    def _reshape_result_df(self, df):
        df['ボートレーサー'] = df['ボートレーサー'].apply(lambda x: x.replace('\u3000', '').replace(' ', ''))
        df['racer_id'] = df['ボートレーサー'].apply(lambda x: x[:4])
        df['racer_name'] = df['ボートレーサー'].apply(lambda x: x[4:])
        df.drop('ボートレーサー', axis=1, inplace=True)
        return df

    def _reshape_return_df(self, df):
        df = df[df[['組番', '払戻金', '人気']].isna().sum(1)!=3].copy()
        df['払戻金'] = df['払戻金'].apply(lambda x: str(x).replace(chr(165), "").replace(',', ""))
        return df


class OddsScraper(object):
    def __init__(self):
        self.base_url = 'https://www.boatrace.jp/owpc/pc/race/{}?rno={}&jcd={}&hd={}'
        self.race_type_dict = {
            '単勝': 'oddstf', '複勝': 'oddstf',
            '3連単': 'odds3t', '3連複': 'odds3f',
            '2連単': 'odds2tf', '2連複': 'odds2tf',
            '拡連複': 'oddsk'}

    def get_tansho_table(self, race_number, jcd, date):
        url = self.base_url.format(
            self.race_type_dict['単勝'], race_number, jcd, date)
        tables = pd.read_html(url)
        if len(tables)==0:
            return None
        df = tables[1].rename(columns={'Unnamed: 0': 'First', '単勝オッズ': 'Odds'})
        return df.drop('ボートレーサー', axis=1)

    def get_rentan3_table(self, race_number, jcd, date):
        url = self.base_url.format(
            self.race_type_dict['3連単'], race_number, jcd, date)
        tables = pd.read_html(url)
        if len(tables)==0:
            return None
        return self._reshape_ren_table(tables[1], 3)

    def get_renfuku3_table(self, race_number, jcd, date):
        url = self.base_url.format(
            self.race_type_dict['3連複'], race_number, jcd, date)
        tables = pd.read_html(url)
        if len(tables)==0:
            return None
        df = self._reshape_ren_table(tables[1], 3)
        return df[df[['Second', 'Third', 'Odds']].isna().sum(1)!=3].copy()

    def get_rentanfuku2_table(self, race_number, jcd, date):
        url = self.base_url.format(
            self.race_type_dict['2連単'], race_number, jcd, date)
        tables = pd.read_html(url)
        if len(tables)==0:
            return (None, None)
        rentan2_df = self._reshape_ren_table(tables[1], 2)
        renfuku2_df = self._reshape_ren_table(tables[2], 2)
        renfuku2_df = renfuku2_df[renfuku2_df[['Second', 'Odds']].isna().sum(1)!=2].copy()
        return rentan2_df, renfuku2_df

    def _reshape_ren_table(self, df, delta):
        num = len(df.columns)//delta
        l = list()
        for i in range(num):
            tmp = df.iloc[:, i*delta:(i+1)*delta]
            tmp.columns = ['Second', 'Odds'] if delta==2 else ['Second', 'Third', 'Odds']
            tmp['First'] = i+1
            tmp = tmp[['First', 'Second', 'Odds']] if delta==2 else tmp[['First', 'Second', 'Third', 'Odds']]
            l.append(tmp)
        return pd.concat(l)

