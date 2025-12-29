import os
import json
import time
import requests
from const import API_KEY, API_LINK, COMPANIES, ENDPOINTS
from pathlib import Path
from enum import Enum

lst = []


def call_api(endpoint, params, corp_code):
    res = requests.get(API_LINK + endpoint, params={'crtfc_key': API_KEY, 'corp_code':corp_code, **params})
    return res.json()

def save_json(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    # 전체 기업 리스트
    for corp_code, corp_name, _, _ in COMPANIES:
        # 엔드포인트 (지금은 재무재표만)
        # endpoint : fnlttSinglAcntAll.json
        # params:
        #   'endpoint':'', 
        #   'crtfc_key':API_KEY, 
        #   'bsns_year':'2024', 
        #   'reprt_code':'11011', 
        #   'fs_div':'OFS'
        for endpoint, params in ENDPOINTS:
            data = call_api(endpoint, params, corp_code)
            if data['status'] == '000':
                time.sleep(.1)
                save_json(data, f'json/{corp_code}_{corp_name}_CFS.json')
                print(f'저장: {corp_code}_{corp_name}_CFS')
            else:
                print(f'실패: {data['status']}_{corp_code}_{corp_name}_CFS')
                lst.append(corp_code)
        print(lst)
if __name__ == '__main__':
    main()