from rest_framework import serializers
from .models import Currency, DocumentType, Company, Invoice

class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ['id', 'name', 'code', 'exchange_rate_to_usd']

class DocumentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentType
        fields = ['id', 'name', 'description']

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['comp_id', 'name']

class InvoiceSerializer(serializers.ModelSerializer):
    profit = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    doc_type_name = serializers.CharField(source='doc_type.name', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'company', 'company_name', 'source_id', 'year',
            'vouch_type_id', 'vouch_id', 'msicid', 'docid',
            'reservation_no', 'vouch_date', 'selling_fare',
            'cost_price', 'total_invoice', 'profit', 'customer',
            'agent_name', 'airline', 'from_city', 'to_city',
            'travel_date', 'hotel_name', 'discount',
            'currency', 'currency_code', 'doc_type', 'doc_type_name',
            'created_at'
        ]
        read_only_fields = ['created_at']
