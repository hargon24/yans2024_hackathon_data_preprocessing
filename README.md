# yans2024_hackathon_data_preprocessing

## 趣旨
YANS2024で実施したハッカソンの大喜利リーダーボードで使う学習データを整理するためのコード集。
テストデータは別のルートで作成済みなので、このコードでは作成できない（しようと思えばできるが…）。

データは以下の2つ
* bokete: boketeのクロールデータを元に作成されたデータ
  * 日本語用のデータを選んだ上で、不適切な表現を除去
  * テキストデータが入っていないため、OCRをしてテキスト抽出
  * テストデータを除いて学習用データを構築。
* keitai: ケータイ大喜利のデータ
  * NHK 『着信御礼! ケータイ大喜利』の過去のお題と回答を有志が整理したブログ記事からクロールしてくるコードを整備
  * HTMLからbs4や正規表現などを使って泥臭くとってくるコードになっているので、一部のテキストは正しく取れてないかもしれない。
  * ブログリンク: https://keitaioogiri.hatenablog.com/entry/work

## 必要なライブラリ
### 共通
* pandas
* tqdm
* huggingface datasets

### bokete用
* hojichar: テキストのクリーニング用
* openai: OCR用
  * 別途OpenAI APIのキーが必要

### ケータイ大喜利用
* beautifulsoup4
* bs4
* requests


## 使い方
### CLoT-jaからbokete-trainへの変換
1. 以下から`images.zip`と`jp.jsonl`をダウンロードする。
https://huggingface.co/datasets/zhongshsh/CLoT-Oogiri-GO

2. 以下のようなディレクトリ構成にしておく。`setting.json`の`original_data_dir_path`には以下の例でいう`original`までの絶対パスを記載しておく。

```
- original
  - images
  - jp.jsonl
```

3. OCRを実行する。OCRのプロンプトは`ocr_prompts.json`に書き込む。結果はステップ2と同じ`settings.json`を使っていれば、ステップ2のoriginalの下に保存される。

```shell
$ python openai_api_ocr.py settings.json ocr_prompts.json
```

4. 以下を実行。
```shell
$ python bokete_preprocess.py settings.json
```

## ケータイ大喜利のクロール

以下を実行すれば取れるはず。
```shell
$ python keitai_crawling.py
```

## setting.jsonの構成
```json
{
    "openai_api_key": "sk-proj-***",
    "openai_api_model_name": "gpt-4o",
    "original_data_dir_path": "/path/to/clot/data",
    "ogiri_save_data_dir_path": "/path/to/bokete-train/save_dir",
    "ogiri_train_samples": {
        "image_to_text": 500,
        "text_to_text": 100,
        "image_text_to_text": 100
    },
    "keitai_data_dir_path": "/path/to/bokete-keitai/save_dir"
}
```
