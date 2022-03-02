# scraping
自分用のスクレイピングコードをまとめたディレクトリです。

以下の3サイトに対応しています。
- 競馬([netkeiba](https://www.netkeiba.com/))
- 競輪([netkeirin](https://keirin.netkeiba.com/))
- 競艇([boatrace](https://www.boatrace.jp/))

## 競馬 (netkeiba)
レースIDに基づいてスクレイピングを行います。
- レースIDのスクレイピング (地方競馬も対応)
- [データベース](https://db.netkeiba.com/?rf=navi)ページからのレース情報のスクレイピング
- 前走5走までの馬柱のスクレイピング
- オッズ情報のスクレイピング
- 自動購入機能

## 競輪 (netkeirin)
レースIDに基づいてスクレイピングを行います。
- データベースページからのレース情報のスクレイピング
- オッズ情報のスクレイピング

## 競艇 (boatrace)
JCDに基づいてスクレイピングを行います。
- JCDのスクレイピング
- レース結果のスクレイピング
- オッズ情報のスクレイピング


# Requirement

* selenium
* pandas
* tqdm
* BeautifulSoup4
* requests

# Installation

```bash
git clone https://github.com/apiss2/scraping.git
pip install ./scraping
```

# Usage

あとでかく
