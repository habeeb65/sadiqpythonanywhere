from django.urls import path
from . import views  # Import views directly from the current module


urlpatterns = [
    path('create-invoice/', views.create_invoice, name='create_invoice'),
    path('invoice/<int:invoice_id>/pdf/', views.generate_invoice_pdf, name='generate_invoice_pdf'),  # Use views.generate_invoice_pdf
    path('Accountvendor_summary/', views.vendor_summary, name='vendor_summary'),
    path('expense/<int:pk>/pdf/', views.generate_expense_pdf, name='generate_expense_pdf'),
    path('damage/<int:pk>/pdf/', views.generate_damage_pdf, name='generate_damage_pdf'),
    path('packaging_invoice/<int:invoice_id>/pdf/', views.generate_packaging_invoice_pdf, name='generate_packaging_pdf'),
    path('vendor-summary/', views.vendor_purchase_summary, name='vendor_purchase_summary'),
    path('customer-summary/', views.customer_purchase_summary, name='customer_purchase_summary'),
     path('vendor-bulk-payment/', views.vendor_bulk_payment, name='vendor_bulk_payment'),
    path('customer-bulk-payment/', views.customer_bulk_payment, name='customer_bulk_payment'),
    path('vendor/<int:vendor_id>/invoices/', views.vendor_invoice_detail, name='vendor_invoice_detail'),
    path('customer/<int:customer_id>/invoices/', views.customer_invoice_detail, name='customer_invoice_detail'),
    path('generate-invoice-pdf/<int:invoice_id>/', views.generate_invoice_pdf, name='generate_invoice_pdf'),
    path('generate-sales-invoice-pdf/<int:invoice_id>/', views.generate_sales_invoice_pdf, name='generate_sales_invoice_pdf'),
    path('generate-expense-pdf/<int:pk>/', views.generate_expense_pdf, name='generate_expense_pdf'),
    path('generate-damage-pdf/<int:pk>/', views.generate_damage_pdf, name='generate_damage_pdf'),
    path('generate-packaging-pdf/<int:invoice_id>/', views.generate_packaging_invoice_pdf, name='generate_packaging_pdf'),
    path('add-vendor/', views.add_vendor, name='add_vendor'),
    path('test-connection/', views.test_connection, name='test_connection'),
    path('api/vendor-outstanding-invoices/', views.vendor_outstanding_invoices_api, name='vendor_outstanding_invoices_api'),
    path('inventory-summary/', views.inventory_summary, name='inventory_summary'),
    path('export-inventory/', views.export_inventory, name='export_inventory'),

]


