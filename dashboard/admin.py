from django.contrib import admin
from .models import Currency, DocumentType, Company, Invoice

# Register your models here.

@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'exchange_rate_to_usd')
    search_fields = ('code', 'name')
    ordering = ('code',)

@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)
    ordering = ('name',)

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('comp_id', 'name')
    search_fields = ('comp_id', 'name')
    ordering = ('name',)

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('vouch_id', 'company', 'customer', 'agent_name', 
                   'total_invoice', 'vouch_date', 'doc_type')
    list_filter = ('company', 'doc_type', 'year', 'vouch_date')
    search_fields = ('vouch_id', 'customer', 'agent_name', 'airline', 'hotel_name')
    date_hierarchy = 'vouch_date'
    ordering = ('-vouch_date',)
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'company', 'source_id', 'year', 'vouch_type_id',
                'vouch_id', 'msicid', 'docid', 'reservation_no'
            )
        }),
        ('Financial Information', {
            'fields': (
                'selling_fare', 'cost_price', 'total_invoice',
                'discount', 'currency', 'doc_type'
            )
        }),
        ('Travel Details', {
            'fields': (
                'customer', 'agent_name', 'airline',
                'from_city', 'to_city', 'travel_date',
                'hotel_name'
            )
        }),
        ('System Information', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
