from bs4 import BeautifulSoup
import requests
import time
import pathlib
import pandas as pd
import json
import sys
import re

def crawl_ktai_ogiri(episode_id: int, crawled_file_dir: pathlib.Path) -> dict:
    answers = list()

    save_file_path = crawled_file_dir.joinpath(f'{episode_id}.html')
    if save_file_path.exists() is False:
        url = f"https://keitaioogiri.hatenablog.com/entry/{episode_id}"

        response = requests.get(url)
        if response.status_code != 200:
            print(f'Page: {episode_id} is not existed.')
            return answers
        else:
            print(f'Page: {episode_id} is crawled.')
            time.sleep(1)
            with open(save_file_path, 'w') as wf:
                wf.write(response.text)

    soup = BeautifulSoup(open(save_file_path, encoding='utf-8'), 'html.parser')
    print(f'Page: {episode_id}.html is loaded.')

    content = soup.find_all('div', {'class': 'entry-content hatenablog-entry'})[0]

    parents = content.find_all('h4')
    for odai_id, parent in enumerate(parents, start=1):
        if parent:
            if len(parent.text.split('　')) > 1:
                odai = parent.text.split('　')[1]
            else:
                odai = parent.text
            table = parent.find_next_sibling('table')
            
            if table:
                rows = table.find_all('tr')
                for answer_id, row in enumerate(rows[1:], start=1):
                    columns = row.find_all('td')
                    if len(columns) > 2:
                        number = columns[0].get_text(strip=True)

                        response = ''.join(columns[1].find('font').stripped_strings)

                        prefecture = ''
                        pen_name = ''
                        rank = ''
                        full_text = columns[1].get_text(separator='　', strip=True)
                        match = re.search(r'(.+?)\s+(.+?)(?:さん)?(?:（(.+?)）)?$', full_text)
                        if match:
                            
                            pref_name = match.group(2).split('　')
                            pref_name = [n for n in pref_name if len(n) > 0]
                            for p in pref_name:
                                if p.endswith('東京都') or p.endswith('北海道') or p.endswith('府') or p.endswith('県'):
                                    prefecture = p
                            if prefecture == '':
                                if len(pref_name) > 1:
                                    prefecture = pref_name[-2]
                            pen_name = pref_name[-1]
                            rank = f"（{match.group(3)}）" if match.group(3) else ""

                        if number == '':
                            total_answer_id = -1
                        else:
                            total_answer_id = int(number)

                        # ブログの記事上では、スコア相当の情報としてアンテナの絵文字が付いていた。そのリンク別にスコアに戻す処理をしている。
                        image = columns[2].find('img')['src'] if columns[2].find('img') else ''
                        if image == 'https://cdn-ak.f.st-hatena.com/images/fotolife/a/attey35/20200503/20200503131348.png':
                            score = 3.0
                        elif image == 'https://cdn-ak.f.st-hatena.com/images/fotolife/a/attey35/20200503/20200503131404.png':
                            score = 2.0
                        elif image == 'https://cdn-ak.f.st-hatena.com/images/fotolife/a/attey35/20200503/20200503131357.png':
                            score = 2.5
                        elif image == 'https://cdn-ak.f.st-hatena.com/images/fotolife/a/attey35/20200503/20200503131410.png':
                            score = 1.0
                        elif image.startswith('https://cdn-ak.f.st-hatena.com/images/fotolife/a/attey35/'):
                            score = -1
                        else:
                            score = 0.0

                        award = columns[2].find('font')
                        if award is not None:
                            is_awarded = award.get_text(strip=True)
                        else:
                            is_awarded = ""

                        j = {
                            'episode_id': str(episode_id),
                            'odai_id': odai_id,
                            'total_answer_id': total_answer_id,
                            'answer_id': answer_id,
                            'odai': odai,
                            'response': response,
                            'is_awarded': is_awarded,
                            'prefecture': prefecture,
                            'pen_name': pen_name,
                            'rank': rank, 
                            'score': score
                        }
                        answers.append(j)
    return answers

def main(settings: dict) -> None:
    keitai_data_dir = pathlib.Path(settings["keitai_data_dir_path"])
    crawled_file_dir = keitai_data_dir.joinpath("crawled_html_files")
    crawled_file_dir.mkdir(exist_ok=True)

    special = ['ex1', 'ex2', 'ex3', 'sp1', 'sp2', 'sp3', 'sp4']
    episode_ids = [ f"{i:03}" for i in range(1, 304) ] + special

    df = None
    for episode_id in episode_ids:
        answers = crawl_ktai_ogiri(episode_id=episode_id, crawled_file_dir=crawled_file_dir)
        if len(answers) > 0:
            mdf = pd.DataFrame(answers)
            if df is None:
                df = mdf
            else:
                df = pd.concat([df, mdf])
            
    df = df.reset_index()
    df = df.drop('index', axis=1)
    df['episode_id'] = df['episode_id'].apply(lambda x:str(x))
    df.to_json(keitai_data_dir.joinpath('ktai_all_data.jsonl'), orient='records', lines=True, force_ascii=False)

# %%
if __name__ == "__main__":
    setting_file_path = pathlib.Path(sys.argv[1])
    with open(setting_file_path) as rf:
        settings = json.load(rf)
    
    main(settings=settings)