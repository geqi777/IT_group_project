# 电子商务平台

## 项目概述

这是一个功能完整的电子商务平台，支持用户购物、支付、订单管理、退货处理以及积分系统等功能。该项目基于Django框架构建，提供了丰富的功能模块，适合中小型电商业务使用。

## 主要功能

### 用户端
- **账户管理**：注册、登录、个人资料管理
- **商品浏览**：分类查看、搜索、筛选
- **购物车**：添加商品、调整数量、移除商品
- **订单处理**：提交订单、支付、查看订单状态
- **钱包系统**：余额充值、积分管理
- **退货系统**：申请退货、查看退货状态
- **评价系统**：对已购商品进行评价、查看评价

### 管理员端
- **商品管理**：添加、编辑、删除商品
- **订单管理**：查看订单、更新订单状态
- **用户管理**：查看用户信息、管理用户账户
- **退货管理**：处理退货申请、确认退款
- **促销管理**：创建和管理促销码
- **统计分析**：销售数据统计、订单分析、评价分析

## 技术栈

- **后端**：Django 4.2
- **前端**：HTML, CSS, JavaScript, Bootstrap 5
- **数据库**：MySQL/PostgreSQL
- **支付集成**：模拟支付系统
- **部署**：支持PythonAnywhere, Render, AWS, Google Cloud等

## 安装指南

### 前提条件
- Python 3.9+
- pip (Python包管理器)
- 虚拟环境工具 (推荐: venv或virtualenv)
- MySQL或PostgreSQL数据库

### 本地开发环境设置

1. **克隆仓库**
   ```bash
   git clone https://github.com/your-username/IT_group_project.git
   cd IT_group_project
   ```

2. **创建并激活虚拟环境**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **配置环境变量**
   创建`.env`文件并添加以下配置:
   ```
   DEBUG=True
   SECRET_KEY=your_secret_key
   DATABASE_URL=mysql://user:password@localhost:3306/dbname
   ```

5. **数据库迁移**
   ```bash
   python manage.py migrate
   ```

6. **创建超级用户**
   ```bash
   python manage.py createsuperuser
   ```

7. **启动开发服务器**
   ```bash
   python manage.py runserver
   ```

## 部署指南

### 部署到PythonAnywhere

1. **注册PythonAnywhere账号**
   访问[PythonAnywhere](https://www.pythonanywhere.com/)并注册

2. **上传代码**
   使用Git或上传ZIP文件
   ```bash
   git clone https://github.com/your-username/IT_group_project.git
   ```

3. **创建虚拟环境并安装依赖**
   ```bash
   mkvirtualenv --python=python3.9 shop_env
   workon shop_env
   cd IT_group_project
   pip install -r requirements.txt
   ```

4. **配置Web应用**
   - 在PythonAnywhere仪表板中添加新的Web应用
   - 选择"Manual configuration"和Python 3.9
   - 设置虚拟环境路径
   - 配置WSGI文件
   - 设置静态文件路径

5. **配置数据库**
   - 创建MySQL数据库
   - 更新settings.py中的数据库配置
   - 运行迁移
   ```bash
   python manage.py migrate
   ```

6. **收集静态文件**
   ```bash
   python manage.py collectstatic
   ```

7. **重启Web应用**

详细部署指南请参考文档：[部署指南](docs/deployment.md)

## 项目截图

![首页](docs/images/homepage.png)
![商品列表](docs/images/products.png)
![购物车](docs/images/cart.png)
![管理后台](docs/images/admin.png)

## 贡献指南

我们欢迎社区贡献，请遵循以下步骤：

1. Fork项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

## 许可证

本项目采用MIT许可证 - 详见[LICENSE](LICENSE)文件

## 联系方式

项目维护者 - [your-email@example.com](mailto:your-email@example.com)

---

© 2023 电子商务平台团队
