import sqlite3
import pandas as pd
from decimal import Decimal
from datetime import datetime
import os

# 你的文件路径（请先上传文件）
file_paths = ["crackers.csv", "Gift sets.csv", "milk.csv"]

# 读取所有 Excel 文件
dfs = [pd.read_csv(file) for file in file_paths]

# 按行合并
merged_df = pd.concat(dfs, ignore_index=True)

# 保存合并后的 Excel 文件
merged_df.to_csv("merged.csv", index=False)

print("合并完成，已保存为 merged.xlsx")

# **连接到 SQLite 数据库**
db_path = r"new_unicraft_system.sqlite3"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# **读取 CSV**
df = pd.read_csv("merged.csv")
current_id = 1

# **遍历 DataFrame 并插入数据**
for _, row in df.iterrows():
    # print(row["picture"])
    try:
        cursor.execute("""
            INSERT INTO main_system_product
            (id,name, description, category, price, stock, status, picture, created_time, updated_time)
            VALUES (?,?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            current_id,
            row["name"],
            row.get("description", ""),  # 允许空值
            row["category"],
            float(row["price"]),  # 确保 price 是 float
            int(row["stock"]),  # 确保 stock 是 int
            row["status"],
            row.get("picture", ""),  # 允许空值
            row["created_time"],
            row["updated_time"]
        ))
        current_id+=1
    except Exception as e:
        print(f"❌ 插入失败: {e}")

# **提交更改并关闭数据库连接**
conn.commit()
conn.close()

print("✅ CSV 数据已成功写入 SQLite 数据库！")
