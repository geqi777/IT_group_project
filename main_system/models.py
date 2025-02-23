from telnetlib import STATUS

from django.db import models
from django.utils import timezone
import datetime
from django.core.validators import MinValueValidator, MaxValueValidator
from main_system.utils.map_function import get_lat_lng_from_address


# 订阅
class Subscription(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)  #email不重复
    created_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.email}"

# 商品
class Product(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('locked', 'Locked'),
    ]

    CATEGORY_CHOICES = [
        ("clothing", "Clothing"),
        ("food", "Food"),
        ("furniture", "Furniture"),
        ("accessories", "Accessories"),
        ("gift", "Gift"),
    ]
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=64, choices=CATEGORY_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    stock = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    picture = models.ImageField(upload_to='static/image/products/', blank=True, null=True)
    created_time = models.DateTimeField(auto_now_add=True)
    updated_time = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # 自动调整产品状态
        if self.stock == 0:
            self.status = 'Locked'
        super().save(*args, **kwargs)

    def is_available(self):
        # 检查商品是否可用
        return self.status == 'active' and self.stock > 0

    def __str__(self):
        return self.name


# 性别选择
gender_choice = [
    (1, 'Male'),
    (2, 'Female'),
    (3, 'Other'),
    (4, "Don't want to say"),
    (5, "Unknown")
]

# 管理员
class Operator(models.Model):
    name = models.CharField(max_length=50)
    date_of_birth = models.DateField(default=datetime.date.today)
    gender = models.IntegerField(choices=gender_choice, default=5)
    email = models.EmailField()
    phone = models.CharField(max_length=50)
    account = models.CharField(max_length=50, unique=True)  # 账号必须唯一
    password = models.CharField(max_length=50)
    is_operator = models.BooleanField(default=False)
    role = models.CharField(max_length=50)
    join_time = models.DateField(default=datetime.date.today)

    def __str__(self):
        return f"{self.name} - {self.role}"


# 用户
class User(models.Model):
    name = models.CharField(max_length=50)
    date_of_birth = models.DateField(default=datetime.date.today)
    gender = models.IntegerField(choices=gender_choice, default=5)
    email = models.EmailField()
    phone = models.CharField(max_length=50, null=True, blank=True)
    address = models.CharField(max_length=50, null=True, blank=True)
    account = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=50)
    create_time = models.DateTimeField(default=timezone.now)

    # User 关联 Wallet (1:1)
    wallet_balance = models.FloatField(default=0.0)
    wallet = models.OneToOneField('Wallet', on_delete=models.CASCADE, null=True, blank=True)

    # User 关联 PaymentCard (1:n)
    payment_cards = models.ManyToManyField('PaymentCard', blank=True)

    # User 关联 Coupon (1:n)
    coupons = models.ManyToManyField('Coupon', blank=True)

    def deduct_balance(self, amount):
        """ 从钱包中扣除余额 """
        if self.wallet and self.wallet.balance >= amount:
            self.wallet.balance -= amount
            self.wallet.save()
            return True
        return False

    def __str__(self):
        return self.name


# 钱包(balance & points)
class Wallet(models.Model):
    user = models.OneToOneField('User', on_delete=models.CASCADE, null=True, blank=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, validators=[MinValueValidator(0.0)])
    points = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    def add_balance(self, amount):
        """ 增加余额 """
        self.balance += amount
        self.save()

    def add_points(self, points):
        """ 增加积分 """
        self.points += points
        self.save()

    def deduct_points(self, points):
        """ 扣除积分 """
        if self.points >= points:
            self.points -= points
            self.save()
            return True
        return False

    def __str__(self):
        return f"Wallet of {self.user.name}"

# 钱包交易记录(充值，消费，退款，优惠券使用)
class WalletTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('topup', 'Topup'),
        ('withdraw', 'Withdraw'),
        ('purchase', 'Purchase'),
        ('refund', 'Refund'),
        ('points_increase', 'Points Increase'),
        ('points_decrease', 'Points Decrease'),
        ('coupon_addition', 'Coupon Addition'),
        ('coupon_deduction', 'Coupon Deduction'),
        ('coupon_expired', 'Coupon Expired'),
    ]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)  # 充值、扣款、积分兑换等
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Only for balance changes
    points = models.IntegerField(null=True, blank=True)  # Only for points changes
    coupon = models.ForeignKey('Coupon', null=True, blank=True, on_delete=models.SET_NULL, related_name="used_transactions")  # For payment with coupon
    payment_card = models.ForeignKey('PaymentCard', null=True, blank=True, on_delete=models.SET_NULL, related_name="transactions")
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.transaction_type.capitalize()} - {self.wallet.user.name}"


# 优惠券
class Coupon(models.Model):
    wallet = models.ForeignKey('Wallet', on_delete=models.CASCADE, null=True, blank=True, related_name='coupons')
    code = models.CharField(max_length=10, unique=True)
    discount = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(0.01)])
    expiry_date = models.DateField(null=True, blank=True)
    min_order_value = models.DecimalField(max_digits=6, decimal_places=2, default=10.00, validators=[MinValueValidator(0.01)])
    max_activations = models.IntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(50)])
    created_time = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=32, choices=[('active', 'Active'), ('used', 'Used'), ('expired', 'Expired')])

    def is_valid(self):
        """Check if the coupon is valid for a specific user"""
        return self.status == 'active' and self.expiry_date >= timezone.now().date()

    def __str__(self):
        return f"Coupon {self.code} - {self.status}"

# 支付卡
class PaymentCard(models.Model):
    wallet = models.ForeignKey('Wallet', on_delete=models.CASCADE, null=True, blank=True, related_name='payment_cards')
    card_number = models.CharField(max_length=16, unique=True)
    expiry_date = models.CharField(max_length=5)  # Format: MM/YY
    cvv = models.CharField(max_length=4)  # 支持3-4位CVV
    nickname = models.CharField(max_length=50, null=True, blank=True)  # Optional nickname
    country = models.CharField(max_length=50)
    postcode = models.CharField(max_length=50)
    created_time = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.nickname or 'Card'} - {self.card_number[-4:]}"







class Customer(models.Model):
    name = models.CharField(max_length=50)
    email = models.EmailField()
    date_of_birth = models.DateField(default=datetime.date.today)
    gender = models.IntegerField(choices=gender_choice, default=5)
    phone = models.CharField(max_length=50, null=True, blank=True)
    address = models.CharField(max_length=50, null=True, blank=True)
    account = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=50)
    account_balance = models.FloatField(default=0.0)
    create_time = models.DateTimeField(default=timezone.now)
    is_verified = models.BooleanField(default=False)
    trip_points = models.IntegerField(default=0)
    coupons = models.ManyToManyField(Coupon, blank=True)

    # 添加 driver_license 字段
    driver_license = models.ImageField(upload_to='customer/license/', null=True, blank=True)

    def deduct_points(self, points):
        if self.trip_points >= points:
            self.trip_points -= points
            self.save()
            return True
        return False


class Employee(models.Model):
    name = models.CharField(max_length=50)
    date_of_birth = models.DateField(default=datetime.date.today)
    gender = models.IntegerField(choices=gender_choice, default=5)
    email = models.EmailField()
    phone = models.CharField(max_length=50)
    address = models.CharField(max_length=50)
    account = models.CharField(max_length=50, unique=True)  # 账号必须唯一
    password = models.CharField(max_length=50)
    is_employee = models.BooleanField(default=False)
    role = models.CharField(max_length=50)
    join_time = models.DateField(default=datetime.date.today)
    department = models.ForeignKey('Department', null=True, blank=True, on_delete=models.CASCADE)  # 使用大写引用


class Vehicle(models.Model):
    name = models.CharField(max_length=50)
    power = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    price = models.IntegerField(default=0)

    SITUATION_CHOICES = [
        ('very_poor', 'Very Poor'),
        ('poor', 'Poor'),
        ('average', 'Average'),
        ('good', 'Good'),
        ('excellent', 'Excellent'),
    ]
    situation = models.CharField(max_length=50, choices=SITUATION_CHOICES)

    VEHICLE_TYPE_CHOICES = [
        ('electric_car', 'Electric Car'),
        ('scooter', 'Scooter'),
        ('e_bike', 'E-bike'),
    ]
    vehicle_type = models.CharField(max_length=50, choices=VEHICLE_TYPE_CHOICES)
    vehicle_number = models.CharField(max_length=50, unique=True)

    is_available = models.BooleanField(default=True)
    rental_time = models.DateTimeField(null=True, blank=True)

    # 车辆的地理位置
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    user = models.ForeignKey(to='Customer', null=True, blank=True, on_delete=models.CASCADE)
    luggage = models.IntegerField(default=1, null=True, blank=True)
    capacity = models.IntegerField(default=1, null=True, blank=True)
    marks = models.IntegerField(default=5)

    needs_charging = models.BooleanField(default=False)  # 是否需要充电
    needs_repair = models.BooleanField(default=False)  # 是否需要维修

    damaged_part = models.TextField(blank=True, default='')  # 维修部位
    location = models.CharField(max_length=255, null=True, blank=True)  # 关联地点

    def save(self, *args, **kwargs):
        # 如果有用户在使用车辆，车辆不可用，且设置租赁时间
        if self.user_id is not None:
            self.is_available = False
            if self.rental_time is None:
                self.rental_time = timezone.now()
        else:
            self.is_available = True
            self.rental_time = None

        # 需要充电的逻辑
        if self.power < 20:
            self.needs_charging = True
            self.is_available = False
        else:
            self.needs_charging = False

        # 需要维修的逻辑
        if self.situation in ['Very Poor', 'Poor']:
            self.needs_repair = True
            self.is_available = False
        else:
            self.needs_repair = False

        # 保存更新
        super().save(*args, **kwargs)


class Department(models.Model):
    name = models.CharField(max_length=50, unique=True)  # 部门名称最好唯一

    def __str__(self):
        return self.name


class Location(models.Model):
    name = models.CharField(max_length=100)  # 地点名称
    supports_repair = models.BooleanField(default=False)  # 是否支持维修
    supports_charging = models.BooleanField(default=False)  # 是否支持充电
    address = models.CharField(max_length=255, blank=True, null=True)  # 地址字段
    capacity = models.PositiveIntegerField(default=50)  # 地点可容纳的车辆数量

    # 新增字段，存储经纬度
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # 如果有地址但没有经纬度，则通过地址获取经纬度
        if self.address and (not self.latitude or not self.longitude):
            self.latitude, self.longitude = get_lat_lng_from_address(self.address)
        super().save(*args, **kwargs)

    def get_remaining_capacity(self):
        # 假设有一个车辆模型与位置关联，可以计算当前车辆数
        current_vehicle_count = Vehicle.objects.filter(latitude=self.latitude, longitude=self.longitude).count()
        return self.capacity - current_vehicle_count


class Card(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='cards')
    card_number = models.CharField(max_length=16, unique=True)
    expiry_date = models.CharField(max_length=5)  # Format: MM/YY
    cvv = models.CharField(max_length=4)  # 支持3-4位CVV
    nickname = models.CharField(max_length=50, null=True, blank=True)  # Optional nickname
    country = models.CharField(max_length=50)
    postcode = models.CharField(max_length=50)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.nickname or 'Card'} ending in {self.card_number[-4:]}"

        # return f"{self.user} - {self.vehicle} ({self.start_time} - {self.end_time})"

class TopupHistory(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="topup_histories")  # 用户字段
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # 金额字段
    date = models.DateTimeField(auto_now_add=True)  # 充值时间
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name="topup_histories")  # 指向 Card 模型的外键


class WalletHistory(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('top_up', 'Top Up'),
        ('payment', 'Payment'),
        ('points_increase', 'Points Increase'),
        ('points_exchange', 'Points Exchange'),
        ('coupon_addition', 'Coupon Addition'),
        ('coupon_deduction', 'Coupon Deduction'),
        ('coupon_expired', 'Coupon Expired')
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='wallet_history')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)  # 充值、扣款、积分兑换等
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Only for balance changes
    trip_points = models.IntegerField(null=True, blank=True)  # Only for trip points changes
    date = models.DateTimeField(auto_now_add=True)
    top_up = models.ForeignKey(TopupHistory, null=True, blank=True, on_delete=models.SET_NULL, related_name="wallet_transactions")  # For top up
    coupon = models.ForeignKey(Coupon, null=True, blank=True, on_delete=models.SET_NULL, related_name="wallet_usages")  # For payment with coupon
    details = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.transaction_type.capitalize()} - {self.customer.name}"


class History(models.Model):
    STATUS_CHOICES = (
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
    )

    user = models.ForeignKey('Customer', on_delete=models.CASCADE, related_name='history')  # 用户的历史记录
    vehicle = models.ForeignKey('Vehicle', on_delete=models.CASCADE, related_name='histories')  # 车辆的历史记录

    # 时间和费用
    start_time = models.DateTimeField(default=timezone.now)  # 开始时间
    end_time = models.DateTimeField(null=True, blank=True)  # 结束时间，允许为空
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # 位置记录
    start_location_name = models.CharField(max_length=255)  # 开始地址名称
    start_location_latitude = models.FloatField()  # 开始地址纬度
    start_location_longitude = models.FloatField()  # 开始地址经度

    end_location_name = models.CharField(max_length=255, blank=True, null=True)  # 结束地址名称，允许为空
    end_location_latitude = models.FloatField(blank=True, null=True)  # 结束地址纬度，允许为空
    end_location_longitude = models.FloatField(blank=True, null=True)  # 结束地址经度，允许为空

    # 持续时间，确保是 timedelta 对象
    duration = models.DurationField(null=True, blank=True)  # 如果可能为空，确保在赋值前处理为 timedelta 对象
    distance = models.CharField(max_length=20, default='0 km', blank=True)  # 不需要 null=True，默认 0 即可

    # 车辆状态和租赁状态
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ongoing')  # 状态，默认进行中
    rating = models.PositiveSmallIntegerField(default=5)  # 用户评分，假设满分为 5
    review = models.TextField(blank=True, null=True)  # 用户评价，允许为空

    def __str__(self):
        return f"History for {self.vehicle.name} by {self.user.name} (Status: {self.status})"


class VehicleReport(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    history = models.ForeignKey(History, on_delete=models.CASCADE)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Report for {self.vehicle.name} on {self.created_at}'
