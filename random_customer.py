import pandas as pd
import random
from faker import Faker
import hashlib
import sqlite3
import string
import datetime

fake = Faker('en_GB')

# 生成未加密密码
def generate_custom_password(length=8):
    if length < 8:
        raise ValueError("密码长度不能少于 8 位")

    uppercase_letter = random.choice(string.ascii_uppercase)
    lowercase_letter = random.choice(string.ascii_lowercase)
    numbers = ''.join(random.choices(string.digits, k=length - 2))
    password = uppercase_letter + lowercase_letter + numbers
    return password

# MD5 加密
def md5(data):
    SECRET_KEY = 'django-insecure-*qpp)07*j2%tua^fjlk!kj3v2mx+_2$89tni(-ou*zk86*(y9%'
    obj = hashlib.md5(SECRET_KEY.encode('utf-8'))
    obj.update(data.encode('utf-8'))
    return obj.hexdigest()

# 获取表中的最大 id
def get_max_id_from_db(table_name, conn):
    query = f"SELECT MAX(id) as max_id FROM {table_name}"
    result = pd.read_sql_query(query, conn)
    return result['max_id'].iloc[0] if result['max_id'].iloc[0] is not None else 0

# 生成客户数据并保存未加密的密码到 Excel
def generate_customers_and_save_to_excel(num_records, excel_file, max_id):
    data = []
    for i in range(num_records):
        id = max_id + i + 1  # 从最大 id 开始递增
        name = fake.name()
        email = fake.email()
        date_of_birth = fake.date_of_birth(minimum_age=18, maximum_age=80).strftime('%Y-%m-%d')
        gender = random.choice([0, 1])
        phone = '0' + ''.join(random.choices('0123456789', k=10))
        address = fake.address().replace('\n', ', ')
        account = f"{name.lower().replace(' ', '_')}_{random.randint(1000, 9999)}"
        password = generate_custom_password()  # 未加密密码
        account_balance = random.randint(0, 100000)
        create_time = datetime.datetime.now().isoformat()
        is_verified = random.choice([True])
        trip_points = random.randint(0, 1000)
        driver_license = 'customer/license/example_license.png'

        data.append({
            'id': id,  # 使用递增的 id
            'name': name,
            'email': email,
            'date_of_birth': date_of_birth,
            'gender': gender,
            'phone': phone,
            'address': address,
            'account': account,
            'password': password,  # 未加密密码
            'account_balance': account_balance,
            'create_time': create_time,
            'is_verified': is_verified,
            'trip_points': trip_points,
            'driver_license': driver_license
        })

    # 将未加密密码数据保存到 Excel
    df = pd.DataFrame(data)
    df.to_excel(excel_file, index=False)
    print(f"未加密的密码数据已保存到 {excel_file}")
    return df

# 读取未加密密码的数据，加密密码并保存到数据库
def encrypt_passwords_and_save_to_db(df, table_name, conn):
    # 加密密码
    df['password'] = df['password'].apply(md5)

    # 将加密后的数据保存到数据库
    df.to_sql(table_name, conn, if_exists='append', index=False)
    print(f"数据已成功保存到 {table_name} 数据表中")

# 连接到 SQLite 数据库
conn = sqlite3.connect('new_e_vehicle_share_system.sqlite3')  # 替换为你的数据库路径

# 获取现有表中的最大 id
max_id = get_max_id_from_db('main_system_customer', conn)

# 生成客户数据并保存未加密密码到 Excel
df_unencrypted = generate_customers_and_save_to_excel(50, 'customers_unencrypted.xlsx', max_id)

# 将加密后的数据保存到数据库
encrypt_passwords_and_save_to_db(df_unencrypted, 'main_system_customer', conn)

# 关闭数据库连接
conn.close()
