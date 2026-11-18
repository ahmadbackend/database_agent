from django.db import models


class Supervisor(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    def __str__(self):
        return self.name


class Branch(models.Model):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    supervisor = models.ForeignKey(
        Supervisor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='branches',
    )

    class Meta:
        verbose_name_plural = 'branches'

    def __str__(self):
        return self.name


class Seller(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name='sellers',
    )

    def __str__(self):
        return f'{self.name} ({self.branch.name})'


class Product(models.Model):
    name = models.CharField(max_length=150)
    barcode = models.CharField(max_length=50, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    expiry_date = models.DateField(null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name


class Invoice(models.Model):
    number = models.CharField(max_length=20, unique=True)
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name='invoices',
    )
    seller = models.ForeignKey(
        Seller,
        on_delete=models.PROTECT,
        related_name='invoices',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    products = models.ManyToManyField(
        Product,
        through='InvoiceItem',
        related_name='invoices',
    )

    def __str__(self):
        return f'Invoice #{self.number}'

    @property
    def total(self):
        return sum(item.line_total for item in self.items.all())


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='items',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='invoice_items',
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f'{self.quantity} x {self.product.name}'

    @property
    def line_total(self):
        return self.quantity * self.unit_price
