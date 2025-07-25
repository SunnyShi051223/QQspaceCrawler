import os
import json

def save_content(qq, contents):
    os.makedirs('data', exist_ok=True)
    file_path = os.path.join('data', f'{qq}_shuoshuo.json')
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(contents, f, ensure_ascii=False, indent=2)