from openai import OpenAI
import pandas as pd
import base64
import pathlib
import json
import sys

def encode_image(image_path: pathlib.Path) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def send_openai_api(image_path: pathlib.Path, prompt: str, openai_client: OpenAI, model_name: str) -> str:
    base64_image = encode_image(image_path=image_path)
    try:
        response = openai_client.chat.completions.create(
            model=model_name,
            messages=[
                {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                    }
                ]
                }
            ],
            max_tokens=300
        )
        return response
    except:
        return None

def load_ocr_results(ocr_save_file_path: pathlib.Path) -> list[int]:
    ocr_finished_image_names = list()
    if ocr_save_file_path.exists():
        ordf = pd.read_json(ocr_save_file_path, orient='records', lines=True)
        if 'image_id' in ordf.columns:
            ocr_finished_image_names = ordf['image_id'].unique().tolist()
        print(f'{len(ocr_finished_image_names)} files are already OCRed.')
    else:
        ocr_save_file_path.touch()
        print(f'{ocr_save_file_path} is generated.')
    return ocr_finished_image_names

def main(openai_client: OpenAI, settings: dict) -> None:
    df = pd.read_json(settings["original_metadata_file"], orient='record', lines=True)
    
    ocr_save_file_path = pathlib.Path(settings["original_dataset_dir"].joinpath('ocr_results.jsonl'))
    ocr_finished_image_names = load_ocr_results(ocr_save_file_path=ocr_save_file_path)

    image_dir = settings["original_dataset_dir"].joinpath('images')
    for i, r in df[df['type']!='I2T'].sort_values('image').iterrows():
        image_id = r["image"]
        if image_id in ocr_finished_image_names:
            continue

        task_type = r["type"]
        prompt = prompts[task_type]

        image_path = image_dir.joinpath(f'{image_id}.jpg')
        api_response = send_openai_api(image_path=image_path, prompt=prompt, openai_client=openai_client, model_name=settings["openai_api_model_name"])
        if api_response is not None:
            ocr_result = {'image_id': int(image_id), 'text': api_response.choices[0].message.content, 'image_token_size': api_response.usage.prompt_tokens}
            with open(ocr_save_file_path, 'a', encoding='utf-8') as af:
                json.dump(ocr_result, af, ensure_ascii=False)
                af.write('\n')

            ocr_finished_image_names.append(image_id)
            print(f'{i}, the image file {image_id} was OCRed')

if __name__ == "__main__":
    setting_file_path = pathlib.Path(sys.argv[1])
    with open(setting_file_path) as rf:
        settings = json.load(rf)

    prompt_file_path = pathlib.Path(sys.argv[2])
    with open(prompt_file_path) as rf:
        prompts = json.load(rf)

    client = OpenAI(api_key=settings["openai_api_key"])

    settings["original_dataset_dir"] = pathlib.Path(settings["original_data_dir_path"])
    settings["original_metadata_file"] = settings["original_dataset_dir"].joinpath('jp.jsonl')

    main(openai_client=client, settings=settings)