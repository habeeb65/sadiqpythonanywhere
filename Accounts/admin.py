from django.contrib import admin
from .models import Purchase, PurchaseVendor, PurchaseInvoice, Product, PurchaseProduct, Payment
from .models import SalesInvoice, SalesProduct, SalesPayment, Customer, Product, Expense, Damages, SalesLot, Packaging_Invoice
from django.shortcuts import redirect  # Add this line
from django.urls import reverse
from django.urls import path
from django.utils.html import format_html
from django.http import JsonResponse
from django.db import models
from django.http import HttpResponse



admin.site.site_header = "Star Mango Supplies Korutla"   # Header displayed at the top of the admin
admin.site.site_title = "Star Mango Supplies Korutla"     # Title tag for the admin pages
admin.site.index_title = "Welcome to Star Mango Supplies Korutla Admin Panel"  # Title on the admin index page
# Inline for PurchaseProduct within an Invoice
class PurchaseProductInline(admin.TabularInline):
    model = PurchaseProduct
    extra = 1  # Number of empty forms to show initially
    readonly_fields = ('total', 'loading_unloading', 'serial_number')  # Make calculated fields read-only
    fields = ('serial_number', 'product', 'quantity', 'price', 'damage', 'discount', 'rotten', 'loading_unloading', 'total')
    ordering = ('serial_number',)  # Order products by serial number

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset

    def serial_number(self, obj):
        if obj.pk:
            return obj.serial_number
        else:
            # Predict the next serial number for new items
            if hasattr(obj, 'invoice') and obj.invoice and obj.invoice.pk:
                existing_products = PurchaseProduct.objects.filter(invoice=obj.invoice)
                if existing_products.exists():
                    max_serial = existing_products.aggregate(models.Max('serial_number'))['serial_number__max'] or 0
                    return max_serial + 1
                return 1  # First product for this invoice
        return "-"  # Fallback if we can't predict
    serial_number.short_description = "Serial Number"

# Inline for Payments within an Invoice
class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 1  # Number of empty forms to show
    fields = ('amount','payment_mode','attachment', 'date')
    readonly_fields = ('date',)  # Optionally make date read-only

# Admin for PurchaseInvoice
class PurchaseInvoiceAdmin(admin.ModelAdmin):
    model = PurchaseInvoice
    list_display = ('invoice_number','lot_number', 'vendor_name', 'net_total_after_cash_cutting', 'paid_amount', 'due_amount_display', 'payment_status', 'date', 'print_invoice')
    readonly_fields = ('invoice_number', 'lot_number','net_total', 'net_total_after_cash_cutting', 'paid_amount_display', 'due_amount_display', 'payment_status')
    search_fields = ('invoice_number','lot_number', 'vendor__name')
    list_filter = ('date', 'vendor')
    autocomplete_fields = ['vendor']

    # Removing Media class to stop loading JavaScript
    # class Media:
    #     js = ('admin/js/purchase_calculation.js',)

    # Remove the static inlines list and replace with get_inlines method
    def get_inlines(self, request, obj=None):
        # Always show both product and payment inlines
        return [PurchaseProductInline, PaymentInline]

    def vendor_name(self, obj):
        return obj.vendor.name
    vendor_name.short_description = "Vendor"

    def net_total_display(self, obj):
        return f"₹{obj.net_total:.2f}"
    net_total_display.short_description = "Net Total"

    def paid_amount_display(self, obj):
        payments = obj.payments.all()
        details = "<br/>".join([f"₹{payment.amount} on {payment.date}" for payment in payments])
        total_paid = f"<b>Total Paid:</b> ₹{obj.paid_amount:.2f}"
        return format_html(f"{details}<br/>{total_paid}")
    paid_amount_display.short_description = "Paid Amount"

    def due_amount_display(self, obj):
        return format_html(f"<b style='color: #dc3545;'>₹{obj.due_amount:.2f}</b>")
    due_amount_display.short_description = "Due Amount"

    def payment_status(self, obj):
        if obj.due_amount == 0:
            status = "Paid"
        elif obj.paid_amount == 0:
            status = "Unpaid"
        else:
            status = "Partial"

        colors = {
            'Paid': '#28a745',
            'Unpaid': '#dc3545',
            'Partial': '#ffc107'
        }
        return format_html(f"<b style='color: {colors.get(status, '#000')};'>{status}</b>")
    payment_status.short_description = "Payment Status"

    def print_invoice(self, obj):
        url = reverse('generate_invoice_pdf', args=[obj.id])
        return format_html('<a class="button" href="{}" target="_blank">Print Invoice</a>', url)
    print_invoice.short_description = "Print Invoice"

    def save_model(self, request, obj, form, change):
        """Override save_model to ensure calculations are performed properly"""
        super().save_model(request, obj, form, change)
        # After saving, update the net_total once more to ensure it's correct
        if obj.pk:
            calculated_total = sum(product.total for product in obj.purchase_products.all())
            if obj.net_total != calculated_total:
                # Use update to avoid triggering another full save
                PurchaseInvoice.objects.filter(pk=obj.pk).update(net_total=calculated_total)

    def save_formset(self, request, form, formset, change):
        """Override save_formset to ensure all formsets are saved"""
        # Always save all formsets, whether creating new or editing
        super().save_formset(request, form, formset, change)
        # After saving formsets, make sure the parent object's calculations are updated
        obj = form.instance
        if obj.pk:
            calculated_total = sum(product.total for product in obj.purchase_products.all())
            if obj.net_total != calculated_total:
                # Use update to avoid triggering another full save
                PurchaseInvoice.objects.filter(pk=obj.pk).update(net_total=calculated_total)

    def response_change(self, request, obj):
        if "_print_without_payments" in request.POST:
            url = reverse('generate_invoice_pdf', args=[obj.id]) + "?hide_payments=1"
            return redirect(url)
        return super().response_change(request, obj)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('autocomplete/', self.admin_site.admin_view(self.autocomplete)),
        ]
        return custom_urls + urls

    def autocomplete(self, request):
        query = request.GET.get('q', '')
        lots = PurchaseInvoice.objects.filter(lot_number__icontains=query)[:10]
        results = []
        for lot in lots:
            products = lot.get_product_quantities()
            product_info = ", ".join([f"{k}: {v}" for k, v in products.items()])
            results.append({
                'id': lot.id,
                'text': f"{lot.lot_number} - Available: {product_info}",
            })
        return JsonResponse({'results': results})


    class Meta:
        verbose_name = "Purchase Invoice"
        verbose_name_plural = "Purchase Invoices"
# Admin for PurchaseProduct
class PurchaseProductAdmin(admin.ModelAdmin):
    list_display = ('serial_number', 'invoice', 'product', 'quantity', 'price_display', 'total', 'damage', 'discount', 'rotten')
    readonly_fields = ('total', 'serial_number')  # Make calculated fields read-only
    ordering = ('invoice', 'serial_number')  # Order by invoice then serial number

    def price_display(self, obj):
        return f"₹{obj.price:.2f}"
    price_display.short_description = "Price"

# Admin for Payment
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'amount_display', 'date')

    def amount_display(self, obj):
        return f"₹{obj.amount:.2f}"
    amount_display.short_description = "Amount"

class SalesProductInline(admin.TabularInline):
    model = SalesProduct
    extra = 1  # Number of empty forms to show initially
    readonly_fields = ('total', 'net_weight', 'serial_number')
    fields = ('serial_number', 'product', 'lot_number' , 'gross_weight', 'discount', 'rotten', 'net_weight', 'price', 'total') #added by azher
    ordering = ('serial_number',)  # Order products by serial number


    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset

    def serial_number(self, obj):
        if obj.pk:
            return obj.serial_number
        else:
            # Predict the next serial number for new items
            if hasattr(obj, 'invoice') and obj.invoice and obj.invoice.pk:
                existing_products = SalesProduct.objects.filter(invoice=obj.invoice)
                if existing_products.exists():
                    max_serial = existing_products.aggregate(models.Max('serial_number'))['serial_number__max'] or 0
                    return max_serial + 1
                return 1  # First product for this invoice
        return "-"  # Fallback if we can't predict
    serial_number.short_description = "S/No"

# Inline for SalesPayment within a Sales Invoice
class SalesPaymentInline(admin.TabularInline):
    model = SalesPayment
    extra = 1  # Number of empty forms to show
    fields = ('amount', 'payment_mode', 'attachment', 'date')
    readonly_fields = ('date',)

# Admin for SalesInvoice
class SalesInvoiceAdmin(admin.ModelAdmin):
    list_display = (
        'invoice_number',
        'vendor_name',
        'net_total_after_commission',
        'packaging_total_display',
        'purchased_crates_total_display',
        'net_total_after_packaging',
        'paid_amount_display',
        'due_amount_display',
        'payment_status',
        'invoice_date',
        'print_invoice'
    )
    readonly_fields = (
        'invoice_number',
        'net_total',
        'net_total_after_commission',
        'packaging_total',
        'purchased_crates_total',
        'net_total_after_packaging',
        'paid_amount',
        'due_amount',
        'payment_status'
    )

    # Simple procedural fields layout rearranged
    fields = [
        # Basic information
        'vendor', 'invoice_date', 'vehicle_number', 'gross_vehicle_weight', 'reference',

        # Outgoing Crates
        'no_of_crates', 'cost_per_crate',

        # Incoming Crates
        'purchased_crates_quantity', 'purchased_crates_unit_price',
        'purchased_crates_total', # Read-only calculated field

        # Sales, Commission & Packaging Cost
        'invoice_number', # Read-only
        'net_total', # Read-only
        'commission_percentage', # New commission percentage field
        'net_total_after_commission', # Read-only
        'packaging_total', # Read-only (Total packaging cost)

        # Final Totals & Payments
        'net_total_after_packaging', # Read-only
        'paid_amount', # Read-only
        'due_amount', # Read-only
        'payment_status' # Read-only
    ]

    def get_inlines(self, request, obj=None):
        return [SalesProductInline, SalesPaymentInline]  # Removed SalesLotInline

    search_fields = ('invoice_number', 'vendor__name', )
    list_filter = ('invoice_date',)

    actions = [admin.actions.delete_selected]

    def vendor_name(self, obj):
        return obj.vendor.name
    vendor_name.short_description = "Customer"

    def paid_amount_display(self, obj):
        payments = obj.payments.all()
        details = "<br/>".join([f"₹{payment.amount} on {payment.date}" for payment in payments])
        total_paid = f"<b>Total Paid:</b> ₹{obj.paid_amount:.2f}"
        return format_html(f"{details}<br/>{total_paid}")
    paid_amount_display.short_description = "Paid Amount"

    def due_amount_display(self, obj):
        return format_html(f"<b style='color: #dc3545;'>₹{obj.due_amount:.2f}</b>")
    due_amount_display.short_description = "Due Amount"

    def payment_status(self, obj):
        status = obj.payment_status()
        colors = {
            'Paid': '#28a745',
            'Unpaid': '#dc3545',
            'Partial': '#ffc107'
        }
        return format_html(f"<b style='color: {colors.get(status, '#000')};'>{status}</b>")
    payment_status.short_description = "Payment Status"

    def print_invoice(self, obj):
        url = reverse('generate_sales_invoice_pdf', args=[obj.id])
        return format_html('<a class="button" href="{}" target="_blank">Print Invoice</a>', url)
    print_invoice.short_description = "Print Invoice"

    def save_formset(self, request, form, formset, change):
        if change and not getattr(formset.instance, 'pk', None):
            if hasattr(formset.instance, 'sales_invoice'):
                # If this is a nested inline (formset inside another formset)
                # and we are *editing*, do nothing. This prevents validation.
                pass
        else:
            # If creating a new invoice (change=False), save all formsets as usual.
            super().save_formset(request, form, formset, change)

    def response_change(self, request, obj):
        if "_print_without_payments" in request.POST:
            url = reverse('generate_sales_invoice_pdf', args=[obj.id]) + "?hide_payments=1"
            return redirect(url)
        return super().response_change(request, obj)

    def change_form(self, request, obj=None, **kwargs):
        if obj:
            self.fieldsets = list(self.fieldsets)
            self.fieldsets.append((
                'Print Options',
                {'fields': [], 'description': '''
                    <a class="button" href="{}" target="_blank">Print With Payments</a>&nbsp;
                    <a class="button" href="{}?hide_payments=1" target="_blank">Print Without Payments</a>
                '''.format(
                    reverse('generate_sales_invoice_pdf', args=[obj.id]),
                    reverse('generate_sales_invoice_pdf', args=[obj.id])
                )}
            ))
        return super().change_form(request, obj, **kwargs)

    def packaging_total_display(self, obj):
        return f"₹{obj.packaging_total:.2f}"
    packaging_total_display.short_description = "Total packaging cost"

    def purchased_crates_total_display(self, obj):
        return f"₹{obj.purchased_crates_total:.2f}"
    purchased_crates_total_display.short_description = "Purchased crates total"

# Admin for SalesProduct
class SalesProductAdmin(admin.ModelAdmin):
    list_display = ('serial_number', 'invoice', 'product', 'gross_weight', 'discount', 'rotten', 'net_weight', 'price', 'total')
    readonly_fields = ('total', 'net_weight', 'serial_number')
    ordering = ('invoice', 'serial_number')  # Order by invoice then serial number

    def serial_number(self, obj):
        return obj.serial_number
    serial_number.short_description = "S/No"

# Admin for SalesPayment
class SalesPaymentAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'amount', 'date', 'payment_mode')
    list_filter = ('date', 'payment_mode')

# Optionally, register Customer and Product if not already registered
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_number', 'address')



class ProductAdmin(admin.ModelAdmin):
    list_display = ('name',)

class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('date', 'paid_by', 'paid_to', 'amount', 'description', 'print_expense')
    search_fields = ('paid_to', 'description')
    list_filter = ('date', 'paid_by')
    ordering = ('-date',)

    def print_expense(self, obj):
        url = reverse('generate_expense_pdf', args=[obj.id])
        return format_html('<a class="button" href="{}" target="_blank">Print Expense</a>', url)
    print_expense.short_description = "Print"

class DamagesAdmin(admin.ModelAdmin):
    list_display = ('date', 'name', 'due_to', 'amount_loss', 'description', 'print_damage')
    search_fields = ('due_to', 'description')
    list_filter = ('date', 'name')
    ordering = ('-date',)

    def print_damage(self, obj):
        url = reverse('generate_damage_pdf', args=[obj.id])
        return format_html('<a class="button" href="{}" target="_blank">Print Damage</a>', url)
    print_damage.short_description = "Print"
class packagingsAdmin(admin.ModelAdmin):

    list_display = (
        'no_of_crates',
        'cost_per_crate',
        'packaging_total_display',
        'print_packaging_invoice'
    )
    list_display_links = None
    list_editable = ('no_of_crates', 'cost_per_crate')
    readonly_fields = ('packaging_total_display',)
    list_filter = ('no_of_crates',)
    search_fields = ('no_of_crates', 'cost_per_crate')

    def packaging_total_display(self, obj):
        return f"₹{obj.packaging_total:.2f}"
    packaging_total_display.short_description = "Total packaging cost"

    def print_packaging_invoice(self, obj):
        url = reverse('generate_packaging_pdf', args=[obj.id])
        return format_html('<a class="button" href="{}" target="_blank">Print Invoice</a>', url)
    print_packaging_invoice.short_description = "Print"

# Admin for PurchaseVendor
class PurchaseVendorAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_number', 'area')
    search_fields = ('name', 'contact_number', 'area')

# Registering Vendor models
admin.site.register(PurchaseVendor, PurchaseVendorAdmin)
# Registering Purchase models
admin.site.register(PurchaseInvoice, PurchaseInvoiceAdmin)
admin.site.register(PurchaseProduct, PurchaseProductAdmin)
admin.site.register(Payment, PaymentAdmin)

# Registering Sales models
admin.site.register(SalesInvoice, SalesInvoiceAdmin)
admin.site.register(SalesProduct, SalesProductAdmin)
admin.site.register(SalesPayment, SalesPaymentAdmin)
admin.site.register(Customer, CustomerAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Expense, ExpenseAdmin)
admin.site.register(Damages, DamagesAdmin)
admin.site.register(SalesLot) # Simple registration for now
admin.site.register(Packaging_Invoice, packagingsAdmin)


