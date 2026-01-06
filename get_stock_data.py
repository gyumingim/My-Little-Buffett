import json
import requests
from const import API_LINK, COMPANIES, ENDPOINTS

def main():
    for e, p, name in ENDPOINTS:
        for c, n, _, _ in COMPANIES:
            filename = f'{c}_{n}_{name}.json'
            res = requests.get(API_LINK + e, params={'corp_code': c, **p})
            data = res.json()
            
            if data['status'] == '000':
                with open(f'json/{name}/{filename}', 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f'저장: {n}')
            else:
                print(f'없어용: {n}')

if __name__ == '__main__':
    main()