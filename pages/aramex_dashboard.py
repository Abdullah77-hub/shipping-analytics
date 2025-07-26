try:
    from auth_protection import check_authentication, add_logout_button
    if not check_authentication():
        st.stop()
except ImportError:
    st.error("❌ ملف الحماية غير موجود")
    st.stop()

# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import os

# ==================== إعدادات الصفحة ====================
st.set_page_config(
    page_title="Aramex Analytics",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==================== Session State ====================
if 'show_upload' not in st.session_state:
    st.session_state.show_upload = False
if 'show_sla_upload' not in st.session_state:
    st.session_state.show_sla_upload = False

# ==================== دوال SLA ====================
def save_sla_data(df, source="manual"):
    """حفظ بيانات SLA في session state"""
    st.session_state['sla_saved_data'] = {
        'sla_df': df,
        'save_time': datetime.now(),
        'source': source,
        'total_cities': len(df)
    }
    st.success(f"تم حفظ بيانات اتفاقية SLA! ({len(df):,} مدينة)")

def get_sla_data():
    """استرجاع بيانات SLA"""
    return st.session_state.get('sla_saved_data', None)

def has_sla_data():
    """التحقق من وجود بيانات SLA"""
    saved_data = get_sla_data()
    return saved_data is not None and 'sla_df' in saved_data

def clear_sla_data():
    """مسح بيانات SLA"""
    if 'sla_saved_data' in st.session_state:
        del st.session_state['sla_saved_data']
        st.success("تم مسح بيانات اتفاقية SLA")

@st.cache_data(show_spinner=False)
def process_sla_data(df):
    """معالجة بيانات SLA"""
    df.columns = df.columns.str.strip()
    
    city_col = None
    days_col = None
    
    for col in df.columns:
        col_lower = str(col).lower()
        if any(keyword in col_lower for keyword in ['city', 'مدينة', 'destination']):
            city_col = col
        elif any(keyword in col_lower for keyword in ['day', 'يوم', 'أيام', 'sla', 'target']):
            days_col = col
    
    if city_col is None or days_col is None:
        if len(df.columns) >= 2:
            city_col = df.columns[0]
            days_col = df.columns[1]
    
    if city_col and days_col:
        sla_clean = pd.DataFrame({
            'المدينة': df[city_col].astype(str).str.strip(),
            'SLA_أيام': pd.to_numeric(df[days_col], errors='coerce')
        })
        
        sla_clean = sla_clean.dropna()
        sla_clean = sla_clean[sla_clean['المدينة'] != '']
        
        return sla_clean
    else:
        st.error("لم يتم العثور على اعمدة المدينة والايام في ملف SLA")
        return pd.DataFrame()

# ==================== دوال Aramex ====================
def save_aramex_data(df, source="manual"):
    """حفظ بيانات Aramex"""
    st.session_state['aramex_saved_data'] = {
        'main_df': df,
        'save_time': datetime.now(),
        'source': source,
        'total_rows': len(df),
        'total_columns': len(df.columns)
    }
    st.success(f"تم حفظ بيانات Aramex! ({len(df):,} شحنة)")

def get_aramex_data():
    """استرجاع بيانات Aramex"""
    return st.session_state.get('aramex_saved_data', None)

def has_aramex_data():
    """التحقق من وجود بيانات Aramex"""
    saved_data = get_aramex_data()
    return saved_data is not None and 'main_df' in saved_data

def clear_aramex_data():
    """مسح بيانات Aramex"""
    if 'aramex_saved_data' in st.session_state:
        del st.session_state['aramex_saved_data']
        st.success("تم مسح بيانات Aramex")

def safe_date_conversion(series, column_name):
    """تحويل آمن وسريع للتواريخ"""
    if series is None or len(series) == 0:
        return pd.Series(dtype='datetime64[ns]')
    
    # محاولة التحويل المباشر أولاً (الأسرع)
    try:
        converted = pd.to_datetime(series, errors='coerce')
        if not converted.isna().all():
            return converted
    except:
        pass
    
    # محاولة معالجة الأرقام (Excel serial dates) - محسن
    try:
        numeric_series = pd.to_numeric(series, errors='coerce')
        valid_mask = (numeric_series >= 1) & (numeric_series <= 50000)  # نطاق أضيق للسرعة
        if valid_mask.any():
            converted = pd.to_datetime(numeric_series, errors='coerce', origin='1899-12-30', unit='D')
            current_year = datetime.now().year
            reasonable_mask = (converted.dt.year >= 2020) & (converted.dt.year <= current_year + 1)
            if reasonable_mask.any():
                return converted
    except:
        pass
    
    # إرجاع سلسلة فارغة إذا فشلت المحاولات
    return pd.Series([pd.NaT] * len(series), dtype='datetime64[ns]')
@st.cache_data(show_spinner=False, max_entries=5, ttl=600)
def process_aramex_data(df):
    """معالجة بيانات Aramex الرئيسية مع التصنيف الجديد للحالات"""
    
    # خريطة الأعمدة
    column_mapping = {
        'AWB': 'رقم_الشحنة',
        'Status': 'الحالة',
        'Destination City': 'المدينة_الوجهة',
        'Origin City': 'المدينة_المنشأ',
        'Pickup Date (Creation Date)': 'تاريخ_الاستلام',
        'First Out For Delivery': 'المحاولة_الأولى',
        '2nd Delivery Attempt': 'المحاولة_الثانية', 
        '3rd Delivery Attempt': 'المحاولة_الثالثة',
        'Total Delivery Attempts': 'إجمالي_المحاولات',
        'Last Attempted Delivery Action Date': 'تاريخ_آخر_محاولة',
        'Expected Delivery Date': 'التاريخ_المتوقع_للتسليم',
        'Transit Days': 'أيام_النقل',
        'Weight': 'الوزن',
        'COD Value': 'المبلغ_المستحق',
        'Destination city tier': 'مستوى_المدينة',
        'Destination Country': 'الدولة_الوجهة',
        'Consignee Reference 1': 'المرجع_الشحنة_1',
        'Delivery Date': 'تاريخ_التسليم'
    }
    
    # إعادة تسمية الأعمدة
    df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
    
    # معالجة التواريخ المحسنة
    date_columns = ['تاريخ_الاستلام', 'المحاولة_الأولى', 'المحاولة_الثانية', 'المحاولة_الثالثة', 'تاريخ_التسليم']
    for col in date_columns:
        if col in df.columns:
            df[col] = safe_date_conversion(df[col], col)
    
    # معالجة الأرقام
    numeric_columns = ['إجمالي_المحاولات', 'أيام_النقل', 'الوزن', 'المبلغ_المستحق']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # التصنيف الجديد لحالة التسليم
    if 'الحالة' in df.columns:
        status_upper = df['الحالة'].astype(str).str.upper().str.strip()
        
        # ✅ تم التسليم (Delivered)
        delivered_statuses = [
            'DELIVERED', 'SHIPMENT DELIVERED', 'PAID', 'SHIPMENT DELIVERED OK'
        ]

        # 🚚 جاري التسليم (In Progress)
        in_progress_statuses = [
            'EXCEPTION', 'FORWARD TO DELIVERY WAREHOUSE', 'HAL', 'HELD AT CUSTOMS',
            'HELD FOR PICKUP', 'IN PROGRESS', 'OUT FOR DELIVERY', 'SHIPMENT OUT FOR DELIVERY',
            'SORTING', 'TRANSIT', 'PENDING', 'PROCESSING', 'IN TRANSIT', 'DEPOSITED',
            'EXPIRED', 'RECEIVED-INBOUND TEAM', 'LOCKED', 'NOT-DELIVERED', 'NOT-DEPOSITED',
            'R-WAITING', 'R-DEPOSITED', 'IN-TRANSIT-R', 'PICKED UP', 'AWAITING CONSIGNEE FOR COLLECTION',
            'NO RESPONSE', 'INCORRECT PHONE', 'AT DESTINATION FACILITY', 'LEFT ORIGIN',
            'STILL AT ORIGIN', 'AT HUB FACILITY', 'INCORRECT ADDRESS', 'SHIPMENT STORED AT WAREHOUSE',
            'SHIPMENT CONFISCATED', 'CUSTOMER NOT AVAILABLE', 'CUSTOMER CONTACT ATTEMPTS COMPLETED',
            'ATTEMPTED TO DELIVER', 'REDIRECT UNDER A NEW SHIPMENT', 'UNDER DELIVERY',
            'ADDRESS INFORMATION NEEDED, CONTACT DHL', 'ARRIVED AT DELIVERY FACILITY',
            'AWAITING COLLECTION BY RECIPIENT AS REQUESTED', 'CLEARANCE DELAY CD',
            'CLEARANCE PROCESSING COMPLETE', 'CLOSED SHIPMENT', 'CUSTOMS STATUS UPDATED',
            'DELIVERY ARRANGED, NO DETAILS EXPECTED', 'DEPARTED FACILITY',
            'FORWARDED FOR DELIVERY – DETAILS EXPECTED', 'PROCESSED AT DHL LOCATION',
            'RECIPIENT REFUSED DELIVERY', 'SCHEDULED FOR DELIVERY AS AGREED',
            'SCHEDULED FOR DELIVERY ND', 'SHIPMENT HELD – AVAILABLE UPON RECEIPT OF PAYMENT',
            'SHIPMENT ON HOLD', 'WITH DELIVERY COURIER', 'DATA RECEIVED', 'ARRIVED', 'SHIPPED',
            'ADDRESS ACQUIRED', 'CUSTOMER NOT ANSWERING'
        ]
        
        # 🔁 مرتجع (Returned)
        returned_statuses = [
            'RETURN TO SHIPPER', 'RETURNED', 'REFUSED', 'OTHER FINAL STATUS',
            'CANCELLED', 'CANCELED', 'NOTRECEIVED', 'SHIPMENT REFUSED',
            'CUSTOMER HAS REFUSED THE SHIPMENT', 'RETURNED TO SHIPPER SHIPMENT NOT DELIVERED',
            'UNABLE TO LOCATE', 'TO BE RETURN TO SHIPPER', 'SKELETON RECORD TERMINATED',
            'TERMINATED'
        ]
        
        # ❌ استرجاع (Lost/Partial Return)
        lost_statuses = ['LOST', 'PICKUP']
        
        # إنشاء الشروط للتصنيف
        delivered_condition = status_upper.isin(delivered_statuses)
        in_progress_condition = status_upper.isin(in_progress_statuses)
        returned_condition = status_upper.isin(returned_statuses)
        lost_condition = status_upper.isin(lost_statuses)
        
        # تطبيق التصنيف
        df['حالة_التسليم'] = np.select(
            [delivered_condition, in_progress_condition, returned_condition, lost_condition],
            ['تم التسليم', 'قيد التوصيل', 'مرتجع', 'استرجاع'],
            default='أخرى'
        )
    
    # تحديد الشحنات المستثناة
    if 'المرجع_الشحنة_1' in df.columns:
        df['للاستثناء'] = df['المرجع_الشحنة_1'].astype(str).str.contains('_return', na=False, case=False)
    else:
        df['للاستثناء'] = False
    
    # حساب أيام المحاولة الأولى
    if 'تاريخ_الاستلام' in df.columns and 'المحاولة_الأولى' in df.columns:
        mask = df['تاريخ_الاستلام'].notna() & df['المحاولة_الأولى'].notna()
        if mask.sum() > 0:
            try:
                days_diff = (df.loc[mask, 'المحاولة_الأولى'] - df.loc[mask, 'تاريخ_الاستلام']).dt.days
                df['أيام_للمحاولة_الأولى'] = np.nan
                df.loc[mask, 'أيام_للمحاولة_الأولى'] = days_diff
                valid_mask = (df['أيام_للمحاولة_الأولى'] >= 0) & (df['أيام_للمحاولة_الأولى'] <= 365)
                df.loc[~valid_mask, 'أيام_للمحاولة_الأولى'] = np.nan
            except Exception as e:
                st.warning("تحذير: لم يتم حساب أيام المحاولة الأولى بسبب مشكلة في التواريخ")
                df['أيام_للمحاولة_الأولى'] = np.nan
    
    return df

# ==================== دوال إضافة معلومات SLA والـ FDS ====================
def add_sla_and_fds_columns(df, sla_df=None):
    """إضافة أعمدة SLA وحسابات FDS"""
    
    # نسخ البيانات
    df_enhanced = df.copy()
    
    # إضافة الأعمدة الجديدة
    df_enhanced['SLA_أيام'] = np.nan
    df_enhanced['حالة_SLA_محاولة_أولى'] = 'غير محدد'
    df_enhanced['تسليم_من_أول_محاولة'] = False
    df_enhanced['ضمن_SLA'] = False
    df_enhanced['مؤهل_FDS'] = False
    
    # إضافة معلومات SLA إذا توفرت
    if sla_df is not None and len(sla_df) > 0:
        # دمج بيانات SLA
        sla_dict = dict(zip(sla_df['المدينة'], sla_df['SLA_أيام']))
        df_enhanced['SLA_أيام'] = df_enhanced['المدينة_الوجهة'].map(sla_dict)
    
    # حساب حالة SLA للمحاولة الأولى
    if 'أيام_للمحاولة_الأولى' in df_enhanced.columns:
        for idx, row in df_enhanced.iterrows():
            days_to_first = row['أيام_للمحاولة_الأولى']
            sla_days = row['SLA_أيام']
            
            if pd.notna(days_to_first):
                if pd.notna(sla_days):
                    if days_to_first <= sla_days:
                        df_enhanced.at[idx, 'حالة_SLA_محاولة_أولى'] = 'في SLA' if days_to_first == sla_days else 'قبل SLA'
                        df_enhanced.at[idx, 'ضمن_SLA'] = True
                    else:
                        df_enhanced.at[idx, 'حالة_SLA_محاولة_أولى'] = 'بعد SLA'
                else:
                    # استخدام SLA افتراضي = 2 أيام
                    default_sla = 2
                    if days_to_first <= default_sla:
                        df_enhanced.at[idx, 'حالة_SLA_محاولة_أولى'] = 'ضمن افتراضي'
                        df_enhanced.at[idx, 'ضمن_SLA'] = True
                    else:
                        df_enhanced.at[idx, 'حالة_SLA_محاولة_أولى'] = 'بعد افتراضي'
    
    # تحديد الشحنات المُسلمة من أول محاولة
    if 'تاريخ_التسليم' in df_enhanced.columns and 'المحاولة_الأولى' in df_enhanced.columns:
        # التحقق من تطابق تاريخ التسليم مع تاريخ المحاولة الأولى (نفس اليوم)
        delivery_mask = (
            df_enhanced['حالة_التسليم'] == 'تم التسليم'
        ) & (
            df_enhanced['تاريخ_التسليم'].notna()
        ) & (
            df_enhanced['المحاولة_الأولى'].notna()
        ) & (
            df_enhanced['تاريخ_التسليم'].dt.date == df_enhanced['المحاولة_الأولى'].dt.date
        )
        
        df_enhanced.loc[delivery_mask, 'تسليم_من_أول_محاولة'] = True
    else:
        # البديل: استخدام عدد المحاولات = 1
        if 'إجمالي_المحاولات' in df_enhanced.columns:
            delivery_mask = (
                df_enhanced['حالة_التسليم'] == 'تم التسليم'
            ) & (
                df_enhanced['إجمالي_المحاولات'] == 1
            )
            
            df_enhanced.loc[delivery_mask, 'تسليم_من_أول_محاولة'] = True
    
    # تحديد الشحنات المؤهلة لـ FDS
    fds_mask = (
        df_enhanced['تسليم_من_أول_محاولة'] == True
    ) & (
        df_enhanced['ضمن_SLA'] == True
    )
    
    df_enhanced.loc[fds_mask, 'مؤهل_FDS'] = True
    
    return df_enhanced
# ==================== دوال التحليل المحدثة مع FDS ====================
@st.cache_data(show_spinner=False)
def analyze_delivery_attempts_with_fds(df):
    """تحليل محاولات التوصيل مع FDS"""
    analysis = {}
    
    if 'حالة_التسليم' not in df.columns:
        return {}
    
    total_shipments = len(df)
    
    if total_shipments == 0:
        return {}
    
    # حساب DR (Delivery Rate)
    delivered_shipments = len(df[df['حالة_التسليم'] == 'تم التسليم'])
    dr_rate = (delivered_shipments / total_shipments * 100)
    analysis['DR'] = round(dr_rate, 1)
    
    # حساب FDS (مع SLA)
    if 'مؤهل_FDS' in df.columns:
        fds_count = len(df[df['مؤهل_FDS'] == True])
        fds_rate = (fds_count / total_shipments * 100)
        analysis['FDS'] = round(fds_rate, 1)
        analysis['عدد_FDS'] = fds_count
    
    # حساب SLA Rate الإجمالي
    if 'ضمن_SLA' in df.columns:
        sla_compliant_count = len(df[df['ضمن_SLA'] == True])
        sla_rate = (sla_compliant_count / total_shipments * 100)
        analysis['SLA_Rate'] = round(sla_rate, 1)
        analysis['عدد_SLA_ملتزم'] = sla_compliant_count
    
    # تحليل حسب عدد المحاولات (للمسلم فقط)
    delivered_df = df[df['حالة_التسليم'] == 'تم التسليم']
    
    if len(delivered_df) > 0 and 'إجمالي_المحاولات' in delivered_df.columns:
        delivered_df = delivered_df[delivered_df['إجمالي_المحاولات'].notna()]
        delivered_df = delivered_df[delivered_df['إجمالي_المحاولات'] > 0]
        
        total_delivered_shipments = len(delivered_df)
        
        if total_delivered_shipments > 0:
            attempt_counts = delivered_df['إجمالي_المحاولات'].value_counts().sort_index()
            
            percentages = {
                'المحاولة 1': 0, 
                'المحاولة 2': 0, 
                'المحاولة 3': 0, 
                'أكثر من 3 محاولات': 0
            }
            
            for attempt, count in attempt_counts.items():
                percentage = (count / total_delivered_shipments) * 100
                
                if attempt == 1:
                    percentages['المحاولة 1'] = percentage
                elif attempt == 2:
                    percentages['المحاولة 2'] = percentage
                elif attempt == 3:
                    percentages['المحاولة 3'] = percentage
                elif attempt > 3:
                    percentages['أكثر من 3 محاولات'] += percentage
            
            for key, value in percentages.items():
                analysis[key] = round(value, 1)
    
    return analysis

@st.cache_data(show_spinner=False, ttl=300)
def analyze_weekly_trends_enhanced(df):
    """تحليل الاتجاهات الأسبوعية للأداء مع FDS"""
    if 'تاريخ_الاستلام' not in df.columns or len(df) == 0:
        return pd.DataFrame()
    
    df_with_dates = df[df['تاريخ_الاستلام'].notna()].copy()
    
    if len(df_with_dates) == 0:
        return pd.DataFrame()
    
    try:
        df_with_dates['تاريخ_الاستلام'] = pd.to_datetime(df_with_dates['تاريخ_الاستلام'])
        df_with_dates['بداية_الأسبوع'] = df_with_dates['تاريخ_الاستلام'].dt.to_period('W').dt.start_time
        df_with_dates['رقم_الأسبوع'] = df_with_dates['تاريخ_الاستلام'].dt.isocalendar().week
    except Exception as e:
        return pd.DataFrame()
    
    weekly_analysis = []
    
    for week_start, week_data in df_with_dates.groupby('بداية_الأسبوع'):
        total_shipments = len(week_data)
        
        if total_shipments == 0:
            continue
        
        # DR Rate
        delivered_count = (week_data['حالة_التسليم'] == 'تم التسليم').sum() if 'حالة_التسليم' in week_data.columns else 0
        dr_rate = (delivered_count / total_shipments * 100)
        
        # FDS
        fds_count = 0
        if 'مؤهل_FDS' in week_data.columns:
            fds_count = (week_data['مؤهل_FDS'] == True).sum()
        fds_rate = (fds_count / total_shipments * 100)
        
        # SLA Rate
        sla_count = 0
        if 'ضمن_SLA' in week_data.columns:
            sla_count = (week_data['ضمن_SLA'] == True).sum()
        sla_rate = (sla_count / total_shipments * 100)
        
        # Pending Rate
        pending_count = (week_data['حالة_التسليم'] == 'قيد التوصيل').sum() if 'حالة_التسليم' in week_data.columns else 0
        pending_rate = (pending_count / total_shipments * 100)
        
        week_number = week_data['رقم_الأسبوع'].iloc[0] if len(week_data) > 0 else 0
        week_label = f"W{week_number}-{week_start.year}"
        
        weekly_analysis.append({
            'الأسبوع': week_label,
            'رقم_الأسبوع_الرقمي': week_number,
            'تاريخ_البداية': week_start,
            'إجمالي_الشحنات': total_shipments,
            'DR': round(dr_rate, 1),
            'FDS': round(fds_rate, 1),
            'SLA_Rate': round(sla_rate, 1),
            'Pending': round(pending_rate, 1)
        })
    
    result_df = pd.DataFrame(weekly_analysis)
    
    if len(result_df) > 0:
        result_df = result_df.sort_values('تاريخ_البداية').reset_index(drop=True)
    
    return result_df

@st.cache_data(show_spinner=False, ttl=300)
def analyze_cities_performance_enhanced(df, city_filter=None, country_filter=None):
    """تحليل أداء المدن مع FDS"""
    if 'المدينة_الوجهة' not in df.columns or len(df) == 0:
        return pd.DataFrame()
    
    df_filtered = df.copy()
    if city_filter and city_filter != 'الكل':
        df_filtered = df_filtered[df_filtered['المدينة_الوجهة'] == city_filter]
    if country_filter and country_filter != 'الكل' and 'الدولة_الوجهة' in df.columns:
        df_filtered = df_filtered[df_filtered['الدولة_الوجهة'] == country_filter]
    
    if len(df_filtered) == 0:
        return pd.DataFrame()
    
    # تجميع البيانات حسب المدينة
    city_stats = []
    
    for city, city_data in df_filtered.groupby('المدينة_الوجهة'):
        total_shipments = len(city_data)
        
        if total_shipments == 0:
            continue
        
        # حساب المؤشرات
        delivered_count = (city_data['حالة_التسليم'] == 'تم التسليم').sum() if 'حالة_التسليم' in city_data.columns else 0
        dr_rate = (delivered_count / total_shipments * 100)
        
        # FDS
        fds_count = (city_data['مؤهل_FDS'] == True).sum() if 'مؤهل_FDS' in city_data.columns else 0
        fds_rate = (fds_count / total_shipments * 100)
        
        # SLA Rate
        sla_count = 0
        if 'ضمن_SLA' in city_data.columns:
            sla_count = (city_data['ضمن_SLA'] == True).sum()
        sla_rate = (sla_count / total_shipments * 100)
        
        # Pending Rate
        pending_count = (city_data['حالة_التسليم'] == 'قيد التوصيل').sum() if 'حالة_التسليم' in city_data.columns else 0
        pending_rate = (pending_count / total_shipments * 100)
        
        # متوسط الأيام
        avg_days = city_data['أيام_للمحاولة_الأولى'].mean() if 'أيام_للمحاولة_الأولى' in city_data.columns else 0
        
        # متوسط المحاولات
        avg_attempts = city_data['إجمالي_المحاولات'].mean() if 'إجمالي_المحاولات' in city_data.columns else 0
        
        # SLA المحدد للمدينة
        city_sla = city_data['SLA_أيام'].iloc[0] if 'SLA_أيام' in city_data.columns and city_data['SLA_أيام'].notna().any() else 'غير محدد'
        
        # الدولة
        country = city_data['الدولة_الوجهة'].iloc[0] if 'الدولة_الوجهة' in city_data.columns else 'غير محدد'
        
        city_stats.append({
            'المدينة': city,
            'الدولة': country,
            'إجمالي_الشحنات': total_shipments,
            'SLA_أيام': city_sla,
            'DR': round(dr_rate, 1),
            'FDS': round(fds_rate, 1),
            'SLA_Rate': round(sla_rate, 1),
            'Pending': round(pending_rate, 1),
            'متوسط_الأيام': round(avg_days, 1) if pd.notna(avg_days) else 0,
            'متوسط_المحاولات': round(avg_attempts, 1) if pd.notna(avg_attempts) else 0
        })
    
    result_df = pd.DataFrame(city_stats)
    
    if len(result_df) > 0:
        result_df = result_df.sort_values('إجمالي_الشحنات', ascending=False)
    
    return result_df

# ==================== دالة عرض الحالات الأخرى ====================
def analyze_other_statuses(df):
    """تحليل الحالات غير المصنفة"""
    if 'حالة_التسليم' not in df.columns or 'الحالة' not in df.columns:
        return pd.DataFrame()
    
    other_shipments = df[df['حالة_التسليم'] == 'أخرى'].copy()
    
    if len(other_shipments) == 0:
        return pd.DataFrame()
    
    status_analysis = other_shipments['الحالة'].value_counts().reset_index()
    status_analysis.columns = ['الحالة_الأصلية', 'عدد_الشحنات']
    status_analysis['النسبة_المئوية'] = (status_analysis['عدد_الشحنات'] / len(other_shipments) * 100).round(2)
    
    return status_analysis

@st.cache_data(show_spinner=False, ttl=300)
def analyze_delayed_shipments(df, sla_df=None):
    """تحليل الشحنات المتأخرة مع SLA"""
    if len(df) == 0:
        return pd.DataFrame()
    
    # تصفية الشحنات قيد التوصيل فقط
    pending_shipments = df[df['حالة_التسليم'] == 'قيد التوصيل'].copy() if 'حالة_التسليم' in df.columns else df.copy()
    
    if len(pending_shipments) == 0:
        return pd.DataFrame()
    
    # تصفية الشحنات التي لها تاريخ استلام
    pending_shipments = pending_shipments[pending_shipments['تاريخ_الاستلام'].notna()].copy()
    
    if len(pending_shipments) == 0:
        return pd.DataFrame()
    
    # حساب الأيام منذ الاستلام
    today = datetime.now()
    pending_shipments['أيام_منذ_الاستلام'] = (today - pending_shipments['تاريخ_الاستلام']).dt.days
    
    # تصفية الشحنات التي مضى عليها أكثر من 0 أيام
    pending_shipments = pending_shipments[pending_shipments['أيام_منذ_الاستلام'] >= 0]
    
    if len(pending_shipments) == 0:
        return pd.DataFrame()
    
    # إضافة معلومات SLA إذا توفرت
    if sla_df is not None and len(sla_df) > 0:
        # دمج بيانات SLA
        sla_dict = dict(zip(sla_df['المدينة'], sla_df['SLA_أيام']))
        pending_shipments['SLA_أيام'] = pending_shipments['المدينة_الوجهة'].map(sla_dict)
        
        # تحديد الشحنات المتأخرة (تجاوزت SLA)
        pending_shipments['متأخر'] = (
            pending_shipments['SLA_أيام'].notna() & 
            (pending_shipments['أيام_منذ_الاستلام'] > pending_shipments['SLA_أيام'])
        )
        
        # تصفية الشحنات المتأخرة فقط
        delayed_shipments = pending_shipments[pending_shipments['متأخر']].copy()
        
        if len(delayed_shipments) > 0:
            # حساب أيام التأخير
            delayed_shipments['أيام_التأخير'] = (
                delayed_shipments['أيام_منذ_الاستلام'] - delayed_shipments['SLA_أيام']
            )
    else:
        # إذا لم تتوفر بيانات SLA، اعتبر الشحنات متأخرة بعد 3 أيام (افتراضي)
        default_sla = 3
        pending_shipments['SLA_أيام'] = default_sla
        pending_shipments['متأخر'] = pending_shipments['أيام_منذ_الاستلام'] > default_sla
        
        delayed_shipments = pending_shipments[pending_shipments['متأخر']].copy()
        
        if len(delayed_shipments) > 0:
            delayed_shipments['أيام_التأخير'] = (
                delayed_shipments['أيام_منذ_الاستلام'] - default_sla
            )
    
    if len(delayed_shipments) == 0:
        return pd.DataFrame()
    
    # إضافة تصنيف شدة التأخير
    def classify_delay_severity(days):
        if days <= 2:
            return 'تأخير بسيط'
        elif days <= 5:
            return 'تأخير متوسط'
        elif days <= 10:
            return 'تأخير شديد'
        else:
            return 'تأخير حرج'
    
    delayed_shipments['شدة_التأخير'] = delayed_shipments['أيام_التأخير'].apply(classify_delay_severity)
    
    # تحديد الأعمدة المطلوبة للعرض مع إضافة عمود أيام التأخير عن SLA
    display_columns = ['رقم_الشحنة', 'المدينة_الوجهة', 'الدولة_الوجهة', 'تاريخ_الاستلام', 
                      'أيام_منذ_الاستلام', 'SLA_أيام', 'أيام_التأخير_عن_SLA', 'أيام_التأخير', 'شدة_التأخير', 'الحالة']
    
    # إضافة عمود أيام التأخير عن SLA (الحساب الصحيح)
    if len(delayed_shipments) > 0:
        # حساب تاريخ انتهاء SLA (تاريخ الاستلام + عدد أيام SLA)
        today = datetime.now()
        
        # حساب الأيام التي تجاوزت SLA
        delayed_shipments['تاريخ_انتهاء_SLA'] = delayed_shipments['تاريخ_الاستلام'] + pd.to_timedelta(delayed_shipments['SLA_أيام'], unit='D')
        delayed_shipments['أيام_التأخير_عن_SLA'] = (today - delayed_shipments['تاريخ_انتهاء_SLA']).dt.days
        
        # التأكد من أن القيم موجبة فقط (للشحنات المتأخرة فعلاً)
        delayed_shipments['أيام_التأخير_عن_SLA'] = delayed_shipments['أيام_التأخير_عن_SLA'].clip(lower=0)
    
    # التأكد من وجود الأعمدة
    available_columns = [col for col in display_columns if col in delayed_shipments.columns]
    
    result = delayed_shipments[available_columns].copy()
    
    # ترتيب حسب أيام التأخير (الأكثر تأخيراً أولاً)
    result = result.sort_values('أيام_التأخير', ascending=False)
    
    return result

def analyze_delay_summary(delayed_df):
    """تحليل ملخص الشحنات المتأخرة"""
    if len(delayed_df) == 0:
        return {}
    
    summary = {
        'إجمالي_المتأخرة': len(delayed_df),
        'متوسط_أيام_التأخير': delayed_df['أيام_التأخير'].mean(),
        'أقصى_تأخير': delayed_df['أيام_التأخير'].max(),
        'أقل_تأخير': delayed_df['أيام_التأخير'].min()
    }
    
    # تحليل حسب شدة التأخير
    if 'شدة_التأخير' in delayed_df.columns:
        severity_counts = delayed_df['شدة_التأخير'].value_counts()
        for severity, count in severity_counts.items():
            summary[f'عدد_{severity}'] = count
            summary[f'نسبة_{severity}'] = (count / len(delayed_df) * 100)
    
    # تحليل حسب المدن
    if 'المدينة_الوجهة' in delayed_df.columns:
        city_counts = delayed_df['المدينة_الوجهة'].value_counts()
        summary['أكثر_المدن_تأخيراً'] = city_counts.head(5).to_dict()
    
    return summary
# ==================== دوال العرض والرسوم البيانية المحدثة ====================
def create_fds_performance_chart(analysis_data):
    """إنشاء مخطط أداء FDS"""
    if not analysis_data or 'FDS' not in analysis_data:
        return None
    
    categories = ['معدل التسليم (DR)', 'FDS (مع SLA)', 'SLA Rate']
    values = [
        analysis_data.get('DR', 0),
        analysis_data.get('FDS', 0),
        analysis_data.get('SLA_Rate', 0)
    ]
    
    colors = ['#4ecdc4', '#1f77b4', '#9467bd']
    
    fig = go.Figure(data=[
        go.Bar(
            x=categories,
            y=values,
            text=[f'{v:.1f}%' for v in values],
            textposition='outside',
            marker_color=colors,
            textfont=dict(size=14, color='#2c3e50', weight='bold')
        )
    ])
    
    fig.update_layout(
        title='مؤشرات الأداء الرئيسية',
        font=dict(family='Cairo', size=12),
        height=350,
        yaxis_title='النسبة المئوية (%)',
        yaxis_range=[0, max(values) * 1.2 if values else 10],
        showlegend=False,
        plot_bgcolor='rgba(248,249,250,0.8)',
        paper_bgcolor='white'
    )
    
    return fig

def create_weekly_performance_chart(weekly_df):
    """إنشاء مخطط الأداء الأسبوعي مع FDS"""
    if len(weekly_df) == 0:
        return None
    
    fig = go.Figure()
    
    colors = {
        'DR': '#17becf',
        'FDS': '#1f77b4',
        'SLA_Rate': '#9467bd',
        'Pending': '#d62728'
    }
    
    for metric, color in colors.items():
        if metric in weekly_df.columns:
            display_name = metric.replace('_', ' ')
            if metric == 'FDS':
                display_name = 'FDS (مع SLA)'
            elif metric == 'SLA_Rate':
                display_name = 'SLA Rate'
                
            fig.add_trace(go.Scatter(
                x=weekly_df.index,
                y=weekly_df[metric],
                mode='lines+markers',
                name=display_name,
                line=dict(color=color, width=3),
                marker=dict(size=8),
                hovertemplate=f'<b>{display_name}</b><br>الأسبوع: %{{customdata}}<br>القيمة: %{{y:.1f}}%<extra></extra>',
                customdata=weekly_df['الأسبوع']
            ))
    
    fig.update_layout(
        title=f'اتجاه مؤشرات الأداء عبر الأسابيع ({len(weekly_df)} أسبوع)',
        xaxis_title='تسلسل الأسابيع',
        yaxis_title='النسبة المئوية (%)',
        font=dict(family='Cairo', size=12),
        height=450,
        plot_bgcolor='rgba(248,249,250,0.8)',
        paper_bgcolor='white',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    fig.update_yaxes(range=[0, 100])
    
    return fig

def create_delay_severity_chart(delayed_df):
    """إنشاء مخطط شدة التأخير"""
    if len(delayed_df) == 0 or 'شدة_التأخير' not in delayed_df.columns:
        return None
    
    severity_counts = delayed_df['شدة_التأخير'].value_counts()
    
    # ألوان مختلفة لكل مستوى تأخير
    color_map = {
        'تأخير بسيط': '#f39c12',
        'تأخير متوسط': '#e67e22', 
        'تأخير شديد': '#e74c3c',
        'تأخير حرج': '#8e44ad'
    }
    
    colors = [color_map.get(severity, '#95a5a6') for severity in severity_counts.index]
    
    fig = px.bar(
        x=severity_counts.index,
        y=severity_counts.values,
        color=severity_counts.index,
        color_discrete_map=color_map,
        text=severity_counts.values,
        title='توزيع الشحنات المتأخرة حسب شدة التأخير'
    )
    
    fig.update_traces(
        textposition='outside',
        textfont_size=14,
        textfont_color='#2c3e50',
        textfont_weight='bold'
    )
    
    fig.update_layout(
        height=350,
        font=dict(family='Cairo', size=12),
        xaxis_title='شدة التأخير',
        yaxis_title='عدد الشحنات',
        showlegend=False,
        plot_bgcolor='rgba(248,249,250,0.8)',
        paper_bgcolor='white'
    )
    
    return fig

def display_delayed_shipments_section(df, sla_df=None):
    """عرض قسم الشحنات المتأخرة"""
    delayed_shipments = analyze_delayed_shipments(df, sla_df)
    
    if len(delayed_shipments) == 0:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<h3 class="chart-title">✅ لا توجد شحنات متأخرة</h3>', unsafe_allow_html=True)
        st.success("جميع الشحنات ضمن المواعيد المحددة أو تم تسليمها!")
        st.markdown('</div>', unsafe_allow_html=True)
        return
    
    # ملخص الشحنات المتأخرة
    delay_summary = analyze_delay_summary(delayed_shipments)
    
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown('<h3 class="chart-title">⏰ الشحنات المتأخرة</h3>', unsafe_allow_html=True)
    
    # مؤشرات الشحنات المتأخرة
    delay_col1, delay_col2, delay_col3, delay_col4 = st.columns(4)
    
    with delay_col1:
        st.metric("إجمالي المتأخرة", f"{delay_summary.get('إجمالي_المتأخرة', 0):,}")
    
    with delay_col2:
        avg_delay = delay_summary.get('متوسط_أيام_التأخير', 0)
        st.metric("متوسط أيام التأخير", f"{avg_delay:.1f}")
    
    with delay_col3:
        max_delay = delay_summary.get('أقصى_تأخير', 0)
        st.metric("أقصى تأخير", f"{max_delay} يوم")
    
    with delay_col4:
        total_pending = len(df[df['حالة_التسليم'] == 'قيد التوصيل']) if 'حالة_التسليم' in df.columns else 0
        delay_rate = (delay_summary.get('إجمالي_المتأخرة', 0) / total_pending * 100) if total_pending > 0 else 0
        st.metric("نسبة التأخير", f"{delay_rate:.1f}%")
    
    # مخطط شدة التأخير
    delay_chart = create_delay_severity_chart(delayed_shipments)
    if delay_chart:
        st.plotly_chart(delay_chart, use_container_width=True)
    
    # جدول الشحنات المتأخرة
    st.markdown("### 📋 جدول الشحنات المتأخرة")
    
    delay_filter_col1, delay_filter_col2, delay_filter_col3, delay_filter_col4 = st.columns(4)
    
    with delay_filter_col1:
        cities_delayed = ['الكل'] + sorted(delayed_shipments['المدينة_الوجهة'].unique().tolist())
        selected_delay_city = st.selectbox("فلتر المدينة", cities_delayed, key="delay_city_filter")
    
    with delay_filter_col2:
        severities = ['الكل'] + delayed_shipments['شدة_التأخير'].unique().tolist()
        selected_severity = st.selectbox("شدة التأخير", severities, key="delay_severity_filter")
    
    with delay_filter_col3:
        min_delay_days = st.number_input(
            "الحد الأدنى لأيام التأخير",
            min_value=0,
            max_value=int(delayed_shipments['أيام_التأخير'].max()),
            value=0,
            key="min_delay_filter"
        )
    
    with delay_filter_col4:
        delay_rows_options = ['20', '50', '100', 'الكل']
        selected_delay_rows = st.selectbox("عدد الصفوف", delay_rows_options, key="delay_rows_filter")
    
    # تطبيق الفلاتر
    filtered_delayed = delayed_shipments.copy()
    
    if selected_delay_city != 'الكل':
        filtered_delayed = filtered_delayed[filtered_delayed['المدينة_الوجهة'] == selected_delay_city]
    
    if selected_severity != 'الكل':
        filtered_delayed = filtered_delayed[filtered_delayed['شدة_التأخير'] == selected_severity]
    
    if min_delay_days > 0:
        filtered_delayed = filtered_delayed[filtered_delayed['أيام_التأخير'] >= min_delay_days]
    
    if selected_delay_rows != 'الكل':
        filtered_delayed = filtered_delayed.head(int(selected_delay_rows))
    
    # عرض الجدول
    if len(filtered_delayed) > 0:
        display_delayed = filtered_delayed.copy()
        
        # إضافة عمود أيام التأخير عن SLA (الحساب الصحيح)
        if 'تاريخ_الاستلام' in display_delayed.columns and 'SLA_أيام' in display_delayed.columns:
            # تحويل تاريخ الاستلام للصيغة الصحيحة إذا لم يكن كذلك
            if display_delayed['تاريخ_الاستلام'].dtype == 'object':
                display_delayed['تاريخ_الاستلام'] = pd.to_datetime(display_delayed['تاريخ_الاستلام'])
            
            # حساب تاريخ انتهاء SLA
            display_delayed['تاريخ_انتهاء_SLA'] = display_delayed['تاريخ_الاستلام'] + pd.to_timedelta(display_delayed['SLA_أيام'], unit='D')
            
            # حساب الأيام المتأخرة عن SLA
            today = datetime.now()
            display_delayed['أيام_التأخير_عن_SLA'] = (today - display_delayed['تاريخ_انتهاء_SLA']).dt.days
            
            # التأكد من أن القيم موجبة فقط
            display_delayed['أيام_التأخير_عن_SLA'] = display_delayed['أيام_التأخير_عن_SLA'].clip(lower=0)
        
        # إعادة تسمية الأعمدة للعرض
        column_rename = {
            'رقم_الشحنة': 'رقم الشحنة',
            'المدينة_الوجهة': 'المدينة الوجهة', 
            'الدولة_الوجهة': 'الدولة الوجهة',
            'تاريخ_الاستلام': 'تاريخ الاستلام',
            'أيام_منذ_الاستلام': 'أيام منذ الاستلام',
            'SLA_أيام': 'SLA (أيام)',
            'أيام_التأخير_عن_SLA': 'أيام التأخير عن SLA',
            'أيام_التأخير': 'أيام التأخير',
            'شدة_التأخير': 'شدة التأخير',
            'الحالة': 'الحالة'
        }
        
        display_delayed = display_delayed.rename(columns=column_rename)
        
        # تنسيق التاريخ
        if 'تاريخ الاستلام' in display_delayed.columns:
            display_delayed['تاريخ الاستلام'] = display_delayed['تاريخ الاستلام'].dt.strftime('%Y-%m-%d')
        
        st.dataframe(
            display_delayed, 
            use_container_width=True, 
            height=500, 
            hide_index=True
        )
        
        # أزرار التحميل والإجراءات
        delay_action_col1, delay_action_col2, delay_action_col3 = st.columns(3)
        
        with delay_action_col1:
            if st.button("📄 تحميل الشحنات المتأخرة (CSV)", use_container_width=True):
                csv_data = filtered_delayed.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="💾 تحميل CSV",
                    data=csv_data,
                    file_name=f"delayed_shipments_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        
        with delay_action_col2:
            if st.button("📊 تحميل ملخص التأخير", use_container_width=True):
                summary_df = pd.DataFrame([delay_summary]).T
                summary_df.columns = ['القيمة']
                summary_csv = summary_df.to_csv(encoding='utf-8-sig')
                st.download_button(
                    label="💾 تحميل ملخص",
                    data=summary_csv,
                    file_name=f"delay_summary_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        
        with delay_action_col3:
            # عرض إحصائيات سريعة
            critical_count = len(filtered_delayed[filtered_delayed['شدة_التأخير'] == 'تأخير حرج'])
            if critical_count > 0:
                st.error(f"⚠️ {critical_count} شحنة تأخير حرج")
            else:
                st.success("✅ لا توجد حالات تأخير حرج")
    else:
        st.info("لا توجد شحنات متأخرة تطابق الفلاتر المحددة")
    
    st.markdown('</div>', unsafe_allow_html=True)

def display_other_statuses_section(df):
    """عرض قسم الحالات الأخرى"""
    other_analysis = analyze_other_statuses(df)
    
    if len(other_analysis) == 0:
        return
    
    total_other = other_analysis['عدد_الشحنات'].sum()
    total_shipments = len(df[~df['للاستثناء']]) if 'للاستثناء' in df.columns else len(df)
    other_percentage = (total_other / total_shipments * 100) if total_shipments > 0 else 0
    
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown('<h3 class="chart-title">📋 تفاصيل الحالات الأخرى (غير المصنفة)</h3>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("إجمالي الحالات الأخرى", f"{total_other:,}")
    
    with col2:
        st.metric("النسبة من الإجمالي", f"{other_percentage:.1f}%")
    
    with col3:
        unique_statuses = len(other_analysis)
        st.metric("أنواع الحالات", f"{unique_statuses}")
    
    with col4:
        avg_per_status = total_other / unique_statuses if unique_statuses > 0 else 0
        st.metric("متوسط لكل حالة", f"{avg_per_status:.0f}")
    
    st.markdown("### 📊 تفصيل الحالات الأخرى")
    
    filter_col1, filter_col2 = st.columns(2)
    
    with filter_col1:
        min_count = st.number_input(
            "الحد الأدنى لعدد الشحنات", 
            min_value=1, 
            max_value=int(other_analysis['عدد_الشحنات'].max()), 
            value=1,
            key="other_status_min_count"
        )
    
    with filter_col2:
        show_rows = st.selectbox(
            "عدد الصفوف للعرض", 
            ['10', '20', '50', 'الكل'],
            key="other_status_rows"
        )
    
    filtered_analysis = other_analysis[other_analysis['عدد_الشحنات'] >= min_count]
    
    if show_rows != 'الكل':
        filtered_analysis = filtered_analysis.head(int(show_rows))
    
    display_df = filtered_analysis.copy()
    display_df = display_df.rename(columns={
        'الحالة_الأصلية': 'الحالة الأصلية',
        'عدد_الشحنات': 'عدد الشحنات',
        'النسبة_المئوية': 'النسبة المئوية (%)'
    })
    
    st.dataframe(display_df, use_container_width=True, height=400, hide_index=True)
    
    if len(filtered_analysis) > 1:
        st.markdown("### 📈 أكثر الحالات الأخرى شيوعاً")
        
        top_statuses = filtered_analysis.head(10)
        
        fig_other = px.bar(
            x=top_statuses['عدد_الشحنات'],
            y=top_statuses['الحالة_الأصلية'],
            orientation='h',
            text=top_statuses['عدد_الشحنات'],
            color=top_statuses['عدد_الشحنات'],
            color_continuous_scale='Reds',
            title="أعلى 10 حالات أخرى (غير مصنفة)"
        )
        
        fig_other.update_traces(
            textposition='inside',
            textfont_size=12,
            textfont_color='white',
            textfont_weight='bold'
        )
        
        fig_other.update_layout(
            height=max(300, len(top_statuses) * 40),
            font=dict(family='Cairo', size=11),
            xaxis_title='عدد الشحنات',
            yaxis_title='',
            showlegend=False,
            coloraxis_showscale=False,
            margin=dict(t=40, b=20, l=20, r=20),
            plot_bgcolor='rgba(248,249,250,0.8)',
            paper_bgcolor='white'
        )
        
        st.plotly_chart(fig_other, use_container_width=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("📄 تحميل قائمة الحالات الأخرى (CSV)", use_container_width=True):
            csv_data = other_analysis.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="💾 تحميل CSV",
                data=csv_data,
                file_name=f"other_statuses_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    st.markdown("### 💡 اقتراحات لتحسين التصنيف")
    st.info("""
    **لتقليل عدد الحالات غير المصنفة:**
    1. راجع الحالات الأكثر شيوعاً في الجدول أعلاه
    2. قم بإضافة هذه الحالات إلى قوائم التصنيف المناسبة في الكود
    3. تأكد من صحة كتابة أسماء الحالات
    4. استخدم هذا التقرير لتطوير منطق التصنيف بشكل مستمر
    """)
    
    st.markdown('</div>', unsafe_allow_html=True)
# ==================== CSS ====================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700&display=swap');
    
    * {
        font-family: 'Cairo', sans-serif !important;
    }
    
    .main {
        background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 50%, #fecfef 100%);
        padding: 1rem;
    }
    
    .aramex-header {
        background: linear-gradient(135deg, #ff6b6b, #ee5a24);
        padding: 1.5rem;
        border-radius: 15px;
        margin-bottom: 1rem;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    }
    
    .aramex-title {
        color: white;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .aramex-subtitle {
        color: #fff;
        font-size: 1rem;
        margin-top: 0.3rem;
        opacity: 0.9;
    }
    
    .fds-highlight {
        background: linear-gradient(135deg, #1f77b4, #4dabf7);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        text-align: center;
    }
    
    .upload-area {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #ff6b6b;
    }
    
    .kpi-container {
        display: flex;
        gap: 1rem;
        margin-bottom: 1.5rem;
        flex-wrap: wrap;
    }
    
    .kpi-card {
        flex: 1;
        min-width: 200px;
        background: white;
        padding: 1.5rem 1rem;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(255, 107, 107, 0.15);
        text-align: center;
        border-left: 4px solid;
        transition: transform 0.2s ease;
    }
    
    .kpi-card:hover {
        transform: translateY(-3px);
    }
    
    .kpi-card.shipments { border-left-color: #ff6b6b; }
    .kpi-card.delivered { border-left-color: #4ecdc4; }
    .kpi-card.fds { border-left-color: #1f77b4; }
    .kpi-card.sla { border-left-color: #9467bd; }
    .kpi-card.cities { border-left-color: #f9ca24; }
    
    .kpi-value {
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
        color: #2c3e50;
    }
    
    .kpi-label {
        font-size: 0.9rem;
        color: #7f8c8d;
        margin-top: 0.3rem;
        font-weight: 600;
    }
    
    .kpi-delta {
        font-size: 0.8rem;
        margin-top: 0.2rem;
        padding: 0.1rem 0.5rem;
        border-radius: 15px;
        display: inline-block;
    }
    
    .chart-container {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(255, 107, 107, 0.1);
        margin-bottom: 1.5rem;
        border-top: 3px solid #ff6b6b;
    }
    
    .chart-title {
        color: #2c3e50;
        font-size: 1.2rem;
        font-weight: 700;
        margin-bottom: 1rem;
        text-align: center;
        border-bottom: 1px solid #ff6b6b;
        padding-bottom: 0.3rem;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    
    .block-container {
        max-width: 1400px;
        padding-top: 1rem;
    }
    
    .dataframe {
        font-size: 0.9rem !important;
    }
    
    .stSpinner > div {
        border-color: #ff6b6b !important;
    }
    
    .error-message {
        background: #ffe6e6;
        border: 1px solid #ff9999;
        color: #cc0000;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .warning-message {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ==================== العنوان الرئيسي ====================
st.markdown("""
<div class="aramex-header">
    <div class="aramex-title">📊 نظام تحليل الشحنات المحدث</div>
    <div class="aramex-subtitle">تحليل شامل مع FDS (التسليم من أول محاولة مع SLA) والالتزام باتفاقيات الخدمة</div>
</div>
""", unsafe_allow_html=True)

# إضافة تنويه حول FDS
st.markdown("""
<div class="fds-highlight">
    <h4>🎯 FDS المحدث</h4>
    <p>FDS = الشحنات المُسلمة من أول محاولة + ضمن مدة SLA المحددة</p>
</div>
""", unsafe_allow_html=True)

# ==================== شريط التحكم ====================
col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 1])

with col1:
    if st.button("📤 رفع بيانات الشحنات", use_container_width=True, type="primary"):
        st.session_state.show_upload = not st.session_state.show_upload
        st.session_state.show_sla_upload = False

with col2:
    if st.button("📋 رفع اتفاقية SLA", use_container_width=True):
        st.session_state.show_sla_upload = not st.session_state.show_sla_upload
        st.session_state.show_upload = False

with col3:
    if st.button("🔄 تحديث البيانات", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

with col4:
    if has_aramex_data() and st.button("🗑️", use_container_width=True, help="مسح البيانات"):
        clear_aramex_data()
        if has_sla_data():
            clear_sla_data()
        st.rerun()

with col5:
    if has_aramex_data():
        saved_info = get_aramex_data()
        st.success(f"✓ {saved_info['total_rows']:,}")
    else:
        st.info("📊")

# ==================== منطقة رفع الملفات ====================
if st.session_state.show_upload or st.session_state.show_sla_upload:
    with st.container():
        if st.session_state.show_upload:
            st.markdown('<div class="upload-area">', unsafe_allow_html=True)
            uploaded_file = st.file_uploader(
                "اختر ملف بيانات الشحنات (Excel)",
                type=['xlsx', 'xls'],
                key="aramex_uploader",
                help="يدعم الملفات حتى 200,000 شحنة"
            )
            
            if uploaded_file:
                try:
                    with st.spinner("معالجة البيانات..."):
                        progress_bar = st.progress(0)
                        
                        progress_bar.progress(20)
                        excel_file = pd.ExcelFile(uploaded_file)
                        sheet_name = 'Detailed Data' if 'Detailed Data' in excel_file.sheet_names else excel_file.sheet_names[0]
                        
                        progress_bar.progress(40)
                        df = pd.read_excel(uploaded_file, sheet_name=sheet_name)
                        
                        progress_bar.progress(60)
                        df = df.dropna(how='all')
                        
                        progress_bar.progress(80)
                        df = process_aramex_data(df)
                        
                        progress_bar.progress(100)
                        save_aramex_data(df, "يدوي")
                        
                        progress_bar.empty()
                        
                        st.session_state.show_upload = False
                        st.success("✅ تم رفع البيانات بنجاح!")
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"خطأ في معالجة الملف: {str(e)}")
                    st.markdown("""
                    <div class="error-message">
                        <strong>تأكد من:</strong>
                        <ul>
                            <li>الملف في صيغة Excel (.xlsx أو .xls)</li>
                            <li>الملف يحتوي على البيانات المطلوبة</li>
                            <li>التواريخ في الملف بصيغة صحيحة</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
        elif st.session_state.show_sla_upload:
            st.markdown('<div class="upload-area">', unsafe_allow_html=True)
            uploaded_sla = st.file_uploader(
                "اختر ملف اتفاقية SLA (Excel)",
                type=['xlsx', 'xls'],
                key="sla_uploader",
                help="ملف يحتوي على أسماء المدن والأيام المستهدفة للتسليم"
            )
            
            if uploaded_sla:
                try:
                    with st.spinner("معالجة SLA..."):
                        sla_df = pd.read_excel(uploaded_sla)
                        sla_processed = process_sla_data(sla_df)
                        
                        if len(sla_processed) > 0:
                            save_sla_data(sla_processed, "يدوي")
                            st.session_state.show_sla_upload = False
                            st.success("✅ تم رفع اتفاقية SLA بنجاح!")
                            st.rerun()
                        else:
                            st.error("لم يتم العثور على بيانات صالحة في ملف SLA")
                            
                except Exception as e:
                    st.error(f"خطأ في معالجة ملف SLA: {str(e)}")
            st.markdown('</div>', unsafe_allow_html=True)

# ==================== التحليل الرئيسي ====================
if has_aramex_data():
    saved_data = get_aramex_data()
    df = saved_data['main_df']
    
    if len(df) == 0:
        st.error("الملف المرفوع فارغ أو لا يحتوي على بيانات صالحة")
        st.stop()
    
    # إضافة أعمدة SLA والـ FDS
    sla_data = None
    if has_sla_data():
        sla_info = get_sla_data()
        sla_data = sla_info['sla_df']
        st.info(f"📋 تم تحميل اتفاقية SLA: {len(sla_data)} مدينة")
    
    # إضافة حالات SLA والـ FDS
    df_with_sla = add_sla_and_fds_columns(df, sla_data)
    
    file_size_mb = len(df_with_sla) * len(df_with_sla.columns) * 8 / (1024 * 1024)
    st.info(f"📈 تم تحميل {len(df_with_sla):,} شحنة | الحجم: ~{file_size_mb:.1f} MB | آخر تحديث: {saved_data['save_time'].strftime('%Y-%m-%d %H:%M')}")
    
    if len(df_with_sla) > 50000:
        st.warning("⚠️ ملف كبير - قد تحتاج المعالجة وقتاً أطول")
    
    # فصل الشحنات المستثناة
    excluded_shipments = df_with_sla[df_with_sla['للاستثناء']] if 'للاستثناء' in df_with_sla.columns else pd.DataFrame()
    other_shipments = df_with_sla[df_with_sla['حالة_التسليم'] == 'أخرى'] if 'حالة_التسليم' in df_with_sla.columns else pd.DataFrame()
    lost_shipments = df_with_sla[df_with_sla['حالة_التسليم'] == 'استرجاع'] if 'حالة_التسليم' in df_with_sla.columns else pd.DataFrame()

    # تصفية البيانات الرئيسية
    df_filtered_main = df_with_sla[~df_with_sla['للاستثناء']] if 'للاستثناء' in df_with_sla.columns else df_with_sla.copy()

    # عرض إحصائيات المستثنيات إذا وجدت
    if len(excluded_shipments) > 0 or len(other_shipments) > 0 or len(lost_shipments) > 0:
        st.warning(f"⚠️ تم استثناء {len(excluded_shipments)} شحنة مرتجعة، {len(lost_shipments)} شحنة استرجاع، و {len(other_shipments)} شحنة بحالة أخرى من التحليل")

    # الفلاتر
    filter_col1, filter_col2, filter_col3 = st.columns([2, 2, 6])
    
    with filter_col1:
        cities = ['الكل'] + sorted(df_filtered_main['المدينة_الوجهة'].dropna().unique().tolist()) if 'المدينة_الوجهة' in df_filtered_main.columns else ['الكل']
        selected_city = st.selectbox("المدينة", cities, key="city_filter")
    
    with filter_col2:
        countries = ['الكل']
        if 'الدولة_الوجهة' in df_filtered_main.columns:
            countries += sorted(df_filtered_main['الدولة_الوجهة'].dropna().unique().tolist())
        selected_country = st.selectbox("الدولة", countries, key="country_filter")
    
    # تطبيق الفلاتر
    df_filtered = df_filtered_main.copy()
    if selected_city != 'الكل':
        df_filtered = df_filtered[df_filtered['المدينة_الوجهة'] == selected_city]
    if selected_country != 'الكل' and 'الدولة_الوجهة' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['الدولة_الوجهة'] == selected_country]
    
    # التحقق من وجود بيانات بعد الفلترة
    if len(df_filtered) == 0:
        st.warning("⚠️ لا توجد بيانات بعد تطبيق الفلاتر المحددة")
        st.stop()
    
    # حساب المؤشرات مع التحديثات
    total_shipments = len(df_filtered)
    delivered_shipments = len(df_filtered[df_filtered['حالة_التسليم'] == 'تم التسليم']) if 'حالة_التسليم' in df_filtered.columns else 0
    delivery_rate = (delivered_shipments / total_shipments * 100) if total_shipments > 0 else 0
    
    # FDS
    fds_count = len(df_filtered[df_filtered['مؤهل_FDS'] == True]) if 'مؤهل_FDS' in df_filtered.columns else 0
    fds_rate = (fds_count / total_shipments * 100) if total_shipments > 0 else 0
    
    # SLA Rate الإجمالي
    sla_compliant = df_filtered[df_filtered['ضمن_SLA'] == True] if 'ضمن_SLA' in df_filtered.columns else pd.DataFrame()
    sla_rate = (len(sla_compliant) / total_shipments * 100) if total_shipments > 0 else 0
    
    cities_analysis = analyze_cities_performance_enhanced(df_filtered)
    unique_cities = len(cities_analysis) if len(cities_analysis) > 0 else 0
    
    # عرض المؤشرات المحدثة (4 مؤشرات الآن)
    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card shipments">
            <div class="kpi-value">{total_shipments:,}</div>
            <div class="kpi-label">إجمالي الشحنات</div>
            <div class="kpi-delta" style="background: #e3f2fd; color: #1565c0;">مُحلل</div>
        </div>
        <div class="kpi-card delivered">
            <div class="kpi-value">{delivery_rate:.1f}%</div>
            <div class="kpi-label">معدل التسليم (DR)</div>
            <div class="kpi-delta" style="background: #e8f5e8; color: #2e7d32;">{delivered_shipments:,}</div>
        </div>
        <div class="kpi-card fds">
            <div class="kpi-value">{fds_rate:.1f}%</div>
            <div class="kpi-label">FDS (مع SLA)</div>
            <div class="kpi-delta" style="background: #e3f2fd; color: #1565c0;">{fds_count:,}</div>
        </div>
        <div class="kpi-card sla">
            <div class="kpi-value">{sla_rate:.1f}%</div>
            <div class="kpi-label">SLA Rate الإجمالي</div>
            <div class="kpi-delta" style="background: #f3e5f5; color: #7b1fa2;">{len(sla_compliant):,}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # الرسوم البيانية الأساسية
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<h3 class="chart-title">حالات الشحنات</h3>', unsafe_allow_html=True)
        
        if 'حالة_التسليم' in df_filtered.columns:
            status_counts = df_filtered['حالة_التسليم'].value_counts()
            
            if len(status_counts) > 0:
                fig_status = px.pie(
                    values=status_counts.values,
                    names=status_counts.index,
                    color_discrete_map={
                        'تم التسليم': '#4ecdc4',
                        'قيد التوصيل': '#f39c12',
                        'مرتجع': '#e74c3c',
                        'استرجاع': '#9b59b6',
                        'أخرى': '#95a5a6'
                    },
                    hole=0.4
                )
                
                fig_status.update_traces(
                    textposition='inside',
                    textinfo='percent+label',
                    textfont_size=12,
                    marker=dict(line=dict(color='#FFFFFF', width=2)),
                    texttemplate='%{label}<br>%{percent}'
                )
                
                fig_status.update_layout(
                    height=350,
                    font=dict(family="Cairo", size=12),
                    showlegend=False,
                    margin=dict(t=20, b=20, l=20, r=20)
                )
                
                st.plotly_chart(fig_status, use_container_width=True)
            else:
                st.info("لا توجد بيانات كافية لعرض مخطط حالات الشحنات بعد التصفية.")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<h3 class="chart-title">مؤشرات الأداء الرئيسية</h3>', unsafe_allow_html=True)
        
        analysis_data = {
            'DR': delivery_rate,
            'FDS': fds_rate,
            'SLA_Rate': sla_rate
        }
        
        performance_chart = create_fds_performance_chart(analysis_data)
        if performance_chart:
            st.plotly_chart(performance_chart, use_container_width=True)
        else:
            st.info("لا توجد بيانات كافية لعرض مؤشرات الأداء.")
        
        st.markdown('</div>', unsafe_allow_html=True)

    # عرض تفاصيل الحالات الأخرى (غير المصنفة)
    if 'حالة_التسليم' in df_filtered.columns:
        other_shipments_count = len(df_filtered[df_filtered['حالة_التسليم'] == 'أخرى'])
        
        if other_shipments_count > 0:
            st.warning(f"⚠️ يوجد {other_shipments_count:,} شحنة بحالات غير مصنفة - راجع التفاصيل أدناه")
            display_other_statuses_section(df_filtered)

    # تقرير الاتجاهات الأسبوعية المحدث
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown('<h3 class="chart-title">📈 اتجاه الأداء الأسبوعي</h3>', unsafe_allow_html=True)
    
    weekly_trends = analyze_weekly_trends_enhanced(df_filtered)
    
    if len(weekly_trends) > 0:
        weekly_chart = create_weekly_performance_chart(weekly_trends)
        if weekly_chart:
            st.plotly_chart(weekly_chart, use_container_width=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("📊 تحميل البيانات الأسبوعية (CSV)", use_container_width=True):
                csv_data = weekly_trends.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="💾 تحميل CSV",
                    data=csv_data,
                    file_name=f"weekly_performance_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        
        st.markdown("### 📋 جدول الأداء الأسبوعي")
        
        weekly_col1, weekly_col2 = st.columns(2)
        with weekly_col1:
            weeks_to_show = st.selectbox("عدد الأسابيع للعرض", [5, 10, 15, 20, "الكل"], index=1, key="weekly_rows_filter")
        
        with weekly_col2:
            sort_by = st.selectbox("ترتيب حسب", ["الأسبوع", "DR", "FDS", "SLA Rate"], key="weekly_sort")
        
        display_weekly = weekly_trends.copy()
        
        if sort_by == "الأسبوع":
            display_weekly = display_weekly.sort_values('تاريخ_البداية', ascending=False)
        elif sort_by == "DR":
            display_weekly = display_weekly.sort_values('DR', ascending=False)
        elif sort_by == "FDS":
            display_weekly = display_weekly.sort_values('FDS', ascending=False)
        elif sort_by == "SLA Rate":
            display_weekly = display_weekly.sort_values('SLA_Rate', ascending=False)
        
        if weeks_to_show != "الكل":
            display_weekly = display_weekly.head(int(weeks_to_show))
        
        # عرض الجدول الأسبوعي
        display_df = display_weekly[['الأسبوع', 'إجمالي_الشحنات', 'DR', 'FDS', 'SLA_Rate']].copy()
        display_df = display_df.rename(columns={
            'الأسبوع': 'الأسبوع',
            'إجمالي_الشحنات': 'إجمالي الشحنات',
            'DR': 'DR (%)',
            'FDS': 'FDS (%)',
            'SLA_Rate': 'SLA Rate (%)'
        })
        
        st.dataframe(display_df, use_container_width=True, height=400, hide_index=True)
        
        st.markdown("### 📊 ملخص الاتجاهات")
        trend_col1, trend_col2, trend_col3 = st.columns(3)
        
        if len(weekly_trends) >= 2:
            latest_week = weekly_trends.iloc[-1]
            previous_week = weekly_trends.iloc[-2]
            
            dr_change = latest_week['DR'] - previous_week['DR']
            fds_change = latest_week['FDS'] - previous_week['FDS']
            sla_change = latest_week['SLA_Rate'] - previous_week['SLA_Rate']
            
            with trend_col1:
                st.metric("DR", f"{latest_week['DR']:.1f}%", f"{dr_change:+.1f}%")
            with trend_col2:
                st.metric("FDS", f"{latest_week['FDS']:.1f}%", f"{fds_change:+.1f}%")
            with trend_col3:
                st.metric("SLA Rate", f"{latest_week['SLA_Rate']:.1f}%", f"{sla_change:+.1f}%")
        else:
            st.info("نحتاج لبيانات أسبوعين على الأقل لعرض الاتجاهات")
    else:
        st.markdown("""
        <div class="warning-message">
            <h4>ℹ️ لا توجد بيانات كافية لإنشاء التقرير الأسبوعي</h4>
            <p><strong>للحصول على تقرير أسبوعي تأكد من أن البيانات تغطي عدة أسابيع وأن التواريخ صحيحة.</strong></p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

    # عرض الشحنات المتأخرة
    display_delayed_shipments_section(df_filtered, sla_data)

    # تحليل المدن مع FDS
    if len(cities_analysis) > 0:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<h3 class="chart-title">🏙️ أداء المدن مع FDS</h3>', unsafe_allow_html=True)
        
        table_filter_col1, table_filter_col2 = st.columns(2)
        
        with table_filter_col1:
            table_cities = ['الكل'] + sorted(cities_analysis['المدينة'].tolist())
            selected_table_city = st.selectbox("ابحث عن مدينة", table_cities, key="table_city_filter")
        
        with table_filter_col2:
            rows_options = ['10', '20', '50', '100', 'الكل']
            selected_rows = st.selectbox("عدد الصفوف", rows_options, key="table_rows_filter", index=1)
        
        filtered_cities_analysis = cities_analysis.copy()
        
        if selected_table_city != 'الكل':
            filtered_cities_analysis = filtered_cities_analysis[filtered_cities_analysis['المدينة'] == selected_table_city]
        
        if selected_rows == 'الكل':
            display_cities = filtered_cities_analysis
        else:
            num_rows = int(selected_rows)
            display_cities = filtered_cities_analysis.head(num_rows)
        
        # إعادة تسمية الأعمدة للعرض
        display_cities_renamed = display_cities.copy()
        display_cities_renamed = display_cities_renamed.rename(columns={
            'المدينة': 'المدينة',
            'الدولة': 'الدولة',
            'إجمالي_الشحنات': 'إجمالي الشحنات',
            'SLA_أيام': 'SLA (أيام)',
            'DR': 'DR (%)',
            'FDS': 'FDS (%)',
            'SLA_Rate': 'SLA Rate (%)',
            'متوسط_الأيام': 'متوسط الأيام',
            'متوسط_المحاولات': 'متوسط المحاولات'
        })
        
        st.dataframe(display_cities_renamed, use_container_width=True, height=400, hide_index=True)
        
        # رسوم بيانية للمدن مع FDS
        city_col1, city_col2 = st.columns(2)
        
        with city_col1:
            if len(cities_analysis) > 0:
                top_cities_fds = cities_analysis.nlargest(8, 'FDS')
                
                if len(top_cities_fds) > 0:
                    fig_fds = px.bar(
                        x=top_cities_fds['FDS'],
                        y=top_cities_fds['المدينة'],
                        orientation='h',
                        text=[f'{x:.1f}%' for x in top_cities_fds['FDS']],
                        color_discrete_sequence=['#1f77b4'] * len(top_cities_fds),
                        title='🎯 أعلى 8 مدن FDS (مع SLA)'
                    )
                    
                    fig_fds.update_traces(
                        textposition='inside',
                        textfont_size=13,
                        textfont_color='white',
                        textfont_weight='bold'
                    )
                    
                    fig_fds.update_layout(
                        height=350,
                        font=dict(family='Cairo', size=11),
                        xaxis_title='FDS (%)',
                        yaxis_title='',
                        showlegend=False,
                        xaxis=dict(range=[0, 100]),
                        plot_bgcolor='rgba(248,249,250,0.8)',
                        paper_bgcolor='white'
                    )
                    
                    st.plotly_chart(fig_fds, use_container_width=True)
        
        with city_col2:
            if len(cities_analysis) > 0:
                top_cities_sla = cities_analysis.nlargest(8, 'SLA_Rate')
                
                if len(top_cities_sla) > 0:
                    fig_sla = px.bar(
                        x=top_cities_sla['SLA_Rate'],
                        y=top_cities_sla['المدينة'],
                        orientation='h',
                        text=[f'{x:.1f}%' for x in top_cities_sla['SLA_Rate']],
                        color_discrete_sequence=['#9467bd'] * len(top_cities_sla),
                        title='⏱️ أعلى 8 مدن SLA Rate'
                    )
                    
                    fig_sla.update_traces(
                        textposition='inside',
                        textfont_size=13,
                        textfont_color='white',
                        textfont_weight='bold'
                    )
                    
                    fig_sla.update_layout(
                        height=350,
                        font=dict(family='Cairo', size=11),
                        xaxis_title='SLA Rate (%)',
                        yaxis_title='',
                        showlegend=False,
                        xaxis=dict(range=[0, 100]),
                        plot_bgcolor='rgba(248,249,250,0.8)',
                        paper_bgcolor='white'
                    )
                    
                    st.plotly_chart(fig_sla, use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

else:
    # عرض رسالة عدم وجود بيانات
    st.markdown("""
    <div class="chart-container" style="text-align: center; padding: 3rem;">
        <h2 style="color: #ff6b6b;">لا توجد بيانات</h2>
        <p style="color: #7f8c8d;">اضغط على "رفع بيانات الشحنات" لتحميل البيانات</p>
        <p style="color: #7f8c8d;">ثم ارفع ملف SLA للاستفادة من FDS</p>
    </div>
    """, unsafe_allow_html=True)

# ==================== الشريط الجانبي ====================
add_logout_button()

with st.sidebar:
    st.markdown("### 📊 الحالة")
    
    if has_aramex_data():
        saved_info = get_aramex_data()
        st.success(f"✓ {saved_info['total_rows']:,} شحنة")
        
        if has_sla_data():
            sla_info = get_sla_data()
            st.info(f"✓ {sla_info['total_cities']} مدينة SLA")
        else:
            st.warning("⚠️ لا توجد بيانات SLA")
    else:
        st.warning("لا توجد بيانات")
    
    st.markdown("---")
    st.markdown("### 🎯 المميزات")
    st.info("🔵 FDS مع SLA") 
    st.info("📊 SLA Rate الإجمالي")
    st.info("📈 تقارير أسبوعية")
    st.info("🏙️ تحليل المدن")
    st.info("⏰ الشحنات المتأخرة")
    
    st.markdown("---")
    st.markdown("### 💡 نصائح الاستخدام")
    st.info("📝 ارفع ملف الشحنات أولاً")
    st.info("📋 ارفع ملف SLA للاستفادة الكاملة")
    st.info("🔄 حدث البيانات دورياً")
    st.info("📊 راجع FDS في التقارير")

# ==================== التذييل ====================
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #999; font-size: 0.8rem;">
    نظام تحليل الشحنات المحدث - Enhanced Shipment Analytics System v3.1<br>
    مع FDS (تسليم أول محاولة + ضمن SLA) و SLA Rate الإجمالي
</div>
""", unsafe_allow_html=True)
