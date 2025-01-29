import logging
from django.db import connection
from datetime import datetime, timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)

# Reusable function for getting date range
def get_date_range(table_names):
    """Get the date range for the last month and current month"""
    try:
        with connection.cursor() as cursor:
            # Try each table name
            for table_name in table_names:
                try:
                    cursor.execute(f\"\"\"
                        WITH CurrentData AS (
                            SELECT 
                                MAX(vouch_date) as max_date,
                                ADD_MONTHS(TRUNC(MAX(vouch_date), 'MM'), -1) as start_date
                            FROM {table_name}
                        )
                        SELECT 
                            TO_CHAR(start_date, 'YYYY-MM-DD') as start_date,
                            TO_CHAR(max_date, 'YYYY-MM-DD') as max_date
                        FROM CurrentData
                    \"\"\")
                    row = cursor.fetchone()
                    if row and all(row):  # Check if we have both dates
                        start_date, end_date = row
                        logger.info(f"Found date range in {table_name}: {start_date} to {end_date}")
                        return {
                            'start': datetime.strptime(start_date, '%Y-%m-%d').date(),
                            'end': datetime.strptime(end_date, '%Y-%m-%d').date()
                        }
                except Exception as e:
                    logger.error(f"Error getting date range from {table_name}: {str(e)}")
                    continue

        # Fallback to a default date range if no data found
        today = timezone.now().date()
        start_date = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        
        logger.warning(f"No valid date range found in tables. Using default range: {start_date} to {today}")
        return {
            'start': start_date,
            'end': today
        }

    except Exception as e:
        logger.error(f"Error in get_date_range: {str(e)}")
        # Return a default date range on error
        today = timezone.now().date()
        start_date = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        return {
            'start': start_date,
            'end': today
        }

# Comprehensive method to introspect database views and tables
def introspect_database_view():
    """
    Comprehensive method to introspect database views and tables
    """
    try:
        with connection.cursor() as cursor:
            # Get all tables and views
            cursor.execute(\"\"\"
                SELECT 
                    owner, 
                    table_name, 
                    table_type 
                FROM all_tables 
                WHERE owner = SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA')
                OR owner = UPPER(SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA'))
            \"\"\")
            tables = cursor.fetchall()
            
            logger.error("ALL TABLES AND VIEWS:")
            for table in tables:
                logger.error(f"Owner: {table[0]}, Name: {table[1]}, Type: {table[2]}")
            
            # Function to get column details
            def get_column_details(table_name):
                try:
                    cursor.execute(f\"\"\"
                        SELECT 
                            column_name, 
                            data_type, 
                            data_length, 
                            nullable,
                            data_precision,
                            data_scale
                        FROM all_tab_columns 
                        WHERE table_name = :table_name
                        AND owner = SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA')
                        ORDER BY column_id
                    \"\"\", {'table_name': table_name})
                    return cursor.fetchall()
                except Exception as e:
                    logger.error(f"Error getting columns for {table_name}: {str(e)}")
                    return []
            
            # Get columns for potential invoice tables
            invoice_like_tables = [
                table[1] for table in tables 
                if 'INVOICE' in table[1].upper() or 'MV_' in table[1].upper()
            ]
            
            logger.error("INVOICE-LIKE TABLES:")
            for table_name in invoice_like_tables:
                logger.error(f"\\nColumns for {table_name}:")
                columns = get_column_details(table_name)
                for col in columns:
                    logger.error(f"Column: {col[0]}, "
                                 f"Type: {col[1]}, "
                                 f"Length: {col[2]}, "
                                 f"Nullable: {col[3]}, "
                                 f"Precision: {col[4]}, "
                                 f"Scale: {col[5]}")
            
            # Try to get sample data from invoice-like tables
            logger.error("\\nSAMPLE DATA FROM INVOICE-LIKE TABLES:")
            for table_name in invoice_like_tables:
                try:
                    cursor.execute(f"SELECT * FROM {table_name} WHERE ROWNUM <= 3")
                    sample_rows = cursor.fetchall()
                    logger.error(f"\\nSample data from {table_name}:")
                    for row in sample_rows:
                        logger.error(str(row))
                except Exception as e:
                    logger.error(f"Error getting sample data from {table_name}: {str(e)}")
    
    except Exception as e:
        logger.error(f"CRITICAL ERROR in database introspection: {str(e)}")

def detect_invoice_columns(table_name):
    """
    Dynamically detect columns for invoice-related calculations
    """
    try:
        with connection.cursor() as cursor:
            # Get column details
            cursor.execute(f\"\"\"
                SELECT 
                    column_name, 
                    data_type
                FROM all_tab_columns 
                WHERE table_name = :table_name
                AND owner = SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA')
            \"\"\", {'table_name': table_name})
            columns = cursor.fetchall()
            
            # Mapping of possible column names
            column_mappings = {
                'total_amount': [
                    'TOTAL_AMOUNT', 'TOTAL_INVOICE', 'INVOICE_AMOUNT', 
                    'TOTAL_VALUE', 'AMOUNT'
                ],
                'total_cost': [
                    'TOTAL_COST', 'COST_PRICE', 'TOTAL_EXPENSES', 
                    'COST', 'EXPENSES'
                ],
                'total_profit': [
                    'TOTAL_PROFIT', 'NET_EARNING', 'NET_PROFIT', 
                    'PROFIT', 'NET_INCOME'
                ]
            }
            
            # Find matching columns
            found_columns = {}
            column_names = [col[0] for col in columns]
            
            for key, possible_names in column_mappings.items():
                found = next((name for name in possible_names if name in column_names), None)
                found_columns[key] = found
            
            return found_columns

def create_flexible_kpi_query(table_name):
    \"\"\"
    Create a flexible KPI query based on detected columns
    \"\"\"
    # Detect columns
    columns = detect_invoice_columns(table_name)
    
    # Fallback column names if detection fails
    total_amount_col = columns.get('total_amount', 'TOTAL_AMOUNT')
    total_cost_col = columns.get('total_cost', 'TOTAL_COST')
    total_profit_col = columns.get('total_profit', 'TOTAL_PROFIT')
    
    # Construct flexible query
    kpi_query = f\"\"\"
        WITH LastMonthData AS (
            SELECT 
                MAX(vouch_date) as max_date,
                ADD_MONTHS(TRUNC(MAX(vouch_date), 'MM'), -1) as start_date
            FROM {table_name}
        )
        SELECT 
            COUNT(*) as total_bookings,
            COALESCE(SUM({total_amount_col}), 0) as total_sales,
            COALESCE(SUM({total_cost_col}), 0) as total_cost,
            COALESCE(SUM({total_profit_col}), 0) as total_profit,
            COALESCE(AVG({total_amount_col}), 0) as avg_invoice_value
        FROM {table_name} i
        WHERE i.VOUCH_DATE >= (SELECT start_date FROM LastMonthData)
        AND i.VOUCH_DATE <= (SELECT max_date FROM LastMonthData)
    \"\"\"
    
    return kpi_query
