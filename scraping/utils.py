import pandas as pd
from tqdm import tqdm
import re

from .base import SoupScraperBase


class AmedasStationScraper(SoupScraperBase):
    """
    アメダスの観測地点の一覧を取得できるクラス

    Examples
    ----------
    >>> df = AmedasStationScraper().run()
    """

    def __init__(self, encoding='utf-8'):
        super().__init__()
        self.encoding = encoding
        url = 'https://www.data.jma.go.jp/obd/stats/etrn/select/prefecture00.php?prec_no=&block_no=&year=&month=&day=&view='
        self.soup = self._get_soup(url, encoding=self.encoding)

    def run(self):
        area_list, area_link_list = self.get_all_area_link()
        df = self.get_all_station_link(area_list, area_link_list)
        return df

    def get_all_area_link(self):
        elements = self.soup.find_all('area')
        area_list = [element['alt'] for element in elements]
        area_link_list = [element['href'] for element in elements]
        return area_list, area_link_list

    def get_all_station_link(self, area_list, area_link_list) -> pd.DataFrame:
        dfs = list()
        for area, area_link in tqdm(zip(area_list, area_link_list)):
            dfs.append(self.get_station_data(area, area_link))
        df = pd.concat(dfs).reset_index(drop=True)
        return self.format_df(df)

    def get_station_data(self, area, area_link) -> pd.DataFrame:
        url = 'https://www.data.jma.go.jp/obd/stats/etrn/select/' + area_link
        soup = self._get_soup(url, encoding=self.encoding)
        elements = soup.find_all('area')
        station_list = [element['alt'] for element in elements]
        station_link_list = [element['href'].strip(
            '../') for element in elements]
        station_info = [element['onmouseover'] if element.has_attr(
            'onmouseover') else '-' for element in elements]
        assert len(station_list) == len(station_link_list)
        data = {'station': station_list,
                'url': station_link_list, 'info': station_info}
        df = pd.DataFrame(data)
        df['area'] = area
        return df[['area', 'station', 'url', 'info']]

    def defaultfind(self, pattern, s, default=None, callback=None):
        cont = re.findall(pattern, s)
        if len(cont) == 0:
            return default
        else:
            if callback is not None:
                return callback(cont[0])
            return cont[0]

    def format_df(self, df):
        # prec_no
        df['prec_no'] = df.url.apply(
            lambda x: self.defaultfind("prec_no=\d{1,2}&", x))
        df = df.dropna()
        df.prec_no = df.prec_no.apply(lambda x: x[8:-1])
        # block_no
        df['block_no'] = df.url.apply(
            lambda x: self.defaultfind("block_no=\d{4,6}&", x))
        df = df.dropna()
        df.block_no = df.block_no.apply(lambda x: x[9:-1])
        # block_no
        df['type'] = df['info'].apply(
            lambda x: self.defaultfind("Point\('.'", x))
        df = df.dropna()
        df['type'] = df['type'].apply(lambda x: x[7:-1])
        # 不要部分削除
        df.drop(['url', 'info'], inplace=True, axis=1)
        df.drop_duplicates(inplace=True)
        return df.reset_index(drop=True)


class AmedasDatabaseScraper(SoupScraperBase):
    def __init__(self, timestep='hourly'):
        super().__init__()
        self.base_url = 'https://www.data.jma.go.jp/obd/stats/etrn/view/{}_{}1.php?prec_no={}&block_no={}&year={}&month={}&day={}&view=p1'
        assert timestep in ['daily', 'hourly', '10min']
        self.timestep = timestep
        self.prec_no = None
        self.block_no = None
        self.station_type = None

    def initialize(self, prec_no, block_no, station_type, timestep=None):
        self.prec_no = prec_no
        self.block_no = block_no
        self.station_type = station_type
        if timestep is not None:
            assert timestep in ['daily', 'hourly', '10min']
            self.timestep = timestep

    def get_data(self, year, month, day):
        assert self.prec_no is not None
        assert self.block_no is not None
        assert self.station_type is not None
        df = pd.read_html(self.base_url.format(
            self.timestep, self.station_type, self.prec_no, self.block_no,
            year, month, day))[0]
        cols = [i[-1] for i in df.columns.to_list()]
        df.columns = cols
        return df
