from telnetlib import STATUS

from django.db import models
from django.utils import timezone
import datetime
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


# Subscription
class Subscription(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)  # email must be unique
    created_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.email}"

# Gender Choices
gender_choice = [
    (1, 'Male'),
    (2, 'Female'),
    (3, 'Other'),
    (4, "Don't want to say"),
    (5, "Unknown")
]

# Operator
class Operator(models.Model):
    name = models.CharField(max_length=50)
    # date_of_birth = models.DateField(default=datetime.date.today)
    gender = models.IntegerField(choices=gender_choice, default=5)
    email = models.EmailField()
    phone = models.CharField(max_length=50)
    account = models.CharField(max_length=50, unique=True)  # account must be unique
    password = models.CharField(max_length=50)
    is_operator = models.BooleanField(default=False)
    role = models.CharField(max_length=50)


    def verify_password(self, password):
        """Verify if the password is correct"""
        from main_system.utils.encrypt import md5
        return self.password == md5(password)
    
    def set_password(self, password):
        """Set the encrypted password"""
        from main_system.utils.encrypt import md5
        self.password = md5(password)

    def __str__(self):
        return f"{self.name} - {self.role}"


# User
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

    # User related Wallet (1:1)
    # wallet = models.OneToOneField('Wallet', on_delete=models.CASCADE, null=True, blank=True)

    # User related PaymentCard (1:n)
    #payment_cards = models.ManyToManyField('PaymentCard', blank=True)

    # User related Coupon (1:n)
    coupons = models.ManyToManyField('Coupon', blank=True)

    @property
    def wallet_balance(self):
        """Get the user's wallet balance"""
        wallet = Wallet.objects.filter(user=self).first()
        return wallet.balance if wallet else Decimal('0.00')

    def deduct_balance(self, amount):
        """Deduct balance from the wallet"""
        wallet = Wallet.objects.filter(user=self).first()
        if wallet and wallet.balance >= amount:
            wallet.balance -= amount
            wallet.save()
            return True
        return False

    def __str__(self):
        return self.name


# Wallet (balance & points)
class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, validators=[MinValueValidator(0.0)])
    points = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    def add_balance(self, amount):
        """ Add balance """
        self.balance += amount
        self.save()

    def add_points(self, points):
        """ Add points """
        self.points += points
        self.save()

    def deduct_points(self, points):
        """ Deduct points """
        if self.points >= points:
            self.points -= points
            self.save()
            return True
        return False

    def __str__(self):
        return f"Wallet of {self.user.name}"

# Wallet Transaction Records (top-up, purchase, refund, points change, promo code usage)
class WalletTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('top_up', 'top up'),
        ('purchase', 'purchase'),
        ('refund', 'refund'),
        ('points_earned', 'points earned'),
        ('points_used', 'points used'),
        ('points_refund', 'points refund'),
        ('promo_code_used', 'promo code used'),
        ('card_payment', 'card payment'),
    ]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Amount change
    points = models.IntegerField(null=True, blank=True)  # Points change
    order = models.ForeignKey('Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')  # Related order
    promo_code = models.ForeignKey('PromoCode', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')  # Related promo code
    payment_card = models.ForeignKey('PaymentCard', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')  # Related payment card
    original_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Amount before discount
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Amount after discount
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.wallet.user.name} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Wallet Transaction Record'
        verbose_name_plural = 'Wallet Transaction Records'


# Promo Code
class PromoCode(models.Model):
    code = models.CharField(max_length=10, unique=True)
    discount = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(0.01)])
    min_order_value = models.DecimalField(max_digits=6, decimal_places=2, default=10.00, validators=[MinValueValidator(0.01)])
    expiry_date = models.DateTimeField()
    created_time = models.DateTimeField(default=timezone.now)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=32, choices=[('active', 'active'), ('inactive', 'inactive'), ('expired', 'expired')], default='active')

    def is_valid(self):
        """Check if the promo code is valid"""
        return self.status == 'active' and self.expiry_date > timezone.now()

    def __str__(self):
        return f"PromoCode: {self.code} (£{self.discount})"


# Payment Card
class PaymentCard(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_payment_cards', null=True)  # Temporarily allow null
    wallet = models.ForeignKey('Wallet', on_delete=models.CASCADE, null=True, blank=True, related_name='wallet_cards')
    card_number = models.CharField(max_length=16, unique=True)
    expiry_date = models.CharField(max_length=5)  # Format: MM/YY
    cvv = models.CharField(max_length=4)  # Support 3-4 digit CVV
    nickname = models.CharField(max_length=50, null=True, blank=True)  # Optional nickname
    country = models.CharField(max_length=50)
    postcode = models.CharField(max_length=50)
    created_time = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.nickname or 'Card'} - {self.card_number[-4:]}"

    def save(self, *args, **kwargs):
        # Ensure postcode is always stored in uppercase
        if self.postcode:
            self.postcode = self.postcode.upper()
        super().save(*args, **kwargs)


# Product
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
        # 确保created_time不为空（对新对象和已存在对象都检查）
        if not hasattr(self, 'created_time') or self.created_time is None:
            self.created_time = timezone.now()
        # 自动调整产品状态
        if self.stock == 0:
            self.status = 'locked'
        super().save(*args, **kwargs)

    def is_available(self):
        # Check if the product is available
        return self.status == 'active' and self.stock > 0

    @property
    def average_rating(self):
        """Get the average rating of the product"""
        reviews = self.reviews.filter(is_deleted=False)
        if reviews.exists():
            return reviews.aggregate(models.Avg('rating'))['rating__avg']
        return 0

    @property
    def total_sales(self):
        """Get the total sales of the product"""
        return OrderItem.objects.filter(
            product=self,
            order__order_status='completed'
        ).aggregate(
            total=models.Sum('quantity')
        )['total'] or 0

    def __str__(self):
        return self.name


# Product Review
class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    order_item = models.OneToOneField('OrderItem', on_delete=models.CASCADE, related_name='review')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    created_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_time']
        indexes = [
            models.Index(fields=['product', '-created_time']),
            models.Index(fields=['user', '-created_time']),
        ]

    def __str__(self):
        return f"{self.user.name}'s review for {self.product.name}"


# Cart
class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_cart')  # Related user
    created_time = models.DateTimeField(auto_now_add=True)

    def get_subtotal_amount(self):
        """Calculate the subtotal amount of products"""
        TWO_PLACES = Decimal('0.01')
        return sum(item.get_item_subtotal() for item in self.items.all()).quantize(TWO_PLACES)

    def get_shipping_fee(self):
        """Calculate the shipping fee, free shipping for orders over £30, otherwise £5 shipping fee"""
        TWO_PLACES = Decimal('0.01')
        subtotal = self.get_subtotal_amount()
        return (Decimal('0') if subtotal >= Decimal('30') else Decimal('5')).quantize(TWO_PLACES)

    def get_vat(self):
        """Calculate VAT, which is 5% of the product subtotal"""
        TWO_PLACES = Decimal('0.01')
        return (self.get_subtotal_amount() * Decimal('0.05')).quantize(TWO_PLACES)

    def get_total_amount(self):
        """Calculate the total amount of the cart (including shipping fee and VAT)"""
        TWO_PLACES = Decimal('0.01')
        return (self.get_subtotal_amount() + self.get_shipping_fee() + self.get_vat()).quantize(TWO_PLACES)

    def total_items(self):
        """Calculate the total number of items in the cart"""
        return sum(item.quantity for item in self.items.all())

    def __str__(self):
        return f"Cart of {self.user.name}"

# Cart Item
class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')  # Related cart
    product = models.ForeignKey(Product, on_delete=models.CASCADE)  # Related product
    quantity = models.IntegerField(default=1)  # Quantity
    add_time = models.DateTimeField(default=timezone.now)  # Changed auto_now_add to default

    def get_item_subtotal(self):
        """Calculate the subtotal amount of a single product"""
        return self.product.price * Decimal(str(self.quantity))

    def __str__(self):
        return f"{self.quantity} of {self.product.name} in {self.cart.user.name}'s cart"


# Order
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
    order_number = models.CharField(max_length=20, unique=True)  # Order number
    subtotal_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Product subtotal
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Total amount (including shipping fee and tax)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Shipping fee
    vat = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # VAT
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Amount after discount
    order_status = models.CharField(max_length=32, choices=ORDER_STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=32, choices=PAYMENT_METHOD_CHOICES, default='wallet')
    payment_status = models.BooleanField(default=False)  # Payment status
    shipping_address = models.TextField()  # Shipping address
    contact_name = models.CharField(max_length=100, null=True, blank=True)  # Contact name
    contact_email = models.EmailField(null=True, blank=True)  # Contact email
    payment_card = models.ForeignKey('PaymentCard', on_delete=models.SET_NULL, null=True, blank=True)
    points_used = models.IntegerField(default=0)  # Points used
    points_earned = models.IntegerField(default=0)  # Points earned
    timestamp = models.DateTimeField(auto_now_add=True)  # Created time
    paid_time = models.DateTimeField(null=True, blank=True)  # Paid time
    complete_time = models.DateTimeField(null=True, blank=True)  # Completed time
    promo_code = models.ForeignKey(PromoCode, on_delete=models.SET_NULL, null=True, blank=True)
    promo_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        TWO_PLACES = Decimal('0.01')
        
        # Generate order number
        if not self.order_number:
            self.order_number = timezone.now().strftime('%Y%m%d%H%M%S') + str(self.user.id).zfill(4)

        # Calculate product subtotal
        if not self.subtotal_amount:
            self.subtotal_amount = sum(item.item_subtotal for item in self.items.all())

        # Calculate shipping fee
        if not self.shipping_fee:
            self.shipping_fee = Decimal('0') if self.subtotal_amount >= Decimal('30') else Decimal('5')

        # Calculate VAT
        if not self.vat:
            self.vat = (self.subtotal_amount * Decimal('0.05')).quantize(TWO_PLACES)

        # Calculate total amount (including shipping fee and tax)
        if not self.total_amount:
            self.total_amount = (self.subtotal_amount + self.shipping_fee + self.vat).quantize(TWO_PLACES)

        # Calculate final amount
        if not self.final_amount:
            self.final_amount = self.total_amount
            # If a promo code is used and the promo code is valid, apply the promo code discount
            if self.promo_code and self.promo_code.is_valid():
                self.promo_discount = min(self.promo_code.discount, self.total_amount)
                self.final_amount = (self.final_amount - self.promo_discount).quantize(TWO_PLACES)

        super().save(*args, **kwargs)

    def complete_order(self):
        """Complete the order"""
        self.order_status = 'completed'
        self.complete_time = timezone.now()
        self.points_earned = int(self.final_amount * 10)  # Earn 10 points for every £1 spent
        self.save()

        # Update user points
        self.user.wallet.points += self.points_earned
        self.user.wallet.save()

    def __str__(self):
        return f"Order {self.order_number} ({self.get_order_status_display()})"

    def get_total_amount(self):
        """Calculate the total amount of the order (including shipping fee and VAT)"""
        TWO_PLACES = Decimal('0.01')
        subtotal = sum(item.item_subtotal for item in self.items.all())
        shipping = Decimal('0') if subtotal >= Decimal('30') else Decimal('5')
        vat = subtotal * Decimal('0.05')
        return (subtotal + shipping + vat).quantize(TWO_PLACES)


# Order Item
class OrderItem(models.Model):
    RETURN_STATUS_CHOICES = [
        ('none', 'none'),
        ('pending', 'pending'),
        ('approved', 'approved'),
        ('rejected', 'rejected'),
        ('shipped', 'shipped'),
        ('received', 'received'),
        ('refunded', 'refunded')
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price at the time of order
    item_subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    # Return related fields
    return_status = models.CharField(max_length=20, choices=RETURN_STATUS_CHOICES, default='none')
    return_reason = models.CharField(max_length=50, null=True, blank=True)
    return_details = models.TextField(null=True, blank=True)
    return_time = models.DateTimeField(null=True, blank=True)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    refund_time = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.price:
            self.price = self.product.price
        self.item_subtotal = self.price * Decimal(str(self.quantity))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Order {self.order.order_number}"

    def add_review(self, rating, comment):
        """Add a review"""
        Review.objects.create(
            product=self.product,
            order_item=self,
            user=self.order.user,
            rating=rating,
            comment=comment
        )

    def apply_return(self, reason, details):
        """Apply for a return"""
        self.return_status = 'pending'
        self.return_reason = reason
        self.return_details = details
        self.return_time = timezone.now()
        self.save()

    def process_return(self, status, refund_amount=None):
        """Process the return application"""
        self.return_status = status
        if status == 'refunded' and refund_amount:
            self.refund_amount = refund_amount
            self.refund_time = timezone.now()
        self.save()


# History (merge order history and payment history)
class HistoryNew(models.Model):
    HISTORY_TYPE_CHOICES = [
        ('order_created', 'Order Created'),
        ('order_paid', 'Order Paid'),
        ('order_shipped', 'Order Shipped'),
        ('order_delivered', 'Order Delivered'),
        ('order_completed', 'Order Completed'),
        ('order_cancelled', 'Order Cancelled'),
        ('order_refunded', 'Order Refunded'),
        ('wallet_topup', 'Wallet Top-up'),
        ('wallet_purchase', 'Wallet Purchase'),
        ('points_earned', 'Points Earned'),
        ('points_used', 'Points Used'),
        ('promo_code_used', 'Promo Code Used'),  # New: Promo code usage record
        ('promo_code_returned', 'Promo Code Returned'),  # New: Promo code return record
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='history')
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='history')
    history_type = models.CharField(max_length=32, choices=HISTORY_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Involved amount
    points = models.IntegerField(null=True, blank=True)  # Involved points
    details = models.TextField(blank=True, null=True)  # Detailed information
    promo_code = models.ForeignKey('PromoCode', on_delete=models.SET_NULL, null=True, blank=True)  # New: Related promo code
    original_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # New: Amount before discount
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)    # New: Amount after discount
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.name} - {self.get_history_type_display()} - {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'History Record'
        verbose_name_plural = 'History Records'

# Coupon
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







