from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import (
    Sum, Count, F, Q, Value, Case, When,
    DecimalField, IntegerField, ExpressionWrapper
)
from django.db.models.functions import TruncMonth, Coalesce, TruncWeek, TruncYear
from django.db import connection
from .models import Sale, Agent, Provider, Activity
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from .models import Sale  # Make sure to import the SalesOfficer model
from .models import InvoiceView
from django.http import JsonResponse

import json

logger = logging.getLogger(__name__)

# Reusable function for getting date range
def get_date_range(table_names):
    """Get the date range for the last month and current month"""
    try:
        with connection.cursor() as cursor:
            # Try each table name
            for table_name in table_names:
                try:
                    cursor.execute(f"""
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
                    """)
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
                    # View functions
                    def dashboard(request):
                        return render(request, 'dashboard.html')

                    def agents_dashboard(request):
                        return render(request, 'agents_dashboard.html')

                    def providers_dashboard(request):
                        return render(request, 'providers_dashboard.html')

                    def sales_officers_dashboard(request):
                        """View for sales officers dashboard"""
                        Sale = apps.get_model('dashboard', 'Sale')
                        Sale = Sale.objects.exclude(user_name='AS')
                        context = {'salesofficers': sales}
                        return render(request, 'dashboard/sales_officers_dashboard.html', context)

                    def activities_dashboard(request):
                        return render(request, 'activities_dashboard.html')
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
            cursor.execute("""
                SELECT 
                    owner, 
                    table_name, 
                    table_type 
                FROM all_tables 
                WHERE owner = SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA')
                OR owner = UPPER(SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA'))
            """)
            tables = cursor.fetchall()
            
            logger.error("ALL TABLES AND VIEWS:")
            for table in tables:
                logger.error(f"Owner: {table[0]}, Name: {table[1]}, Type: {table[2]}")
            
            # Function to get column details
            def get_column_details(table_name):
                try:
                    cursor.execute(f"""
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
                    """, {'table_name': table_name})
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
                logger.error(f"\nColumns for {table_name}:")
                columns = get_column_details(table_name)
                for col in columns:
                    logger.error(f"Column: {col[0]}, "
                                 f"Type: {col[1]}, "
                                 f"Length: {col[2]}, "
                                 f"Nullable: {col[3]}, "
                                 f"Precision: {col[4]}, "
                                 f"Scale: {col[5]}")
            
            # Try to get sample data from invoice-like tables
            logger.error("\nSAMPLE DATA FROM INVOICE-LIKE TABLES:")
            for table_name in invoice_like_tables:
                try:
                    cursor.execute(f"SELECT * FROM {table_name} WHERE ROWNUM <= 3")
                    sample_rows = cursor.fetchall()
                    logger.error(f"\nSample data from {table_name}:")
                    for row in sample_rows:
                        logger.error(str(row))
                except Exception as e:
                    logger.error(f"Error getting sample data from {table_name}: {str(e)}")
    
    except Exception as e:
        logger.error(f"CRITICAL ERROR in database introspection: {str(e)}")

# Reusable function for creating detailed dashboard
def create_detailed_dashboard(request, group_field, template_name):
    try:
        # Get filter parameters
        year = request.GET.get('year')
        comp_id = request.GET.get('company')
        search_query = request.GET.get('search', '')
        page = request.GET.get('page', 1)

        logger.info(f"Starting dashboard creation with group_field: {group_field}")
        logger.info(f"Filters - Year: {year}, Company: {comp_id}, Search: {search_query}")

        # Get date range for last two months
        date_range = get_date_range(['MV_IAMS_INVOICE_INFO'])
        if not date_range:
            logger.error("Could not fetch date range")
            return render(request, template_name, {'error': 'Could not fetch date range'})

        logger.info(f"Using date range - Start: {date_range['start']}, End: {date_range['end']}")

        # Base queryset with date range filter
        queryset = InvoiceView.objects.using('default').filter(
            vouch_date__gte=date_range['start'],
            vouch_date__lte=date_range['end']
        )

        # Apply filters
        if year:
            queryset = queryset.filter(year=year)
        if comp_id:
            queryset = queryset.filter(comp_id=comp_id)
        if search_query:
            queryset = queryset.filter(
                Q(**{f"{group_field}__icontains": search_query})
            )

        logger.info(f"Total records after filtering: {queryset.count()}")

        # Define field types for aggregation
        decimal_field = DecimalField(max_digits=19, decimal_places=2)

        # Calculate overall KPIs
        overall_stats = queryset.aggregate(
            total_sales=Coalesce(Sum('total_invoice', output_field=decimal_field), Value(0, output_field=decimal_field)),
            total_cost=Coalesce(Sum('cost_price', output_field=decimal_field), Value(0, output_field=decimal_field)),
            total_profit=Coalesce(Sum('net_earning', output_field=decimal_field), Value(0, output_field=decimal_field)),
            total_bookings=Count('vouch_id'),
        )
        
        # Calculate average invoice value
        if overall_stats['total_bookings'] > 0:
            overall_stats['avg_invoice_value'] = overall_stats['total_sales'] / overall_stats['total_bookings']
        else:
            overall_stats['avg_invoice_value'] = 0

        # Aggregate data by group field
        group_stats = list(queryset.values(group_field).annotate(
            total_sales=Coalesce(Sum('total_invoice', output_field=decimal_field), Value(0, output_field=decimal_field)),
            total_cost=Coalesce(Sum('cost_price', output_field=decimal_field), Value(0, output_field=decimal_field)),
            total_profit=Coalesce(Sum('net_earning', output_field=decimal_field), Value(0, output_field=decimal_field)),
            total_bookings=Count('vouch_id')
        ).order_by('-total_sales')[:100])

        # Calculate average invoice value for each group
        for stat in group_stats:
            if stat['total_bookings'] > 0:
                stat['avg_invoice_value'] = float(stat['total_sales']) / stat['total_bookings']
            else:
                stat['avg_invoice_value'] = 0
            # Convert Decimal to float for JSON serialization
            stat['total_sales'] = float(stat['total_sales'])
            stat['total_cost'] = float(stat['total_cost'])
            stat['total_profit'] = float(stat['total_profit'])

        # Get top performers for monthly trends
        top_performers = group_stats[:10]
        
        # Calculate monthly trends
        monthly_trends = list(
            queryset.filter(**{f"{group_field}__in": [item[group_field] for item in top_performers]})
            .annotate(
                month=TruncMonth('vouch_date'),
                performer=F(group_field)
            )
            .values('month', 'performer')
            .annotate(
                revenue=Coalesce(Sum('total_invoice'), Value(0, output_field=decimal_field))
            )
            .order_by('month', 'performer')
        )

        # Format the dates for JavaScript
        formatted_trends = []
        for trend in monthly_trends:
            formatted_trends.append({
                'month': trend['month'].strftime('%Y-%m-%d') if trend['month'] else '',
                'performer': trend['performer'] or '',
                'revenue': float(trend['revenue'] or 0)
            })

        # Paginate results
        paginator = Paginator(group_stats, 25)
        page_stats = paginator.get_page(page)

        # Get available years and companies
        years = list(InvoiceView.objects.values_list('year', flat=True)
                    .distinct().order_by('-year'))
        companies = list(InvoiceView.objects.values('comp_id')
                        .distinct().order_by('comp_id'))

        # Prepare context
        context = {
            'paginator': paginator,
            'page_stats': page_stats,
            'monthly_trends': formatted_trends,
            'years': years,
            'companies': companies,
            'selected_year': year,
            'selected_company': comp_id,
            'search_query': search_query,
            'date_range': {
                'start': date_range['start'].strftime('%Y-%m-%d'),
                'end': date_range['end'].strftime('%Y-%m-%d')
            },
            'group_field': group_field,
            'group_title': group_field.replace('_', ' ').title(),
            'data': {  # Add overall stats to context
                'total_sales': float(overall_stats['total_sales']),
                'total_cost': float(overall_stats['total_cost']),
                'total_profit': float(overall_stats['total_profit']),
                'total_bookings': overall_stats['total_bookings'],
                'avg_invoice_value': float(overall_stats['avg_invoice_value']),
                'items': group_stats  # Add the detailed items
            },
            'top_performers': top_performers  # Add top performers for the table
        }

        return render(request, template_name, context)

    except Exception as e:
        logger.error(f"Error in create_detailed_dashboard: {str(e)}", exc_info=True)
        return render(request, template_name, {
            'error': 'An error occurred while generating the dashboard',
            'debug_info': str(e)
        })

# Individual dashboard views
@login_required
def agents_dashboard(request):
    """View for agents dashboard"""
    return create_detailed_dashboard(request, 'agent_name', 'dashboard/agents_dashboard.html')

@login_required
def providers_dashboard(request):
    """View for providers dashboard"""
    return create_detailed_dashboard(request, 'sic_a_name', 'dashboard/providers_dashboard.html')

@login_required
def sales_officers_dashboard(request):
    """View for sales officers dashboard"""
    return create_detailed_dashboard(request, 'user_name', 'dashboard/sales_officers_dashboard.html')

@login_required
def activities_dashboard(request):
    try:
        range_type = request.GET.get('range', 'monthly')
        with connection.cursor() as cursor:
            # Determine date range based on the requested type
            if range_type == 'weekly':
                date_trunc = 'IW'  # ISO week
                months_back = -3
            elif range_type == 'yearly':
                date_trunc = 'YYYY'
                months_back = -24
            else:  # monthly
                date_trunc = 'MM'
                months_back = -12

            # Get Activity Trends with additional metrics
            cursor.execute(f"""
                SELECT 
                    TO_CHAR(TRUNC(VOUCH_DATE, '{date_trunc}'), 'YYYY-MM-DD') as period,
                    COUNT(DISTINCT VOUCH_ID) as total_activities,
                    SUM(TOTAL_INVOICE) as total_revenue,
                    SUM(NET_EARNING) as total_profit,
                    AVG(TOTAL_INVOICE) as avg_invoice_value,
                    COUNT(DISTINCT AGENT_CODE) as unique_agents,
                    COUNT(DISTINCT PROVIDER_CODE) as unique_providers
                FROM MV_IAMS_INVOICE_INFO
                WHERE VOUCH_DATE >= ADD_MONTHS(SYSDATE, {months_back})
                AND CANCEL = 0
                GROUP BY TRUNC(VOUCH_DATE, '{date_trunc}')
                ORDER BY TRUNC(VOUCH_DATE, '{date_trunc}')
            """)
            trends_data = cursor.fetchall()

            # Get Activity Types Distribution with YoY comparison
            cursor.execute("""
                WITH current_year AS (
                    SELECT 
                        DOC_TYPE,
                        COUNT(DISTINCT VOUCH_ID) as total_bookings,
                        SUM(TOTAL_INVOICE) as total_revenue,
                        SUM(NET_EARNING) as total_profit
                    FROM MV_IAMS_INVOICE_INFO
                    WHERE VOUCH_DATE >= ADD_MONTHS(SYSDATE, -12)
                    AND CANCEL = 0
                    GROUP BY DOC_TYPE
                ),
                previous_year AS (
                    SELECT 
                        DOC_TYPE,
                        COUNT(DISTINCT VOUCH_ID) as total_bookings,
                        SUM(TOTAL_INVOICE) as total_revenue,
                        SUM(NET_EARNING) as total_profit
                    FROM MV_IAMS_INVOICE_INFO
                    WHERE VOUCH_DATE >= ADD_MONTHS(SYSDATE, -24)
                    AND VOUCH_DATE < ADD_MONTHS(SYSDATE, -12)
                    AND CANCEL = 0
                    GROUP BY DOC_TYPE
                )
                SELECT 
                    c.DOC_TYPE,
                    c.total_bookings,
                    c.total_revenue,
                    c.total_profit,
                    p.total_bookings as prev_bookings,
                    p.total_revenue as prev_revenue,
                    p.total_profit as prev_profit,
                    ROUND(((c.total_bookings - p.total_bookings) / NULLIF(p.total_bookings, 0)) * 100, 2) as bookings_growth,
                    ROUND(((c.total_revenue - p.total_revenue) / NULLIF(p.total_revenue, 0)) * 100, 2) as revenue_growth
                FROM current_year c
                LEFT JOIN previous_year p ON c.DOC_TYPE = p.DOC_TYPE
                ORDER BY c.total_revenue DESC
                FETCH FIRST 5 ROWS ONLY
            """)
            types_data = cursor.fetchall()

            # Get Advanced KPIs
            cursor.execute("""
                WITH periods AS (
                    SELECT 
                        'Current' as period,
                        COUNT(DISTINCT VOUCH_ID) as activities,
                        SUM(TOTAL_INVOICE) as revenue,
                        AVG(TOTAL_INVOICE) as avg_price,
                        SUM(NET_EARNING) as earnings,
                        COUNT(DISTINCT AGENT_CODE) as active_agents,
                        COUNT(DISTINCT PROVIDER_CODE) as active_providers,
                        SUM(NET_EARNING) / NULLIF(SUM(TOTAL_INVOICE), 0) * 100 as profit_margin,
                        SUM(TOTAL_INVOICE) / NULLIF(COUNT(DISTINCT VOUCH_ID), 0) as revenue_per_activity
                    FROM MV_IAMS_INVOICE_INFO
                    WHERE VOUCH_DATE >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -1)
                    AND CANCEL = 0
                    UNION ALL
                    SELECT 
                        'Previous' as period,
                        COUNT(DISTINCT VOUCH_ID) as activities,
                        SUM(TOTAL_INVOICE) as revenue,
                        AVG(TOTAL_INVOICE) as avg_price,
                        SUM(NET_EARNING) as earnings,
                        COUNT(DISTINCT AGENT_CODE) as active_agents,
                        COUNT(DISTINCT PROVIDER_CODE) as active_providers,
                        SUM(NET_EARNING) / NULLIF(SUM(TOTAL_INVOICE), 0) * 100 as profit_margin,
                        SUM(TOTAL_INVOICE) / NULLIF(COUNT(DISTINCT VOUCH_ID), 0) as revenue_per_activity
                    FROM MV_IAMS_INVOICE_INFO
                    WHERE VOUCH_DATE >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -2)
                    AND VOUCH_DATE < ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -1)
                    AND CANCEL = 0
                )
                SELECT 
                    MAX(CASE WHEN period = 'Current' THEN activities END) as curr_activities,
                    MAX(CASE WHEN period = 'Current' THEN revenue END) as curr_revenue,
                    MAX(CASE WHEN period = 'Current' THEN avg_price END) as curr_avg_price,
                    MAX(CASE WHEN period = 'Current' THEN earnings END) as curr_earnings,
                    MAX(CASE WHEN period = 'Current' THEN active_agents END) as curr_active_agents,
                    MAX(CASE WHEN period = 'Current' THEN active_providers END) as curr_active_providers,
                    MAX(CASE WHEN period = 'Current' THEN profit_margin END) as curr_profit_margin,
                    MAX(CASE WHEN period = 'Current' THEN revenue_per_activity END) as curr_revenue_per_activity,
                    MAX(CASE WHEN period = 'Previous' THEN activities END) as prev_activities,
                    MAX(CASE WHEN period = 'Previous' THEN revenue END) as prev_revenue,
                    MAX(CASE WHEN period = 'Previous' THEN avg_price END) as prev_avg_price,
                    MAX(CASE WHEN period = 'Previous' THEN earnings END) as prev_earnings,
                    MAX(CASE WHEN period = 'Previous' THEN active_agents END) as prev_active_agents,
                    MAX(CASE WHEN period = 'Previous' THEN active_providers END) as prev_active_providers,
                    MAX(CASE WHEN period = 'Previous' THEN profit_margin END) as prev_profit_margin,
                    MAX(CASE WHEN period = 'Previous' THEN revenue_per_activity END) as prev_revenue_per_activity
                FROM periods
            """)
            kpi_data = cursor.fetchone()

            # Get Top Performing Agents
            cursor.execute("""
                SELECT 
                    AGENT_CODE,
                    COUNT(DISTINCT VOUCH_ID) as total_activities,
                    SUM(TOTAL_INVOICE) as total_revenue,
                    SUM(NET_EARNING) as total_profit,
                    AVG(TOTAL_INVOICE) as avg_invoice_value
                FROM MV_IAMS_INVOICE_INFO
                WHERE VOUCH_DATE >= ADD_MONTHS(SYSDATE, -12)
                AND CANCEL = 0
                GROUP BY AGENT_CODE
                ORDER BY total_revenue DESC
                FETCH FIRST 5 ROWS ONLY
            """)
            top_agents = cursor.fetchall()

        # Calculate growth rates
        def calculate_growth(current, previous):
            if previous and previous != 0:
                return round(((current - previous) / previous) * 100, 2)
            return 0

        context = {
            'trends_data': {
                'labels': [row[0] for row in trends_data],
                'revenue': [float(row[2]) for row in trends_data],
                'activities': [int(row[1]) for row in trends_data],
                'profit': [float(row[3]) for row in trends_data],
                'avg_value': [float(row[4]) for row in trends_data],
                'agents': [int(row[5]) for row in trends_data],
                'providers': [int(row[6]) for row in trends_data]
            },
            'types_data': {
                'labels': [row[0] for row in types_data],
                'current_revenue': [float(row[2]) for row in types_data],
                'previous_revenue': [float(row[5]) if row[5] else 0 for row in types_data],
                'growth': [float(row[8]) for row in types_data]
            },
            'top_agents': {
                'labels': [row[0] for row in top_agents],
                'activities': [int(row[1]) for row in top_agents],
                'revenue': [float(row[2]) for row in top_agents],
                'profit': [float(row[3]) for row in top_agents],
                'avg_value': [float(row[4]) for row in top_agents]
            },
            'kpi_data': {
                'activities': {
                    'value': kpi_data[0],
                    'previous': kpi_data[8],
                    'growth': calculate_growth(kpi_data[0], kpi_data[8])
                },
                'revenue': {
                    'value': float(kpi_data[1]),
                    'previous': float(kpi_data[9]),
                    'growth': calculate_growth(float(kpi_data[1]), float(kpi_data[9]))
                },
                'avg_price': {
                    'value': float(kpi_data[2]),
                    'previous': float(kpi_data[10]),
                    'growth': calculate_growth(float(kpi_data[2]), float(kpi_data[10]))
                },
                'earnings': {
                    'value': float(kpi_data[3]),
                    'previous': float(kpi_data[11]),
                    'growth': calculate_growth(float(kpi_data[3]), float(kpi_data[11]))
                },
                'active_agents': {
                    'value': kpi_data[4],
                    'previous': kpi_data[12],
                    'growth': calculate_growth(kpi_data[4], kpi_data[12])
                },
                'active_providers': {
                    'value': kpi_data[5],
                    'previous': kpi_data[13],
                    'growth': calculate_growth(kpi_data[5], kpi_data[13])
                },
                'profit_margin': {
                    'value': float(kpi_data[6]),
                    'previous': float(kpi_data[14]),
                    'growth': calculate_growth(float(kpi_data[6]), float(kpi_data[14]))
                },
                'revenue_per_activity': {
                    'value': float(kpi_data[7]),
                    'previous': float(kpi_data[15]),
                    'growth': calculate_growth(float(kpi_data[7]), float(kpi_data[15]))
                }
            }
        }

        return render(request, 'dashboard/activities_dashboard.html', context)

    except Exception as e:
        logger.error(f"Error in activities_dashboard: {str(e)}")
        return render(request, 'dashboard/activities_dashboard.html', {
            'error': 'An error occurred while fetching the data'
        })

    try:
        with connection.cursor() as cursor:
            # Get KPIs for current period
            cursor.execute("""
                WITH current_period AS (
                    SELECT 
                        COUNT(DISTINCT VOUCH_ID) as activities,
                        SUM(TOTAL_INVOICE) as revenue,
                        AVG(TOTAL_INVOICE) as avg_price,
                        SUM(NET_EARNING) as earnings
                    FROM MV_IAMS_INVOICE_INFO
                    WHERE VOUCH_DATE >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -1)
                    AND CANCEL = 0
                ),
                previous_period AS (
                    SELECT 
                        COUNT(DISTINCT VOUCH_ID) as activities,
                        SUM(TOTAL_INVOICE) as revenue,
                        AVG(TOTAL_INVOICE) as avg_price,
                        SUM(NET_EARNING) as earnings
                    FROM MV_IAMS_INVOICE_INFO
                    WHERE VOUCH_DATE >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -2)
                    AND VOUCH_DATE < ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -1)
                    AND CANCEL = 0
                )
                SELECT 
                    c.activities, c.revenue, c.avg_price, c.earnings,
                    ROUND(((c.activities - p.activities) / NULLIF(p.activities, 0)) * 100, 2) as activities_growth,
                    ROUND(((c.revenue - p.revenue) / NULLIF(p.revenue, 0)) * 100, 2) as revenue_growth,
                    ROUND(((c.avg_price - p.avg_price) / NULLIF(p.avg_price, 0)) * 100, 2) as price_growth,
                    ROUND(((c.earnings - p.earnings) / NULLIF(p.earnings, 0)) * 100, 2) as earnings_growth
                FROM current_period c, previous_period p
            """)
            kpi_data = cursor.fetchone()

            # Get Activity Trends
            cursor.execute("""
                SELECT 
                    TO_CHAR(TRUNC(VOUCH_DATE, 'MM'), 'YYYY-MM-DD') as month,
                    SUM(TOTAL_INVOICE) as revenue
                FROM MV_IAMS_INVOICE_INFO
                WHERE VOUCH_DATE >= ADD_MONTHS(SYSDATE, -12)
                AND CANCEL = 0
                GROUP BY TRUNC(VOUCH_DATE, 'MM')
                ORDER BY TRUNC(VOUCH_DATE, 'MM')
            """)
            trends_data = cursor.fetchall()

            # Get Activity Types Distribution
            cursor.execute("""
                SELECT 
                    DOC_TYPE,
                    SUM(TOTAL_INVOICE) as revenue
                FROM MV_IAMS_INVOICE_INFO
                WHERE VOUCH_DATE >= ADD_MONTHS(SYSDATE, -12)
                AND CANCEL = 0
                GROUP BY DOC_TYPE
                ORDER BY SUM(TOTAL_INVOICE) DESC
                FETCH FIRST 5 ROWS ONLY
            """)
            types_data = cursor.fetchall()

            # تجهيز البيانات
            data = {
                'kpi_data': {
                    'activities': {'value': kpi_data[0], 'growth': kpi_data[4]},
                    'revenue': {'value': float(kpi_data[1]), 'growth': kpi_data[5]},
                    'avg_price': {'value': float(kpi_data[2]), 'growth': kpi_data[6]},
                    'earnings': {'value': float(kpi_data[3]), 'growth': kpi_data[7]}
                },
                'trends_data': {
                    'labels': [row[0] for row in trends_data],
                    'values': [float(row[2]) for row in trends_data]
                },
                'types_data': {
                    'labels': [row[0] for row in types_data],
                    'values': [float(row[2]) for row in types_data]
                }
            }

            context = {
                'data': json.dumps(data)
            }

            return render(request, 'dashboard/activities_dashboard.html', context)

    except Exception as e:
        print(f"Error: {str(e)}")
        return render(request, 'dashboard/activities_dashboard.html', {
            'error': 'An error occurred while fetching the data'
        })

    try:
        with connection.cursor() as cursor:
            # Get KPIs
            cursor.execute("""
                WITH current_month AS (
                    SELECT 
                        COUNT(DISTINCT VOUCH_ID) as bookings,
                        SUM(TOTAL_INVOICE) as revenue,
                        SUM(NET_EARNING) as profit,
                        COUNT(DISTINCT DOC_TYPE) as doc_types
                    FROM MV_IAMS_INVOICE_INFO
                    WHERE TRUNC(VOUCH_DATE, 'MM') = TRUNC(SYSDATE, 'MM')
                    AND CANCEL = 0
                ),
                previous_month AS (
                    SELECT 
                        COUNT(DISTINCT VOUCH_ID) as bookings,
                        SUM(TOTAL_INVOICE) as revenue,
                        SUM(NET_EARNING) as profit
                    FROM MV_IAMS_INVOICE_INFO
                    WHERE TRUNC(VOUCH_DATE, 'MM') = TRUNC(ADD_MONTHS(SYSDATE, -1), 'MM')
                    AND CANCEL = 0
                ),
                yearly_stats AS (
                    SELECT 
                        SUM(TOTAL_INVOICE) as yearly_revenue,
                        COUNT(DISTINCT VOUCH_ID) as yearly_bookings,
                        AVG(TOTAL_INVOICE) as avg_invoice,
                        SUM(NET_EARNING) as yearly_profit
                    FROM MV_IAMS_INVOICE_INFO
                    WHERE VOUCH_DATE >= ADD_MONTHS(SYSDATE, -12)
                    AND CANCEL = 0
                )
                SELECT 
                    c.bookings, c.revenue, c.profit, c.doc_types,
                    y.yearly_revenue, y.yearly_bookings, y.avg_invoice, y.yearly_profit,
                    ROUND(((c.bookings - p.bookings) / NULLIF(p.bookings, 0) * 100), 2) as bookings_growth,
                    ROUND(((c.revenue - p.revenue) / NULLIF(p.revenue, 0) * 100), 2) as revenue_growth,
                    ROUND(((c.profit - p.profit) / NULLIF(p.profit, 0) * 100), 2) as profit_growth
                FROM current_month c, previous_month p, yearly_stats y
            """)
            kpi_data = cursor.fetchone()

            # Get Monthly Trends
            cursor.execute("""
                SELECT 
                    TO_CHAR(TRUNC(VOUCH_DATE, 'MM'), 'YYYY-MM') as month,
                    COUNT(DISTINCT VOUCH_ID) as bookings,
                    SUM(TOTAL_INVOICE) as revenue,
                    SUM(NET_EARNING) as profit
                FROM MV_IAMS_INVOICE_INFO
                WHERE VOUCH_DATE >= ADD_MONTHS(SYSDATE, -12)
                AND CANCEL = 0
                GROUP BY TRUNC(VOUCH_DATE, 'MM')
                ORDER BY TRUNC(VOUCH_DATE, 'MM')
            """)
            trends = cursor.fetchall()

            # Get Top Doc Types
            cursor.execute("""
                SELECT 
                    DOC_TYPE,
                    COUNT(DISTINCT VOUCH_ID) as bookings,
                    SUM(TOTAL_INVOICE) as revenue,
                    SUM(NET_EARNING) as profit,
                    AVG(TOTAL_INVOICE) as avg_invoice,
                    ROUND(SUM(TOTAL_INVOICE) * 100 / SUM(SUM(TOTAL_INVOICE)) OVER (), 2) as revenue_percentage
                FROM MV_IAMS_INVOICE_INFO
                WHERE VOUCH_DATE >= ADD_MONTHS(SYSDATE, -12)
                AND CANCEL = 0
                GROUP BY DOC_TYPE
                ORDER BY SUM(TOTAL_INVOICE) DESC
                FETCH FIRST 5 ROWS ONLY
            """)
            doc_types = cursor.fetchall()

            context = {
                # KPI Cards
                'kpi_data': {
                    'current': {
                        'bookings': kpi_data[0],
                        'revenue': kpi_data[1],
                        'profit': kpi_data[2],
                        'doc_types': kpi_data[3]
                    },
                    'yearly': {
                        'revenue': kpi_data[4],
                        'bookings': kpi_data[5],
                        'avg_invoice': kpi_data[6],
                        'profit': kpi_data[7]
                    },
                    'growth': {
                        'bookings': kpi_data[8],
                        'revenue': kpi_data[9],
                        'profit': kpi_data[10]
                    }
                },
                
                # Charts Data
                'trends_data': json.dumps({
                    'labels': [row[0] for row in trends],
                    'bookings': [row[1] for row in trends],
                    'revenue': [float(row[2]) for row in trends],
                    'profit': [float(row[3]) for row in trends]
                }),
                
                'types_data': json.dumps({
                    'labels': [row[0] for row in doc_types],
                    'data': [{
                        'doc_type': row[0],
                        'bookings': row[1],
                        'revenue': float(row[2]),
                        'profit': float(row[3]),
                        'avg_invoice': float(row[4]),
                        'percentage': float(row[5])
                    } for row in doc_types]
                })
            }

            return render(request, 'dashboard/activities_dashboard.html', context)

    except Exception as e:
        print(f"Error: {str(e)}")
        return render(request, 'dashboard/activities_dashboard.html', {
            'error': 'An error occurred while fetching the data'
        })
    try:
        range_type = request.GET.get('range', 'monthly')
        with connection.cursor() as cursor:
            # تحديد نطاق التاريخ بناءً على النوع المطلوب
            if range_type == 'weekly':
                date_trunc = 'IW'  # ISO week
                months_back = -3
            elif range_type == 'yearly':
                date_trunc = 'YYYY'
                months_back = -24
            else:  # monthly
                date_trunc = 'MM'
                months_back = -12
           # Get Activity Trends
            cursor.execute(f"""
                SELECT 
                    TO_CHAR(TRUNC(VOUCH_DATE, '{date_trunc}'), 'YYYY-MM-DD') as period,
                    COUNT(DISTINCT VOUCH_ID) as total_activities,
                    SUM(TOTAL_INVOICE) as total_revenue,
                    SUM(NET_EARNING) as total_profit
                FROM MV_IAMS_INVOICE_INFO
                WHERE VOUCH_DATE >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), {months_back})
                AND CANCEL = 0
                GROUP BY TRUNC(VOUCH_DATE, '{date_trunc}')
                ORDER BY TRUNC(VOUCH_DATE, '{date_trunc}')
            """)
            trends_data = cursor.fetchall()

            # Get Activity Types Distribution
            cursor.execute("""
                SELECT 
                    DOC_TYPE,
                    COUNT(DISTINCT VOUCH_ID) as total_bookings,
                    SUM(TOTAL_INVOICE) as total_revenue
                FROM MV_IAMS_INVOICE_INFO
                WHERE VOUCH_DATE >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12)
                AND CANCEL = 0
                GROUP BY DOC_TYPE
                ORDER BY SUM(TOTAL_INVOICE) DESC
                FETCH FIRST 5 ROWS ONLY
            """)
            types_data = cursor.fetchall()

            # Get KPI Data
            cursor.execute("""
                WITH current_period AS (
                    SELECT 
                        COUNT(DISTINCT VOUCH_ID) as activities,
                        SUM(TOTAL_INVOICE) as revenue,
                        AVG(TOTAL_INVOICE) as avg_price,
                        SUM(NET_EARNING) as earnings
                    FROM MV_IAMS_INVOICE_INFO
                    WHERE VOUCH_DATE >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -1)
                    AND CANCEL = 0
                ),
                previous_period AS (
                    SELECT 
                        COUNT(DISTINCT VOUCH_ID) as activities,
                        SUM(TOTAL_INVOICE) as revenue,
                        AVG(TOTAL_INVOICE) as avg_price,
                        SUM(NET_EARNING) as earnings
                    FROM MV_IAMS_INVOICE_INFO
                    WHERE VOUCH_DATE >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -2)
                    AND VOUCH_DATE < ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -1)
                    AND CANCEL = 0
                )
                SELECT 
                    c.activities, c.revenue, c.avg_price, c.earnings,
                    ((c.activities - p.activities) / NULLIF(p.activities, 0)) * 100 as activities_growth,
                    ((c.revenue - p.revenue) / NULLIF(p.revenue, 0)) * 100 as revenue_growth,
                    ((c.avg_price - p.avg_price) / NULLIF(p.avg_price, 0)) * 100 as price_growth,
                    ((c.earnings - p.earnings) / NULLIF(p.earnings, 0)) * 100 as earnings_growth
                FROM current_period c, previous_period p
            """)
            kpi_data = cursor.fetchone()

            return JsonResponse({
                'trends_data': {
                    'labels': [row[0] for row in trends_data],
                    'values': [float(row[2]) for row in trends_data]
                },
                'types_data': {
                    'labels': [row[0] for row in types_data],
                    'values': [float(row[2]) for row in types_data]
                },
                'kpi_data': {
                    'activities': {
                        'value': kpi_data[0],
                        'growth': kpi_data[4]
                    },
                    'revenue': {
                        'value': float(kpi_data[1]),
                        'growth': kpi_data[5]
                    },
                    'avg_price': {
                        'value': float(kpi_data[2]),
                        'growth': kpi_data[6]
                    },
                    'earnings': {
                        'value': float(kpi_data[3]),
                        'growth': kpi_data[7]
                    }
                }
            })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    except Exception as e:
        print(f"Error: {str(e)}")
        return render(request, 'dashboard/activities_dashboard.html', {
            'error': 'An error occurred while fetching the data'
        })

from django.http import JsonResponse

def activities_data(request):
    try:
        range_type = request.GET.get('range', 'monthly')
        with connection.cursor() as cursor:
            # تحديد نطاق التاريخ بناءً على النوع المطلوب
            if range_type == 'weekly':
                date_trunc = 'IW'  # ISO week
                months_back = -3
            elif range_type == 'yearly':
                date_trunc = 'YYYY'
                months_back = -24
            else:  # monthly
                date_trunc = 'MM'
                months_back = -12

            # Get Activity Trends
            cursor.execute(f"""
                SELECT 
                    TO_CHAR(TRUNC(VOUCH_DATE, '{date_trunc}'), 'YYYY-MM-DD') as period,
                    COUNT(DISTINCT VOUCH_ID) as total_activities,
                    SUM(TOTAL_INVOICE) as total_revenue,
                    SUM(NET_EARNING) as total_profit
                FROM MV_IAMS_INVOICE_INFO
                WHERE VOUCH_DATE >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), {months_back})
                AND CANCEL = 0
                GROUP BY TRUNC(VOUCH_DATE, '{date_trunc}')
                ORDER BY TRUNC(VOUCH_DATE, '{date_trunc}')
            """)
            trends_data = cursor.fetchall()

            # Get Activity Types Distribution
            cursor.execute("""
                SELECT 
                    DOC_TYPE,
                    COUNT(DISTINCT VOUCH_ID) as total_bookings,
                    SUM(TOTAL_INVOICE) as total_revenue
                FROM MV_IAMS_INVOICE_INFO
                WHERE VOUCH_DATE >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12)
                AND CANCEL = 0
                GROUP BY DOC_TYPE
                ORDER BY SUM(TOTAL_INVOICE) DESC
                FETCH FIRST 5 ROWS ONLY
            """)
            types_data = cursor.fetchall()

            # Get KPIs
            cursor.execute("""
                WITH current_period AS (
                    SELECT 
                        COUNT(DISTINCT VOUCH_ID) as activities,
                        SUM(TOTAL_INVOICE) as revenue,
                        AVG(TOTAL_INVOICE) as avg_price,
                        SUM(NET_EARNING) as earnings
                    FROM MV_IAMS_INVOICE_INFO
                    WHERE VOUCH_DATE >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -1)
                    AND CANCEL = 0
                ),
                previous_period AS (
                    SELECT 
                        COUNT(DISTINCT VOUCH_ID) as activities,
                        SUM(TOTAL_INVOICE) as revenue,
                        AVG(TOTAL_INVOICE) as avg_price,
                        SUM(NET_EARNING) as earnings
                    FROM MV_IAMS_INVOICE_INFO
                    WHERE VOUCH_DATE >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -2)
                    AND VOUCH_DATE < ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -1)
                    AND CANCEL = 0
                )
                SELECT 
                    c.activities, c.revenue, c.avg_price, c.earnings,
                    ROUND(((c.activities - p.activities) / NULLIF(p.activities, 0)) * 100, 2) as activities_growth,
                    ROUND(((c.revenue - p.revenue) / NULLIF(p.revenue, 0)) * 100, 2) as revenue_growth,
                    ROUND(((c.avg_price - p.avg_price) / NULLIF(p.avg_price, 0)) * 100, 2) as price_growth,
                    ROUND(((c.earnings - p.earnings) / NULLIF(p.earnings, 0)) * 100, 2) as earnings_growth
                FROM current_period c, previous_period p
            """)
            kpi_data = cursor.fetchone()

            return JsonResponse({
                'trends_data': {
                    'labels': [row[0] for row in trends_data],
                    'values': [float(row[2]) for row in trends_data]
                },
                'types_data': {
                    'labels': [row[0] for row in types_data],
                    'values': [float(row[2]) for row in types_data]
                },
                'kpi_data': {
                    'activities': {
                        'value': kpi_data[0],
                        'growth': kpi_data[4]
                    },
                    'revenue': {
                        'value': float(kpi_data[1]),
                        'growth': kpi_data[5]
                    },
                    'avg_price': {
                        'value': float(kpi_data[2]),
                        'growth': kpi_data[6]
                    },
                    'earnings': {
                        'value': float(kpi_data[3]),
                        'growth': kpi_data[7]
                    }
                }
            })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def calculate_doc_type_growth(cursor, doc_type):
    cursor.execute("""
        WITH current_period AS (
            SELECT SUM(TOTAL_INVOICE) as revenue
            FROM MV_IAMS_INVOICE_INFO
            WHERE DOC_TYPE = :doc_type
            AND VOUCH_DATE >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -1)
            AND CANCEL = 0
        ),
        previous_period AS (
            SELECT SUM(TOTAL_INVOICE) as revenue
            FROM MV_IAMS_INVOICE_INFO
            WHERE DOC_TYPE = :doc_type
            AND VOUCH_DATE >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -2)
            AND VOUCH_DATE < ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -1)
            AND CANCEL = 0
        )
        SELECT 
            ((c.revenue - p.revenue) / NULLIF(p.revenue, 0)) * 100
        FROM current_period c, previous_period p
    """, {'doc_type': doc_type})
    
    result = cursor.fetchone()
    return result[0] if result and result[0] else 0
    return create_detailed_dashboard(request, 'doc_type', 'dashboard/activities_dashboard.html')

@login_required
@login_required
def dashboard(request):
    # Get date ranges
    today = datetime.now()
    last_month = today - timedelta(days=30)
    
    # Basic KPI calculations
    context = {
        'total_sales': Sale.objects.count(),
        'total_revenue': Sale.objects.aggregate(total=Sum('total_price'))['total'] or 0,
        'active_agents': Agent.objects.filter(user__is_active=1).count(),
        'total_activities': Activity.objects.count(),
        
        # Growth calculations
        'sales_growth': calculate_growth('sales'),
        'revenue_growth': calculate_growth('revenue'),
        'agents_growth': calculate_growth('agents'),
        'activities_growth': calculate_growth('activities'),
    }
    
    # Add chart data
    context.update({
        'sales_data': json.dumps(get_sales_data()),
        'agents_data': json.dumps(get_agents_data()),
    })
    
    return render(request, 'dashboard/dashboard.html', context)
    # Get date ranges
    today = datetime.now()
    last_month = today - timedelta(days=30)
    
    # Basic KPI calculations
    context = {
        'total_sales': Sale.objects.count(),
        'total_revenue': Sale.objects.aggregate(total=Sum('total_price'))['total'] or 0,
        'active_agents': Agent.objects.filter(user__is_active=1).count(),
        'total_activities': Activity.objects.count(),
        
        # Growth calculations
        'sales_growth': calculate_growth('sales'),
        'revenue_growth': calculate_growth('revenue'),
        'agents_growth': calculate_growth('agents'),
        'activities_growth': calculate_growth('activities'),
    }
    
    # Add chart data
    context.update({
        'sales_data': json.dumps(get_sales_data()),
        'agents_data': json.dumps(get_agents_data()),
    })
    
    return render(request, 'dashboard/dashboard.html', context)

def calculate_growth(metric_type):
    """Calculate growth percentage for different metrics"""
    today = datetime.now()
    last_month = today - timedelta(days=30)
    two_months_ago = today - timedelta(days=60)
    
    if metric_type == 'sales':
        current = Sale.objects.filter(date__gte=last_month).count()
        previous = Sale.objects.filter(date__gte=two_months_ago, date__lt=last_month).count()
    elif metric_type == 'revenue':
        current = Sale.objects.filter(date__gte=last_month).aggregate(total=Sum('total_price'))['total'] or 0
        previous = Sale.objects.filter(date__gte=two_months_ago, date__lt=last_month).aggregate(total=Sum('total_price'))['total'] or 0
    elif metric_type == 'agents':
        current = Agent.objects.filter(user__is_active=1, user__date_joined__gte=last_month).count()
        previous = Agent.objects.filter(user__is_active=1, user__date_joined__gte=two_months_ago, user__date_joined__lt=last_month).count()
    elif metric_type == 'activities':
        current = Activity.objects.filter(sale__date__gte=last_month).count()
        previous = Activity.objects.filter(sale__date__gte=two_months_ago, sale__date__lt=last_month).count()
    
    if previous == 0:
        return 100 if current > 0 else 0
    return ((current - previous) / previous) * 100

def get_sales_data(period='monthly'):
    """Get sales data for charts"""
    today = datetime.now()
    
    if period == 'weekly':
        sales = Sale.objects.annotate(
            period=TruncWeek('date')
        ).values('period').annotate(
            total=Sum('total_price')
        ).order_by('period')
    elif period == 'yearly':
        sales = Sale.objects.annotate(
            period=TruncYear('date')
        ).values('period').annotate(
            total=Sum('total_price')
        ).order_by('period')
    else:  # monthly
        sales = Sale.objects.annotate(
            period=TruncMonth('date')
        ).values('period').annotate(
            total=Sum('total_price')
        ).order_by('period')
    
    return {
        'labels': [s['period'].strftime('%Y-%m-%d') for s in sales],
        'values': [float(s['total']) for s in sales]
    }

def get_agents_data():
    """Get top agents data for charts"""
    top_agents = Sale.objects.filter(
        agent__user__is_active=1
    ).values(
        'agent__user__username'
    ).annotate(
        total_sales=Sum('total_price')
    ).order_by('-total_sales')[:5]
    
    return {
        'labels': [agent['agent__user__username'] for agent in top_agents],
        'values': [float(agent['total_sales']) for agent in top_agents]
    }

# Add API endpoints for chart updates
from django.http import JsonResponse

def update_chart_data(request):
    period = request.GET.get('period', 'monthly')
    chart_type = request.GET.get('type', 'sales')
    
    if chart_type == 'sales':
        data = get_sales_data(period)
    else:
        data = get_agents_data()
    
    return JsonResponse(data)

@login_required
def agents(request):
    agents = Agent.objects.all()
    return render(request, 'dashboard/agents.html', {'agents': agents})

@login_required
def providers(request):
    providers = Provider.objects.all()
    return render(request, 'dashboard/providers.html', {'providers': providers})

@login_required
def sales(request):
    sales = Sale.objects.all()
    return render(request, 'dashboard/sales.html', {'sales': sales})

@login_required
def activities(request):
    activities = Activity.objects.all()
    return render(request, 'dashboard/activities.html', {'activities': activities})

def detect_invoice_columns(table_name):
    """
    Dynamically detect columns for invoice-related calculations
    """
    try:
        with connection.cursor() as cursor:
            # Get column details
            cursor.execute(f"""
                SELECT 
                    column_name, 
                    data_type
                FROM all_tab_columns 
                WHERE table_name = :table_name
                AND owner = SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA')
            """, {'table_name': table_name})
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
    
    except Exception as e:
        logger.error(f"Error detecting columns for {table_name}: {str(e)}")
        return {}

def create_flexible_kpi_query(table_name):
    """
    Create a flexible KPI query based on detected columns
    """
    # Detect columns
    columns = detect_invoice_columns(table_name)
    
    # Fallback column names if detection fails
    total_amount_col = columns.get('total_amount', 'TOTAL_AMOUNT')
    total_cost_col = columns.get('total_cost', 'TOTAL_COST')
    total_profit_col = columns.get('total_profit', 'TOTAL_PROFIT')
    
    # Construct flexible query
    kpi_query = f"""
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
    """
    
    return kpi_query