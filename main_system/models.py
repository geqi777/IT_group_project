from telnetlib import STATUS

from django.db import models
from django.utils import timezone
import datetime
from django.core.validators import MinValueValidator, MaxValueValidator
from main_system.utils.map_function import get_lat_lng_from_address
from decimal import Decimal


# 订阅
class Subscription(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)  #email不重复
    created_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.email}"

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
    # wallet = models.OneToOneField('Wallet', on_delete=models.CASCADE, null=True, blank=True)

    # User 关联 PaymentCard (1:n)
    payment_cards = models.ManyToManyField('PaymentCard', blank=True)

    # User 关联 Coupon (1:n)
    coupons = models.ManyToManyField('Coupon', blank=True)

    @property
    def wallet_balance(self):
        """获取用户钱包余额"""
        wallet = Wallet.objects.filter(user=self).first()
        return wallet.balance if wallet else Decimal('0.00')

    def deduct_balance(self, amount):
        """从钱包中扣除余额"""
        wallet = Wallet.objects.filter(user=self).first()
        if wallet and wallet.balance >= amount:
            wallet.balance -= amount
            wallet.save()
            return True
        return False

    def __str__(self):
        return self.name


# 钱包(balance & points)
class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
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

# 钱包交易记录(充值，消费，退款，积分变动，优惠码使用)
class WalletTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('topup', 'topup'),
        ('purchase', 'purchase'),
        ('refund', 'refund'),
        ('points_earned', 'points earned'),
        ('points_used', 'points used'),
        ('promo_code_used', 'promo code used'),
    ]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # 金额变动
    points = models.IntegerField(null=True, blank=True)  # 积分变动
    order = models.ForeignKey('Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')  # 关联订单
    promo_code = models.ForeignKey('PromoCode', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')  # 关联优惠码
    payment_card = models.ForeignKey('PaymentCard', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')  # 关联支付卡
    original_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # 优惠前金额
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # 优惠后金额
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.wallet.user.name} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"

    class Meta:
        ordering = ['-timestamp']
        verbose_name = '钱包交易记录'
        verbose_name_plural = '钱包交易记录'


# 优惠码
class PromoCode(models.Model):
    code = models.CharField(max_length=10, unique=True)
    discount = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(0.01)])
    min_order_value = models.DecimalField(max_digits=6, decimal_places=2, default=10.00, validators=[MinValueValidator(0.01)])
    expiry_date = models.DateTimeField()
    created_time = models.DateTimeField(default=timezone.now)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=32, choices=[('active', 'active'), ('inactive', 'inactive'), ('expired', 'expired')], default='active')

    def is_valid(self):
        """检查优惠码是否有效"""
        return self.status == 'active' and self.expiry_date > timezone.now().date()

    def __str__(self):
        return f"PromoCode: {self.code} (£{self.discount})"


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


# 商品
class Product(models.Model):
    STATUS_CHOICES = [
        ('active', 'active'),
        ('locked', 'locked'),
    ]

    CATEGORY_CHOICES = [
        ('clothing', 'clothing'),
        ('food', 'food'),
        ('home', 'home & living'),
        ('accessories', 'accessories'),
        ('art', 'art'),
        ('toys', 'toys & games'),
        ('tools', 'craft supplies & tools'),
        ('gift', 'gift'),
    ]
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=64, choices=CATEGORY_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    stock = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    picture = models.ImageField(upload_to='media/image/products/', blank=True, null=True)
    created_time = models.DateTimeField(auto_now_add=True)
    updated_time = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # 自动调整产品状态
        if self.stock == 0:
            self.status = 'locked'
        super().save(*args, **kwargs)

    def is_available(self):
        # 检查商品是否可用
        return self.status == 'active' and self.stock > 0

    def __str__(self):
        return self.name


# 购物车
class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_cart')  # 关联用户
    created_time = models.DateTimeField(auto_now_add=True)

    def get_subtotal_amount(self):
        """计算商品小计金额"""
        TWO_PLACES = Decimal('0.01')
        return sum(item.get_item_subtotal() for item in self.items.all()).quantize(TWO_PLACES)

    def get_shipping_fee(self):
        """计算运费，订单金额>30免运费，否则收取5英镑运费"""
        TWO_PLACES = Decimal('0.01')
        subtotal = self.get_subtotal_amount()
        return (Decimal('0') if subtotal >= Decimal('30') else Decimal('5')).quantize(TWO_PLACES)

    def get_vat(self):
        """计算增值税，为商品小计的5%"""
        TWO_PLACES = Decimal('0.01')
        return (self.get_subtotal_amount() * Decimal('0.05')).quantize(TWO_PLACES)

    def get_total_amount(self):
        """计算购物车总金额（含运费和增值税）"""
        TWO_PLACES = Decimal('0.01')
        return (self.get_subtotal_amount() + self.get_shipping_fee() + self.get_vat()).quantize(TWO_PLACES)

    def total_items(self):
        """计算购物车商品总数"""
        return sum(item.quantity for item in self.items.all())

    def __str__(self):
        return f"Cart of {self.user.name}"

# 购物项
class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')  # 关联购物车
    product = models.ForeignKey(Product, on_delete=models.CASCADE)  # 关联商品
    quantity = models.IntegerField(default=1)  # 数量
    add_time = models.DateTimeField(default=timezone.now)  # 将auto_now_add改为default

    def get_item_subtotal(self):
        """计算单个商品的小计金额"""
        return self.product.price * Decimal(str(self.quantity))

    def __str__(self):
        return f"{self.quantity} of {self.product.name} in {self.cart.user.name}'s cart"


# 订单
class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ('pending', 'pending'),
        ('paid', 'paid'),
        ('shipped', 'shipped'),
        ('delivered', 'delivered'),
        ('completed', 'completed'),
        ('cancelled', 'cancelled'),
        ('refunded', 'refunded'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('wallet', 'wallet'),
        ('card', 'card'),
        ('points', 'points')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True)  # 订单号
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    vat = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True) 
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # 优惠后金额
    order_status = models.CharField(max_length=32, choices=ORDER_STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=32, choices=PAYMENT_METHOD_CHOICES, default='wallet')
    payment_status = models.BooleanField(default=False)  # 支付状态
    shipping_address = models.TextField()  # 收货地址
    payment_card = models.ForeignKey('PaymentCard', on_delete=models.SET_NULL, null=True, blank=True)
    points_used = models.IntegerField(default=0)  # 使用的积分数
    points_earned = models.IntegerField(default=0)  # 获得的积分数
    timestamp = models.DateTimeField(auto_now_add=True)  # 创建时间
    paid_time = models.DateTimeField(null=True, blank=True)  # 支付时间
    complete_time = models.DateTimeField(null=True, blank=True)  # 完成时间
    promo_code = models.ForeignKey(PromoCode, on_delete=models.SET_NULL, null=True, blank=True)
    promo_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        TWO_PLACES = Decimal('0.01')
        
        # 生成订单号
        if not self.order_number:
            self.order_number = timezone.now().strftime('%Y%m%d%H%M%S') + str(self.user.id).zfill(4)

        # 计算总金额
        if not self.total_amount:
            self.total_amount = self.get_total_amount()

        # 计算最终金额
        if not self.final_amount:
            self.final_amount = self.total_amount
            # 如果使用了优惠码且优惠码有效，应用优惠码折扣
            if self.promo_code and self.promo_code.is_valid():
                self.promo_discount = min(self.promo_code.discount, self.total_amount)
                self.final_amount -= self.promo_discount

        super().save(*args, **kwargs)

    def complete_order(self):
        """完成订单"""
        self.order_status = 'completed'
        self.complete_time = timezone.now()
        self.points_earned = int(self.final_amount * 10)  # 消费1元获得10积分
        self.save()

        # 更新用户积分
        self.user.wallet.points += self.points_earned
        self.user.wallet.save()

    def __str__(self):
        return f"Order {self.order_number} ({self.get_order_status_display()})"

    def get_total_amount(self):
        """计算订单总金额（含运费和增值税）"""
        TWO_PLACES = Decimal('0.01')
        subtotal = sum(item.item_subtotal for item in self.items.all())
        shipping = Decimal('0') if subtotal >= Decimal('30') else Decimal('5')
        vat = subtotal * Decimal('0.05')
        return (subtotal + shipping + vat).quantize(TWO_PLACES)


# 订单项
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # 下单时的价格
    item_subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        # 保存下单时的价格和小计
        if not self.price:
            self.price = self.product.price
        self.item_subtotal = self.price * Decimal(str(self.quantity))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Order {self.order.order_number}"


# 历史记录（合并订单历史和支付历史）
class HistoryNew(models.Model):
    HISTORY_TYPE_CHOICES = [
        ('order_created', '创建订单'),
        ('order_paid', '订单支付'),
        ('order_shipped', '订单发货'),
        ('order_delivered', '订单送达'),
        ('order_completed', '订单完成'),
        ('order_cancelled', '订单取消'),
        ('order_refunded', '订单退款'),
        ('wallet_topup', '钱包充值'),
        ('wallet_purchase', '钱包消费'),
        ('points_earned', '获得积分'),
        ('points_used', '使用积分'),
        ('promo_code_used', '使用优惠码'),  # 新增：优惠码使用记录
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='history')
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='history')
    history_type = models.CharField(max_length=32, choices=HISTORY_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # 涉及金额
    points = models.IntegerField(null=True, blank=True)  # 涉及积分
    details = models.TextField(blank=True, null=True)  # 详细信息
    promo_code = models.ForeignKey('PromoCode', on_delete=models.SET_NULL, null=True, blank=True)  # 新增：关联优惠码
    original_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # 新增：优惠前金额
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)    # 新增：优惠后金额
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.name} - {self.get_history_type_display()} - {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']
        verbose_name = '历史记录'
        verbose_name_plural = '历史记录'


# old
# 优惠券
class Coupon(models.Model):
    wallet = models.ForeignKey('Wallet', on_delete=models.CASCADE, null=True, blank=True, related_name='coupons')
    code = models.CharField(max_length=10, unique=True)
    discount = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(0.01)])
    expiry_date = models.DateField(null=True, blank=True)
    min_order_value = models.DecimalField(max_digits=6, decimal_places=2, default=10.00, validators=[MinValueValidator(0.01)])
    max_activations = models.IntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(50)])
    created_time = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=32, choices=[('active', 'active'), ('used', 'used'), ('expired', 'expired')], default='active')

    def is_valid(self):
        """Check if the coupon is valid for a specific user"""
        return self.status == 'active' and self.expiry_date >= timezone.now().date()

    def __str__(self):
        return f"Coupon {self.code} - {self.status}"


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
