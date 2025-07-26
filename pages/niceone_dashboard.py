try:
    from auth_protection import check_authentication, add_logout_button
    if not check_authentication():
        st.stop()
except ImportError:
    st.error("❌ ملف الحماية غير موجود")
    st.stop()

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import re
import os
import glob
import time
from pathlib import Path
import hashlib


# 🔧 دوال حفظ البيانات البسيطة - مُحسّنة للسرعة
def save_company_data(company_name, df, branch_files=None, source="manual"):
    """حفظ البيانات في session_state بسرعة عالية"""
    data_key = f"{company_name.lower()}_saved_data"
    
    # حفظ البيانات الرئيسية بدون نسخ عميق لتوفير الوقت
    st.session_state[data_key] = {
        'main_df': df,  # إزالة .copy() لتوفير الوقت والذاكرة
        'branch_files': branch_files if branch_files else None,  # إزالة .copy() 
        'save_time': datetime.now(),
        'source': source,
        'total_rows': len(df),
        'total_columns': len(df.columns)
    }
    
    # رسالة نجاح سريعة
    st.success(f"✅ تم حفظ بيانات {company_name}! ({len(df):,} سجل)")
def get_company_data(company_name):
    """استرجاع البيانات من session_state"""
    data_key = f"{company_name.lower()}_saved_data"
    return st.session_state.get(data_key, None)

def has_saved_data(company_name):
    """تحقق من وجود بيانات محفوظة"""
    saved_data = get_company_data(company_name)
    return saved_data is not None and 'main_df' in saved_data

def clear_company_data(company_name):
    """مسح البيانات المحفوظة"""
    data_key = f"{company_name.lower()}_saved_data"
    if data_key in st.session_state:
        del st.session_state[data_key]
        st.success(f"✅ تم مسح بيانات {company_name}")

def show_saved_data_info(company_name):
    """عرض معلومات البيانات المحفوظة بشكل مبسط"""
    saved_data = get_company_data(company_name)
    if saved_data:
        save_time = saved_data['save_time'].strftime('%H:%M:%S')
        st.info(f"📋 **بيانات محفوظة:** {saved_data['total_rows']:,} سجل - {save_time} - {saved_data['source']}")
        return True
    return False

# CSS محسّن ومبسط
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700&display=swap');
    
    * {
        font-family: 'Cairo', sans-serif !important;
    }
    
    .main {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1rem;
    }
    
    .metric-delta {
        white-space: nowrap;
    }
    
    /* Header */
    .main-header {
        background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    }
    
    .main-title {
        color: white;
        font-size: 3rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .main-subtitle {
        color: #ecf0f1;
        font-size: 1.2rem;
        margin-top: 0.5rem;
        opacity: 0.9;
    }
    
    /* Status Panel - إضافة جديدة */
    .status-panel {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 6px 20px rgba(0,0,0,0.2);
    }
    
    /* Auto Update Settings */
    .auto-update-panel {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 6px 20px rgba(0,0,0,0.2);
    }
    
    .status-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-left: 8px;
        animation: pulse 2s infinite;
    }
    
    .status-active { background-color: #27ae60; }
    .status-inactive { background-color: #e74c3c; }
    .status-updating { background-color: #f39c12; }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    
    /* KPI Cards */
    .kpi-container {
        display: flex;
        gap: 1.5rem;
        margin-bottom: 2rem;
        flex-wrap: wrap;
    }
    
    .kpi-card {
        flex: 1;
        min-width: 250px;
        background: white;
        padding: 2rem 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        text-align: center;
        border-left: 5px solid;
        transition: transform 0.3s ease;
    }
    
    .kpi-card:hover {
        transform: translateY(-5px);
    }
    
    .kpi-card.orders { border-left-color: #3498db; }
    .kpi-card.success { border-left-color: #27ae60; }
    .kpi-card.first-attempt { border-left-color: #e74c3c; }
    .kpi-card.avg-attempts { border-left-color: #f39c12; }
    
    .kpi-value {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        color: #2c3e50;
    }
    
    .kpi-label {
        font-size: 1rem;
        color: #7f8c8d;
        margin-top: 0.5rem;
        font-weight: 600;
    }
    
    .kpi-change {
        font-size: 0.9rem;
        margin-top: 0.3rem;
        padding: 0.2rem 0.8rem;
        border-radius: 20px;
        display: inline-block;
    }
    
    /* Filter Section */
    .filter-section {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        margin-bottom: 2rem;
    }
    
    .filter-title {
        color: #2c3e50;
        font-size: 1.3rem;
        font-weight: 700;
        margin-bottom: 1rem;
        border-bottom: 2px solid #3498db;
        padding-bottom: 0.5rem;
    }
    
    /* Chart Containers */
    .chart-container {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        margin-bottom: 2rem;
        width: 100%;
    }
    
    .chart-title {
        color: #2c3e50;
        font-size: 1.3rem;
        font-weight: 700;
        margin-bottom: 1rem;
        text-align: center;
        border-bottom: 2px solid #ecf0f1;
        padding-bottom: 0.5rem;
    }
    
    /* File Path Display */
    .file-path {
        background: #f8f9fa;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        border-left: 3px solid #007bff;
        font-family: monospace;
        font-size: 0.9rem;
        margin: 0.5rem 0;
    }
    
    /* Upload Section */
    .upload-section {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        margin-bottom: 2rem;
        transition: all 0.3s ease;
    }
    
    .upload-section.hidden {
        display: none;
    }
    
    /* Info Box */
    .info-box {
        background: linear-gradient(135deg, #e3f2fd, #bbdefb);
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #2196f3;
        margin: 1rem 0;
    }
    
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    
    .block-container {
        max-width: 1400px;
        padding-top: 1rem;
    }
    
    /* Responsive */
    @media (max-width: 768px) {
        .kpi-container {
            flex-direction: column;
        }
        
        .main-title {
            font-size: 2rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# دوال المساعدة
def fix_duplicate_columns(df):
    columns = df.columns.tolist()
    new_columns = []
    column_counts = {}
    
    for col in columns:
        clean_col = str(col).strip()
        if clean_col in column_counts:
            column_counts[clean_col] += 1
            new_col_name = f"{clean_col}_{column_counts[clean_col]}"
        else:
            column_counts[clean_col] = 0
            new_col_name = clean_col
        new_columns.append(new_col_name)
    
    df.columns = new_columns
    return df

def process_column_names(df):
    if len(df.columns) > 0 and (df.columns[0] == '#' or 'Unnamed' in str(df.columns[0])):
        df = df.drop(df.columns[0], axis=1)
    
    expected_columns = [
        'رقم الطلب', 'رقم التتبع', 'اسم العميل', 'هاتف العميل',
        'موقع العميل', 'المطلوب تحصيله', 'السبب', 'حالة الطلب',
        'رقم ورقة التشغيل', 'الرقم التعريفي', 'اسم المندوب',
        'تاريخ استلام الشحنة', 'تاريخ الشحن'
    ]
    
    current_columns = df.columns.tolist()
    new_column_names = {}
    
    for i, col in enumerate(current_columns):
        if i < len(expected_columns):
            new_column_names[col] = expected_columns[i]
    
    df = df.rename(columns=new_column_names)
    return df

def analyze_attempts(df):
    try:
        if 'تاريخ استلام الشحنة' in df.columns and 'تاريخ الشحن' in df.columns:
            
            def convert_receive_date(date_val):
                try:
                    if pd.isna(date_val):
                        return None
                    if isinstance(date_val, pd.Timestamp) or hasattr(date_val, 'date'):
                        return pd.to_datetime(date_val).date()
                    elif isinstance(date_val, (int, float)) and date_val > 40000:
                        excel_epoch = pd.Timestamp('1899-12-30')
                        return (excel_epoch + pd.Timedelta(days=date_val)).date()
                    else:
                        return pd.to_datetime(date_val, errors='coerce').date()
                except:
                    return None
            
            def convert_ship_date(date_val):
                try:
                    if pd.isna(date_val):
                        return None
                    if isinstance(date_val, str) and '/' in date_val:
                        parts = date_val.split('/')
                        if len(parts) == 3:
                            return pd.to_datetime(f"{parts[2]}-{parts[1]}-{parts[0]}", errors='coerce').date()
                    return pd.to_datetime(date_val, errors='coerce').date()
                except:
                    return None
            
            df['تاريخ_استلام_محول'] = df['تاريخ استلام الشحنة'].apply(convert_receive_date)
            df['تاريخ_شحن_محول'] = df['تاريخ الشحن'].apply(convert_ship_date)
            
            def determine_attempt_type(row):
                try:
                    status = str(row.get('حالة الطلب', '')).strip()
                    if not ('Delivered' in status and 'Confirmed' in status):
                        return 'غير مسلم'
                    
                    receive_date = row['تاريخ_استلام_محول']
                    ship_date = row['تاريخ_شحن_محول']
                    
                    if pd.isna(receive_date) or pd.isna(ship_date):
                        return 'تاريخ مفقود'
                    
                    if receive_date == ship_date:
                        return 'المحاولة الأولى'
                    elif ship_date > receive_date:
                        return 'محاولة إضافية'
                    else:
                        return 'تاريخ شحن قبل الاستلام'
                        
                except:
                    return 'خطأ في المعالجة'
            
            df['نوع_المحاولة'] = df.apply(determine_attempt_type, axis=1)
            df['حالة_مسلم'] = df['حالة الطلب'].astype(str).apply(
                lambda x: 'مسلم' if 'Delivered' in x and 'Confirmed' in x else 'غير مسلم'
            )
            
        else:
            df['نوع_المحاولة'] = 'عمود التاريخ مفقود'
            df['حالة_مسلم'] = 'غير محدد'
            
        return df
        
    except Exception as e:
        st.error(f"خطأ في تحليل المحاولات: {str(e)}")
        df['نوع_المحاولة'] = 'خطأ في التحليل'
        df['حالة_مسلم'] = 'خطأ'
        return df

def get_file_hash(file_path):
    """حساب hash للملف لتتبع التغييرات"""
    try:
        with open(file_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        return file_hash
    except:
        return None

def find_latest_files(folder_path, pattern="*.xlsx"):
    """البحث عن أحدث الملفات في المجلد"""
    try:
        files = glob.glob(os.path.join(folder_path, pattern))
        if not files:
            files = glob.glob(os.path.join(folder_path, "*.xls"))
        if not files:
            files = glob.glob(os.path.join(folder_path, "*.csv"))
        
        if files:
            # ترتيب حسب تاريخ التعديل
            files.sort(key=os.path.getmtime, reverse=True)
            return files
        return []
    except:
        return []

def auto_load_data(main_folder=None, branch_folder=None):
    """تحميل البيانات تلقائياً من المجلدات المحددة"""
    main_df = None
    branch_files = []
    
    # تحميل الملف الرئيسي
    if main_folder and os.path.exists(main_folder):
        main_files = find_latest_files(main_folder)
        if main_files:
            latest_main = main_files[0]
            try:
                if latest_main.endswith('.csv'):
                    main_df = pd.read_csv(latest_main, encoding='utf-8')
                else:
                    main_df = pd.read_excel(latest_main)
                
                main_df = fix_duplicate_columns(main_df)
                main_df = process_column_names(main_df)
                main_df = main_df.dropna(how='all')
                
                if 'المطلوب تحصيله' in main_df.columns:
                    main_df['المطلوب تحصيله'] = pd.to_numeric(main_df['المطلوب تحصيله'], errors='coerce').fillna(0)
                
                st.session_state.current_main_file = latest_main
                st.session_state.main_file_hash = get_file_hash(latest_main)
                
            except Exception as e:
                st.error(f"خطأ في قراءة الملف الرئيسي {latest_main}: {str(e)}")
    
    # تحميل ملفات الفروع
    if branch_folder and os.path.exists(branch_folder):
        branch_file_list = find_latest_files(branch_folder)
        for file_path in branch_file_list:
            try:
                with open(file_path, 'rb') as f:
                    # محاكاة UploadedFile object
                    class MockFile:
                        def __init__(self, path):
                            self.name = os.path.basename(path)
                            self._file_path = path
                        
                        def read(self):
                            with open(self._file_path, 'rb') as f:
                                return f.read()
                    
                    branch_files.append(MockFile(file_path))
            except Exception as e:
                st.error(f"خطأ في قراءة ملف الفرع {file_path}: {str(e)}")
    
    return main_df, branch_files

@st.cache_data(show_spinner=False)  # إضافة show_spinner=False لتقليل الرسائل
def load_branch_data(branch_files):
    all_branch_data = []
    
    if not branch_files:
        return pd.DataFrame()
    
    # إضافة معالجة أخطاء محسنة
    success_count = 0
    error_files = []
    
    for file in branch_files:
        try:
            # محاولة قراءة الملف بطرق مختلفة
            df_branch = None
            
            if hasattr(file, '_file_path'):
                file_path = file._file_path
                file_name = file.name
            else:
                file_name = file.name if hasattr(file, 'name') else str(file)
                
            # محاولة قراءة الملف
            try:
                if hasattr(file, '_file_path'):
                    # للتحديث التلقائي
                    if file_name.endswith('.xlsx'):
                        df_branch = pd.read_excel(file_path, engine='openpyxl')
                    elif file_name.endswith('.xls'):
                        # محاولة قراءة ملف xls قديم
                        try:
                            df_branch = pd.read_excel(file_path, engine='xlrd')
                        except:
                            # إذا فشل xlrd، جرب openpyxl
                            df_branch = pd.read_excel(file_path, engine='openpyxl')
                    else:
                        df_branch = pd.read_excel(file_path)
                else:
                    # للرفع اليدوي
                    if file_name.endswith('.xlsx'):
                        df_branch = pd.read_excel(file, engine='openpyxl')
                    elif file_name.endswith('.xls'):
                        # محاولة قراءة ملف xls قديم
                        try:
                            df_branch = pd.read_excel(file, engine='xlrd')
                        except:
                            # إذا فشل xlrd، جرب openpyxl
                            df_branch = pd.read_excel(file, engine='openpyxl')
                    else:
                        df_branch = pd.read_excel(file)
                        
            except Exception as read_error:
                error_files.append(f"{file_name}: {str(read_error)}")
                continue
            
            # معالجة البيانات إذا تم قراءة الملف بنجاح
            if df_branch is not None and not df_branch.empty:
                branch_number = re.search(r'(\d+)', file_name)
                branch_id = branch_number.group(1) if branch_number else 'unknown'
                
                # معالجة أعمدة الملف
                if len(df_branch.columns) >= 3:
                    # التعامل مع أعمدة مختلفة
                    if len(df_branch.columns) >= 4:
                        df_branch.columns = ['#', 'Reference_ID', 'Branch_Name', 'Branch_Date']
                        if df_branch.columns[0] == '#':
                            df_branch = df_branch.drop(df_branch.columns[0], axis=1)
                            df_branch.columns = ['Reference_ID', 'Branch_Name', 'Branch_Date']
                    else:
                        df_branch.columns = ['Reference_ID', 'Branch_Name', 'Branch_Date']
                    
                    df_branch['Branch_ID'] = branch_id
                    df_branch = df_branch.dropna(subset=['Reference_ID'])
                    
                    # تنظيف البيانات
                    df_branch['Reference_ID'] = df_branch['Reference_ID'].astype(str)
                    df_branch['Branch_Date'] = pd.to_datetime(df_branch['Branch_Date'], errors='coerce')
                    
                    all_branch_data.append(df_branch)
                    success_count += 1
                    
        except Exception as e:
            error_files.append(f"{file_name}: خطأ عام - {str(e)}")
    
    # عرض نتائج المعالجة
    if success_count > 0:
        st.success(f"✅ تم قراءة {success_count} ملف فرع بنجاح")
    
    if error_files:
        with st.expander(f"⚠️ مشاكل في قراءة {len(error_files)} ملف", expanded=False):
            for error in error_files:
                st.error(error)
            
            st.markdown("**💡 حلول مقترحة:**")
            st.markdown("1. تأكد من أن الملفات بصيغة Excel (.xlsx أو .xls)")
            st.markdown("2. جرب حفظ الملفات بصيغة .xlsx")
            st.markdown("3. تأكد من أن الملفات غير محمية بكلمة مرور")
            st.markdown("4. لحل مشكلة xlrd، استخدم الأمر:")
            st.code("pip install xlrd openpyxl")
    
    # دمج البيانات
    if all_branch_data:
        try:
            combined_branches = pd.concat(all_branch_data, ignore_index=True)
            combined_branches = combined_branches.sort_values(['Reference_ID', 'Branch_Date'], ascending=[True, False])
            latest_branches = combined_branches.groupby('Reference_ID').first().reset_index()
            
            st.info(f"📊 تم معالجة {len(latest_branches)} رقم تتبع من ملفات الفروع")
            return latest_branches
        except Exception as e:
            st.error(f"خطأ في دمج بيانات الفروع: {str(e)}")
    
    return pd.DataFrame()

def merge_with_branches(main_df, branch_df):
    if branch_df.empty:
        main_df['فرع_الشحنة'] = 'WH'
        main_df['تاريخ_الفرع'] = None
        return main_df
    
    main_df['رقم التتبع_str'] = main_df['رقم التتبع'].astype(str)
    branch_df['Reference_ID_str'] = branch_df['Reference_ID'].astype(str)
    
    merged_df = main_df.merge(
        branch_df[['Reference_ID_str', 'Branch_Name', 'Branch_Date', 'Branch_ID']], 
        left_on='رقم التتبع_str', 
        right_on='Reference_ID_str', 
        how='left'
    )
    
    merged_df['فرع_الشحنة'] = merged_df['Branch_Name'].fillna('WH')
    merged_df['تاريخ_الفرع'] = merged_df['Branch_Date']
    
    columns_to_drop = ['رقم التتبع_str', 'Reference_ID_str', 'Branch_Name', 'Branch_Date', 'Branch_ID']
    merged_df = merged_df.drop([col for col in columns_to_drop if col in merged_df.columns], axis=1)
    
    return merged_df

def create_sample_data():
    np.random.seed(42)
    
    names = ['أحمد محمد', 'فاطمة علي', 'خالد سعد', 'نور الهدى', 'عمر يوسف']
    cities = ['الرياض', 'جدة', 'الدمام', 'مكة', 'المدينة']
    drivers = ['أحمد عادل', 'محمد خالد', 'مرسال أمين', 'سعد الدوسري', 'فهد العتيبي']
    statuses = ['Delivered Confirmed', 'In Progress', 'Failed Delivery']
    
    data = []
    base_date = datetime.now() - timedelta(days=30)
    
    for i in range(200):
        receive_date = base_date + timedelta(days=np.random.randint(0, 30))
        
        if np.random.random() < 0.7:
            ship_date = receive_date
        else:
            ship_date = receive_date + timedelta(days=np.random.randint(1, 5))
        
        status = np.random.choice(statuses, p=[0.8, 0.15, 0.05])
        
        record = {
            'رقم الطلب': f'960037{64000 + i}',
            'رقم التتبع': f'273{19000 + i}',
            'اسم العميل': np.random.choice(names),
            'هاتف العميل': f'96656{np.random.randint(1000000, 9999999)}',
            'موقع العميل': f'{np.random.choice(cities)}, المملكة العربية السعودية',
            'المطلوب تحصيله': round(np.random.uniform(50, 800), 2),
            'السبب': 'Order Purchase',
            'حالة الطلب': status,
            'رقم ورقة التشغيل': f'611511{4 + i % 3}',
            'الرقم التعريفي': np.random.randint(700, 900),
            'اسم المندوب': np.random.choice(drivers),
            'تاريخ استلام الشحنة': receive_date.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
            'تاريخ الشحن': ship_date.strftime('%d/%m/%Y'),
            'فرع_الشحنة': np.random.choice(['WH', 'Aqiq', 'Labn', 'Naseem', 'Tabuk'])
        }
        data.append(record)
    
    return pd.DataFrame(data)

# التحقق من المكتبات المطلوبة
def check_required_libraries():
    missing_libs = []
    
    try:
        import xlrd
    except ImportError:
        missing_libs.append("xlrd")
    
    try:
        import openpyxl
    except ImportError:
        missing_libs.append("openpyxl")
    
    if missing_libs:
        st.warning(f"⚠️ مكتبات مفقودة لقراءة ملفات Excel: {', '.join(missing_libs)}")
        with st.expander("💡 حل مشكلة قراءة ملفات Excel", expanded=False):
            st.markdown("**لحل مشكلة قراءة ملفات Excel، نفذ الأوامر التالية:**")
            st.code("""
pip install xlrd>=2.0.1
pip install openpyxl
            """)
            st.markdown("**أو استخدم:**")
            st.code("pip install xlrd openpyxl")
            st.markdown("**بعد التثبيت، أعد تشغيل النظام**")
    
    return len(missing_libs) == 0

# فحص المكتبات عند بدء النظام
libs_ok = check_required_libraries()

# عنوان مبسط للنظام
st.markdown("""
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            padding: 1.5rem; border-radius: 10px; margin-bottom: 1rem; text-align: center;">
    <h2 style="color: white; margin: 0; font-size: 1.8rem;">🚚 نظام تحليل الشحن - NiceOne</h2>
</div>
""", unsafe_allow_html=True)

# إعداد حالة الجلسة
if 'show_upload' not in st.session_state:
    st.session_state.show_upload = False  # مخفي بشكل افتراضي

if 'auto_update_enabled' not in st.session_state:
    st.session_state.auto_update_enabled = False

if 'main_folder_path' not in st.session_state:
    st.session_state.main_folder_path = ""

if 'branch_folder_path' not in st.session_state:
    st.session_state.branch_folder_path = ""

if 'update_interval' not in st.session_state:
    st.session_state.update_interval = 60

if 'last_update_time' not in st.session_state:
    st.session_state.last_update_time = None

if 'current_main_file' not in st.session_state:
    st.session_state.current_main_file = None

if 'main_file_hash' not in st.session_state:
    st.session_state.main_file_hash = None

if 'show_upload' not in st.session_state:
    st.session_state.show_upload = False

# 🔄 عرض حالة البيانات المحفوظة - مبسط للسرعة
saved_data_info = get_company_data("niceone")
if saved_data_info:
    st.markdown("""
    <div class="status-panel">
        <h3 style="margin: 0 0 1rem 0; font-size: 1.3rem;">💾 بيانات محفوظة</h3>
    </div>
    """, unsafe_allow_html=True)
    
    status_col1, status_col2, status_col3 = st.columns(3)
    
    with status_col1:
        st.metric("📊 السجلات", f"{saved_data_info['total_rows']:,}")
    
    with status_col2:
        st.metric("🕐 الوقت", saved_data_info['save_time'].strftime('%H:%M'))
    
    with status_col3:
        if st.button("🗑️ مسح", use_container_width=True):
            clear_company_data("niceone")
            st.rerun()

# قسم الإعدادات المخفي
if st.session_state.get('show_settings', False):
    st.markdown("""
    <div style="background: #f0f2f6; padding: 1.5rem; border-radius: 10px; margin: 1rem 0; border-left: 4px solid #6c757d;">
        <div style="display: flex; justify-content: between; align-items: center; margin-bottom: 1rem;">
            <h4 style="margin: 0; color: #6c757d;">⚙️ إعدادات النظام</h4>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    settings_col1, settings_col2, settings_col3 = st.columns([2, 2, 1])
    
    with settings_col1:
        st.selectbox("🎨 نمط العرض", ["افتراضي", "مظلم", "فاتح"], key="theme_setting")
        st.selectbox("📊 نوع الرسوم البيانية", ["تفاعلي", "ثابت"], key="chart_type")
    
    with settings_col2:
        st.number_input("📈 حد التقرير التنفيذي", min_value=10, max_value=1000, value=50, key="exec_report_threshold")
        st.checkbox("🔊 الإشعارات الصوتية", key="sound_notifications")
    
    with settings_col3:
        if st.button("❌", help="إغلاق الإعدادات"):
            st.session_state.show_settings = False
            st.rerun()

# واجهة التحديث التلقائي
st.markdown("""
<div class="auto-update-panel">
    <h3 style="margin: 0 0 1rem 0; font-size: 1.5rem;">
        🔄 نظام التحديث التلقائي للبيانات
    </h3>
</div>
""", unsafe_allow_html=True)

# إعدادات التحديث التلقائي
auto_col1, auto_col2, auto_col3, auto_col4 = st.columns([2, 2, 2, 2])

with auto_col1:
    auto_update = st.checkbox(
        "تفعيل التحديث التلقائي",
        value=st.session_state.auto_update_enabled,
        help="تفعيل مراقبة المجلدات والتحديث التلقائي للبيانات"
    )
    st.session_state.auto_update_enabled = auto_update

with auto_col2:
    update_interval = st.selectbox(
        "⏱️ فترة التحديث",
        options=[30, 60, 120, 300, 600],
        format_func=lambda x: f"{x} ثانية" if x < 60 else f"{x//60} دقيقة",
        index=1,
        help="كم مرة يتم فحص الملفات للتحديثات"
    )
    st.session_state.update_interval = update_interval

with auto_col3:
    main_folder = st.text_input(
        "📁 مجلد الملفات الرئيسية",
        value=st.session_state.main_folder_path,
        placeholder="C:/shipping_data/main/",
        help="مسار المجلد الذي يحتوي على ملفات البيانات الرئيسية"
    )
    st.session_state.main_folder_path = main_folder

with auto_col4:
    branch_folder = st.text_input(
        "🏢 مجلد ملفات الفروع",
        value=st.session_state.branch_folder_path,
        placeholder="C:/shipping_data/branches/",
        help="مسار المجلد الذي يحتوي على ملفات الفروع"
    )
    st.session_state.branch_folder_path = branch_folder

# أزرار التحكم المبسطة
control_col1, control_col2, control_col3, control_col4 = st.columns([2, 2, 2, 2])

with control_col1:
    if st.button("🔄 تحديث الآن", use_container_width=True):
        if main_folder:
            with st.spinner("جاري تحديث البيانات..."):
                st.session_state.last_update_time = datetime.now()
                st.rerun()

with control_col2:
    manual_mode = st.button("📁 رفع ملفات", use_container_width=True)
    if manual_mode:
        st.session_state.show_upload = not st.session_state.show_upload

with control_col3:
    if st.button("⚙️ إعدادات", use_container_width=True):
        st.session_state.show_settings = not st.session_state.get('show_settings', False)

with control_col4:
    if st.button("ℹ️ معلومات", use_container_width=True):
        st.session_state.show_info = not st.session_state.get('show_info', False)

# حالة النظام
status_col1, status_col2, status_col3 = st.columns([2, 3, 3])

with status_col1:
    if auto_update and main_folder:
        status_class = "status-active"
        status_text = "نشط"
    elif auto_update:
        status_class = "status-inactive"
        status_text = "في انتظار المسارات"
    else:
        status_class = "status-inactive"
        status_text = "غير نشط"
    
    st.markdown(f"""
    <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 8px;">
        حالة النظام: <strong>{status_text}</strong>
        <span class="status-indicator {status_class}"></span>
    </div>
    """, unsafe_allow_html=True)

with status_col2:
    if st.session_state.current_main_file:
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 8px;">
            <strong>الملف الحالي:</strong><br>
            <div class="file-path">{os.path.basename(st.session_state.current_main_file)}</div>
        </div>
        """, unsafe_allow_html=True)

with status_col3:
    if st.session_state.last_update_time:
        time_diff = datetime.now() - st.session_state.last_update_time
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 8px;">
            <strong>آخر تحديث:</strong><br>
            {st.session_state.last_update_time.strftime('%H:%M:%S')} 
            (منذ {int(time_diff.total_seconds())} ثانية)
        </div>
        """, unsafe_allow_html=True)

# التحديث التلقائي
if auto_update and main_folder:
    current_time = datetime.now()
    if (st.session_state.last_update_time is None or 
        (current_time - st.session_state.last_update_time).total_seconds() >= update_interval):
        
        # فحص تغيير الملفات مع عرض التقدم
        should_update = False
        status_placeholder = st.empty()
        
        with status_placeholder.container():
            with st.spinner("🔍 جاري فحص المجلدات للتحديثات..."):
                if main_folder and os.path.exists(main_folder):
                    latest_files = find_latest_files(main_folder)
                    if latest_files:
                        latest_file = latest_files[0]
                        current_hash = get_file_hash(latest_file)
                        
                        if (st.session_state.current_main_file != latest_file or 
                            st.session_state.main_file_hash != current_hash):
                            should_update = True
                            st.success(f"✅ تم اكتشاف تحديث في الملف: {os.path.basename(latest_file)}")
                        else:
                            st.info("📋 لا توجد تحديثات جديدة")
        
        if should_update:
            st.session_state.last_update_time = current_time
            status_placeholder.success("🔄 جاري تحديث البيانات...")
            time.sleep(1)  # إعطاء وقت لعرض الرسالة
            st.rerun()
        else:
            st.session_state.last_update_time = current_time
            status_placeholder.empty()  # مسح الرسالة بعد الفحص

# الوضع اليدوي المبسط
if st.session_state.show_upload:
    st.markdown("""
    <div style="background: #f8f9fa; padding: 1.5rem; border-radius: 10px; margin: 1rem 0; border-left: 4px solid #007bff;">
        <div style="display: flex; justify-content: between; align-items: center; margin-bottom: 1rem;">
            <h4 style="margin: 0; color: #007bff;">📁 رفع الملفات</h4>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([3, 3, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "الملف الرئيسي",
            type=['csv', 'xlsx', 'xls'],
            help="ملف بيانات الشحن الرئيسي",
            key="manual_main_file"
        )
    
    with col2:
        branch_files_manual = st.file_uploader(
            "ملفات الفروع (اختياري)",
            type=['xlsx', 'xls'],  # دعم كلا النوعين
            accept_multiple_files=True,
            help="ملفات الفروع للتحليل المفصل - يُفضل استخدام .xlsx",
            key="manual_branch_files"
        )
        
        # نصائح لملفات الفروع
        if not libs_ok:
            st.info("💡 لقراءة ملفات .xls، تحتاج لتثبيت xlrd")
        
        if st.session_state.get('show_branch_tips', False):
            st.markdown("""
            **📋 تنسيق ملف الفرع المطلوب:**
            - العمود الأول: رقم التتبع
            - العمود الثاني: اسم الفرع  
            - العمود الثالث: التاريخ
            """)
        
        if st.button("💡", help="عرض نصائح ملفات الفروع"):
            st.session_state.show_branch_tips = not st.session_state.get('show_branch_tips', False)
    
    with col3:
        if st.button("❌", help="إغلاق"):
            st.session_state.show_upload = False
            st.rerun()
else:
    uploaded_file = None
    branch_files_manual = []

# تحديد مصدر البيانات - مُحسّن للسرعة
# أولاً: فحص البيانات المحفوظة بسرعة
saved_data = get_company_data("niceone") if not uploaded_file else None

if saved_data:
    # استخدام البيانات المحفوظة مباشرة
    df = saved_data['main_df']
    branch_files = saved_data['branch_files'] if saved_data['branch_files'] else []
    data_source = f"محفوظ - {saved_data['source']}"
    
    # عرض مبسط للبيانات المحفوظة
    show_saved_data_info("NiceOne")
    
elif uploaded_file:
    # تحميل يدوي مُحسّن
    try:
        # إظهار تقدم التحميل
        with st.spinner("🔄 جاري قراءة الملف..."):
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file, encoding='utf-8')
            else:
                df = pd.read_excel(uploaded_file)
        
        # معالجة سريعة للبيانات
        with st.spinner("📊 جاري معالجة البيانات..."):
            df = fix_duplicate_columns(df)
            df = process_column_names(df)
            df = df.dropna(how='all')
            
            if 'المطلوب تحصيله' in df.columns:
                df['المطلوب تحصيله'] = pd.to_numeric(df['المطلوب تحصيله'], errors='coerce').fillna(0)
        
        branch_files = branch_files_manual if branch_files_manual else []
        data_source = "يدوي"
        
        # حفظ البيانات المرفوعة يدوياً دون إعادة تحميل
        save_company_data("niceone", df, branch_files, "يدوي")
        
    except Exception as e:
        st.error(f"خطأ في قراءة الملف: {str(e)}")
        df = create_sample_data()
        branch_files = []
        data_source = "تجريبي"

elif auto_update and main_folder and os.path.exists(main_folder):
    # تحميل تلقائي
    df, branch_files = auto_load_data(main_folder, branch_folder)
    data_source = "تلقائي"
    
    # حفظ البيانات المحملة تلقائياً دون إعادة تحميل
    if df is not None and len(df) > 0:
        save_company_data("niceone", df, branch_files, "تلقائي")
        
else:
    # بيانات تجريبية
    df = create_sample_data()
    branch_files = []
    data_source = "تجريبي"

# معالجة البيانات والعرض
if df is not None and len(df) > 0:
    # معالجة بيانات الفروع
    if branch_files:
        branch_data = load_branch_data(branch_files)
        df = merge_with_branches(df, branch_data)
    else:
        df['فرع_الشحنة'] = 'WH'
    
    df = analyze_attempts(df)
    
    # إضافة أعمدة للتحليل
    df['حالة_مترجمة'] = df['حالة الطلب'].map(lambda x: 'تم التسليم' if 'Delivered' in str(x) or 'confirmed' in str(x) 
                                                else 'قيد التوصيل' if 'Progress' in str(x) or 'pending' in str(x)
                                                else 'فشل التسليم' if 'Failed' in str(x) or 'failed' in str(x)
                                                else 'أخرى')
    
    # فلتر المناديب والفروع
    st.markdown('<div class="filter-section">', unsafe_allow_html=True)
    st.markdown('<h3 class="filter-title">🎛️ الفلاتر</h3>', unsafe_allow_html=True)
    
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([2, 2, 2, 2])
    
    with filter_col1:
        drivers = ['الكل'] + sorted(df['اسم المندوب'].dropna().unique().tolist())
        selected_driver = st.selectbox("👤 اختر المندوب", drivers, key="driver_filter")
    
    with filter_col2:
        branches = ['الكل'] + sorted(df['فرع_الشحنة'].dropna().unique().tolist())
        selected_branch = st.selectbox("🏢 اختر الفرع", branches, key="branch_filter")
    
    with filter_col3:
        date_range = st.date_input(
            "📅 نطاق التاريخ",
            value=[
                datetime.now().date() - timedelta(days=30),
                datetime.now().date()
            ],
            help="اختر النطاق الزمني للتحليل"
        )
    
    with filter_col4:
        statuses = ['الكل', 'تم التسليم', 'قيد التوصيل', 'فشل التسليم']
        selected_status = st.selectbox("📋 حالة الطلب", statuses, key="status_filter")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # تطبيق الفلاتر
    filtered_df = df.copy()
    
    if selected_driver != 'الكل':
        filtered_df = filtered_df[filtered_df['اسم المندوب'] == selected_driver]
    
    if selected_branch != 'الكل':
        filtered_df = filtered_df[filtered_df['فرع_الشحنة'] == selected_branch]
    
    if len(date_range) == 2 and 'تاريخ_شحن_محول' in filtered_df.columns:
        filtered_df['تاريخ_شحن_للفلترة'] = pd.to_datetime(filtered_df['تاريخ_شحن_محول'], errors='coerce')
        mask_date = (filtered_df['تاريخ_شحن_للفلترة'].dt.date >= date_range[0]) & (filtered_df['تاريخ_شحن_للفلترة'].dt.date <= date_range[1])
        filtered_df = filtered_df[mask_date]
    
    if selected_status != 'الكل':
        filtered_df = filtered_df[filtered_df['حالة_مترجمة'] == selected_status]
    
    # حساب المؤشرات
    total_orders = len(filtered_df)
    delivered_orders = len(filtered_df[filtered_df['حالة_مسلم'] == 'مسلم'])
    first_attempt_deliveries = len(filtered_df[filtered_df['نوع_المحاولة'] == 'المحاولة الأولى'])
    additional_attempt_deliveries = len(filtered_df[filtered_df['نوع_المحاولة'] == 'محاولة إضافية'])
    
    first_time_shipments = len(filtered_df[
        (filtered_df['تاريخ_استلام_محول'] == filtered_df['تاريخ_شحن_محول']) & 
        (pd.notna(filtered_df['تاريخ_استلام_محول'])) & 
        (pd.notna(filtered_df['تاريخ_شحن_محول']))
    ]) if 'تاريخ_استلام_محول' in filtered_df.columns and 'تاريخ_شحن_محول' in filtered_df.columns else first_attempt_deliveries
    
    success_rate = (delivered_orders / total_orders * 100) if total_orders > 0 else 0
    first_attempt_rate = (first_attempt_deliveries / first_time_shipments * 100) if first_time_shipments > 0 else 0
    avg_attempts = 1 + (additional_attempt_deliveries / delivered_orders) if delivered_orders > 0 else 1
    
    # KPI Cards
    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card orders">
            <div class="kpi-value">{total_orders:,}</div>
            <div class="kpi-label">📦 إجمالي الطلبات</div>
            <div class="kpi-change" style="background: #e3f2fd; color: #1976d2;">الفترة النشطة</div>
        </div>
        <div class="kpi-card success">
            <div class="kpi-value">{success_rate:.2f}%</div>
            <div class="kpi-label">✅ نسبة التسليم الكلية</div>
            <div class="kpi-change" style="background: #e8f5e8; color: #388e3c;">{delivered_orders:,} تم تسليمها</div>
        </div>
        <div class="kpi-card first-attempt">
            <div class="kpi-value">{first_attempt_rate:.2f}%</div>
            <div class="kpi-label">🎯 نسبة التسليم من المحاولة الأولى</div>
            <div class="kpi-change" style="background: #ffebee; color: #d32f2f;">{first_attempt_deliveries:,} من {first_time_shipments:,}</div>
        </div>
        <div class="kpi-card avg-attempts">
            <div class="kpi-value">{avg_attempts:.2f}</div>
            <div class="kpi-label">🔄 متوسط المحاولات</div>
            <div class="kpi-change" style="background: #fff3e0; color: #f57c00;">نقاط الكفاءة</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # إضافة معلومات إضافية تحت KPIs
    if total_orders > 0:
        st.markdown(f"""
        <div class="info-box">
            <strong>📊 ملخص سريع - مصدر البيانات: {data_source}:</strong><br>
            • <strong>الشحنات التي خرجت لأول مرة:</strong> {first_time_shipments:,} شحنة<br>
            • <strong>نجح من المحاولة الأولى:</strong> {first_attempt_deliveries:,} شحنة<br>
            • <strong>إجمالي المحاولات الإضافية:</strong> {additional_attempt_deliveries:,} طلب<br>
            • <strong>معدل المحاولات الإضافية:</strong> {(additional_attempt_deliveries/total_orders*100):.2f}%
        </div>
        """, unsafe_allow_html=True)
    
    # الرسوم البيانية الأساسية
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<h3 class="chart-title">📊 توزيع حالات الطلبات</h3>', unsafe_allow_html=True)
        
        status_counts = filtered_df['حالة_مترجمة'].value_counts()
        
        fig_status = px.pie(
            values=status_counts.values,
            names=status_counts.index,
            color_discrete_map={
                'تم التسليم': '#27ae60',
                'قيد التوصيل': '#f39c12',
                'فشل التسليم': '#e74c3c',
                'أخرى': '#95a5a6'
            },
            hole=0.4
        )
        
        fig_status.update_traces(
            textposition='inside',
            textinfo='percent+label',
            textfont_size=14,
            marker=dict(line=dict(color='#FFFFFF', width=2))
        )
        
        fig_status.update_layout(
            showlegend=True,
            height=400,
            font=dict(size=12, family='Cairo'),
            margin=dict(t=20, b=20, l=20, r=20),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="center",
                x=0.5
            )
        )
        
        st.plotly_chart(fig_status, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<h3 class="chart-title">🎯 تحليل محاولات التسليم</h3>', unsafe_allow_html=True)
        
        # حساب المحاولات بنفس طريقة KPI تماماً
        delivered_first_attempt = first_attempt_deliveries
        failed_first_attempt = first_time_shipments - first_attempt_deliveries
        
        if first_time_shipments > 0:
            attempt_data = {
                'المحاولة الأولى': delivered_first_attempt,
                'محاولة إضافية': failed_first_attempt
            }
            
            fig_attempts = px.pie(
                values=list(attempt_data.values()),
                names=list(attempt_data.keys()),
                color_discrete_map={
                    'المحاولة الأولى': '#3498db',
                    'محاولة إضافية': '#9b59b6'
                },
                hole=0.4
            )
            
            fig_attempts.update_traces(
                textposition='inside',
                textinfo='percent+label+value',
                textfont_size=14,
                marker=dict(line=dict(color='#FFFFFF', width=2))
            )
            
            fig_attempts.update_layout(
                showlegend=True,
                height=400,
                font=dict(size=12, family='Cairo'),
                margin=dict(t=20, b=20, l=20, r=20),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.2,
                    xanchor="center",
                    x=0.5
                )
            )
            
            st.plotly_chart(fig_attempts, use_container_width=True)
        else:
            st.info("📊 لا توجد بيانات محاولات التسليم")
        
        st.markdown('</div>', unsafe_allow_html=True)

    # تحليل تفصيلي للفروع والتسليم
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown('<h3 class="chart-title">🏢 تحليل مفصل للفروع والأداء</h3>', unsafe_allow_html=True)
    
    # إحصائيات شاملة للفروع
    branch_detailed = filtered_df.groupby('فرع_الشحنة').agg({
        'رقم الطلب': 'count',
        'حالة_مسلم': lambda x: (x == 'مسلم').sum()
    })
    
    # تسطيح الأعمدة
    branch_detailed.columns = ['إجمالي الطلبات', 'تم التسليم']
    branch_detailed['لم تُسلم'] = branch_detailed['إجمالي الطلبات'] - branch_detailed['تم التسليم']
    branch_detailed['نسبة التسليم الكلية (%)'] = (branch_detailed['تم التسليم'] / branch_detailed['إجمالي الطلبات'] * 100).round(2)
    
    # حساب محاولات التسليم لكل فرع بالطريقة الصحيحة
    branch_detailed['المحاولة الأولى'] = 0
    branch_detailed['الشحنات الأولى'] = 0
    branch_detailed['نسبة التسليم من المحاولة الأولى (%)'] = 0.0
    
    for idx, row in branch_detailed.iterrows():
        branch_name = idx  # اسم الفرع هو index
        branch_data = filtered_df[filtered_df['فرع_الشحنة'] == branch_name]
        
        # حساب الشحنات التي خرجت لأول مرة لهذا الفرع
        branch_first_time = len(branch_data[
            (branch_data['تاريخ_استلام_محول'] == branch_data['تاريخ_شحن_محول']) & 
            (pd.notna(branch_data['تاريخ_استلام_محول'])) & 
            (pd.notna(branch_data['تاريخ_شحن_محول']))
        ]) if 'تاريخ_استلام_محول' in branch_data.columns and 'تاريخ_شحن_محول' in branch_data.columns else 0
        
        # حساب المسلم من المحاولة الأولى لهذا الفرع
        branch_first_attempt = len(branch_data[branch_data['نوع_المحاولة'] == 'المحاولة الأولى'])
        
        # تحديث القيم
        branch_detailed.loc[idx, 'المحاولة الأولى'] = branch_first_attempt
        branch_detailed.loc[idx, 'الشحنات الأولى'] = branch_first_time
        
        # حساب معدل المحاولة الأولى
        if branch_first_time > 0:
            branch_detailed.loc[idx, 'نسبة التسليم من المحاولة الأولى (%)'] = round((branch_first_attempt / branch_first_time * 100), 2)
        else:
            branch_detailed.loc[idx, 'نسبة التسليم من المحاولة الأولى (%)'] = 0.0
    
    branch_detailed = branch_detailed.reset_index()
    branch_detailed = branch_detailed.sort_values('إجمالي الطلبات', ascending=False)
    
    # عرض الجدول مع تنسيق النسب المئوية
    st.markdown("**📊 جدول تفصيلي لأداء الفروع:**")
    
    # تلوين الجدول حسب الأداء مع تنسيق النسب
    def highlight_performance(s):
        if s.name in ['نسبة التسليم الكلية (%)', 'نسبة التسليم من المحاولة الأولى (%)']:
            colors = []
            for v in s:
                try:
                    val = float(v) if isinstance(v, str) else v
                    if val >= 80:
                        colors.append('background-color: #d4edda')
                    elif val >= 60:
                        colors.append('background-color: #fff3cd')
                    else:
                        colors.append('background-color: #f8d7da')
                except:
                    colors.append('')
            return colors
        return ['' for _ in s]
    
    # تنسيق النسب المئوية لعرضها بشكل صحيح
    display_branch = branch_detailed.copy()
    display_branch['نسبة التسليم الكلية (%)'] = display_branch['نسبة التسليم الكلية (%)'].apply(lambda x: f"{x:.2f}")
    display_branch['نسبة التسليم من المحاولة الأولى (%)'] = display_branch['نسبة التسليم من المحاولة الأولى (%)'].apply(lambda x: f"{x:.2f}")
    
    styled_branch = display_branch.style.apply(highlight_performance)
    st.dataframe(styled_branch, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # رسوم بيانية مفصلة للفروع
    branch_col1, branch_col2 = st.columns(2)
    
    with branch_col1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<h3 class="chart-title">📈 مقارنة أداء الفروع</h3>', unsafe_allow_html=True)
        
        fig_branch_compare = go.Figure()
        fig_branch_compare.add_trace(go.Bar(
            name='نسبة التسليم الكلية (%)',
            x=branch_detailed['فرع_الشحنة'],
            y=branch_detailed['نسبة التسليم الكلية (%)'],
            marker_color='#3498db',
            text=branch_detailed['نسبة التسليم الكلية (%)'].apply(lambda x: f"{x:.2f}"),
            textposition='auto'
        ))
        fig_branch_compare.add_trace(go.Bar(
            name='نسبة التسليم من المحاولة الأولى (%)',
            x=branch_detailed['فرع_الشحنة'],
            y=branch_detailed['نسبة التسليم من المحاولة الأولى (%)'],
            marker_color='#e74c3c',
            text=branch_detailed['نسبة التسليم من المحاولة الأولى (%)'].apply(lambda x: f"{x:.2f}"),
            textposition='auto'
        ))
        
        fig_branch_compare.update_layout(
            barmode='group',
            height=400,
            font=dict(family='Cairo', size=12),
            yaxis_title='النسبة المئوية (%)',
            xaxis_title='الفرع'
        )
        
        st.plotly_chart(fig_branch_compare, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with branch_col2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<h3 class="chart-title">📦 توزيع الطلبات حسب الفروع</h3>', unsafe_allow_html=True)
        
        fig_branch_distribution = px.pie(
            branch_detailed,
            values='إجمالي الطلبات',
            names='فرع_الشحنة',
            color_discrete_sequence=px.colors.qualitative.Set3,
            hole=0.4
        )
        
        fig_branch_distribution.update_traces(
            textposition='inside',
            textinfo='percent+label',
            textfont_size=12
        )
        
        fig_branch_distribution.update_layout(
            height=400,
            font=dict(family='Cairo', size=12),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="center",
                x=0.5
            )
        )
        
        st.plotly_chart(fig_branch_distribution, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # أداء المناديب المحسّن والمفصل
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown('<h3 class="chart-title">👥 تحليل شامل لأداء المناديب</h3>', unsafe_allow_html=True)
    
    # إحصائيات المناديب مع التركيز على عدد التحميل
    driver_performance = filtered_df.groupby('اسم المندوب').agg({
        'رقم الطلب': 'count',  # عدد التحميل (إجمالي الطلبات المحملة)
        'حالة_مسلم': lambda x: (x == 'مسلم').sum(),
        'نوع_المحاولة': lambda x: (x == 'المحاولة الأولى').sum()
    }).reset_index()
    
    driver_performance['نسبة التوصيل (%)'] = (driver_performance['حالة_مسلم'] / driver_performance['رقم الطلب'] * 100).round(2)
    driver_performance['نسبة التسليم من المحاولة الأولى (%)'] = (driver_performance['نوع_المحاولة'] / driver_performance['حالة_مسلم'] * 100).round(2).fillna(0)
    
    # إعادة تسمية الأعمدة
    driver_performance.columns = ['اسم المندوب', 'عدد التحميل', 'تم التسليم', 'المحاولة الأولى', 'نسبة التوصيل (%)', 'نسبة التسليم من المحاولة الأولى (%)']
    
    # ترتيب المناديب حسب نسبة التوصيل
    driver_performance = driver_performance.sort_values('نسبة التوصيل (%)', ascending=False)
    
    # تحديد أفضل وأسوأ وأنشط المناديب
    top_5_drivers = driver_performance.head(5)
    bottom_5_drivers = driver_performance.tail(5)
    most_active_driver = driver_performance.loc[driver_performance['عدد التحميل'].idxmax()]
    
    # عرض الملخص السريع
    summary_col1, summary_col2, summary_col3 = st.columns(3)
    
    with summary_col1:
        st.markdown("### 🏆 أفضل مندوب")
        best_driver = driver_performance.iloc[0]
        st.markdown(f"""
        **{best_driver['اسم المندوب']}**  
        📦 عدد التحميل: {best_driver['عدد التحميل']:,}  
        ✅ نسبة التوصيل: {best_driver['نسبة التوصيل (%)']:.2f}%  
        🎯 المحاولة الأولى: {best_driver['نسبة التسليم من المحاولة الأولى (%)']:.2f}%
        """)
    
    with summary_col2:
        st.markdown("### ⚡ أنشط مندوب")
        st.markdown(f"""
        **{most_active_driver['اسم المندوب']}**  
        📦 عدد التحميل: {most_active_driver['عدد التحميل']:,}  
        ✅ نسبة التوصيل: {most_active_driver['نسبة التوصيل (%)']:.2f}%  
        🎯 المحاولة الأولى: {most_active_driver['نسبة التسليم من المحاولة الأولى (%)']:.2f}%
        """)
    
    with summary_col3:
        st.markdown("### ⚠️ يحتاج تحسين")
        worst_driver = driver_performance.iloc[-1]
        st.markdown(f"""
        **{worst_driver['اسم المندوب']}**  
        📦 عدد التحميل: {worst_driver['عدد التحميل']:,}  
        ✅ نسبة التوصيل: {worst_driver['نسبة التوصيل (%)']:.2f}%  
        🎯 المحاولة الأولى: {worst_driver['نسبة التسليم من المحاولة الأولى (%)']:.2f}%
        """)
    
    # التبويبات للتحليل المفصل
    tab1, tab2, tab3, tab4 = st.tabs(["📊 جميع المناديب", "🏆 أفضل 5", "⚠️ أقل 5", "📈 رسم مختلط"])
    
    with tab1:
        st.markdown("**📋 أداء جميع المناديب:**")
        
        # تلوين جدول المناديب
        def color_driver_performance(val):
            if pd.isna(val):
                return ''
            # تحويل النص المنسق إلى رقم للمقارنة
            if isinstance(val, str) and val != '':
                try:
                    val = float(val)
                except:
                    return ''
            if isinstance(val, (int, float)):
                if val >= 95:
                    return 'background-color: #d4edda; color: #155724; font-weight: bold;'
                elif val >= 90:
                    return 'background-color: #d1ecf1; color: #0c5460; font-weight: bold;'
                elif val >= 80:
                    return 'background-color: #fff3cd; color: #856404; font-weight: bold;'
                else:
                    return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
            return ''
        
        styled_all_drivers = driver_performance.copy()
        # تنسيق النسب للعرض
        styled_all_drivers['نسبة التوصيل (%)'] = styled_all_drivers['نسبة التوصيل (%)'].apply(lambda x: f"{x:.2f}")
        styled_all_drivers['نسبة التسليم من المحاولة الأولى (%)'] = styled_all_drivers['نسبة التسليم من المحاولة الأولى (%)'].apply(lambda x: f"{x:.2f}")
        
        # تطبيق التلوين على النسخة الأصلية من البيانات (الرقمية)
        styled_display = styled_all_drivers.style.applymap(
            lambda val: color_driver_performance(val), 
            subset=['نسبة التوصيل (%)', 'نسبة التسليم من المحاولة الأولى (%)']
        )
        st.dataframe(styled_display, use_container_width=True, height=400)
        
        # إحصائيات عامة
        avg_delivery_rate = driver_performance['نسبة التوصيل (%)'].mean()
        avg_first_attempt = driver_performance['نسبة التسليم من المحاولة الأولى (%)'].mean()
        total_drivers = len(driver_performance)
        
        st.markdown(f"""
        **📊 إحصائيات عامة:**
        - إجمالي المناديب: {total_drivers:,}
        - متوسط نسبة التوصيل: {avg_delivery_rate:.2f}%
        - متوسط المحاولة الأولى: {avg_first_attempt:.2f}%
        """)
    
    with tab2:
        st.markdown("**🏆 أفضل 5 مناديب في الأداء:**")
        
        # رسم بياني لأفضل 5
        fig_top5 = px.bar(
            top_5_drivers,
            x='اسم المندوب',
            y='نسبة التوصيل (%)',
            color='نسبة التسليم من المحاولة الأولى (%)',
            color_continuous_scale='Greens',
            title='أفضل 5 مناديب',
            text='نسبة التوصيل (%)'
        )
        fig_top5.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
        fig_top5.update_layout(height=400, font=dict(family='Cairo', size=12))
        st.plotly_chart(fig_top5, use_container_width=True)
        
        # جدول أفضل 5 مع تنسيق النسب
        display_top5 = top_5_drivers.copy()
        display_top5['نسبة التوصيل (%)'] = display_top5['نسبة التوصيل (%)'].apply(lambda x: f"{x:.2f}")
        display_top5['نسبة التسليم من المحاولة الأولى (%)'] = display_top5['نسبة التسليم من المحاولة الأولى (%)'].apply(lambda x: f"{x:.2f}")
        
        styled_top5 = display_top5.style.applymap(
            lambda val: color_driver_performance(val), 
            subset=['نسبة التوصيل (%)', 'نسبة التسليم من المحاولة الأولى (%)']
        )
        st.dataframe(styled_top5, use_container_width=True)
    
    with tab3:
        st.markdown("**⚠️ أقل 5 مناديب في الأداء (يحتاجون تحسين):**")
        
        # رسم بياني لأقل 5
        fig_bottom5 = px.bar(
            bottom_5_drivers,
            x='اسم المندوب',
            y='نسبة التوصيل (%)',
            color='نسبة التوصيل (%)',
            color_continuous_scale='Reds',
            title='أقل 5 مناديب في الأداء',
            text='نسبة التوصيل (%)'
        )
        fig_bottom5.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
        fig_bottom5.update_layout(height=400, font=dict(family='Cairo', size=12))
        st.plotly_chart(fig_bottom5, use_container_width=True)
        
        # جدول أقل 5 مع تنسيق النسب
        display_bottom5 = bottom_5_drivers.copy()
        display_bottom5['نسبة التوصيل (%)'] = display_bottom5['نسبة التوصيل (%)'].apply(lambda x: f"{x:.2f}")
        display_bottom5['نسبة التسليم من المحاولة الأولى (%)'] = display_bottom5['نسبة التسليم من المحاولة الأولى (%)'].apply(lambda x: f"{x:.2f}")
        
        styled_bottom5 = display_bottom5.style.applymap(
            lambda val: color_driver_performance(val), 
            subset=['نسبة التوصيل (%)', 'نسبة التسليم من المحاولة الأولى (%)']
        )
        st.dataframe(styled_bottom5, use_container_width=True)
        
        # توصيات للتحسين
        st.markdown("**💡 توصيات للتحسين:**")
        for _, driver in bottom_5_drivers.iterrows():
            if driver['نسبة التوصيل (%)'] < 80:
                st.markdown(f"• **{driver['اسم المندوب']}**: يحتاج تدريب مكثف - نسبة التوصيل {driver['نسبة التوصيل (%)']:.2f}%")
            elif driver['نسبة التوصيل (%)'] < 90:
                st.markdown(f"• **{driver['اسم المندوب']}**: يحتاج متابعة - نسبة التوصيل {driver['نسبة التوصيل (%)']:.2f}%")
    
    with tab4:
        st.markdown("**📈 شارت مختلط: نسبة التوصيل + عدد التحميل:**")
        
        # أخذ أفضل 15 مندوب للوضوح
        chart_drivers = driver_performance.head(15)
        
        # إنشاء الرسم المختلط
        fig_mixed = go.Figure()
        
        # إضافة الأعمدة لنسبة التوصيل
        fig_mixed.add_trace(go.Bar(
            x=chart_drivers['اسم المندوب'],
            y=chart_drivers['نسبة التوصيل (%)'],
            name='نسبة التوصيل (%)',
            marker=dict(
                color=chart_drivers['نسبة التوصيل (%)'],
                colorscale='RdYlGn',
                cmin=60,
                cmax=100,
                showscale=True,
                colorbar=dict(title="نسبة التوصيل (%)", x=1.02)
            ),
            text=chart_drivers['نسبة التوصيل (%)'].apply(lambda x: f"{x:.2f}"),
            texttemplate='%{text}%',
            textposition='outside',
            yaxis='y'
        ))
        
        # تطبيع عدد التحميل لجعله مناسب لوضعه كنقاط
        max_delivery_rate = chart_drivers['نسبة التوصيل (%)'].max()
        normalized_loading = (chart_drivers['عدد التحميل'] / chart_drivers['عدد التحميل'].max()) * (max_delivery_rate * 0.8)
        
        # إضافة النقاط لعدد التحميل
        fig_mixed.add_trace(go.Scatter(
            x=chart_drivers['اسم المندوب'],
            y=normalized_loading,
            mode='markers+text',
            name='عدد التحميل',
            marker=dict(
                size=chart_drivers['عدد التحميل'] / chart_drivers['عدد التحميل'].max() * 40 + 10,
                color='darkblue',
                opacity=0.7,
                line=dict(width=2, color='white')
            ),
            text=chart_drivers['عدد التحميل'],
            textposition='middle center',
            textfont=dict(color='white', size=10),
            yaxis='y2'
        ))
        
        # تحديث التخطيط
        fig_mixed.update_layout(
            title=dict(
                text='تحليل مختلط: نسبة التوصيل وعدد التحميل للمناديب',
                x=0.5,
                font=dict(size=16, family='Cairo')
            ),
            xaxis=dict(
                title='اسم المندوب',
                tickangle=45,
                title_font=dict(family='Cairo', size=14)
            ),
            yaxis=dict(
                title='نسبة التوصيل (%)',
                side='left',
                range=[0, max_delivery_rate * 1.1],
                title_font=dict(family='Cairo', size=14)
            ),
            yaxis2=dict(
                title='عدد التحميل (مطبع)',
                side='right',
                overlaying='y',
                range=[0, max_delivery_rate * 1.1],
                showgrid=False,
                title_font=dict(family='Cairo', size=14)
            ),
            height=600,
            font=dict(family='Cairo', size=12),
            legend=dict(
                x=0.02,
                y=0.98,
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="rgba(0,0,0,0.2)",
                borderwidth=1
            ),
            plot_bgcolor='rgba(240,240,240,0.3)',
            showlegend=True
        )
        
        st.plotly_chart(fig_mixed, use_container_width=True)
        
        # شرح الرسم
        st.markdown("""
        **📊 شرح الرسم:**
        - **الأعمدة الملونة**: تمثل نسبة التوصيل لكل مندوب (أخضر = ممتاز، أحمر = ضعيف)
        - **النقاط الزرقاء**: تمثل عدد التحميل (حجم النقطة = عدد الطلبات المحملة)
        - **الرقم داخل النقطة**: العدد الفعلي للطلبات المحملة
        """)
        
        # جدول مقارنة سريع
        comparison_data = pd.DataFrame({
            'النوع': ['أفضل نسبة توصيل', 'أعلى عدد تحميل'],
            'اسم المندوب': [best_driver['اسم المندوب'], most_active_driver['اسم المندوب']],
            'عدد التحميل': [f"{best_driver['عدد التحميل']:,}", f"{most_active_driver['عدد التحميل']:,}"],
            'نسبة التوصيل (%)': [f"{best_driver['نسبة التوصيل (%)']:.2f}", f"{most_active_driver['نسبة التوصيل (%)']:.2f}"]
        })
        
        st.markdown("**📋 مقارنة سريعة:**")
        st.dataframe(comparison_data, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # تحليل تفصيلي للتسليم - تصميم محسن ومرتب
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 2rem; border-radius: 15px; margin-bottom: 1.5rem; 
                box-shadow: 0 8px 25px rgba(0,0,0,0.15);">
        <h3 style="color: white; text-align: center; font-size: 2rem; 
                   margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);">
            🚚 تحليل تفصيلي لمحاولات التسليم
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    # تنظيم البيانات في 3 أعمدة مرتبة
    delivery_col1, delivery_col2, delivery_col3 = st.columns(3)
    
    with delivery_col1:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #74b9ff, #0984e3); 
                    padding: 1.5rem; border-radius: 12px; color: white; 
                    box-shadow: 0 6px 20px rgba(116, 185, 255, 0.3); margin-bottom: 1rem;">
            <h4 style="margin: 0 0 1rem 0; text-align: center; font-size: 1.3rem;">
                📊 إحصائيات التسليم
            </h4>
        </div>
        """, unsafe_allow_html=True)
        
        st.metric("📦 إجمالي الطلبات", f"{total_orders:,}", 
                 help="العدد الكلي للطلبات في الفترة المحددة")
        st.metric("✅ الطلبات المسلمة", f"{delivered_orders:,}", 
                 help="عدد الطلبات التي تم تسليمها بنجاح")
        st.metric("🔄 المحاولات الإضافية", f"{additional_attempt_deliveries:,}", 
                 help="عدد الطلبات التي احتاجت لأكثر من محاولة")
        st.metric("📊 الشحنات الأولى", f"{first_time_shipments:,}", 
                 help="عدد الشحنات التي خرجت لأول مرة")
    
    with delivery_col2:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #fd79a8, #e84393); 
                    padding: 1.5rem; border-radius: 12px; color: white; 
                    box-shadow: 0 6px 20px rgba(253, 121, 168, 0.3); margin-bottom: 1rem;">
            <h4 style="margin: 0 0 1rem 0; text-align: center; font-size: 1.3rem;">
                🎯 معدلات الأداء
            </h4>
        </div>
        """, unsafe_allow_html=True)
        
        st.metric("📈 نسبة التسليم الكلية", f"{success_rate:.2f}%", 
                 delta=f"تم تسليم {delivered_orders:,} من {total_orders:,}", 
                 help="النسبة المئوية للطلبات المسلمة من إجمالي الطلبات")
        st.metric("🎯 نسبة التسليم من المحاولة الأولى", f"{first_attempt_rate:.2f}%", 
                 delta=f"نجح {first_attempt_deliveries:,} من {first_time_shipments:,}", 
                 help="النسبة المئوية للطلبات المسلمة من المحاولة الأولى")
        st.metric("🔢 متوسط المحاولات", f"{avg_attempts:.2f}", 
                 help="متوسط عدد المحاولات اللازمة لتسليم الطلب")
    
    with delivery_col3:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #a29bfe, #6c5ce7); 
                    padding: 1.5rem; border-radius: 12px; color: white; 
                    box-shadow: 0 6px 20px rgba(162, 155, 254, 0.3); margin-bottom: 1rem;">
            <h4 style="margin: 0 0 1rem 0; text-align: center; font-size: 1.3rem;">
                🏆 أفضل الفروع
            </h4>
        </div>
        """, unsafe_allow_html=True)
        
        top_branches = branch_detailed.head(3)
        for i, (_, branch) in enumerate(top_branches.iterrows()):
            rank_emoji = ["🥇", "🥈", "🥉"][i]
            rank_colors = ["#FFD700", "#C0C0C0", "#CD7F32"][i]
            
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, {rank_colors}20, {rank_colors}40); 
                        padding: 0.8rem; border-radius: 8px; margin: 0.5rem 0;
                        border-left: 4px solid {rank_colors};">
                <div style="display: flex; align-items: center;">
                    <span style="font-size: 1.5rem; margin-left: 0.5rem;">{rank_emoji}</span>
                    <div>
                        <div style="font-weight: bold; font-size: 1rem; color: #2c3e50;">
                            {branch['فرع_الشحنة']}
                        </div>
                        <div style="font-size: 0.8rem; color: #7f8c8d;">
                            الكلي: {branch['نسبة التسليم الكلية (%)']:.2f}% | 
                            الأولى: {branch['نسبة التسليم من المحاولة الأولى (%)']:.2f}%
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # إضافة ملخص تنفيذي للمديرين
    if total_orders > 100:  # إذا كان لدينا بيانات كافية
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<h3 class="chart-title">📋 التقرير التنفيذي - ملخص الأداء</h3>', unsafe_allow_html=True)
        
        # تحضير بيانات التقرير التنفيذي
        exec_data = []
        
        # نظرة عامة
        exec_data.append({
            'القسم': '🎯 نظرة عامة',
            'المؤشر': 'إجمالي الطلبات',
            'القيمة': f"{total_orders:,}",
            'الملاحظات': 'الفترة النشطة'
        })
        exec_data.append({
            'القسم': '',
            'المؤشر': 'معدل النجاح',
            'القيمة': f"{success_rate:.2f}%",
            'الملاحظات': 'نسبة التسليم الكلية'
        })
        exec_data.append({
            'القسم': '',
            'المؤشر': 'كفاءة المحاولة الأولى',
            'القيمة': f"{first_attempt_rate:.2f}%",
            'الملاحظات': 'نجح من المحاولة الأولى'
        })
        
        # أفضل الأداءات
        best_branch = branch_detailed.iloc[0]
        best_driver = driver_performance.iloc[0]
        
        exec_data.append({
            'القسم': '🏆 أفضل الأداءات',
            'المؤشر': 'أفضل فرع',
            'القيمة': f"{best_branch['فرع_الشحنة']}",
            'الملاحظات': f"({best_branch['نسبة التسليم الكلية (%)']:.2f}%)"
        })
        exec_data.append({
            'القسم': '',
            'المؤشر': 'أفضل مندوب',
            'القيمة': f"{best_driver['اسم المندوب']}",
            'الملاحظات': f"({best_driver['نسبة التوصيل (%)']:.2f}%)"
        })
        exec_data.append({
            'القسم': '',
            'المؤشر': 'أنشط مندوب',
            'القيمة': f"{most_active_driver['اسم المندوب']}",
            'الملاحظات': f"({most_active_driver['عدد التحميل']:,} طلب)"
        })
        
        # مجالات التحسين
        improvements = []
        
        if first_attempt_rate < 90:
            improvements.append(f"تحسين كفاءة المحاولة الأولى (حالياً {first_attempt_rate:.2f}%)")
        
        if success_rate < 95:
            improvements.append(f"زيادة معدل التسليم الكلي (حالياً {success_rate:.2f}%)")
        
        # الفروع الضعيفة
        weak_branches = branch_detailed[branch_detailed['نسبة التسليم الكلية (%)'] < 85]
        if len(weak_branches) > 0:
            improvements.append(f"تطوير أداء {len(weak_branches)} فرع يحتاج تحسين")
        
        # المناديب الضعاف
        weak_drivers = driver_performance[driver_performance['نسبة التوصيل (%)'] < 85]
        if len(weak_drivers) > 0:
            improvements.append(f"تدريب {len(weak_drivers)} مندوب يحتاج تطوير")
        
        if avg_attempts > 1.2:
            improvements.append(f"تقليل المحاولات الإضافية (حالياً {avg_attempts:.2f})")
        
        # إضافة مجالات التحسين إلى الجدول
        if improvements:
            for i, improvement in enumerate(improvements[:4]):  # أهم 4 نقاط
                exec_data.append({
                    'القسم': '⚠️ مجالات التحسين' if i == 0 else '',
                    'المؤشر': f"نقطة {i+1}",
                    'القيمة': improvement,
                    'الملاحظات': 'يحتاج انتباه'
                })
        else:
            exec_data.append({
                'القسم': '🎉 تقييم الأداء',
                'المؤشر': 'الوضع العام',
                'القيمة': 'ممتاز في جميع المجالات',
                'الملاحظات': 'استمر على هذا الأداء'
            })
        
        # تقييم الأداء العام
        if success_rate >= 95:
            performance_rating = "ممتاز 🌟"
            performance_color = "#27ae60"
        elif success_rate >= 90:
            performance_rating = "جيد جداً ✅"
            performance_color = "#3498db"
        elif success_rate >= 85:
            performance_rating = "جيد ⚠️"
            performance_color = "#f39c12"
        else:
            performance_rating = "يحتاج تحسين ❌"
            performance_color = "#e74c3c"
        
        exec_data.append({
            'القسم': '📊 تقييم الأداء العام',
            'المؤشر': 'التقييم النهائي',
            'القيمة': performance_rating,
            'الملاحظات': f"على أساس {success_rate:.2f}% نجاح"
        })
        
        # إنشاء DataFrame وعرضه
        exec_df = pd.DataFrame(exec_data)
        
        # تنسيق الجدول مع الألوان
        def style_exec_table(row):
            if 'ممتاز' in str(row['القيمة']):
                return ['background-color: #d4edda; font-weight: bold'] * len(row)
            elif 'جيد جداً' in str(row['القيمة']):
                return ['background-color: #d1ecf1; font-weight: bold'] * len(row)
            elif 'جيد' in str(row['القيمة']):
                return ['background-color: #fff3cd; font-weight: bold'] * len(row)
            elif 'يحتاج تحسين' in str(row['القيمة']):
                return ['background-color: #f8d7da; font-weight: bold'] * len(row)
            elif row['القسم'].startswith('🎯'):
                return ['background-color: #e3f2fd'] * len(row)
            elif row['القسم'].startswith('🏆'):
                return ['background-color: #fff8e1'] * len(row)
            elif row['القسم'].startswith('⚠️'):
                return ['background-color: #ffebee'] * len(row)
            elif row['القسم'].startswith('📊'):
                return ['background-color: #f3e5f5'] * len(row)
            else:
                return [''] * len(row)
        
        styled_exec = exec_df.style.apply(style_exec_table, axis=1)
        st.dataframe(styled_exec, use_container_width=True, height=500)
        
        # توصيات سريعة
        st.markdown("### 💡 توصيات سريعة:")
        rec_col1, rec_col2, rec_col3 = st.columns(3)
        
        with rec_col1:
            if first_attempt_rate < 90:
                st.info("📍 تحسين دقة العناوين والتواصل المسبق")
            else:
                st.success("✅ كفاءة المحاولة الأولى ممتازة")
        
        with rec_col2:
            if len(weak_drivers) > 0:
                st.warning(f"👥 برنامج تدريب لـ {len(weak_drivers)} مندوب")
            else:
                st.success("✅ جميع المناديب يؤدون بشكل جيد")
        
        with rec_col3:
            if avg_attempts > 1.3:
                st.error("🔄 مراجعة عمليات التوصيل والجدولة")
            else:
                st.success("✅ متوسط المحاولات مثالي")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, #e3f2fd, #bbdefb); 
                padding: 1.5rem; border-radius: 10px; margin: 1.5rem 0;
                border-left: 4px solid #2196f3; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
            <div style="text-align: center;">
                <div style="font-size: 1.5rem; font-weight: bold; color: #1976d2;">
                    """ + f"{first_time_shipments:,}" + """
                </div>
                <div style="font-size: 0.9rem; color: #424242;">الشحنات الأولى</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 1.5rem; font-weight: bold; color: #388e3c;">
                    """ + f"{first_attempt_deliveries:,}" + """
                </div>
                <div style="font-size: 0.9rem; color: #424242;">نجح من الأولى</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 1.5rem; font-weight: bold; color: #f57c00;">
                    """ + f"{additional_attempt_deliveries:,}" + """
                </div>
                <div style="font-size: 0.9rem; color: #424242;">محاولات إضافية</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 1.5rem; font-weight: bold; color: #7b1fa2;">
                    """ + f"{(additional_attempt_deliveries/total_orders*100):.2f}%" + """
                </div>
                <div style="font-size: 0.9rem; color: #424242;">معدل المحاولات الإضافية</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

else:
    # رسالة عدم وجود بيانات
    st.markdown("""
    <div class="chart-container" style="text-align: center; padding: 4rem;">
        <h2 style="color: #e74c3c; margin-bottom: 2rem;">❌ لا توجد بيانات متاحة</h2>
        <p style="font-size: 1.2rem; color: #7f8c8d; margin-bottom: 2rem;">
            يرجى تحديد مسارات المجلدات أو رفع الملفات يدوياً
        </p>
        <div style="background: linear-gradient(135deg, #f8f9fa, #e9ecef); padding: 2rem; border-radius: 15px; margin-top: 2rem;">
            <h3 style="color: #495057; margin-bottom: 1rem;">🚀 دليل الإعداد السريع:</h3>
            <div style="text-align: right; max-width: 800px; margin: 0 auto;">
                <h4 style="color: #007bff;">📂 للتحديث التلقائي:</h4>
                <p><strong>1. إنشاء المجلدات:</strong></p>
                <div class="file-path">C:\shipping_data\main\</div>
                <div class="file-path">C:\shipping_data\branches\</div>
                <p><strong>2. فعّل "التحديث التلقائي"</strong></p>
                <p><strong>3. اكتب مسارات المجلدات أعلاه</strong></p>
                <p><strong>4. اختر فترة التحديث (ننصح بـ 60 ثانية)</strong></p>
                <p><strong>5. ضع ملفاتك في المجلدات والنظام سيعمل تلقائياً!</strong></p>
                
                <h4 style="color: #28a745; margin-top: 2rem;">📁 للاستخدام اليدوي:</h4>
                <p><strong>1. اضغط "الوضع اليدوي"</strong></p>
                <p><strong>2. ارفع ملف البيانات الرئيسي</strong></p>
                <p><strong>3. ارفع ملفات الفروع (اختياري)</strong></p>
                <p><strong>4. استخدم الفلاتر والتحليلات</strong></p>
                
                <h4 style="color: #dc3545; margin-top: 2rem;">⚠️ متطلبات الملفات:</h4>
                <p>• <strong>الصيغ المدعومة:</strong> Excel (.xlsx, .xls), CSV (.csv)</p>
                <p>• <strong>الأعمدة المطلوبة:</strong> رقم الطلب، رقم التتبع، اسم المندوب، حالة الطلب، تواريخ الشحن</p>
                <p>• <strong>تنسيق التواريخ:</strong> تاريخ الاستلام (ISO), تاريخ الشحن (DD/MM/YYYY)</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# عرض دليل المساعدة في الشريط الجانبي - مع إضافة معلومات حفظ البيانات
add_logout_button()

with st.sidebar:
    st.markdown("---")
    st.markdown("### 💾 حالة البيانات")
    
    # عرض حالة البيانات المحفوظة - مبسط
    if has_saved_data("niceone"):
        st.success("✅ بيانات NiceOne محفوظة")
        saved_info = get_company_data("niceone")
        st.info(f"📊 {saved_info['total_rows']:,} سجل - {saved_info['save_time'].strftime('%H:%M')} - {saved_info['source']}")
        
        if st.button("🗑️ مسح", use_container_width=True, key="sidebar_clear"):
            clear_company_data("niceone")
            st.rerun()
    else:
        st.warning("⚠️ لا توجد بيانات محفوظة")
    
    st.markdown("### 📚 دليل المساعدة")
    
    with st.expander("💾 نظام حفظ البيانات الجديد"):
        st.markdown("""
        **🌟 المميزات الجديدة:**
        - **حفظ تلقائي** للملفات المرفوعة
        - **البيانات تبقى** عند التنقل للصفحات الأخرى
        - **عرض معلومات** البيانات المحفوظة
        - **إمكانية مسح** البيانات عند الحاجة
        
        **🔄 كيف يعمل:**
        1. ارفع الملف → يحفظ تلقائياً
        2. انتقل لصفحة أخرى → البيانات تبقى
        3. عُد لهذه الصفحة → البيانات موجودة
        """)
    
    with st.expander("🔧 إعداد التحديث التلقائي"):
        st.markdown("""
        **الخطوات:**
        1. أنشئ مجلدين على حاسوبك
        2. فعّل التحديث التلقائي 
        3. اكتب مسارات المجلدات
        4. ضع ملفاتك وسيعمل النظام تلقائياً
        
        **مثال على المسارات:**
        ```
        C:/data/main/
        C:/data/branches/
        ```
        """)
    
    with st.expander("📊 فهم التقارير"):
        st.markdown("""
        **المؤشرات الرئيسية:**
        - **نسبة التسليم الكلية:** إجمالي المسلم ÷ إجمالي الطلبات
        - **نسبة المحاولة الأولى:** المسلم من أول محاولة ÷ الشحنات الأولى  
        - **متوسط المحاولات:** عدد المحاولات اللازمة للتسليم
        - **عدد التحميل:** إجمالي الطلبات المحملة للمندوب
        - **نسبة التوصيل:** نجح المندوب في توصيلها ÷ التي حُملت له
        
        **الألوان في الجداول:**
        - 🟢 أخضر: أداء ممتاز (90%+)
        - 🟡 أصفر: أداء جيد (80-89%)
        - 🔴 أحمر: يحتاج تحسين (<80%)
        """)
    
    with st.expander("🛠️ استكشاف الأخطاء"):
        st.markdown("""
        **مشاكل شائعة:**
        
        **لا تظهر البيانات:**
        - تأكد من صحة مسارات المجلدات
        - تحقق من وجود الملفات في المجلدات
        - جرب الوضع اليدوي للاختبار
        
        **بيانات خاطئة:**
        - تأكد من تنسيق التواريخ
        - تحقق من أسماء الأعمدة
        - استخدم ملف Excel بدلاً من CSV
        
        **التحديث لا يعمل:**
        - اضغط "تحديث فوري"
        - تأكد من صلاحيات القراءة للمجلدات
        - جرب فترة تحديث أطول
        """)

# إضافة التحديث التلقائي للصفحة
if auto_update and main_folder:
    # عرض معلومات مبسطة في الشريط الجانبي
    if st.session_state.get('show_info', False):
        with st.sidebar:
            st.markdown("### 🔄 التحديث التلقائي")
            st.markdown(f"**✅ النظام نشط**")
            st.markdown(f"**⏱️ الفترة:** {update_interval} ثانية")
            
            if st.session_state.current_main_file:
                st.markdown(f"**📄 الملف:** `{os.path.basename(st.session_state.current_main_file)}`")
            
            if st.button("🔄 تحديث فوري", use_container_width=True):
                st.session_state.last_update_time = None
                st.rerun()
    
    # نظام التحديث البسيط
    time.sleep(1)

# تذييل مع معلومات حفظ البيانات
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: #6c757d; margin-top: 1rem;">
    <p style="margin: 0;">
        🚚 <strong>NiceOne Analytics</strong> - مع نظام حفظ البيانات الذكي
    </p>
    <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem;">
        💾 البيانات محفوظة طوال الجلسة | 🔄 تحديث تلقائي متاح | ⚡ معالجة سريعة
    </p>
</div>
""", unsafe_allow_html=True)
