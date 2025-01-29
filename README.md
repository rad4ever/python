# Travel Agency Dashboard

A comprehensive Django-based dashboard for tracking key performance indicators (KPIs) and financial analytics for a global travel agency group. The dashboard pulls data from an Oracle Database and provides interactive visualizations and detailed reports.

## Features

- **Real-time KPI Tracking:**
  - Total Revenue
  - Net Earnings
  - Customer Activity
  - Sales Performance
  - Supplier Performance

- **Interactive Dashboards:**
  - Monthly Revenue Trends
  - Document Type Distribution
  - Top Performing Agents
  - Top Customers

- **Filtering Capabilities:**
  - By Year
  - By Company
  - By Document Type

- **REST API Integration**
  - Complete API for all data endpoints
  - Filterable and searchable endpoints
  - Authentication required for all API access

## Prerequisites

- Python 3.11 or higher
- Oracle Database 19.3c
- Oracle Instant Client (for cx_Oracle)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd travel_dash
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/Mac
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure the database settings in `travel_dashboard/settings.py`:
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.oracle',
           'NAME': 'your_oracle_service_name',
           'USER': 'your_username',
           'PASSWORD': 'your_password',
           'HOST': 'your_host',
           'PORT': '1521',
       }
   }
   ```

5. Run migrations:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

7. Import data from Oracle:
   ```bash
   python manage.py import_invoice_data
   ```

8. Run the development server:
   ```bash
   python manage.py runserver
   ```

## Usage

1. Access the dashboard at `http://localhost:8000`
2. Login with your credentials
3. Use the filters at the top of the dashboard to analyze specific data
4. Access the admin interface at `http://localhost:8000/admin` for data management

## API Endpoints

- `/api/currencies/` - List of currencies
- `/api/document-types/` - List of document types
- `/api/companies/` - List of companies
- `/api/invoices/` - List of invoices with filtering options

All API endpoints require authentication and support filtering and pagination.

## Development

- The project uses Django 4.x
- REST API is built with Django REST Framework
- Frontend uses Bootstrap 5 and Plotly.js for visualizations
- Data is cached where appropriate for performance

## Security

- All pages require authentication
- API endpoints are protected
- Database credentials should be stored in environment variables
- CSRF protection is enabled
- Debug mode should be disabled in production

## License

This project is licensed under the MIT License - see the LICENSE file for details
