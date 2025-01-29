import cx_Oracle
from django.core.management.base import BaseCommand
from django.db import transaction
from dashboard.models import Currency, DocumentType, Company, Invoice
from datetime import datetime

class Command(BaseCommand):
    help = 'Import invoice data from Oracle database'

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, help='Import data for specific year')

    def handle(self, *args, **options):
        try:
            # Oracle connection settings from settings.py
            connection = cx_Oracle.connect(
                user="your_username",
                password="your_password",
                dsn="your_host:1521/your_service_name"
            )
            
            cursor = connection.cursor()
            
            # Build the query
            query = """
                SELECT 
                    COMP_ID, SOURCE_ID, YEAR, VOUCH_TYPE_ID, VOUCH_ID, 
                    MSICID, DOCID, RESERVATION_NO, VOUCH_DATE, 
                    SELLING_FARE, COST_PRICE, TOTAL_INVOICE, CUSTOMER, 
                    AGENT_NAME, AIRLINE, FROM_CITY, TO_CITY, TRAVEL_DATE, 
                    HOTEL_NAME, DISCOUNT, CUR_A_NAME, DOC_TYPE
                FROM IAMS_INVOICE_INFO
                WHERE 1=1
            """
            
            params = []
            if options['year']:
                query += " AND YEAR = :year"
                params.append(options['year'])
            
            cursor.execute(query, params)
            
            # Process the data in chunks
            chunk_size = 1000
            while True:
                rows = cursor.fetchmany(chunk_size)
                if not rows:
                    break
                
                with transaction.atomic():
                    for row in rows:
                        # Get or create Currency
                        currency, _ = Currency.objects.get_or_create(
                            code=row[20],  # CUR_A_NAME
                            defaults={'name': row[20], 'exchange_rate_to_usd': 1.0}
                        )
                        
                        # Get or create DocumentType
                        doc_type, _ = DocumentType.objects.get_or_create(
                            name=row[21],  # DOC_TYPE
                            defaults={'description': f'Document type for {row[21]}'}
                        )
                        
                        # Get or create Company
                        company, _ = Company.objects.get_or_create(
                            comp_id=row[0],  # COMP_ID
                            defaults={'name': f'Company {row[0]}'}
                        )
                        
                        # Create or update Invoice
                        Invoice.objects.update_or_create(
                            company=company,
                            vouch_id=row[4],  # VOUCH_ID
                            defaults={
                                'source_id': row[1],
                                'year': row[2],
                                'vouch_type_id': row[3],
                                'msicid': row[5],
                                'docid': row[6],
                                'reservation_no': row[7],
                                'vouch_date': row[8],
                                'selling_fare': row[9],
                                'cost_price': row[10],
                                'total_invoice': row[11],
                                'customer': row[12],
                                'agent_name': row[13],
                                'airline': row[14] or '',
                                'from_city': row[15],
                                'to_city': row[16],
                                'travel_date': row[17],
                                'hotel_name': row[18] or '',
                                'discount': row[19] or 0,
                                'currency': currency,
                                'doc_type': doc_type,
                            }
                        )
            
            self.stdout.write(self.style.SUCCESS('Successfully imported invoice data'))
            
        except cx_Oracle.Error as error:
            self.stdout.write(self.style.ERROR(f'Oracle Error: {error}'))
        except Exception as error:
            self.stdout.write(self.style.ERROR(f'Error: {error}'))
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'connection' in locals():
                connection.close()
