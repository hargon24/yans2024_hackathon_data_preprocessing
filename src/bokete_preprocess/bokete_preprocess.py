import pandas as pd
import hojichar

import sys
import json
import shutil
import pathlib
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("log")

def normalize(sentence: str) -> str:
    cleaner = hojichar.Compose([
        hojichar.document_filters.DocumentNormalizer(),
        hojichar.document_filters.DiscardAdultContentJa(),
        hojichar.document_filters.DiscardAdultContentEn(),
        hojichar.document_filters.DiscardViolenceContentJa(),
        hojichar.document_filters.DiscardDiscriminationContentJa(),
        hojichar.document_filters.DocumentLengthFilter(min_doc_len=0, max_doc_len=100),
    ])

    sentence = cleaner(sentence)
    return sentence

def set_odai(r: pd.Series, ocrdf: pd.DataFrame) -> str:
    task = r['type']
    if task == "image_to_text":
        odai = "画像で一言"
    else:
        records = ocrdf[ocrdf['image_id']==r['image']]
        if len(records) > 0:
            record = records.iloc[0]
            odai = record['text']
            if task == "image_text_to_text":
                if "[空欄]" not in odai:
                    odai = ""
                else:
                    odai = "[空欄]を穴埋めしてください。\n" + odai
        else:
            odai = ""
    return odai

def calculate_score_sums(df: pd.DataFrame, task_types: list[str]) -> dict[str, dict[str, int]]:
    task_scores = dict()
    for task in task_types:
        odai_scores = dict()
        for image_id, g in df[df["type"]==task].groupby("image"):
            score_sum = g['star'].sum()
            odai_scores[image_id] = score_sum
        task_scores[task] = odai_scores
    return task_scores

def choose_train_data(df: pd.DataFrame, task_scores: dict[str, dict[str, int]], settings: dict) -> pd.DataFrame:
    max_responses = 10
    new_format_list = list()
    odai_id = 0
    original_image_dir = settings["original_dataset_dir"].joinpath("images")

    for task in settings["task_types"].values():
        threshold = settings["ogiri_train_samples"][task]
        image_ids = [ image_id for image_id, sum in sorted(task_scores[task].items(), key=lambda x:x[1], reverse=True)[:threshold] ]

        for image_id, g in df[(df["type"]==task) & (df["image"].isin(image_ids))].groupby('image'):
            odai_id += 1
            responses = list()
            
            for response_id, (i, r) in enumerate(g.sort_values(['star'], ascending=False).iterrows(), start=1):
                if response_id > max_responses:
                    break
                responses.append({"response_id": response_id, "text": r['response'], "score": r["star"]})
            
            if len(responses) > 0:
                file_name = r["file_name"]
                # new_format_list.append({"odai_id": f"ogiri-bokete-{odai_id}", "file_name": file_name, "odai": r["odai"], "type": task, "total_scores": task_scores[task][image_id], "responses": responses})
                new_format_list.append({"odai_id": f"ogiri-bokete-{odai_id}", "file_name": file_name, "odai": r["odai"], "type": task, "responses": responses})

                original_file_path = original_image_dir.joinpath(file_name)
                save_file_path = settings["save_data_dir"].joinpath(file_name)
                shutil.copy(original_file_path, save_file_path)

    ndf = pd.DataFrame(new_format_list)
    return ndf

def main(settings: dict) -> None:
    logger.info(f"load original data from {settings['original_metadata_file']}")
    df = pd.read_json(settings["original_metadata_file"], orient='records', lines=True)
    df["type"] = df["type"].apply(lambda x: settings["task_types"][x])
    df["file_name"] = df['image'].apply(lambda x: f"{x}.jpg")
    df['star'] = df['star'].apply(lambda x: int(str(x).replace(',', '')))

    logger.info("eliminate some harmful responses.")
    df['response'] = df['text'].apply(lambda x: normalize(x))

    logger.info(f"load test_file information from {settings['original_dataset_dir'].joinpath('test_file_names.csv')}")
    test_file_names = pd.read_csv(settings["original_dataset_dir"].joinpath("test_file_names.csv"))

    logger.info(f'load OCR results from {settings["original_dataset_dir"].joinpath("ocr_results.jsonl")}')
    ocrdf = pd.read_json(settings["original_dataset_dir"].joinpath('ocr_results.jsonl'), orient='records', lines=True)
    ocrdf['text'] = ocrdf['text'].apply(lambda x: normalize(x))
    
    df['odai'] = df.apply(set_odai, ocrdf=ocrdf, axis=1)

    sdf = df[(df['response'] != '') & (df['odai'] != '') & (~df["file_name"].isin(test_file_names["file_name"].tolist()))]
    sdf = sdf.reset_index()
    sdf = sdf.drop('index', axis=1)

    task_scores = calculate_score_sums(df=sdf, task_types=settings["task_types"].values())

    logger.info(f"choose the train data ")
    train_df = choose_train_data(sdf, task_scores=task_scores, settings=settings)

    logger.info(f'save these files to {settings["save_data_dir"]}')
    save_json_file = settings["save_data_dir"].joinpath(f'metadata.jsonl')
    train_df.to_json(save_json_file, orient='records', lines=True, force_ascii=False)

    logger.info("finish!")

if __name__ == "__main__":
    setting_file_path = pathlib.Path(sys.argv[1])
    with open(setting_file_path) as rf:
        settings = json.load(rf)
    
    settings["original_dataset_dir"] = pathlib.Path(settings["original_data_dir_path"])
    settings["original_metadata_file"] = settings["original_dataset_dir"].joinpath('jp.jsonl')
    settings["save_data_dir"] = pathlib.Path(settings["ogiri_save_data_dir_path"]).joinpath("train")

    settings["task_types"] = {"I2T": "image_to_text", "T2T": "text_to_text", "IT2T": "image_text_to_text"}
    print(settings)
    
    main(settings)