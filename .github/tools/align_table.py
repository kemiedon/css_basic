import unicodedata

def wide_chars(s):
    width = 0
    for c in s:
        if unicodedata.east_asian_width(c) in ('W', 'F', 'A'):
            width += 2
        else:
            width += 1
    return width

table_data = [
    ["公司名稱", "皇贊公司", "陞醫生醫", "雅菲思國際股份有限公司", "艾萬霖", "訊聯"],
    ["**1. 每cc外泌體濃度**", "3,000億顆", "20億顆", "-", "867億顆", "9.4億顆"],
    ["**2. 產品/服務上市時間**", "鱘龍魚相關保健品（鱘龍骨膠原凍、鱘龍魚精華、鱘骨黑蒜飲等）2016年3月22日", "外泌體應用於護膚保養品相關周邊商品 2020年", "護膚保養品相關周邊商品 2009年11月23日", "專注於外泌體的臨床應用與老化治療 保養品相關產品 2020年12月", "細胞治療與儲存 外泌體產品 精準健康&基因檢測 委託研究與製造 2007年7月"],
    ["**3. 市場區隔**", "BtoC、妝品原料、醫美、代理商", "For 醫美機構", "For 醫美機構", "For 醫美機構", "For 醫美機構"],
    ["**4. 行銷通路**", "吳淡如（大咖團購）、團購主（一般團購）、妝品原料、醫美、代理商", "高端醫美通路", "半醫療半美容市場", "高端頭皮修護市場", "醫療美容院線"],
    ["**5. 技術或服務優勢**", "源自鱘龍魚體表天然防護系統的分泌型外泌體科技，結合高穩定性、高純度與高度親膚特性，為護膚應用帶來全新生物科技解決方案。", "源自「生化脈衝」技術：透過專利感應方式，製造出多種功效（如抗老化、分裂修復、生髮）的外泌體。取得國際INCI名稱認證", "與訊聯合作代理美容版本", "高濃度外泌體＋胜肽複合配方，針對頭皮再生，取得衛福部「人源外泌體」化妝品原料核准，同時取得國際INCI名稱認證", "賦活修護、肌膚再生系列，取得衛福部「人源外泌體」化妝品原料核准，同時取得國際INCI名稱認證"]
]

# Calculate max widths
col_widths = [0] * len(table_data[0])
for row in table_data:
    for i, cell in enumerate(row):
        w = wide_chars(cell)
        if w > col_widths[i]:
            col_widths[i] = w

output = ""

# Print Header
header = "|"
for i, cell in enumerate(table_data[0]):
    w = wide_chars(cell)
    padding = col_widths[i] - w
    header += " " + cell + " " * padding + " |"
output += header + "\n"

# Print Separator
separator = "|"
for i in range(len(table_data[0])):
    separator += " " + ":" + "-" * (col_widths[i] - 1) + " |"
output += separator + "\n"

# Print Body
for row in table_data[1:]:
    line = "|"
    for i, cell in enumerate(row):
        w = wide_chars(cell)
        padding = col_widths[i] - w
        line += " " + cell + " " * padding + " |"
    output += line + "\n"

with open('aligned_table.txt', 'w', encoding='utf-8') as f:
    f.write(output)
print("Aligned table written to aligned_table.txt")
