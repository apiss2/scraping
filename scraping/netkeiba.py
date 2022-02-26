import datetime
import re
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup
from dateutil import relativedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from tqdm import tqdm

from .base import SeleniumScraperBase, SoupScraperBase


class NetkeibaSeleniumScraperBase(SeleniumScraperBase):
    def __init__(self, base_url, executable_path, visible=False, wait_time=10):
        super().__init__(executable_path, visible, wait_time)
        self.base_url = base_url

    def visit_page(self, race_id):
        self.driver.get(self.base_url.format(race_id))


class NetkeibaSoupScraperBase(SoupScraperBase):
    def __init__(self, base_url, user_id=None, password=None):
        url, info = None, None
        if (user_id is not None) and (password is not None):
            url = "https://regist.netkeiba.com/account/?pid=login&action=auth"
            info = {'login_id': user_id, 'pswd': password}
        super().__init__(login_url=url, login_info=info)
        self.base_url = base_url
        self.soup = None

    def get_soup(self, race_id):
        self.soup = self._get_soup(self.base_url.format(race_id), encoding='EUC-JP')


class DatabaseScraper(NetkeibaSoupScraperBase):
    HANDICAP_LIST = ['ハンデ', '馬齢', '別定', '定量']
    LOCALHORSE_LIST = ['指', '特指']
    FOREIGNHORSE_LIST = ['国際', '混']
    RACECLASS_LIST = ['オープン', '未勝利', '新馬']
    MAIN_DF_COLUMNS = [
        '着順', '枠番', '馬番', '馬名', '性齢', '斤量', '騎手',
        'タイム', '着差', '単勝', '人気', '馬体重', '調教師']
    PLEMIUS_COLUMNS = ['ﾀｲﾑ指数', '調教ﾀｲﾑ', '厩舎ｺﾒﾝﾄ']

    def __init__(self, user_id=None, password=None):
        super().__init__(
            base_url="https://db.netkeiba.com/race/{}",
            user_id=user_id, password=password)

    def get_main_df(self) -> pd.DataFrame:
        assert self.soup is not None
        rows = self.soup.find(
            'table', attrs={"class": "race_table_01"}).find_all('tr')
        data = [[col.text.replace('\n', '') for col in row.findAll(
            ['td', 'th'])] for row in rows]
        cols = self.MAIN_DF_COLUMNS + self.PLEMIUS_COLUMNS if self.login else self.MAIN_DF_COLUMNS
        main_df = pd.DataFrame(data[1:], columns=data[0])[cols]
        return main_df

    def get_horse_id_list(self) -> list:
        # TODO: get_main_dfと統合
        return self.__get_id_list('horse')

    def get_jockey_id_list(self) -> list:
        # TODO: get_main_dfと統合
        return self.__get_id_list('horse')

    def __get_id_list(self, id_type) -> list:
        assert id_type == 'horse' or id_type == 'jockey'
        atag_list = self.soup.find("table", attrs={"summary": "レース結果"}).find_all(
            "a", attrs={"href": re.compile(f"^/{id_type}")})
        id_list = [re.findall(r"\d+", atag["href"])[0] for atag in atag_list]
        return id_list

    def get_race_info(self) -> dict:
        # レース情報のスクレイピング
        race_name = self.soup.find(
            "dl", attrs={"class": "racedata fc"}).find('h1').text
        race_info_list = [race_name]
        data_intro = self.soup.find(
            "div", attrs={"class": "data_intro"}).find_all("p")
        race_info_list += data_intro[0].find(
            'span').text.replace('\xa0', '').split('/')
        race_info_list += data_intro[1].text.replace('\xa0', '').split(' ')
        return self.__parse_race_info(race_info_list)

    def __parse_race_info(self, race_info_list) -> dict:
        assert 8 <= len(race_info_list) <= 9
        race_info = {'レース名': race_info_list[0]}
        race_type = race_info_list[1]
        race_info['周回方向'] = '右' if '右' in race_type else '左' if '右' in race_type else '不明'
        race_info['コースタイプ'] = '障害' if '障' in race_type else 'ダート' if 'ダ' in race_type else '芝'
        race_info['馬場状態'] = race_info_list[3].split(' : ')[-1]
        race_info['コース長'] = re.findall(r'\d{3,4}m', race_type)[0][:-1]
        race_info['天候'] = race_info_list[2].split(' : ')[1]
        race_info['日時'] = race_info_list[5]
        race_info['発走'] = race_info_list[4].split(' : ')[1]
        # 開催場所、タイミング
        hold_n = re.search(r'\d+回', race_info_list[6])
        day_n = re.search(r'\d+日目', race_info_list[6])
        racecourse = race_info_list[6][hold_n.span()[1]:day_n.span()[0]]
        race_info['開催回'] = hold_n[0]
        race_info['開催日'] = day_n[0]
        race_info['開催会場'] = racecourse
        # 条件
        s = race_info_list[7] if len(
            race_info_list) == 8 else race_info_list[7] + race_info_list[8]
        sep = s.find('[') if (s.find(
            '[') != -1) and (s.find('[') < s.find('(')) else s.find('(')
        # TODO: スクレイピング時点でレース条件に関する詳細区分を行う
        race_info['レース条件_1'] = s[:sep]
        race_info['レース条件_2'] = s[sep:]
        return race_info

    def get_pay_df(self) -> pd.DataFrame:
        tables = self.soup.find_all('table', attrs={"class": "pay_table_01"})
        rows = tables[0].find_all('tr') + tables[1].find_all('tr')
        data = [[re.sub(r"\<.+?\>", "", str(col).replace('<br/>', 'br')).replace(
            '\n', '') for col in row.findAll(['td', 'th'])] for row in rows]
        return pd.DataFrame(data)


class UmabashiraScraper(object):
    def __init__(self):
        self.base_url = 'http://jiro8.sakura.ne.jp/index.php?code={}'

    def get_umabashira(self, race_id):
        code = str(race_id)[2:]
        html = requests.get(self.base_url.format(code))
        html.encoding = 'cp932'
        dfs = pd.read_html(html.text)
        # TODO: 整形するコード書いておく
        return dfs[12]


class RaceidScraper(NetkeibaSoupScraperBase):
    def __init__(self):
        super().__init__(base_url="https://db.netkeiba.com/race/list/{}")

    def get_raceID_list_from_date(self, today: datetime.date) -> list:
        date = f'{today.year:04}{today.month:02}{today.day:02}'
        self.get_soup(date)
        race_list = self.soup.find('div', attrs={"class": 'race_list fc'})
        if race_list is None:
            return list()
        a_tag_list = race_list.find_all('a')
        href_list = [a_tag.get('href') for a_tag in a_tag_list]
        race_id_list = list()
        for href in href_list:
            for s in re.findall('[0-9]{12}', href):
                race_id_list.append(s)
        return list(set(race_id_list))

    def get_monthly_raceID_list(self, year, month, sleep_time, leave=True) -> list:
        today = datetime.date(year, month, 1)
        race_id_list = list()
        for _ in tqdm(range(31), leave=leave):
            race_id_list += self.get_raceID_list_from_date(today)
            today = today + relativedelta.relativedelta(days=1)
            time.sleep(sleep_time)
        return race_id_list

    def get_yearly_raceID_list(self, year, sleep_time, leave=True) -> list:
        race_id_list = list()
        for i in range(12):
            race_id_list += self.get_monthly_raceID_list(
                year, month=i+1, sleep_time=sleep_time, leave=leave)
        return race_id_list


class OddsScraper(NetkeibaSeleniumScraperBase):
    def __init__(self, executable_path, visible=False, wait_time=10):
        super().__init__(
            base_url='https://race.netkeiba.com/odds/index.html?race_id={}&rf=race_submenu',
            executable_path=executable_path, visible=visible, wait_time=wait_time)

    def get_tansho_odds_table(self, sleep_time=0.2) -> pd.DataFrame:
        # 単勝/複勝
        self._click_element(By.ID, "odds_navi_b1")
        time.sleep(sleep_time)
        tansho_df = self.__get_tanpuku_odds_table(0)
        return tansho_df

    def get_fukusho_odds_table(self, sleep_time=0.2) -> pd.DataFrame:
        # 複勝
        self._click_element(By.ID, "odds_navi_b1")
        time.sleep(sleep_time)
        tansho_df = self.__get_tanpuku_odds_table(1)
        return tansho_df

    def __get_tanpuku_odds_table(self, idx) -> pd.DataFrame:
        # 0なら単勝、1なら複勝のテーブルを取得
        elements = self._get_elements(
            By.CLASS_NAME, "RaceOdds_HorseList_Table")
        dfs = pd.read_html(elements[idx].get_attribute('outerHTML'))
        tanpuku_df = dfs[0][['馬番', 'オッズ']]
        tanpuku_df.columns = ['First', 'Odds']
        return tanpuku_df

    def get_wakuren_odds_table(self) -> pd.DataFrame:
        # 枠連
        self._click_element(By.ID, "odds_navi_b3")
        raise NotImplementedError

    def get_umaren_odds_table(self, sleep_time=0.2) -> pd.DataFrame:
        # 馬連
        self._click_element(By.ID, "odds_navi_b4")
        time.sleep(sleep_time)
        element = self._get_element(By.CLASS_NAME, "GraphOdds")
        dfs = pd.read_html(element.get_attribute('outerHTML'))
        first_list = [int(df.columns.values[0]) for df in dfs]
        umaren_df_list = [df.iloc[:, :2] for df in dfs]
        for i in range(len(umaren_df_list)):
            umaren_df_list[i].columns = ['Second', 'Odds']
            umaren_df_list[i]['First'] = first_list[i]
            umaren_df_list[i] = umaren_df_list[i][['First', 'Second', 'Odds']]
        umaren_df = pd.concat(umaren_df_list, axis=0)
        return umaren_df

    def get_wide_odds_table(self) -> pd.DataFrame:
        # ワイド
        self._click_element(By.ID, "odds_navi_b5")
        raise NotImplementedError

    def get_umatan_odds_table(self, sleep_time=0.2) -> pd.DataFrame:
        # 馬単
        self._click_element(By.ID, "odds_navi_b6")
        time.sleep(sleep_time)
        element = self._get_element(By.CLASS_NAME, "GraphOdds")
        dfs = pd.read_html(element.get_attribute('outerHTML'))
        first_list = [int(df.columns.values[0]) for df in dfs]
        batan_df_list = [df.iloc[:, :2] for df in dfs]
        for i in range(len(batan_df_list)):
            batan_df_list[i].columns = ['Second', 'Odds']
            batan_df_list[i]['First'] = first_list[i]
            batan_df_list[i] = batan_df_list[i][['First', 'Second', 'Odds']]
        batan_df = pd.concat(batan_df_list, axis=0)
        return batan_df

    def get_3renpuku_odds_table(self, sleep_time=0.2) -> pd.DataFrame:
        # 3連複
        self._click_element(By.ID, "odds_navi_b7")
        dropdown = self._get_element(By.ID, "list_select_horse")
        select = Select(dropdown)
        num = len(select.options)
        # スクレイピング
        dfs_list = list()
        for axis_horse_number in range(1, num):
            if axis_horse_number > 1:
                # 軸馬の選択・変更 dropdown select状態にする
                dropdown = self._get_element(By.ID, "list_select_horse")
                select = Select(dropdown)
                select.select_by_value(str(axis_horse_number))
            time.sleep(sleep_time)
            element = self._get_element(By.CLASS_NAME, "GraphOdds")
            dfs = pd.read_html(element.get_attribute('outerHTML'))
            dfs_list.append(dfs)
        # 整形
        renpuku_concat_df_list = list()
        for uma, dfs in enumerate(dfs_list):
            uma += 1
            second_list = [int(df.columns.values[0]) for df in dfs]
            renpuku_df_list = [df.iloc[:, :2] for df in dfs]
            for i in range(len(renpuku_df_list)):
                renpuku_df_list[i].columns = ['Third', 'Odds']
                renpuku_df_list[i]['First'] = uma
                renpuku_df_list[i]['Second'] = second_list[i]
                renpuku_df_list[i] = renpuku_df_list[i][[
                    'First', 'Second', 'Third', 'Odds']]
            renpuku_concat_df_list.append(pd.concat(renpuku_df_list, axis=0))
        renpuku_df = pd.concat(renpuku_concat_df_list, axis=0)
        # 着順をソートして重複を削除
        values = renpuku_df.iloc[:, :3].values
        values.sort()
        renpuku_df.iloc[:, :3] = values
        renpuku_df = renpuku_df.drop_duplicates().reset_index(drop=True)
        return renpuku_df

    def get_3rentan_odds_table(self, sleep_time=0.2) -> pd.DataFrame:
        # 3連単
        self._click_element(By.ID, "odds_navi_b8")
        dropdown = self._get_element(By.ID, "list_select_horse")
        select = Select(dropdown)
        num = len(select.options)
        # スクレイピング
        dfs_list = list()
        for axis_horse_number in range(1, num):
            if axis_horse_number > 1:
                # 軸馬の選択・変更 dropdown select状態にする
                dropdown = self._get_element(By.ID, "list_select_horse")
                select = Select(dropdown)
                select.select_by_value(str(axis_horse_number))
            time.sleep(sleep_time)
            element = self._get_element(By.CLASS_NAME, "GraphOdds")
            dfs = pd.read_html(element.get_attribute('outerHTML'))
            dfs_list.append(dfs)
        # 整形
        tan3concat_df_list = list()
        for uma, dfs in enumerate(dfs_list):
            uma += 1
            second_list = [int(df.columns.values[0]) for df in dfs]
            tan3_df_list = [df.iloc[:, :2] for df in dfs]
            for i in range(len(tan3_df_list)):
                tan3_df_list[i].columns = ['Third', 'Odds']
                tan3_df_list[i]['First'] = uma
                tan3_df_list[i]['Second'] = second_list[i]
                tan3_df_list[i] = tan3_df_list[i][[
                    'First', 'Second', 'Third', 'Odds']]
            tan3concat_df_list.append(pd.concat(tan3_df_list, axis=0))
        tan3_df = pd.concat(tan3concat_df_list, axis=0)
        return tan3_df


class AutoBuyer(SeleniumScraperBase):
    BAKEN_TYPE = ['単勝', '複勝', '枠連', '馬連', 'ワイド', '馬単', '３連複', '３連単']

    def __init__(self, executable_path, demo=True, wait_time=10):
        super().__init__(executable_path, visible=True, wait_time=wait_time)
        if demo:
            self.url = 'https://www.jra.go.jp/IPAT_TAIKEN/s-pat/pw_010_i.html'
        else:
            self.url = 'https://www.ipat.jra.go.jp/'

    def visit_page(self, inet_id, user_number, password, p_ars, sleep_time=1):
        self.driver.get(self.url)
        time.sleep(sleep_time)
        self.login(inet_id, user_number, password, p_ars, sleep_time=sleep_time)


    def login(self, inet_id, user_number, password, p_ars, sleep_time=1):
        # INET-ID
        element = self._get_element(By.XPATH, '//*[@id="top"]/div[3]/div/table/tbody/tr/td[2]/div/div/form/table[1]/tbody/tr/td[2]/span/input')
        element.send_keys(str(inet_id))
        # クリックしてページ遷移
        self._click_element(By.XPATH, '//*[@id="top"]/div[3]/div/table/tbody/tr/td[2]/div/div/form/table[1]/tbody/tr/td[3]/p/a')
        time.sleep(sleep_time)
        # 加入者番号
        element = self._get_element(By.XPATH, '//*[@id="main_area"]/div/div[1]/table/tbody/tr[1]/td[2]/span/input')
        element.send_keys(str(user_number))
        # 暗証番号
        element = self._get_element(By.XPATH, '//*[@id="main_area"]/div/div[1]/table/tbody/tr[2]/td[2]/span/input')
        element.send_keys(str(password))
        # P-ARS番号
        element = self._get_element(By.XPATH, '//*[@id="main_area"]/div/div[1]/table/tbody/tr[3]/td[2]/span/input')
        element.send_keys(p_ars)
        # クリックしてログイン
        self._click_element(By.XPATH, '//*[@id="main_area"]/div/div[1]/table/tbody/tr[1]/td[3]/p/a')

    def vote_baken_type_select(self, baken_type):
        selector = Select(self._get_element(By.XPATH, '//*[@id="bet-basic-type"]'))
        selector.select_by_index(self.BAKEN_TYPE.index(baken_type))

    def vote_umatan_from_df(self, umatan_df):
        for _, row in umatan_df.iterrows():
            self.vote_umatan(
                int(row.First), int(row.Second), int(row.Num))

    def vote_rentan_from_df(self, rentan_df):
        for _, row in rentan_df.iterrows():
            self.vote_rentan(
                int(row.First), int(row.Second), int(row.Third), int(row.Num))

    def vote_umatan(self, first, second, num, sleep_time=0.2):
        # 1着入力
        self._click_element(By.XPATH,
            f'//*[@id="main"]/ui-view/div[2]/ui-view/main/div/div[3]/div/div/span/div/span/bet-basic-exacta-basic/table/tbody/tr[{first}]/td[2]/label/span')
        time.sleep(sleep_time)
        # 2着入力
        self._click_element(By.XPATH,
            f'//*[@id="main"]/ui-view/div[2]/ui-view/main/div/div[3]/div/div/span/div/span/bet-basic-exacta-basic/table/tbody/tr[{second}]/td[3]/label/span')
        time.sleep(sleep_time)
        # 購入金額入力
        element = self._get_element(By.XPATH,
            '//*[@id="main"]/ui-view/div[2]/ui-view/main/div/div[3]/select-list/div/div/div[3]/div[1]/input')
        element.clear()
        time.sleep(0.1)
        element.send_keys(f'{num}')
        time.sleep(sleep_time)
        self._click_element(By.XPATH,
            '//*[@id="main"]/ui-view/div[2]/ui-view/main/div/div[3]/select-list/div/div/div[3]/div[4]/button[2]')
        time.sleep(sleep_time)

    def vote_rentan(self, first, second, third, num, sleep_time=0.2):
        self._click_element(
            By.XPATH, f'//*[@id="main"]/ui-view/div[2]/ui-view/main/div/div[3]/div/div/span/div/span/bet-basic-trifecta-basic/table/tbody/tr[{first}]/td[2]/label/span')
        time.sleep(sleep_time)
        self._click_element(
            By.XPATH, f'//*[@id="main"]/ui-view/div[2]/ui-view/main/div/div[3]/div/div/span/div/span/bet-basic-trifecta-basic/table/tbody/tr[{second}]/td[3]/label/span')
        time.sleep(sleep_time)
        self._click_element(
            By.XPATH, f'//*[@id="main"]/ui-view/div[2]/ui-view/main/div/div[3]/div/div/span/div/span/bet-basic-trifecta-basic/table/tbody/tr[{third}]/td[4]/label/span')
        time.sleep(sleep_time)
        element = self._get_element(
            By.XPATH, '//*[@id="main"]/ui-view/div[2]/ui-view/main/div/div[3]/select-list/div/div/div[3]/div[1]/input')
        time.sleep(0.1)
        element.clear()
        time.sleep(0.1)
        element.send_keys(f'{num}')
        time.sleep(sleep_time)
        self._click_element(
            By.XPATH, '//*[@id="main"]/ui-view/div[2]/ui-view/main/div/div[3]/select-list/div/div/div[3]/div[4]/button[2]')
        time.sleep(sleep_time)


class LocalRaceidScraper(SeleniumScraperBase):
    '''
    地方競馬のレースIDスクレイピング用クラス
    '''
    RACECOURSE_ID_DICT = {
        65: '帯広', 30: '門別', 35: '盛岡', 36: '水沢', 42: '浦和', 43: '船橋',
        44: '大井', 45: '川崎', 46: '金沢', 47: '笠松', 48: '名古屋',
        50: '園田', 51: '姫路', 54: '高知', 55: '佐賀'}
    def __init__(self, executable_path, visible=False, wait_time=2):
        super().__init__(
            executable_path=executable_path, visible=visible, wait_time=wait_time)
        self.base_url = "https://nar.netkeiba.com/racecourse/racecourse_page.html?jyo_cd={}&kaisai_id={}"

    def visit_page(self, racecourse_id, year, month, date):
        kaisai_id = f'{year:04}{racecourse_id:02}{month:02}{date:02}'
        self.driver.get(self.base_url.format(racecourse_id, kaisai_id))

    def get_raceID_list_from_date(self, today: datetime.date, sleep_time=0.2) -> list:
        race_id_list = list()
        for racecourse_id in self.RACECOURSE_ID_DICT.keys():
            self.visit_page(racecourse_id, today.year, today.month, today.day)
            # レースの存在判定
            element = self._get_element(By.XPATH, '//*[@id="RaceList"]/dl/dt/div/p')
            if '-回' in element.get_attribute('outerHTML'):
                continue
            elements = self._get_elements(By.CLASS_NAME, 'RaceList_DataItem')
            for i in range(1, len(elements)+1):
                element = self._get_element(By.XPATH, f'//*[@id="RaceList"]/dl/dd/ul/li[{i}]/a')
                soup = BeautifulSoup(element.get_attribute('outerHTML'), "html.parser")
                race_id = re.findall('\d{12}', soup.find('a').get('href'))[0]
                race_id_list.append(race_id)
            time.sleep(sleep_time)
        return list(set(race_id_list))

    def get_monthly_raceID_list(self, year, month, sleep_time, leave=True) -> list:
        today = datetime.date(year, month, 1)
        race_id_list = list()
        for _ in tqdm(range(31), leave=leave):
            race_id_list += self.get_raceID_list_from_date(today, sleep_time)
            today = today + relativedelta(days=1)
            time.sleep(sleep_time)
        return race_id_list

    def get_yearly_raceID_list(
            self, year, sleep_time, leave=True) -> list:
        race_id_list = list()
        for i in range(12):
            race_id_list += self.get_monthly_raceID_list(
                year, month=i+1, sleep_time=sleep_time, leave=leave)
        return race_id_list
