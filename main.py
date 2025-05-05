# -*- coding: utf-8 -*-
import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import io
from flask import Flask, send_from_directory, request, redirect, url_for, flash, send_file, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

from src.database import db
# Import models
from src.models.client import Client
from src.models.user import User # Import User model

# Define template folder explicitly
app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), 'templates'), static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'stockeify_secret_key_#$@!' # Changed secret key for security

# Enable database functionality
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{os.getenv('DB_USERNAME', 'root')}:{os.getenv('DB_PASSWORD', 'password')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '3306')}/{os.getenv('DB_NAME', 'mydb')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Redirect to login page if user is not logged in
login_manager.login_message = 'يرجى تسجيل الدخول للوصول إلى هذه الصفحة.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database tables if they don't exist
with app.app_context():
    # db.drop_all() # Uncomment only if schema changes require dropping tables
    db.create_all() # Create tables based on models

# --- Authentication Routes ---

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('اسم المستخدم وكلمة المرور مطلوبان.', 'error')
            return redirect(url_for('signup'))

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('اسم المستخدم موجود بالفعل. يرجى اختيار اسم آخر.', 'error')
            return redirect(url_for('signup'))

        try:
            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('تم إنشاء الحساب بنجاح. يمكنك الآن تسجيل الدخول.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء إنشاء الحساب: {str(e)}', 'error')
            print(f"Error creating user: {e}")
            return redirect(url_for('signup'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            flash('اسم المستخدم أو كلمة المرور غير صحيحة. يرجى المحاولة مرة أخرى.', 'error')
            return redirect(url_for('login'))

        login_user(user, remember=remember)
        flash('تم تسجيل الدخول بنجاح!', 'success')
        # Redirect to the page user was trying to access, or index
        next_page = request.args.get('next')
        return redirect(next_page or url_for('index'))

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('تم تسجيل الخروج بنجاح.', 'info')
    return redirect(url_for('login'))

# --- Application Routes (Protected) ---

@app.route('/')
@login_required
def index():
    # Render the index.html template (data entry form)
    return render_template('index.html')

@app.route('/add_client', methods=['POST'])
@login_required
def add_client():
    if request.method == 'POST':
        try:
            client_name = request.form['client_name']
            client_number = request.form['client_number']
            service_tag = request.form['service_tag']
            if service_tag == 'Other Service':
                service_tag = request.form.get('other_service_tag', 'Other Service')

            service_details = request.form.get('service_details')
            start_date_str = request.form['start_date']
            duration = int(request.form['duration'])
            main_price = float(request.form['main_price'])
            additional_costs = float(request.form.get('additional_costs', 0.0))
            client_type = request.form['client_type']
            if client_type == 'other':
                client_type = request.form.get('other_client_type', 'other')

            installments = int(request.form.get('installments', 0))
            notes = request.form.get('notes')

            if not all([client_name, client_number, service_tag, start_date_str, duration > 0, main_price is not None, client_type, installments is not None]):
                flash('يرجى ملء جميع الحقول الإلزامية والتأكد من أن المدة أكبر من صفر.', 'error')
                return redirect(url_for('index'))

            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()

            new_client = Client(
                client_name=client_name,
                client_number=client_number,
                service_tag=service_tag,
                service_details=service_details,
                start_date=start_date,
                duration=duration,
                main_price=main_price,
                additional_costs=additional_costs,
                client_type=client_type,
                installments=installments,
                notes=notes,
                creator_id=current_user.id # Associate with logged-in user
            )

            db.session.add(new_client)
            db.session.commit()
            flash('تمت إضافة العميل بنجاح!', 'success')

        except ValueError:
            flash('خطأ في البيانات المدخلة (مثل الأرقام أو التواريخ). يرجى المحاولة مرة أخرى.', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ غير متوقع: {str(e)}', 'error')
            print(f"Error adding client: {e}")

        return redirect(url_for('index'))

@app.route('/view_clients')
@login_required
def view_clients():
    try:
        clients_query = Client.query.join(User).add_columns(
            Client.id, Client.client_name, Client.client_number, Client.service_tag,
            Client.start_date, Client.duration, Client.main_price, Client.additional_costs,
            Client.client_type, Client.notes, User.username.label('creator_username')
        ) # Join User table and select username

        search_term = request.args.get('search', '')
        service_tag_filter = request.args.get('service_tag', '')
        client_type_filter = request.args.get('client_type', '')
        status_filter = request.args.get('status', '')
        start_date_from_str = request.args.get('start_date_filter', '')
        start_date_to_str = request.args.get('end_date_filter', '')

        if search_term:
            search_like = f"%{search_term}%"
            clients_query = clients_query.filter(
                or_(Client.client_name.like(search_like), Client.client_number.like(search_like))
            )
        if service_tag_filter:
            clients_query = clients_query.filter(Client.service_tag == service_tag_filter)
        if client_type_filter:
            clients_query = clients_query.filter(Client.client_type == client_type_filter)
        if start_date_from_str:
            start_date_from = datetime.strptime(start_date_from_str, '%Y-%m-%d').date()
            clients_query = clients_query.filter(Client.start_date >= start_date_from)
        if start_date_to_str:
            start_date_to = datetime.strptime(start_date_to_str, '%Y-%m-%d').date()
            clients_query = clients_query.filter(Client.start_date <= start_date_to)

        clients_query = clients_query.order_by(Client.created_at.desc())
        filtered_clients = clients_query.all()

        clients_data = []
        today = date.today()

        for client in filtered_clients:
            start_date = client.start_date
            end_date = start_date + timedelta(days=client.duration)
            remaining_days = (end_date - today).days
            status = "نشط" if remaining_days > 0 else "منتهي"

            if status_filter and status != status_filter:
                continue

            total_price = client.main_price + client.additional_costs

            clients_data.append({
                'id': client.id,
                'client_name': client.client_name,
                'client_number': client.client_number,
                'service_tag': client.service_tag,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'days_left': remaining_days if remaining_days > 0 else 0,
                'status': status,
                'client_type': client.client_type,
                'total_price': total_price,
                'notes': client.notes,
                'creator': client.creator_username # Add creator username
            })

        return render_template('view_clients.html', clients=clients_data)

    except ValueError:
        flash('صيغة التاريخ غير صحيحة. يرجى استخدام YYYY-MM-DD.', 'error')
        return redirect(url_for('view_clients'))
    except Exception as e:
        flash(f'حدث خطأ أثناء جلب بيانات العملاء: {str(e)}', 'error')
        print(f"Error fetching clients: {e}")
        return redirect(url_for('index'))

@app.route('/export_excel')
@login_required
def export_excel():
    try:
        clients_query = Client.query.join(User).add_columns(
            Client.id, Client.client_name, Client.client_number, Client.service_tag,
            Client.service_details, Client.start_date, Client.duration, Client.main_price,
            Client.additional_costs, Client.client_type, Client.installments, Client.notes,
            Client.created_at, User.username.label('creator_username')
        )

        search_term = request.args.get('search', '')
        service_tag_filter = request.args.get('service_tag', '')
        client_type_filter = request.args.get('client_type', '')
        status_filter = request.args.get('status', '')
        start_date_from_str = request.args.get('start_date_filter', '')
        start_date_to_str = request.args.get('end_date_filter', '')

        if search_term:
            search_like = f"%{search_term}%"
            clients_query = clients_query.filter(
                or_(Client.client_name.like(search_like), Client.client_number.like(search_like))
            )
        if service_tag_filter:
            clients_query = clients_query.filter(Client.service_tag == service_tag_filter)
        if client_type_filter:
            clients_query = clients_query.filter(Client.client_type == client_type_filter)
        try:
            if start_date_from_str:
                start_date_from = datetime.strptime(start_date_from_str, '%Y-%m-%d').date()
                clients_query = clients_query.filter(Client.start_date >= start_date_from)
            if start_date_to_str:
                start_date_to = datetime.strptime(start_date_to_str, '%Y-%m-%d').date()
                clients_query = clients_query.filter(Client.start_date <= start_date_to)
        except ValueError:
             flash('صيغة التاريخ غير صحيحة في الفلاتر. يتم التصدير بدون فلترة التاريخ.', 'warning')

        filtered_clients = clients_query.all()

        if not filtered_clients:
            flash('لا توجد بيانات لتصديرها بناءً على الفلاتر المحددة.', 'info')
            return redirect(url_for('view_clients', **request.args))

        data = []
        today = date.today()

        for client in filtered_clients:
            start_date = client.start_date
            end_date = start_date + timedelta(days=client.duration)
            remaining_days = (end_date - today).days
            status = "نشط" if remaining_days > 0 else "منتهي"

            if status_filter and status != status_filter:
                continue

            total_price = client.main_price + client.additional_costs
            monthly_installment = (total_price / client.installments) if client.installments > 0 else 0

            data.append({
                'معرف العميل': client.id,
                'اسم العميل': client.client_name,
                'رقم العميل': client.client_number,
                'نوع الخدمة': client.service_tag,
                'تفاصيل الخدمة': client.service_details,
                'تاريخ البدء': start_date.strftime('%Y-%m-%d'),
                'المدة (أيام)': client.duration,
                'تاريخ الانتهاء': end_date.strftime('%Y-%m-%d'),
                'الأيام المتبقية': remaining_days if remaining_days > 0 else 0,
                'الحالة': status,
                'السعر الأساسي': client.main_price,
                'التكاليف الإضافية': client.additional_costs,
                'السعر الإجمالي': total_price,
                'نوع العميل': client.client_type,
                'عدد الأقساط': client.installments,
                'القسط الشهري': round(monthly_installment, 2) if monthly_installment > 0 else '-',
                'ملاحظات': client.notes,
                'تاريخ الإضافة': client.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'أضيف بواسطة': client.creator_username # Add creator username
            })

        if not data:
             flash('لا توجد بيانات لتصديرها بناءً على الفلاتر المحددة (بما في ذلك فلتر الحالة).', 'info')
             return redirect(url_for('view_clients', **request.args))

        df = pd.DataFrame(data)

        summary = {
            'اسم العميل': 'الإجمالي',
            'السعر الأساسي': df['السعر الأساسي'].sum(),
            'التكاليف الإضافية': df['التكاليف الإضافية'].sum(),
            'السعر الإجمالي': df['السعر الإجمالي'].sum(),
        }
        summary_df = pd.DataFrame([summary])
        summary_df = summary_df.fillna('')
        df_final = pd.concat([df, summary_df], ignore_index=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_final.to_excel(writer, index=False, sheet_name='بيانات العملاء')
        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'stockeify_clients_{today.strftime("%Y%m%d")}.xlsx'
        )

    except Exception as e:
        flash(f'حدث خطأ أثناء تصدير ملف الإكسل: {str(e)}', 'error')
        print(f"Error exporting Excel: {e}")
        return redirect(url_for('view_clients', **request.args))

# Serve static files (CSS, JS)
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)