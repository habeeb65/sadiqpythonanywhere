from django.db import models
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.contrib.auth.models import User

class PurchaseVendor(models.Model):
    name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=15)
    area = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('account_pay', 'Account Pay'),
        ('upi', 'UPI GPay / PhonePay'),
        ('cash', 'Cash'),
    ]
    invoice = models.ForeignKey('PurchaseInvoice', on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    date = models.DateField(default=date.today)
    # New field: Payment mode as a drop-down
    payment_mode = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cash',  # You can set a default or remove default if needed
        verbose_name="Payment Method"
    )

    # New field: Attachment for screenshot/reference
    attachment = models.FileField(
        upload_to='payment_attachments/',
        blank=True,
        null=True,
        verbose_name="Payment Attachment"
    )

    def clean(self):
        invoice = self.invoice
        # Calculate the total of all payments for this invoice excluding the current instance if it exists.
        if self.pk:
            # Existing payment: exclude self from the total.
            current_total = invoice.payments.exclude(pk=self.pk).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        else:
            # New payment: there is no current value.
            current_total = Decimal('0')

        # Calculate what the new total would be after this payment is added/updated.
        new_total = current_total + self.amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        net_total_after_cash_cutting = invoice.net_total_after_cash_cutting

        # Only validate if net_total_after_cash_cutting is meaningful (> 0.01)
        if net_total_after_cash_cutting > Decimal('0.01') and new_total > net_total_after_cash_cutting:
            raise ValidationError(
                f"Total payment cannot exceed the net total after 2% cash cutting: ₹{net_total_after_cash_cutting}."
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Payment of ₹{self.amount} for Invoice {self.invoice.invoice_number}"


class PurchaseInvoice(models.Model):
    invoice_number = models.CharField(max_length=20, unique=True, editable=False)
    lot_number = models.CharField(max_length=10, unique=True, editable=False)
    date = models.DateField(default=date.today)
    vendor = models.ForeignKey('PurchaseVendor', on_delete=models.CASCADE, related_name='invoices')
    net_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_issuer_name = models.CharField(
        max_length=100,
        choices=[('Abdul Rafi', 'Abdul Rafi'), ('Sadiq', 'Sadiq')],
        blank=True,
        null=True
    )

    def save(self, *args, **kwargs):
        # --- Generate invoice_number if not set (only for new objects) ---
        if not self.invoice_number and self.pk is None:
            last_invoice = PurchaseInvoice.objects.order_by("-id").first()
            if last_invoice and last_invoice.invoice_number:
                try:
                    # Extract the last two digits and increment
                    last_number = int(last_invoice.invoice_number[-3:])
                except ValueError:
                    last_number = 0
                self.invoice_number = f"MS2025R{last_number + 1:03d}"
            else:
                self.invoice_number = "MS2025R01"  # Default starting number

        # --- Generate lot_number if not set (only for new objects) ---
        if not self.lot_number and self.pk is None:
            last_lot = PurchaseInvoice.objects.order_by("-id").first()
            if last_lot and last_lot.lot_number:
                try:
                    last_lot_number = int(last_lot.lot_number.split("-")[-1])
                except ValueError:
                    last_lot_number = 0
                self.lot_number = f"LOT-{last_lot_number + 1:03d}"
            else:
                self.lot_number = "LOT-01"  # Default starting lot number

        # Only update net_total if it's a new instance or update_fields excludes net_total
        update_total = True
        if 'update_fields' in kwargs and kwargs['update_fields'] is not None:
            update_total = 'net_total' not in kwargs['update_fields']

        # First save to ensure instance has a primary key
        super().save(*args, **kwargs)

        # Update net_total if needed (not during a field-specific update that includes net_total)
        if update_total and self.pk:
            calculated_total = sum(product.total for product in self.purchase_products.all())
            if self.net_total != calculated_total:
                self.net_total = calculated_total
                # Update only the net_total field without triggering full save again
                type(self).objects.filter(pk=self.pk).update(net_total=calculated_total)

    @property
    def available_quantity(self):
        # Existing purchased quantity
        total_purchased = sum(product.quantity for product in self.purchase_products.all())

        # Sum of quantities used in ALL sales invoices
        total_used = self.sales_lots.aggregate(total=Sum('quantity'))['total'] or Decimal('0.00')

        return total_purchased - total_used

    @property
    def net_total_after_cash_cutting(self):
        # Calculate net total after deducting 2%
        return round(self.net_total - (self.net_total * Decimal('0.02')), 2)

    @property
    def paid_amount(self):
        return round(sum(payment.amount for payment in self.payments.all()), 2)

    @property
    def due_amount(self):
        return round(self.net_total_after_cash_cutting - self.paid_amount, 2)

    #@property
    # def available_quantity(self):
    #     # Sum of quantities purchased from all products in this invoice.
    #     total_purchased = sum(product.quantity for product in self.purchase_products.all())
    #     # Sum of quantities already sold from this lot in all sales invoices.
    #     total_sold = self.sales_invoices.aggregate(total=Sum('lot_quantity'))['total'] or 0
    #     return total_purchased - total_sold

    def __str__(self):
        return (
            #f"Invoice {self.invoice_number} - Net Total: ₹{self.net_total}, "
            #f"Net Total After Cash Cutting: ₹{self.net_total_after_cash_cutting}, "
            #f"Paid Amount: ₹{self.paid_amount}, Due Amount: ₹{self.due_amount}"
            f" {self.lot_number} (Invoice {self.invoice_number})"
        )

    def get_product_quantities(self):
        products = {}
        for purchase_product in self.purchase_products.all():
            sold = SalesProduct.objects.filter(
                invoice__lot=self,
                product=purchase_product.product
            ).aggregate(total=Sum('quantity'))['total'] or 0
            available = purchase_product.quantity - sold
            products[purchase_product.product.name] = available
        return products
    class Meta:
        verbose_name = "Lot"
        verbose_name = "Purchase Invoice"  # Singular name
        verbose_name_plural = "Purchase Invoices"  # Plural name

    LOT_STATUS = [
        ('available', 'Available'),
        ('sold', 'Sold'),
        ('damaged', 'Damaged'),
        ('reserved', 'Reserved'),
    ]
    status = models.CharField(
        max_length=20,
        choices=LOT_STATUS,
        default='available'
    )
    status_notes = models.TextField(blank=True)
class Purchase(models.Model):
    invoice = models.OneToOneField(PurchaseInvoice, on_delete=models.CASCADE, related_name='purchase_invoice')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        self.total_amount = sum(product.total for product in self.invoice.purchase_products.all())
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Purchase for Invoice {self.invoice.invoice_number}"


class Product(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class PurchaseProduct(models.Model):
    invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE, related_name='purchase_products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    serial_number = models.IntegerField(default=0, editable=False)  # Make it non-editable
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    damage = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Damage (Kg)")
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Discount (%)")
    rotten = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Rotten (Kg)")
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    loading_unloading = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Add this

    def save(self, *args, **kwargs):
        print(f"--- Calculating PurchaseProduct --- ID: {self.pk}") # DEBUG
        print(f"Input -> Qty: {self.quantity}, Price: {self.price}, Dmg: {self.damage}, Disc: {self.discount}, Rotten: {self.rotten}") # DEBUG
    # Auto-generate serial_number if not set (only for new objects)
        if not self.serial_number or self.serial_number == 0:
            # Get all existing products for this invoice and renumber them in sequence
            existing_products = PurchaseProduct.objects.filter(invoice=self.invoice).order_by('id')

            # Determine the next serial number
            if existing_products.exists():
                # Find the highest existing serial number
                max_serial = existing_products.aggregate(models.Max('serial_number'))['serial_number__max'] or 0
                self.serial_number = max_serial + 1
            else:
                self.serial_number = 1  # Start from 1 for the first product in the invoice

        # 1. Calculate physical quantity after damage and rotten
        physical_quantity = self.quantity - self.damage - self.rotten
        physical_quantity = max(physical_quantity, Decimal('0.00'))
        print(f"Step 1 -> Physical Qty: {physical_quantity}") # DEBUG

        # 2. Calculate the base price for the physical quantity
        base_price_total = physical_quantity * self.price
        print(f"Step 2 -> Base Price Total: {base_price_total}") # DEBUG

        # 3. Calculate discount amount based on the base price
        discount_amount = (base_price_total * self.discount) / 100
        print(f"Step 3 -> Discount Amount: {discount_amount}") # DEBUG

        # 4. Calculate price after discount
        price_after_discount = base_price_total - discount_amount
        print(f"Step 4 -> Price After Discount: {price_after_discount}") # DEBUG

        # 5. Calculate loading/unloading cost based on Product Name
        # Accessing product name requires the related object to be loaded
        # Ensure product is loaded, handle potential DoesNotExist if needed (though FK implies it should exist)
        try:
            product_name = self.product.name
        except Product.DoesNotExist:
            product_name = "" # Should not happen with ForeignKey

        if product_name == "Rotten":
            # If Product Name is 'Rotten', loading/unloading cost is zero
            print(f"Step 5 -> Product is '{product_name}', setting loading_unloading to 0") # DEBUG
            self.loading_unloading = Decimal('0.00')
        else:
            # For all other products, calculate loading/unloading based on the *original* quantity
            print(f"Step 5 -> Product is '{product_name}', calculating loading_unloading") # DEBUG
            self.loading_unloading = Decimal(self.quantity) * Decimal('0.40')
            print(f"Step 5 -> Final loading_unloading: {self.loading_unloading}") # DEBUG

        # 6. Calculate final total: Price after discount - loading/unloading cost
        self.total = price_after_discount - self.loading_unloading
        print(f"Step 6 -> Final Total before min check: {self.total}") # DEBUG

        # Ensure total is never zero or negative
        if self.total <= 0:
            self.total = Decimal('0.01')  # Set a minimum value
            print(f"Step 7 -> Adjusted Total to minimum: {self.total}") # DEBUG
        else:
            print(f"Step 7 -> Final Total: {self.total}") # DEBUG

        print("--- Calculation Finished --- ") # DEBUG

        # Save the purchase product with calculated values
        super().save(*args, **kwargs)

        # Update the parent invoice's net_total by triggering a calculation
        # But only if we're not in the middle of a bulk update or creation
        if self.invoice and self.invoice.pk:
            calculated_total = sum(product.total for product in self.invoice.purchase_products.all())
            if self.invoice.net_total != calculated_total:
                # Use direct update to avoid recursive saves
                PurchaseInvoice.objects.filter(pk=self.invoice.pk).update(net_total=calculated_total)

        # After saving, resequence all the serial numbers if needed
        self.resequence_serial_numbers()

    def resequence_serial_numbers(self):
        """Ensure all products in the same invoice have sequential serial numbers"""
        products = PurchaseProduct.objects.filter(invoice=self.invoice).order_by('id')
        for i, product in enumerate(products, start=1):
            if product.serial_number != i:
                PurchaseProduct.objects.filter(pk=product.pk).update(serial_number=i)

    def __str__(self):
        return f"{self.serial_number}. {self.product.name} in Invoice {self.invoice.invoice_number}"


class SalesInvoice(models.Model):
    invoice_number = models.CharField(max_length=20, unique=True, editable=False)
    invoice_date = models.DateField(default=date.today)
    vendor = models.ForeignKey('Customer', on_delete=models.PROTECT, related_name='sales_invoices')
    
    vehicle_number = models.CharField(max_length=50, blank=True, null=True)
    gross_vehicle_weight = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True,
                                               help_text="In Kilograms")
    reference = models.CharField(max_length=200, blank=True, null=True)

    # Crate information - outgoing
    no_of_crates = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, null=True,
                                      verbose_name="No of Crates")
    cost_per_crate = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, null=True,
                                        verbose_name="Packaging cost per crate (₹)")

    # Crate information - incoming
    purchased_crates_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, null=True,
                                                  verbose_name="No of Purchased Crates")
    purchased_crates_unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, null=True,
                                                    verbose_name="Purchased price per crate (₹)")

    # Add commission percentage field
    commission_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Commission percentage (e.g., 2 for 2%)"
    )

    def save(self, *args, **kwargs):
        # Auto-generate invoice number if not set.
        if not self.invoice_number and self.pk is None:
            last_invoice = SalesInvoice.objects.order_by("-id").first()
            if last_invoice and last_invoice.invoice_number:
                try:
                    last_number = int(last_invoice.invoice_number[-2:])
                except ValueError:
                    last_number = 0
                self.invoice_number = f"SA2025S{last_number + 1:02d}"
            else:
                self.invoice_number = "SA2025S01"
        super().save(*args, **kwargs)

    # Computed properties for totals:
    @property
    def total_gross_weight(self):
        """Sum of gross weights of all sales products."""
        total = self.sales_products.aggregate(total=models.Sum('gross_weight'))['total'] or Decimal('0.00')
        return total

    @property
    def net_total(self):
        """Sum of all line item totals."""
        total = self.sales_products.aggregate(total=models.Sum('total'))['total'] or Decimal('0.00')
        return total

    @property
    def net_total_after_commission(self):
        """
        Net Total After Commission = Net Total + (Net Total * Commission Percentage / 100)
        """
        commission_amount = (self.net_total * self.commission_percentage) / Decimal('100.00')
        return self.net_total + commission_amount

    @property
    def packaging_total(self):
        """Total packaging cost = no of crates * packaging cost per crate."""
        # Check if both no_of_crates and cost_per_crate are not None
        if self.no_of_crates is not None and self.cost_per_crate is not None:
            # Return the total cost by multiplying no_of_crates and cost_per_crate
            return Decimal(self.no_of_crates) * self.cost_per_crate
        # Return 0.00 if either no_of_crates or cost_per_crate is None
        return Decimal('0.00')

    @property
    def purchased_crates_total(self):
        """Calculated Purchased crates total = No of Purchased Crates * Purchased price per crate."""
        if self.purchased_crates_quantity is not None and self.purchased_crates_unit_price is not None:
            return (Decimal(self.purchased_crates_quantity) * self.purchased_crates_unit_price).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return Decimal('0.00') # Return 0 if quantity or price is missing

    @property
    def net_total_after_packaging(self):
        """
        Final invoice total = Net Total After Commission + Total packaging cost + Purchased crates total.
        """
        # Ensure this still ADDS the calculated purchased_crates_total
        return self.net_total_after_commission + self.packaging_total + self.purchased_crates_total

    @property
    def paid_amount(self):
        """Sum of all related payments"""
        return self.payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    @property
    def due_amount(self):
        """Remaining balance"""
        return self.net_total_after_packaging - self.paid_amount

    def payment_status(self):
        """Payment status indicator"""
        if self.due_amount == 0:
            return "Paid"
        elif self.paid_amount == 0:
            return "Unpaid"
        return "Partial"

    def __str__(self):
        return f"Sales Invoice {self.invoice_number} for {self.vendor}"


# -------------------------------------------
# Sales Product Model (Line Items)
# -------------------------------------------
class SalesProduct(models.Model):
    invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, related_name='sales_products')
    serial_number = models.IntegerField(editable=False)  # Auto-incremented within the invoice
    product = models.ForeignKey('Product', on_delete=models.CASCADE)

    lot_number = models.CharField(max_length=50, null=True, blank=True, default='Lot-')  # New field
    # We store the weights in kilograms
    gross_weight = models.DecimalField(max_digits=12, decimal_places=2, help_text="Gross Weight in Kgs")
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                                   help_text="Discount as percentage")
    rotten = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                 help_text="Rotten weight in Kgs")
    # These fields are computed:
    net_weight = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True,
                                     help_text="Net Weight in Kgs after discount & rotten deduction")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True,
                                help_text="Total = Net Weight * Price")

    def save(self, *args, **kwargs):
        # Auto-generate serial_number if not set.
        if not self.serial_number:
            last_item = SalesProduct.objects.filter(invoice=self.invoice).order_by('-serial_number').first()
            self.serial_number = last_item.serial_number + 1 if last_item else 1

        # Calculate net_weight:
        # net_weight = gross_weight - (gross_weight * discount/100) - rotten
        self.net_weight = self.gross_weight - ((self.gross_weight * self.discount) / Decimal('100.00')) - self.rotten
        # Calculate total:

        self.total = self.net_weight * self.price


        self.total = (self.net_weight * self.price)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.serial_number}. {self.product.name} in Invoice {self.invoice.invoice_number}"

    lot = models.ForeignKey(
        'SalesLot',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="Link to specific lot usage"
    )
# -------------------------------------------
# Sales Payment Model
# -------------------------------------------
class SalesPayment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('account_pay', 'Account Pay'),
        ('upi', 'UPI GPay / PhonePay'),
        ('cash', 'Cash'),
    ]

    invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    date = models.DateField(default=date.today)
    payment_mode = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cash',
        verbose_name="Payment Method"
    )
    attachment = models.FileField(
        upload_to='sales_payment_attachments/',
        blank=True,
        null=True,
        verbose_name="Payment Attachment"
    )
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Payment of ₹{self.amount} for Sales Invoice {self.invoice.invoice_number}"

class Customer(models.Model):
    name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name
class Expense(models.Model):
    date = models.DateField()
    paid_by = models.CharField(max_length=100)
    paid_to = models.CharField(max_length=100)
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    def __str__(self):
        return f"{self.date} - {self.paid_to} - ₹{self.amount}"
class Damages(models.Model):
    date = models.DateField()
    name = models.CharField(max_length=100)
    due_to = models.CharField(max_length=100)
    description = models.TextField()
    amount_loss = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    def __str__(self):
        return f"{self.date} - {self.due_to} - ₹{self.amount_loss}"
    class Meta:
        verbose_name = "Damage"  # Singular form
        verbose_name_plural = "Damages"  # Explicitly set plural name

class SalesLot(models.Model):
    """Tracks which lots (from purchase invoices) are used in a sales invoice"""
    sales_invoice = models.ForeignKey(
        'SalesInvoice',
        on_delete=models.CASCADE,
        related_name='sales_lots'
    )
    purchase_invoice = models.ForeignKey(
        'PurchaseInvoice',
        on_delete=models.CASCADE,
        related_name='sales_lots',
        verbose_name="Lot"
    )
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Quantity used from this lot (in kgs)"
    )

    class Meta:
        unique_together = ('sales_invoice', 'purchase_invoice')  # Prevent duplicates

    def __str__(self):
        return f"{self.quantity}kg from {self.purchase_invoice.lot_number}"

    def clean(self):
        super().clean()

        # Skip basic validations if required fields are missing
        if not self.purchase_invoice or not self.quantity:
            return

        # Comment out this section if you want to re-enable quantity validation
        """
        # Fetch the existing instance (if updating)
        old_instance = None
        if self.pk:
            try:
                old_instance = SalesLot.objects.get(pk=self.pk)
            except SalesLot.DoesNotExist:
                pass

        # Calculate adjusted available quantity
        if old_instance and old_instance.purchase_invoice_id == self.purchase_invoice_id:
            available = (
                self.purchase_invoice.available_quantity  # Current available
                + old_instance.quantity                   # Add back old quantity
            )
        else:
            available = self.purchase_invoice.available_quantity

        # Validate new quantity against adjusted available
        if self.quantity > available:
            raise ValidationError(
                f"Only {available}kg available in {self.purchase_invoice.lot_number}. "
                f"You're trying to use {self.quantity}kg."
            )
        """

        # Comment out this section if you want to re-enable product validation
        """
        # Ensure product consistency between lot and sales invoice
        if not self.sales_invoice or not self.sales_invoice.pk:
            return  # Skip if parent invoice is unsaved

        sales_products = self.sales_invoice.sales_products.all()
        if sales_products.exists():
            sales_product = sales_products.first().product
            if not self.purchase_invoice.purchase_products.filter(
                product=sales_product
            ).exists():
                raise ValidationError(
                    f"Lot {self.purchase_invoice.lot_number} doesn't contain {sales_product.name}"
                )
        """
class Packaging_Invoice(models.Model):
    no_of_crates = models.IntegerField(blank=True, null=True, verbose_name="No of Crates")
    cost_per_crate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True,
                                        verbose_name="Packaging cost per crate (₹)")

    @property
    def packaging_total(self):
        """Total packaging cost = no of crates * packaging cost per crate."""
        # Check if both no_of_crates and cost_per_crate are not None
        if self.no_of_crates is not None and self.cost_per_crate is not None:
            # Return the total cost by multiplying no_of_crates and cost_per_crate
            return Decimal(self.no_of_crates) * self.cost_per_crate
        # Return 0.00 if either no_of_crates or cost_per_crate is None
        return Decimal('0.00')
class InventoryStatus(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('sold', 'Sold'),
        ('damaged', 'Damaged'),
        ('reserved', 'Reserved'),
    ]

    purchase_invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE, related_name='inventory_statuses')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    quantity = models.DecimalField(max_digits=12, decimal_places=2, help_text="Quantity affected by this status change")
    notes = models.TextField(blank=True, null=True, help_text="Additional notes about the status change")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='inventory_status_changes')

    class Meta:
        verbose_name = "Inventory Status"
        verbose_name_plural = "Inventory Statuses"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.purchase_invoice.lot_number} - {self.status} ({self.quantity}kg)"


