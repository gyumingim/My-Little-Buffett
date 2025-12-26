import xml.etree.ElementTree as ET

def generate_companies_list(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    companies = []
    for node in root.findall('list'):
        corp_code = node.findtext('corp_code')
        corp_name = node.findtext('corp_name')
        stock_code = node.findtext('stock_code').strip()
        
        # 종목코드가 있는 상장사만 포함
        if stock_code:
            # (고유번호, 기업명, 종목코드, 업종-임시값)
            companies.append((corp_code, corp_name, stock_code, "미분류"))
            
    return companies

result_companies = generate_companies_list('CORPCODE.xml')
print(result_companies)
with open('companies_data.py', 'w', encoding='utf-8') as f:
    f.write("COMPANIES = [\n")
    for c in result_companies:
        f.write(f'    ("{c[0]}", "{c[1]}", "{c[2]}", "{c[3]}"),\n')
    f.write("]\n")
print(f"총 {len(result_companies)}개의 상장사 데이터를 'companies_data.py'로 저장했습니다.")