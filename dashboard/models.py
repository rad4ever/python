from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
#from .models import Salesofficer  # Change this from SalesOfficer to Sale

class Currency(models.Model):
    name = models.CharField(max_length=20)
    code = models.CharField(max_length=3)
    exchange_rate_to_usd = models.DecimalField(max_digits=10, decimal_places=4, default=1.0)

    class Meta:
        verbose_name_plural = 'Currencies'

    def __str__(self):
        return f"{self.code} ({self.name})"

class DocumentType(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Agent(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20)
    address = models.TextField()

    def __str__(self):
        return self.user.get_full_name()

class Provider(models.Model):
    name = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)

    def __str__(self):
        return self.name

class Activity(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name

class Sale(models.Model):
    agent = models.ForeignKey('Agent', on_delete=models.CASCADE)
    activity = models.ForeignKey('Activity', on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    quantity = models.IntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    #user = models.OneToOneField('User', on_delete=models.CASCADE)
    user_name = models.CharField(max_length=100, unique=True)
    #sale = models.ForeignKey('Sale', on_delete=models.CASCADE, default=1)  # Add this line
    def __str__(self) -> str:
#    def __str__(self):
        return f"{self.agent} - {self.activity} - {self.date}"

    def save(self, *args, **kwargs):
        self.total_price = self.activity.price * self.quantity
        super().save(*args, **kwargs)
class Company(models.Model):
    comp_id = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=255)
    
    class Meta:
        verbose_name_plural = 'Companies'

    def __str__(self):
        return self.name

class Invoice(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    source_id = models.CharField(max_length=20)
    year = models.IntegerField()
    vouch_type_id = models.CharField(max_length=20)
    vouch_id = models.CharField(max_length=50)
    msicid = models.CharField(max_length=50)
    docid = models.CharField(max_length=50)
    reservation_no = models.CharField(max_length=50)
    vouch_date = models.DateField()
    selling_fare = models.DecimalField(max_digits=15, decimal_places=2)
    cost_price = models.DecimalField(max_digits=15, decimal_places=2)
    total_invoice = models.DecimalField(max_digits=15, decimal_places=2)
    customer = models.CharField(max_length=255)
    agent_name = models.CharField(max_length=255)
    airline = models.CharField(max_length=255, blank=True)
    from_city = models.CharField(max_length=100)
    to_city = models.CharField(max_length=100)
    travel_date = models.DateField()
    hotel_name = models.CharField(max_length=255, blank=True)
    discount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    doc_type = models.ForeignKey(DocumentType, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=['company', 'year']),
            models.Index(fields=['vouch_date']),
            models.Index(fields=['customer']),
            models.Index(fields=['agent_name']),
        ]

    def __str__(self):
        return f"{self.vouch_id} - {self.customer}"

    @property
    def profit(self):
        return self.total_invoice - self.cost_price

class InvoiceView(models.Model):
    # Required fields
    comp_id = models.IntegerField()
    source_id = models.IntegerField()
    year = models.IntegerField()
    vouch_type_id = models.IntegerField()
    vouch_id = models.BigIntegerField(primary_key=True)
    msicid = models.CharField(max_length=20)
    docid = models.CharField(max_length=20)
    isposted = models.IntegerField()

    # Optional fields
    reservation_no = models.CharField(max_length=100, null=True, blank=True)
    vouch_date = models.DateField(null=True, blank=True)
    trans_seq = models.IntegerField(null=True, blank=True)
    pax_name = models.CharField(max_length=2000, null=True, blank=True)
    tkt_no = models.CharField(max_length=300, null=True, blank=True)
    route = models.CharField(max_length=300, null=True, blank=True)
    cust_id = models.IntegerField(null=True, blank=True)
    customer = models.CharField(max_length=601, null=True, blank=True)
    cur_a_name = models.CharField(max_length=20, null=True, blank=True)
    gds = models.IntegerField(null=True, blank=True)
    cur = models.IntegerField(null=True, blank=True)
    note = models.CharField(max_length=255, null=True, blank=True)
    selling_fare = models.CharField(max_length=500, null=True, blank=True)
    cost_price = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
    total_invoice = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
    sic_a_name = models.CharField(max_length=200, null=True, blank=True)
    agent_name = models.CharField(max_length=500, null=True, blank=True)
    agent_id = models.IntegerField(null=True, blank=True)
    cancel = models.IntegerField(null=True, blank=True)
    user_name = models.CharField(max_length=30, null=True, blank=True)
    creation_date = models.DateField(null=True, blank=True)
    show_agent = models.IntegerField(null=True, blank=True)
    airline = models.IntegerField(null=True, blank=True)
    doc_type = models.CharField(max_length=200, null=True, blank=True)
    inv_no = models.CharField(max_length=50, null=True, blank=True)
    person = models.CharField(max_length=600, null=True, blank=True)
    from_city = models.CharField(max_length=100, null=True, blank=True)
    to_city = models.CharField(max_length=100, null=True, blank=True)
    dep_date = models.DateField(null=True, blank=True)
    brand_name = models.CharField(max_length=4000, null=True, blank=True)
    travel_date = models.DateField(null=True, blank=True)
    facility_amount = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
    hotel_name = models.CharField(max_length=500, null=True, blank=True)
    country = models.CharField(max_length=500, null=True, blank=True)
    city = models.CharField(max_length=500, null=True, blank=True)
    nights = models.IntegerField(null=True, blank=True)
    pay_type = models.IntegerField(null=True, blank=True)
    check_in = models.DateField(null=True, blank=True)
    check_out = models.DateField(null=True, blank=True)
    no_of_day = models.IntegerField(null=True, blank=True)
    price = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
    refno = models.CharField(max_length=100, null=True, blank=True)
    org_no = models.IntegerField(null=True, blank=True)
    org_name = models.CharField(max_length=400, null=True, blank=True)
    discount = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
    paid_cash = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
    acc_vouch_no = models.IntegerField(null=True, blank=True)
    posted = models.IntegerField(null=True, blank=True)
    net_earning = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
    op_type = models.IntegerField(null=True, blank=True)
    visa_ref_no = models.CharField(max_length=100, null=True, blank=True)
    add_comm = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'MV_IAMS_INVOICE_INFO'
        ordering = ['-vouch_date']

    def __str__(self):
        return f"{self.vouch_id} - {self.vouch_date}"
