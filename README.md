# Project Name

## Introduction
This is a web application based on the Django framework, designed to provide a comprehensive e-commerce solution. The core features of the project include:

- **User Registration and Login**: Supports user account creation and secure login.
- **Shopping Cart Management**: Users can add products to the cart and proceed to checkout.
- **Order Management**: Users can view and manage their order history.
- **Product Display**: Provides detailed product information and category browsing features.
- **Admin Panel**: Administrators can manage users, orders, and product information.

The project aims to offer a seamless shopping experience for users and convenient management tools for administrators.

## Installation

### Requirements
- **Operating System**: Windows, macOS, Linux
- **Python**: 3.6 or higher
- **Django**: 4.2.7
- **Database**: SQLite3 (default), can also be configured to use PostgreSQL or MySQL
- **Other Python Libraries**:
  - `asgiref`
  - `Brotli`
  - `certifi`
  - `charset-normalizer`
  - `colorama`
  - `contourpy==1.3.0`
  - `crispy-bootstrap5==0.7`
  - `cycler==0.12.1`
  - `django-crispy-forms==2.0`
  - `et-xmlfile==1.1.0`
  - `Faker`
  - `fonttools==4.54.1`
  - `idna==3.10`
  - `iniconfig`
  - `kiwisolver==1.4.7`
  - `matplotlib==3.9.2`
  - `mysqlclient`
  - `numpy==2.1.2`
  - `openpyxl==3.1.5`
  - `packaging==24.1`
  - `pandas==2.2.3`
  - `pillow==10.4.0`
  - `pluggy`
  - `pyotp==2.9.0`
  - `pyparsing==3.2.0`
  - `PySocks`
  - `pytest`
  - `python-dateutil`
  - `pytz==2024.2`
  - `requests`
  - `setuptools==75.1.0`
  - `six`
  - `sqlparse==0.5.1`
  - `typing_extensions`
  - `tzdata==2024.2`
  - `urllib3`
  - `wheel==0.44.0`
  - `win-inet-pton`
  - `xlrd`

### Installation Steps
1. Clone the repository to your local machine:
   ```bash
   git clone <repository-url>
   ```
2. Navigate to the project directory:
   ```bash
   cd IT_group_project
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run database migrations:
   ```bash
   python manage.py migrate
   ```
5. Start the development server:
   ```bash
   python manage.py runserver
   ```

## Usage
- Visit `http://127.0.0.1:8000/` to view the homepage.
- Register a new user or log in with an existing account.
- Manage personal information and orders in the user panel.

## Directory Structure
```
IT_group_project/
│
├── main_system/          # Main application directory
│   ├── templates/        # HTML template files
│   ├── views/            # View functions
│   ├── models.py         # Data models
│   └── urls.py           # URL configuration
│
├── media/                # Media files
│
├── manage.py             # Django management script
├── requirements.txt      # Python dependencies
└── README.md             # Project documentation
```
