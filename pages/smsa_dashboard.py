try:
    from auth_protection import check_authentication, add_logout_button
    if not check_authentication():
        st.stop()
except ImportError:
    st.error("❌ ملف الحماية غير موجود")
    st.stop()

#!/usr/bin/env python
# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import os
import matplotlib.pyplot as plt # Needed for background_gradient


# اعداد الصفحة
st.set_page_config(
    page_title="Samsa Analytics",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state
if 'show_upload' not in st.session_state:
    st.session_state.show_upload = False
if 'show_sla_upload' not in st.session_state:
    st.session_state.show_sla_upload = False

# دوال حفظ بيانات الاتفاقية SLA
def save_sla_data(df, source="manual"):
    st.session_state['sla_saved_data'] = {
        'sla_df': df,
        'save_time': datetime.now(),
        'source': source,
        'total_cities': len(df)
    }

def get_sla_data():
    return st.session_state.get('sla_saved_data', None)

def has_sla_data():
    saved_data = get_sla_data()
    return saved_data is not None and 'sla_df' in saved_data

def clear_sla_data():
    if 'sla_saved_data' in st.session_state:
        del st.session_state['sla_saved_data']

def process_sla_data(df):
    """معالجة بيانات SLA مع مرونة أكبر في اكتشاف الأعمدة"""
    try:
        if df.empty:
            st.error("❌ ملف SLA فارغ")
            return pd.DataFrame()
        
        df.columns = df.columns.str.strip()
        
        city_col = None
        days_col = None
        
        # البحث الذكي عن أعمدة المدينة والأيام
        for col in df.columns:
            col_lower = str(col).lower().strip()
            
            # البحث عن عمود المدينة
            if city_col is None:
                city_keywords = ['city', 'مدينة', 'destination', 'مدن', 'cities', 'location', 'موقع']
                if any(keyword in col_lower for keyword in city_keywords):
                    city_col = col
                    continue
            
            # البحث عن عمود الأيام/SLA
            if days_col is None:
                days_keywords = ['day', 'يوم', 'أيام', 'sla', 'target', 'days', 'هدف', 'ايام']
                if any(keyword in col_lower for keyword in days_keywords):
                    days_col = col
                    continue
        
        # إذا لم نجد الأعمدة بالكلمات المفتاحية، نستخدم أول عمودين
        if city_col is None or days_col is None:
            if len(df.columns) >= 2:
                city_col = df.columns[0]
                days_col = df.columns[1]
                st.info(f"تم استخدام العمودين: '{city_col}' للمدن و '{days_col}' للأيام")
        
        if city_col and days_col:
            try:
                # تنظيف أسماء المدن
                cities_clean = df[city_col].astype(str).str.strip()
                cities_clean = cities_clean.replace(['nan', 'NaN', 'None', ''], np.nan)
                
                # تنظيف الأيام
                days_clean = pd.to_numeric(df[days_col], errors='coerce')
                
                sla_clean = pd.DataFrame({
                    'المدينة': cities_clean,
                    'SLA_أيام': days_clean
                })
                
                # تنظيف البيانات
                sla_clean = sla_clean.dropna()
                sla_clean = sla_clean[sla_clean['المدينة'].str.len() > 0]
                sla_clean = sla_clean[sla_clean['SLA_أيام'] > 0]
                
                if len(sla_clean) == 0:
                    st.error("❌ لا توجد بيانات صالحة في ملف SLA بعد التنظيف")
                    return pd.DataFrame()
                
                st.success(f"✅ تم معالجة {len(sla_clean)} مدينة من ملف SLA")
                
                return sla_clean
                
            except Exception as process_error:
                st.error(f"خطأ في معالجة البيانات: {str(process_error)}")
                return pd.DataFrame()
        else:
            st.error("❌ لم يتم العثور على أعمدة المدينة والأيام في ملف SLA")
            st.info("تأكد من أن الملف يحتوي على عمودين: المدينة + عدد الأيام")
            st.info(f"الأعمدة الموجودة: {list(df.columns)}")
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"خطأ عام في معالجة ملف SLA: {str(e)}")
        return pd.DataFrame()

# دوال حفظ البيانات المحسنة لـ Samsa
def save_samsa_data(df, source="manual"):
    st.session_state['samsa_saved_data'] = {
        'main_df': df,
        'save_time': datetime.now(),
        'source': source,
        'total_rows': len(df),
        'total_columns': len(df.columns)
    }

def get_samsa_data():
    return st.session_state.get('samsa_saved_data', None)

def has_samsa_data():
    saved_data = get_samsa_data()
    return saved_data is not None and 'main_df' in saved_data

def clear_samsa_data():
    if 'samsa_saved_data' in st.session_state:
        del st.session_state['samsa_saved_data']

def update_sla_calculations(df):
    """إعادة حساب SLA بعد رفع ملف SLA"""
    try:
        if not has_sla_data():
            return df
        
        sla_info = get_sla_data()
        sla_df = sla_info['sla_df']
        
        if sla_df.empty:
            return df
        
        # إنشاء خريطة SLA
        sla_mapping = dict(zip(sla_df['المدينة'], sla_df['SLA_أيام']))
        
        # تطبيق SLA على البيانات الرئيسية
        if 'المدينة_الوجهة' in df.columns:
            df['SLA_أيام'] = df['المدينة_الوجهة'].map(sla_mapping)
        
        # إعادة حساب حالة SLA - باستخدام Creation date
        if 'تاريخ_الإنشاء' in df.columns and 'تاريخ_أول_محاولة' in df.columns:
            # إعادة حساب أيام المحاولة الأولى مع حساب الأيام الصحيح
            df['أيام_المحاولة_الأولى'] = (
                pd.to_datetime(df['تاريخ_أول_محاولة'].dt.date) - 
                pd.to_datetime(df['تاريخ_الإنشاء'].dt.date)
            ).dt.days
            df.loc[df['أيام_المحاولة_الأولى'] < 0, 'أيام_المحاولة_الأولى'] = np.nan
            
            # حساب حالة SLA
            def calculate_sla_status_safe(row):
                try:
                    if pd.isna(row.get('أيام_المحاولة_الأولى')) or pd.isna(row.get('SLA_أيام')):
                        return 'غير محدد'
                    elif row['أيام_المحاولة_الأولى'] < row['SLA_أيام']:
                        return 'قبل SLA'
                    elif row['أيام_المحاولة_الأولى'] == row['SLA_أيام']:
                        return 'في SLA'
                    else:
                        return 'بعد SLA'
                except:
                    return 'غير محدد'
            
            df['حالة_SLA_محاولة_أولى'] = df.apply(calculate_sla_status_safe, axis=1)
            
# إعادة حساب تسليم أول محاولة ضمن SLA
            if 'تاريخ_التسليم' in df.columns and 'حالة_التسليم' in df.columns:
                try:
                    # الشرط الأساسي: تسليم في نفس يوم المحاولة الأولى
                    df['تسليم_أول_محاولة_أساسي'] = (
                        (df['حالة_التسليم'] == 'تم التسليم') & 
                        (df['تاريخ_التسليم'].dt.date == df['تاريخ_أول_محاولة'].dt.date)
                    )
                    
                    # FDS الحقيقي: التسليم من أول محاولة + ضمن SLA
                    df['تسليم_أول_محاولة'] = (
                        df['تسليم_أول_محاولة_أساسي'] & 
                        df['حالة_SLA_محاولة_أولى'].isin(['قبل SLA', 'في SLA'])
                    )
                except:
                    df['تسليم_أول_محاولة'] = False
            else:
                df['تسليم_أول_محاولة'] = False        
        return df
        
    except Exception as e:
        st.error(f"خطأ في إعادة حساب SLA: {str(e)}")
        return df

@st.cache_data(show_spinner=False, max_entries=10)
def process_samsa_data(df):
    """معالجة بيانات Samsa بناءً على الأعمدة المحددة - مُحسّن للملف الحالي"""
    
    # إزالة الصفوف والأعمدة الفارغة تماماً
    df = df.dropna(how='all')
    df = df.dropna(axis=1, how='all')
    
    # البحث عن صف العناوين الصحيح
    header_row = 0
    max_search = min(20, len(df))
    
    for i in range(max_search):
        row_str = ' '.join(df.iloc[i].astype(str).str.lower())
        keywords_count = sum(1 for keyword in ['awb', 'reference', 'shipper', 'consignee', 'status', 'pickup', 'delivery']
                            if keyword in row_str)
        if keywords_count >= 2:
            header_row = i
            break
    
    # إعادة تعيين العناوين إذا لزم الأمر
    if header_row > 0:
        df.columns = df.iloc[header_row]
        df = df.iloc[header_row + 1:].reset_index(drop=True)
    
    # تنظيف أسماء الأعمدة
    df.columns = df.columns.astype(str).str.strip().str.replace('\n', ' ')
    
    # البحث الذكي عن الأعمدة - محسن للملف الحالي
    column_mapping = {}
    
    # البحث عن رقم الشحنة
    for col in df.columns:
        col_clean = str(col).strip()
        if any(keyword in col_clean for keyword in ['AWB', 'awb', 'Reference', 'reference', 'Tracking']):
            column_mapping[col] = 'رقم_الشحنة'
            break
    
    # البحث عن المدينة
    for col in df.columns:
        col_clean = str(col).strip()
        if any(keyword in col_clean for keyword in ['Consignee City', 'City', 'city']):
            column_mapping[col] = 'المدينة_الوجهة'
            break
    
    # البحث عن اسم المرسل
    for col in df.columns:
        col_clean = str(col).strip()
        if any(keyword in col_clean for keyword in ['Shipper Name', 'Shipper']):
            column_mapping[col] = 'اسم_المرسل'
            break
    
    # البحث عن اسم المستلم
    for col in df.columns:
        col_clean = str(col).strip()
        if any(keyword in col_clean for keyword in ['Consignee Name', 'Consignee']):
            column_mapping[col] = 'اسم_المستلم'
            break
    
    # البحث عن هاتف المستلم
    for col in df.columns:
        col_clean = str(col).strip()
        if any(keyword in col_clean for keyword in ['Consignee Phone', 'Phone']):
            column_mapping[col] = 'هاتف_المستلم'
            break
    
    # البحث عن العنوان
    for col in df.columns:
        col_clean = str(col).strip()
        if any(keyword in col_clean for keyword in ['Consignee Address', 'Address']):
            column_mapping[col] = 'عنوان_المستلم'
            break
    
    # البحث عن COD
    for col in df.columns:
        col_clean = str(col).strip()
        if col_clean == 'COD':
            column_mapping[col] = 'المبلغ_المستحق'
            break
    
    # البحث عن عدد القطع
    for col in df.columns:
        col_clean = str(col).strip()
        if col_clean == 'PCs':
            column_mapping[col] = 'عدد_القطع'
            break
    
    # البحث عن الوزن
    for col in df.columns:
        col_clean = str(col).strip()
        if 'Weight' in col_clean:
            column_mapping[col] = 'الوزن'
            break
    
    # البحث عن المحتويات
    for col in df.columns:
        col_clean = str(col).strip()
        if col_clean == 'Contents':
            column_mapping[col] = 'المحتويات'
            break
    
    # البحث عن التواريخ
    for col in df.columns:
        col_clean = str(col).strip()
        if col_clean == 'Creation date':
            column_mapping[col] = 'تاريخ_الإنشاء'
        elif col_clean == 'Pickup date':
            column_mapping[col] = 'تاريخ_الاستلام'
        elif col_clean == 'First attempt':
            column_mapping[col] = 'تاريخ_أول_محاولة'
        elif col_clean == 'Delivery date':
            column_mapping[col] = 'تاريخ_التسليم'
    
    # البحث عن الحالة
    for col in df.columns:
        col_clean = str(col).strip()
        if col_clean == 'Status':
            column_mapping[col] = 'الحالة'
            break
    
    # البحث عن الشركة 3PL
    for col in df.columns:
        col_clean = str(col).strip()
        if '3PL Company' in col_clean:
            column_mapping[col] = 'شركة_3PL'
            break
    
    # البحث عن المنطقة
    for col in df.columns:
        col_clean = str(col).strip()
        if col_clean == 'Region':
            column_mapping[col] = 'المنطقة'
            break
    
    # إعادة تسمية الأعمدة
    df = df.rename(columns=column_mapping)
    
    # معالجة التواريخ
    date_columns = ['تاريخ_الإنشاء', 'تاريخ_الاستلام', 'تاريخ_أول_محاولة', 'تاريخ_التسليم']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
    
    # معالجة الأرقام
    numeric_columns = ['المبلغ_المستحق', 'عدد_القطع', 'الوزن']
    for col in numeric_columns:
        if col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = pd.to_numeric(df[col], errors='coerce')
            else:
                temp_series = df[col].astype(str).str.replace(r'[^\d.-]', '', regex=True)
                temp_series = temp_series.str.replace('٫', '.', regex=False)
                df[col] = pd.to_numeric(temp_series, errors='coerce')
    
    # إعداد SLA - فقط إذا تم رفع ملف SLA
    sla_df_for_processing = pd.DataFrame()
    if has_sla_data():
        sla_info = get_sla_data()
        sla_df_for_processing = sla_info['sla_df']
    
    if 'تاريخ_الاستلام' in df.columns and 'تاريخ_أول_محاولة' in df.columns:
        df['أيام_المحاولة_الأولى'] = (
            pd.to_datetime(df['تاريخ_أول_محاولة'].dt.date) - 
            pd.to_datetime(df['تاريخ_الاستلام'].dt.date)
        ).dt.days
        df.loc[df['أيام_المحاولة_الأولى'] < 0, 'أيام_المحاولة_الأولى'] = np.nan
        
        # حساب حالة SLA للمحاولة الأولى - فقط إذا كان هناك ملف SLA
        if not sla_df_for_processing.empty and 'المدينة_الوجهة' in df.columns:
            # إنشاء خريطة SLA
            sla_mapping = dict(zip(sla_df_for_processing['المدينة'], sla_df_for_processing['SLA_أيام']))
            
            # تطبيق SLA على البيانات
            df['SLA_أيام'] = df['المدينة_الوجهة'].map(sla_mapping)
            
            # حساب حالة SLA للمحاولة الأولى
            def calculate_sla_status(row):
                if pd.isna(row['أيام_المحاولة_الأولى']) or pd.isna(row['SLA_أيام']):
                    return 'غير محدد'
                elif row['أيام_المحاولة_الأولى'] < row['SLA_أيام']:
                    return 'قبل SLA'
                elif row['أيام_المحاولة_الأولى'] == row['SLA_أيام']:
                    return 'في SLA'
                else:
                    return 'بعد SLA'
            
            df['حالة_SLA_محاولة_أولى'] = df.apply(calculate_sla_status, axis=1)
        else:
            # إذا لم يتم رفع ملف SLA، لا نحسب حالة SLA
            df['حالة_SLA_محاولة_أولى'] = 'غير محدد'
            df['SLA_أيام'] = np.nan
    
    # حساب أيام التوصيل مع حساب الأيام الصحيح - باستخدام Creation date
    if 'تاريخ_الإنشاء' in df.columns and 'تاريخ_التسليم' in df.columns:
        df['أيام_التوصيل'] = (
            pd.to_datetime(df['تاريخ_التسليم'].dt.date) - 
            pd.to_datetime(df['تاريخ_الإنشاء'].dt.date)
        ).dt.days
    df.loc[df['أيام_التوصيل'] < 0, 'أيام_التوصيل'] = np.nan
    
    # تحديد حالة التسليم
    if 'الحالة' in df.columns:
        status_str = df['الحالة'].astype(str).str.upper()
        
        # تحديد الشحنات المستثناة
        df['مستثنى'] = status_str.str.contains('PICKED UP|PICKUP|التقاط', na=False, regex=True)
        
        # تصنيف الحالات
        df['حالة_التسليم'] = np.select(
            [
                df['مستثنى'],
                status_str.str.contains('DELIVERED|RECEIVED|تم التسليم|مستلم|استلم|COMPLETE', na=False),
                status_str.str.contains('RETURN|مرتجع|رجع|ارجاع|REJECT|REFUSED|FAIL', na=False)
            ],
            ['مستثنى', 'تم التسليم', 'مرتجع'],
            default='قيد التوصيل'
        )
    else:
        df['مستثنى'] = False
        if 'تاريخ_التسليم' in df.columns:
            df['حالة_التسليم'] = df['تاريخ_التسليم'].apply(
                lambda x: 'تم التسليم' if pd.notna(x) else 'قيد التوصيل'
            )
        else:
            df['حالة_التسليم'] = 'قيد التوصيل'
    
    # إضافة رقم الأسبوع - باستخدام Creation date
    if 'تاريخ_الإنشاء' in df.columns:
        df['رقم_الأسبوع'] = df['تاريخ_الإنشاء'].dt.isocalendar().week
        df['الشهر'] = df['تاريخ_الإنشاء'].dt.month
        df['السنة'] = df['تاريخ_الإنشاء'].dt.year 
    # تحديد FDS (First Delivery Success) مع مقارنة التواريخ فقط
    if 'تاريخ_أول_محاولة' in df.columns and 'تاريخ_التسليم' in df.columns:
        try:
            # الشرط الأساسي: تم التسليم في نفس يوم المحاولة الأولى
            df['تسليم_أول_محاولة_أساسي'] = (
                (df['حالة_التسليم'] == 'تم التسليم') & 
                (df['تاريخ_التسليم'].dt.date == df['تاريخ_أول_محاولة'].dt.date)
            )
            
            # FDS الحقيقي: التسليم من أول محاولة + ضمن SLA
            if not sla_df_for_processing.empty and 'حالة_SLA_محاولة_أولى' in df.columns:
                df['تسليم_أول_محاولة'] = (
                    df['تسليم_أول_محاولة_أساسي'] & 
                    df['حالة_SLA_محاولة_أولى'].isin(['قبل SLA', 'في SLA'])
                )
            else:
                # إذا لم يكن هناك SLA، نستخدم الشرط الأساسي فقط
                df['تسليم_أول_محاولة'] = df['تسليم_أول_محاولة_أساسي']
        except:
            df['تسليم_أول_محاولة'] = False
    else:
        df['تسليم_أول_محاولة'] = False

    # استنتاج المنطقة من العنوان (أساسي)
    if 'عنوان_المستلم' in df.columns:
        df['المنطقة'] = df['عنوان_المستلم'].astype(str).str.extract(r'(\w+\s*\w*)', expand=False).fillna('غير محدد')
    elif 'المنطقة' not in df.columns:
        df['المنطقة'] = 'غير محدد'
    
    # التأكد من وجود رقم الشحنة
    if 'رقم_الشحنة' not in df.columns:
        # البحث عن أي عمود يحتوي على أرقام شحنات فريدة
        found_awb_column = False
        for col in df.columns:
            col_str = str(col).lower()
            # البحث عن كلمات مفتاحية لرقم الشحنة
            if any(keyword in col_str for keyword in ['awb', 'tracking', 'shipment', 'waybill', 'reference', 'number']):
                # التحقق من أن العمود يحتوي على قيم فريدة ومعقولة
                unique_ratio = df[col].nunique() / len(df)
                if unique_ratio > 0.8:  # 80% من القيم فريدة
                    df['رقم_الشحنة'] = df[col].astype(str).str.strip()
                    found_awb_column = True
                    break
        
        if not found_awb_column:
            # إذا لم نجد عمود مناسب، نستخدم الفهرس مع تحذير
            df['رقم_الشحنة'] = df.index.astype(str)
    
    return df

@st.cache_data(show_spinner=False)
def calculate_performance_metrics(df):
    """حساب مؤشرات الأداء الجديدة حسب المدينة - فقط إذا كان هناك SLA"""
    try:
        if 'المدينة_الوجهة' not in df.columns:
            return pd.DataFrame()
        
        # التحقق من وجود ملف SLA
        if not has_sla_data():
            return pd.DataFrame()
        
        # استثناء الشحنات المستثناة
        df_active = df[~df.get('مستثنى', False)]
        
        if len(df_active) == 0:
            return pd.DataFrame()
        
        # التحقق من وجود عمود SLA في البيانات
        if 'SLA_أيام' not in df_active.columns:
            return pd.DataFrame()
        
        metrics_list = []
        
        for city in df_active['المدينة_الوجهة'].unique():
            if pd.isna(city):
                continue
                
            city_df = df_active[df_active['المدينة_الوجهة'] == city]
            
            # فلترة المدن التي لها SLA محدد فقط
            city_df_with_sla = city_df[city_df['SLA_أيام'].notna()]
            
            if len(city_df_with_sla) == 0:
                continue
                
            total_shipments = len(city_df_with_sla)
            
            # حساب SLA نسبة (المحاولات في أو قبل SLA)
            sla_compliant = 0
            if 'حالة_SLA_محاولة_أولى' in city_df_with_sla.columns:
                sla_compliant = len(city_df_with_sla[
                    city_df_with_sla['حالة_SLA_محاولة_أولى'].isin(['قبل SLA', 'في SLA'])
                ])
            sla_rate = (sla_compliant / total_shipments * 100) if total_shipments > 0 else 0
            
            # حساب DR (معدل التسليم)
            delivered_count = len(city_df_with_sla[city_df_with_sla.get('حالة_التسليم', '') == 'تم التسليم'])
            dr = (delivered_count / total_shipments * 100) if total_shipments > 0 else 0
            
            # حساب FDS (نجاح التسليم من أول محاولة)
            # حساب FDS (نجاح التسليم من أول محاولة ضمن SLA)
            fds_count = 0
            if 'تسليم_أول_محاولة' in city_df_with_sla.columns:
                # FDS = التسليم من أول محاولة + ضمن SLA من إجمالي شحنات المدينة
                fds_count = len(city_df_with_sla[city_df_with_sla['تسليم_أول_محاولة'] == True])
            fds = (fds_count / total_shipments * 100) if total_shipments > 0 else 0
            # حساب Pending (الشحنات المعلقة)
            pending_count = len(city_df_with_sla[city_df_with_sla.get('حالة_التسليم', '') == 'قيد التوصيل'])
            pending_rate = (pending_count / total_shipments * 100) if total_shipments > 0 else 0
            
            # الحصول على المنطقة
            region = city_df_with_sla['المنطقة'].iloc[0] if 'المنطقة' in city_df_with_sla.columns and len(city_df_with_sla) > 0 else 'غير محدد'
            
            # رقم الأسبوع الأكثر شيوعاً
            week_number = 0
            if 'رقم_الأسبوع' in city_df_with_sla.columns:
                week_mode = city_df_with_sla['رقم_الأسبوع'].mode()
                if len(week_mode) > 0:
                    week_number = int(week_mode.iloc[0])
            
            # SLA المحدد لهذه المدينة
            city_sla = city_df_with_sla['SLA_أيام'].iloc[0]
            if pd.isna(city_sla):
                continue
            
            metrics_list.append({
                'المدينة': city,
                'المنطقة': region,
                'عدد_الشحنات': total_shipments,
                'SLA_المحدد': int(city_sla),
                'SLA_نسبة': round(sla_rate, 1),
                'DR': round(dr, 1),
                'FDS': round(fds, 1),
                'Pending': round(pending_rate, 1),
                'رقم_الأسبوع': week_number
            })
        
        return pd.DataFrame(metrics_list).sort_values('عدد_الشحنات', ascending=False)
        
    except Exception as e:
        st.error(f"خطأ في حساب مؤشرات الأداء: {str(e)}")
        return pd.DataFrame()

@st.cache_data(show_spinner=False)
def calculate_weekly_metrics(df):
    """حساب مؤشرات الأداء حسب الأسبوع"""
    if 'رقم_الأسبوع' not in df.columns:
        return pd.DataFrame()
    
    # استثناء الشحنات المستثناة
    df_active = df[~df.get('مستثنى', False)]
    
    if len(df_active) == 0:
        return pd.DataFrame()
    
    weekly_metrics = []
    
    for week in sorted(df_active['رقم_الأسبوع'].dropna().unique()):
        week_df = df_active[df_active['رقم_الأسبوع'] == week]
        total_shipments = len(week_df)
        
        if total_shipments == 0:
            continue
        
        # حساب المؤشرات للأسبوع
        sla_compliant = 0
        if 'حالة_SLA_محاولة_أولى' in week_df.columns:
            sla_compliant = len(week_df[
                week_df['حالة_SLA_محاولة_أولى'].isin(['قبل SLA', 'في SLA'])
            ])
        sla_rate = (sla_compliant / total_shipments * 100) if total_shipments > 0 else 0
        
        delivered_count = len(week_df[week_df['حالة_التسليم'] == 'تم التسليم'])
        dr = (delivered_count / total_shipments * 100) if total_shipments > 0 else 0
        
        fds_count = 0
        if 'تسليم_أول_محاولة' in week_df.columns:
            fds_count = len(week_df[week_df['تسليم_أول_محاولة'] == True])
        fds = (fds_count / total_shipments * 100) if total_shipments > 0 else 0
        
        pending_count = len(week_df[week_df['حالة_التسليم'] == 'قيد التوصيل'])
        pending_rate = (pending_count / total_shipments * 100) if total_shipments > 0 else 0
        
        weekly_metrics.append({
            'الأسبوع': int(week),
            'عدد_الشحنات': total_shipments,
            'SLA_نسبة': round(sla_rate, 1),
            'DR': round(dr, 1),
            'FDS': round(fds, 1),
            'Pending': round(pending_rate, 1)
        })
    
    return pd.DataFrame(weekly_metrics)

@st.cache_data(show_spinner=False)
def analyze_delivery_performance_fast(df):
    """تحليل أداء التوصيل لـ Samsa"""
    analysis = {}
    
    # استثناء الشحنات المستثناة من التحليل
    df_active = df[~df.get('مستثنى', False)]
    
    if 'حالة_التسليم' in df_active.columns:
        # حساب معدلات التسليم
        total = len(df_active)
        status_counts = df_active['حالة_التسليم'].value_counts()
        
        analysis['معدلات_الحالة'] = {}
        for status in ['تم التسليم', 'قيد التوصيل', 'مرتجع']:
            count = status_counts.get(status, 0)
            analysis['معدلات_الحالة'][status] = {
                'العدد': count,
                'النسبة': round(count/total*100, 1) if total > 0 else 0
            }
    
    return analysis

@st.cache_data(show_spinner=False)
def analyze_cities_performance_samsa(df, city_filter=None, country_filter=None):
    """تحليل أداء المدن لـ Samsa"""
    if 'المدينة_الوجهة' not in df.columns:
        return pd.DataFrame()
    
    # تطبيق الفلاتر
    df_filtered = df.copy()
    
    # استثناء الشحنات المستثناة
    df_filtered = df_filtered[~df_filtered.get('مستثنى', False)]
    
    if city_filter and city_filter != 'الكل':
        df_filtered = df_filtered[df_filtered['المدينة_الوجهة'] == city_filter]
    if country_filter and country_filter != 'الكل' and 'الدولة_الوجهة' in df.columns:
        df_filtered = df_filtered[df_filtered['الدولة_الوجهة'] == country_filter]
    
    if len(df_filtered) == 0:
        return pd.DataFrame()
    
    agg_dict = {'رقم_الشحنة': 'count'}
    
    if 'حالة_التسليم' in df_filtered.columns:
        df_filtered['تم_التسليم'] = (df_filtered['حالة_التسليم'] == 'تم التسليم').astype(int)
        agg_dict['تم_التسليم'] = 'sum'
    
    if 'أيام_التوصيل' in df_filtered.columns and 'حالة_التسليم' in df_filtered.columns:
        # حساب متوسط أيام التوصيل للشحنات المسلمة فقط
        delivered_mask = df_filtered['حالة_التسليم'] == 'تم التسليم'
        df_filtered['أيام_التوصيل_مسلم'] = df_filtered['أيام_التوصيل'].where(delivered_mask)
        agg_dict['أيام_التوصيل_مسلم'] = lambda x: x.dropna().mean()
    
    if 'أيام_المحاولة_الأولى' in df_filtered.columns:
        agg_dict['أيام_المحاولة_الأولى'] = lambda x: x.dropna().mean()
    
    # تجميع حسب المدينة
    city_analysis = df_filtered.groupby('المدينة_الوجهة', observed=True).agg(agg_dict)
    
    # إعادة تسمية الأعمدة
    rename_dict = {'رقم_الشحنة': 'عدد_الشحنات'}
    if 'تم_التسليم' in agg_dict:
        rename_dict['تم_التسليم'] = 'المسلم'
    if 'أيام_التوصيل_مسلم' in city_analysis.columns:
        rename_dict['أيام_التوصيل_مسلم'] = 'متوسط_أيام_للتوصيل'
    if 'أيام_المحاولة_الأولى' in city_analysis.columns:
        rename_dict['أيام_المحاولة_الأولى'] = 'متوسط_أيام_المحاولة_الأولى'
    
    city_analysis = city_analysis.rename(columns=rename_dict)
    
    # حساب نسبة التسليم
    if 'المسلم' in city_analysis.columns:
        city_analysis['نسبة_التسليم'] = (city_analysis['المسلم'] / city_analysis['عدد_الشحنات'] * 100).round(1)
    
    # تقريب القيم
    for col in ['متوسط_أيام_للتوصيل', 'متوسط_أيام_المحاولة_الأولى']:
        if col in city_analysis.columns:
            city_analysis[col] = city_analysis[col].round(1)
    
    return city_analysis.sort_values('عدد_الشحنات', ascending=False)

# CSS مخصص لـ Samsa
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700&display=swap');
    
    * {
        font-family: 'Cairo', sans-serif !important;
    }
    
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
    }
    
    .samsa-header {
        background: linear-gradient(135deg, #5f27cd, #341f97);
        padding: 1.5rem;
        border-radius: 15px;
        margin-bottom: 1rem;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    }
    
    .samsa-title {
        color: white;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .samsa-subtitle {
        color: #fff;
        font-size: 1rem;
        margin-top: 0.3rem;
        opacity: 0.9;
    }
    
    .upload-area {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #5f27cd;
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
        box-shadow: 0 2px 10px rgba(95, 39, 205, 0.15);
        text-align: center;
        border-left: 4px solid;
        transition: transform 0.2s ease;
    }
    
    .kpi-card:hover {
        transform: translateY(-3px);
    }
    
    .kpi-card.shipments { border-left-color: #5f27cd; }
    .kpi-card.delivered { border-left-color: #00d2d3; }
    .kpi-card.transit { border-left-color: #ff9ff3; }
    .kpi-card.cities { border-left-color: #feca57; }
    .kpi-card.excluded { border-left-color: #e74c3c; }
    
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
        box-shadow: 0 2px 10px rgba(95, 39, 205, 0.1);
        margin-bottom: 1.5rem;
        border-top: 3px solid #5f27cd;
    }
    
    .chart-title {
        color: #2c3e50;
        font-size: 1.2rem;
        font-weight: 700;
        margin-bottom: 1rem;
        text-align: center;
        border-bottom: 1px solid #5f27cd;
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
        border-color: #5f27cd !important;
    }
</style>
""", unsafe_allow_html=True)

# العنوان الرئيسي
st.markdown("""
<div class="samsa-header">
    <div class="samsa-title">Samsa Analytics</div>
    <div class="samsa-subtitle">تحليل شامل لبيانات شحنات سمسا - معالجة ذكية وسريعة - مُصحح للملف الحالي</div>
</div>
""", unsafe_allow_html=True)

# شريط التحكم المدمج
col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 1])

with col1:
    if st.button("📤 رفع Samsa", use_container_width=True, type="primary"):
        st.session_state.show_upload = not st.session_state.show_upload
        st.session_state.show_sla_upload = False

with col2:
    if st.button("📋 رفع SLA", use_container_width=True):
        st.session_state.show_sla_upload = not st.session_state.show_sla_upload
        st.session_state.show_upload = False

with col3:
    if st.button("🔄 إعادة حساب", use_container_width=True, help="إعادة حساب SLA بعد رفع ملف جديد"):
        if has_samsa_data() and has_sla_data():
            with st.spinner("إعادة حساب المؤشرات..."):
                saved_data = get_samsa_data()
                df_updated = update_sla_calculations(saved_data['main_df'])
                save_samsa_data(df_updated, "محدث_مع_SLA")
                st.success("✅ تم إعادة حساب المؤشرات!")
                st.rerun()
        else:
            st.warning("يجب رفع ملف Samsa و SLA أولاً")

with col4:
    if has_samsa_data() and st.button("🗑️", use_container_width=True, help="مسح البيانات"):
        clear_samsa_data()
        if has_sla_data():
            clear_sla_data()
        st.rerun()

with col5:
    # عرض حالة البيانات
    if has_samsa_data():
        saved_info = get_samsa_data()
        st.markdown(f"<p style='color: #28a745; text-align: center; font-size: 1.1rem; font-weight: bold;'>✓ {saved_info['total_rows']:,}</p>", unsafe_allow_html=True)
    else:
        st.markdown(f"<p style='color: #17a2b8; text-align: center; font-size: 1.1rem; font-weight: bold;'>📊</p>", unsafe_allow_html=True)

# منطقة رفع الملفات
if st.session_state.show_upload:
    st.markdown('<div class="upload-area">', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "اختر ملف Samsa Excel",
        type=['xlsx', 'xls', 'csv'],
        key="samsa_uploader",
        help="يدعم ملفات Excel و CSV مع الأعمدة المطلوبة"
    )
    
    # عرض قائمة الأعمدة المطلوبة
    with st.expander("📋 الأعمدة المطلوبة", expanded=False):
        st.markdown("""
        **الأعمدة الأساسية المطلوبة:**
        - `AWB` أو `Reference` - رقم الشحنة (مطلوب)
        - `Shipper Name` - اسم المرسل
        - `Consignee Name` - اسم المستلم  
        - `Consignee Phone` - هاتف المستلم
        - `Consignee City` - مدينة المستلم (مطلوب للـ SLA)
        - `Consignee Address` - عنوان المستلم
        - `COD` - المبلغ المستحق
        - `PCs` - عدد القطع
        - `Weight(KG)` - الوزن
        - `Contents` - المحتويات
        - `Creation date` - تاريخ الإنشاء
        - `Pickup date` - تاريخ الاستلام (مطلوب)
        - `First attempt` - تاريخ أول محاولة (مطلوب للـ SLA)
        - `Delivery date` - تاريخ التسليم
        - `Status` - الحالة (مطلوب)
        
        ⚠️ **مهم:** يجب أن تكون أسماء الأعمدة مطابقة تماماً للأسماء المذكورة أعلاه
        """)
    
    if uploaded_file:
        try:
            with st.spinner("معالجة البيانات..."):
                # قراءة الملف
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    try:
                        excel_file = pd.ExcelFile(uploaded_file)
                        target_sheet = None
                        for sheet in excel_file.sheet_names:
                            sheet_lower = sheet.lower()
                            if any(keyword in sheet_lower for keyword in 
                                   ['data', 'detail', 'بيانات', 'تفاصيل', 'shipment', 'شحنات']):
                                target_sheet = sheet
                                break
                        
                        if target_sheet:
                            df = pd.read_excel(uploaded_file, sheet_name=target_sheet)
                        else:
                            df = pd.read_excel(uploaded_file, sheet_name=0)
                    except:
                        df = pd.read_excel(uploaded_file)
                
                # معالجة البيانات
                df_processed = process_samsa_data(df)
                
                save_samsa_data(df_processed, "يدوي")
                st.session_state.show_upload = False
                st.success("✅ تم رفع ملف البيانات بنجاح!")
                st.rerun()
                
        except Exception as e:
            st.error(f"خطأ في معالجة الملف: {str(e)}")
    st.markdown('</div>', unsafe_allow_html=True)

if st.session_state.show_sla_upload:
    st.markdown('<div class="upload-area">', unsafe_allow_html=True)
    uploaded_sla = st.file_uploader(
        "اختر ملف SLA Excel",
        type=['xlsx', 'xls'],
        key="sla_uploader"
    )
    
    if uploaded_sla:
        try:
            with st.spinner("معالجة SLA..."):
                # قراءة الملف مع معلومات تشخيصية
                sla_df = pd.read_excel(uploaded_sla)
                
                # معالجة البيانات
                sla_processed = process_sla_data(sla_df)
                
                if len(sla_processed) > 0:
                    save_sla_data(sla_processed, "يدوي")
                    
                    # إعادة حساب SLA في البيانات الموجودة
                    if has_samsa_data():
                        saved_data = get_samsa_data()
                        df_current = saved_data['main_df']
                        df_updated = update_sla_calculations(df_current)
                        save_samsa_data(df_updated, "محدث_مع_SLA")
                    
                    st.session_state.show_sla_upload = False
                    st.success("✅ تم رفع ملف SLA وإعادة حساب المؤشرات!")
                    st.rerun()
                else:
                    st.error("❌ لم يتم العثور على بيانات صالحة في ملف SLA")
                    
        except Exception as e:
            st.error(f"خطأ: {str(e)}")
    st.markdown('</div>', unsafe_allow_html=True)

# بقية الكود يتبع نفس الهيكل الأصلي
if has_samsa_data():
    saved_data = get_samsa_data()
    df = saved_data['main_df']
    
    # عرض عينة من البيانات
    with st.expander("عرض عينة من البيانات المعالجة", expanded=False):
        display_columns = ['رقم_الشحنة', 'المدينة_الوجهة', 'حالة_التسليم']
        if has_sla_data():
            display_columns.extend(['SLA_أيام', 'حالة_SLA_محاولة_أولى'])
        
        available_display_columns = [col for col in display_columns if col in df.columns]
        st.dataframe(df[available_display_columns].head(10), use_container_width=True)
    
    # الفلاتر - مُحسن
    st.markdown("### 🔍 الفلاتر")
    filter_col1, filter_col2, filter_col3 = st.columns([3, 3, 6])
    
    with filter_col1:
        # البحث عن المدينة مع قائمة منسدلة
        all_cities = []
        if 'المدينة_الوجهة' in df.columns:
            all_cities = sorted([city for city in df['المدينة_الوجهة'].dropna().unique() if str(city).strip()])
        
        if all_cities:
            selected_city = st.selectbox(
                "اختر المدينة:",
                ['الكل'] + all_cities,
                key="main_city_filter",
                help="اختر مدينة محددة للتصفية"
            )
        else:
            selected_city = 'الكل'
            st.selectbox(
                "اختر المدينة:",
                ['الكل'],
                key="main_city_filter_empty",
                help="لا توجد مدن متاحة"
            )

    with filter_col2:
        countries = ['الكل']
        if 'الدولة_الوجهة' in df.columns:
            countries += sorted([country for country in df['الدولة_الوجهة'].dropna().unique() if str(country).strip()])
        selected_country = st.selectbox("الدولة", countries, key="country_filter")
    
    # تطبيق الفلاتر
    df_filtered = df.copy()
    
    if selected_city != 'الكل':
        df_filtered = df_filtered[df_filtered['المدينة_الوجهة'] == selected_city]
    
    if selected_country != 'الكل' and 'الدولة_الوجهة' in df.columns:
        df_filtered = df_filtered[df_filtered['الدولة_الوجهة'] == selected_country]
    
    # حساب المؤشرات
    total_all = len(df_filtered)
    excluded_shipments = len(df_filtered[df_filtered.get('مستثنى', False)])
    total_shipments = total_all - excluded_shipments
    
    # فلترة الشحنات النشطة للحسابات
    df_active = df_filtered[~df_filtered.get('مستثنى', False)]
    
    delivered_shipments = len(df_active[df_active['حالة_التسليم'] == 'تم التسليم']) if 'حالة_التسليم' in df_active.columns else 0
    delivery_rate = (delivered_shipments / total_shipments * 100) if total_shipments > 0 else 0
    
    # تحليل الأداء
    performance_analysis = analyze_delivery_performance_fast(df_filtered)
    
    # تحليل المدن
    cities_analysis = analyze_cities_performance_samsa(df_filtered)
    unique_cities = len(cities_analysis) if len(cities_analysis) > 0 else 0
    
    # حساب المؤشرات الجديدة - فقط إذا كان هناك ملف SLA
    sla_compliant_shipments = 0
    fds_shipments = 0
    sla_rate = 0
    fds_rate = 0
    
    if has_sla_data() and 'حالة_SLA_محاولة_أولى' in df_active.columns:
        # فلترة الشحنات التي لها SLA محدد فقط
        df_with_sla = df_active[df_active['SLA_أيام'].notna()]
        total_sla_shipments = len(df_with_sla)
        
        if total_sla_shipments > 0:
            sla_compliant_shipments = len(df_with_sla[
                df_with_sla['حالة_SLA_محاولة_أولى'].isin(['قبل SLA', 'في SLA'])
            ])
            sla_rate = (sla_compliant_shipments / total_sla_shipments * 100)
            
            if 'تسليم_أول_محاولة' in df_with_sla.columns:
                fds_shipments = len(df_with_sla[df_with_sla['تسليم_أول_محاولة'] == True])
                fds_rate = (fds_shipments / total_sla_shipments * 100)
    
    # عرض المؤشرات المحدثة
    sla_label = "SLA نسبة" if has_sla_data() else "SLA غير متوفر"
    sla_delta_text = f"{sla_compliant_shipments:,}" if has_sla_data() else "ارفع ملف SLA"
    sla_delta_color = "#ff6fb3" if has_sla_data() else "#95a5a6"
    
    fds_label = "FDS - تسليم أول محاولة ضمن SLA" if has_sla_data() else "FDS غير متوفر"
    fds_delta_text = f"{fds_shipments:,}" if has_sla_data() else "ارفع ملف SLA"
    fds_delta_color = "#f39c12" if has_sla_data() else "#95a5a6"
    
    # عرض المؤشرات المحدثة
    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card shipments">
            <div class="kpi-value">{total_shipments:,}</div>
            <div class="kpi-label">الشحنات النشطة</div>
            <div class="kpi-delta" style="background: #e8e2ff; color: #5f27cd;">Samsa</div>
        </div>
        <div class="kpi-card delivered">
            <div class="kpi-value">{delivery_rate:.1f}%</div>
            <div class="kpi-label">DR - معدل التسليم</div>
            <div class="kpi-delta" style="background: #e0f9f9; color: #00a8a8;">{delivered_shipments:,}</div>
        </div>
        <div class="kpi-card transit">
            <div class="kpi-value">{sla_rate:.1f}%</div>
            <div class="kpi-label">{sla_label}</div>
            <div class="kpi-delta" style="background: #ffe0f3; color: {sla_delta_color};">{sla_delta_text}</div>
        </div>
        <div class="kpi-card cities">
            <div class="kpi-value">{fds_rate:.1f}%</div>
            <div class="kpi-label">{fds_label}</div>
            <div class="kpi-delta" style="background: #fef4e0; color: {fds_delta_color};">{fds_delta_text}</div>
        </div>
        <div class="kpi-card excluded">
            <div class="kpi-value">{excluded_shipments:,}</div>
            <div class="kpi-label">مستثنى</div>
            <div class="kpi-delta" style="background: #ffe0e0; color: #e74c3c;">Picked up</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # --- جدول مؤشرات الأداء الجديد - فقط إذا تم رفع ملف SLA ---
    performance_metrics = calculate_performance_metrics(df_filtered)
    
    if len(performance_metrics) > 0 and has_sla_data():
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<h3 class="chart-title">مؤشرات الأداء حسب المدن (الجدول المطلوب)</h3>', unsafe_allow_html=True)
        
        # فلاتر الجدول الجديد
        perf_col1, perf_col2 = st.columns([3, 1])
        with perf_col1:
            search_perf_city = st.text_input("ابحث عن مدينة (مؤشرات الأداء)", key="search_perf_city")
        with perf_col2:
            num_rows_perf = st.selectbox(
                "عدد الصفوف",
                [10, 25, 50, "الكل"],
                key="num_rows_perf"
            )
        
        filtered_perf = performance_metrics.copy()
        if search_perf_city:
            filtered_perf = filtered_perf[
                filtered_perf['المدينة'].str.contains(search_perf_city, case=False, na=False)
            ]
        
        if num_rows_perf != "الكل":
            display_perf = filtered_perf.head(num_rows_perf)
        else:
            display_perf = filtered_perf
        
        # تنسيق الجدول
        format_dict_perf = {
            'SLA_المحدد': '{:.0f} يوم',
            'SLA_نسبة': '{:.1f}%',
            'DR': '{:.1f}%',
            'FDS': '{:.1f}%',
            'Pending': '{:.1f}%',
            'عدد_الشحنات': '{:,.0f}'
        }
        
        # دالة التلوين
        def color_performance_metric(val, good_threshold=80, bad_threshold=60):
            if pd.isna(val):
                return ''
            if val >= good_threshold:
                return 'background-color: #d4f4dd; color: #155724; font-weight: bold;'
            elif val <= bad_threshold:
                return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
            else:
                return 'background-color: #fff3cd; color: #856404; font-weight: bold;'
        
        def color_pending_metric(val, good_threshold=20, bad_threshold=40):
            if pd.isna(val):
                return ''
            if val <= good_threshold:
                return 'background-color: #d4f4dd; color: #155724; font-weight: bold;'
            elif val >= bad_threshold:
                return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
            else:
                return 'background-color: #fff3cd; color: #856404; font-weight: bold;'
        
        styled_perf = display_perf.style.format(format_dict_perf, na_rep='-')
        
        # تطبيق التنسيق
        for col in ['SLA_نسبة', 'DR', 'FDS']:
            if col in display_perf.columns:
                styled_perf = styled_perf.applymap(color_performance_metric, subset=[col])
        
        if 'Pending' in display_perf.columns:
            styled_perf = styled_perf.applymap(color_pending_metric, subset=['Pending'])
        
        st.dataframe(styled_perf, use_container_width=True, height=500)
        
        # تحميل البيانات
        csv_perf = display_perf.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 تحميل مؤشرات الأداء (CSV)",
            data=csv_perf,
            file_name=f"samsa_performance_metrics_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # رسالة عندما لا يوجد ملف SLA
    if not has_sla_data():
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<h3 class="chart-title">مؤشرات الأداء حسب المدن</h3>', unsafe_allow_html=True)
        st.warning("⚠️ **لحساب مؤشرات SLA و FDS، يرجى رفع ملف SLA أولاً**")
        st.info("📋 اضغط على زر 'رفع SLA' في الأعلى لتحميل ملف يحتوي على المدن والأيام المحددة لكل مدينة")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # --- تحليل الأسابيع ---
    weekly_metrics = calculate_weekly_metrics(df_filtered)
    
    if len(weekly_metrics) > 0:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<h3 class="chart-title">تحليل الأداء حسب الأسابيع</h3>', unsafe_allow_html=True)
        
        # جدول الأسابيع
        st.markdown("#### 📊 مؤشرات الأداء الأسبوعية")
        
        format_dict_weekly = {
            'SLA_نسبة': '{:.1f}%',
            'DR': '{:.1f}%',
            'FDS': '{:.1f}%',
            'Pending': '{:.1f}%',
            'عدد_الشحنات': '{:,.0f}'
        }
        
        def color_performance_metric_weekly(val, good_threshold=80, bad_threshold=60):
            if pd.isna(val):
                return ''
            if val >= good_threshold:
                return 'background-color: #d4f4dd; color: #155724; font-weight: bold;'
            elif val <= bad_threshold:
                return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
            else:
                return 'background-color: #fff3cd; color: #856404; font-weight: bold;'
        
        def color_pending_metric_weekly(val, good_threshold=20, bad_threshold=40):
            if pd.isna(val):
                return ''
            if val <= good_threshold:
                return 'background-color: #d4f4dd; color: #155724; font-weight: bold;'
            elif val >= bad_threshold:
                return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
            else:
                return 'background-color: #fff3cd; color: #856404; font-weight: bold;'
        
        styled_weekly = weekly_metrics.style.format(format_dict_weekly, na_rep='-')
        
        # تطبيق التنسيق للأسابيع
        for col in ['SLA_نسبة', 'DR', 'FDS']:
            if col in weekly_metrics.columns:
                styled_weekly = styled_weekly.applymap(color_performance_metric_weekly, subset=[col])
        
        if 'Pending' in weekly_metrics.columns:
            styled_weekly = styled_weekly.applymap(color_pending_metric_weekly, subset=['Pending'])
        
        st.dataframe(styled_weekly, use_container_width=True, height=300)
        
        # مخطط اتجاه الأسابيع
        st.markdown("#### 📈 اتجاه الأداء الأسبوعي")
        
        fig_weekly_trend = go.Figure()
        
        # إضافة خطوط المؤشرات
        for metric, color in [('SLA_نسبة', '#5f27cd'), ('DR', '#00d2d3'), ('FDS', '#ff9ff3'), ('Pending', '#ee5a6f')]:
            if metric in weekly_metrics.columns:
                fig_weekly_trend.add_trace(go.Scatter(
                    x=weekly_metrics['الأسبوع'],
                    y=weekly_metrics[metric],
                    mode='lines+markers',
                    name=metric,
                    line=dict(color=color, width=3),
                    marker=dict(size=8)
                ))
        
        fig_weekly_trend.update_layout(
            title='اتجاه مؤشرات الأداء عبر الأسابيع',
            xaxis_title='رقم الأسبوع',
            yaxis_title='النسبة المئوية (%)',
            height=400,
            font=dict(family='Cairo', size=12),
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_weekly_trend, use_container_width=True)
        
        # تحميل بيانات الأسابيع
        csv_weekly = weekly_metrics.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 تحميل البيانات الأسبوعية (CSV)",
            data=csv_weekly,
            file_name=f"samsa_weekly_metrics_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # --- قسم تفاصيل الشحنات الفردية بالتنسيق المطلوب ---
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown('<h3 class="chart-title">تفاصيل الشحنات الفردية (التقرير النهائي المطلوب)</h3>', unsafe_allow_html=True)
    
    # فلاتر قسم الشحنات الفردية
    detail_col1, detail_col2, detail_col3 = st.columns(3)
    
    with detail_col1:
        status_filter = st.selectbox(
            "فلتر الحالة",
            ["الكل", "تم التسليم", "قيد التوصيل", "مرتجع"],
            key="status_filter_detail"
        )
    
    with detail_col2:
        sla_filter = st.selectbox(
            "فلتر SLA",
            ["الكل", "قبل SLA", "في SLA", "بعد SLA", "غير محدد"],
            key="sla_filter_detail"
        )
    
    with detail_col3:
        num_rows_detail = st.selectbox(
            "عدد الصفوف",
            [50, 100, 200, 500, "الكل"],
            key="num_rows_detail"
        )
    
    # تطبيق الفلاتر
    detail_df = df_active.copy()
    
    if status_filter != "الكل":
        detail_df = detail_df[detail_df['حالة_التسليم'] == status_filter]
    
    if sla_filter != "الكل" and 'حالة_SLA_محاولة_أولى' in detail_df.columns:
        detail_df = detail_df[detail_df['حالة_SLA_محاولة_أولى'] == sla_filter]
    
    # ترتيب البيانات حسب تاريخ الاستلام
    if 'تاريخ_الاستلام' in detail_df.columns:
        detail_df = detail_df.sort_values('تاريخ_الاستلام', ascending=False)
    
    # تحديد عدد الصفوف للعرض
    if num_rows_detail != "الكل":
        display_detail_df = detail_df.head(num_rows_detail)
    else:
        display_detail_df = detail_df
    
    if len(display_detail_df) > 0:
        # إنشاء الجدول بالتنسيق المطلوب
        final_report_columns = [
            'رقم_الشحنة', 'المدينة_الوجهة', 'المنطقة', 
            'حالة_SLA_محاولة_أولى', 'حالة_التسليم',
            'تاريخ_الاستلام', 'تاريخ_أول_محاولة', 'تاريخ_التسليم',
            'رقم_الأسبوع'
        ]
        
        # إضافة الأعمدة الإضافية إذا كانت متوفرة
        additional_columns = [
            'اسم_المرسل', 'اسم_المستلم', 'هاتف_المستلم', 
            'عنوان_المستلم', 'المبلغ_المستحق', 'عدد_القطع', 
            'الوزن', 'المحتويات'
        ]
        
        for col in additional_columns:
            if col in display_detail_df.columns:
                final_report_columns.append(col)
        
        # فلترة الأعمدة الموجودة
        available_columns = [col for col in final_report_columns if col in display_detail_df.columns]
        final_display_df = display_detail_df[available_columns].copy()
        
        st.markdown(f"### 📋 عرض {len(final_display_df):,} شحنة")
        
        # تنسيق العرض
        format_dict_detail = {}
        if 'المبلغ_المستحق' in final_display_df.columns:
            format_dict_detail['المبلغ_المستحق'] = '{:.2f}'
        if 'الوزن' in final_display_df.columns:
            format_dict_detail['الوزن'] = '{:.2f}'
        if 'عدد_القطع' in final_display_df.columns:
            format_dict_detail['عدد_القطع'] = '{:.0f}'
        
        # دالة التلوين للحالة SLA
        def style_sla_status_detail(val):
            if val == 'قبل SLA':
                return 'background-color: #d4edda; color: #155724; font-weight: bold;'
            elif val == 'في SLA':
                return 'background-color: #d1ecf1; color: #0c5460; font-weight: bold;'
            elif val == 'بعد SLA':
                return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
            else:
                return 'background-color: #f8f9fa; color: #6c757d;'
        
        # دالة التلوين لحالة التسليم
        def style_delivery_status(val):
            if val == 'تم التسليم':
                return 'background-color: #d4edda; color: #155724; font-weight: bold;'
            elif val == 'قيد التوصيل':
                return 'background-color: #fff3cd; color: #856404; font-weight: bold;'
            elif val == 'مرتجع':
                return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
            else:
                return ''
        
        # تطبيق التنسيق
        styled_detail_df = final_display_df.style.format(format_dict_detail, na_rep='-')
        
        if 'حالة_SLA_محاولة_أولى' in final_display_df.columns:
            styled_detail_df = styled_detail_df.applymap(
                style_sla_status_detail, 
                subset=['حالة_SLA_محاولة_أولى']
            )
        
        if 'حالة_التسليم' in final_display_df.columns:
            styled_detail_df = styled_detail_df.applymap(
                style_delivery_status, 
                subset=['حالة_التسليم']
            )
        
        # عرض الجدول
        st.dataframe(styled_detail_df, use_container_width=True, height=600)
        
        # زر التحميل للتقرير النهائي
        csv_final = final_display_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 تحميل التقرير النهائي (CSV)",
            data=csv_final,
            file_name=f"samsa_final_report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            help="التقرير الشامل بجميع الحقول والمؤشرات المطلوبة"
        )
    else:
        st.info("لا توجد شحنات تطابق معايير البحث المحددة")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # الرسوم البيانية الأصلية
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<h3 class="chart-title">حالات الشحنات</h3>', unsafe_allow_html=True)
        
        if 'حالة_التسليم' in df_active.columns:
            status_counts = df_active['حالة_التسليم'].value_counts()
            
            main_statuses = ['تم التسليم', 'قيد التوصيل', 'مرتجع']
            for status in main_statuses:
                if status not in status_counts.index:
                    status_counts[status] = 0
            
            status_counts = status_counts.reindex(main_statuses, fill_value=0)
            status_counts = status_counts[status_counts > 0]
            
            fig_status = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                color_discrete_map={
                    'تم التسليم': '#00d2d3',
                    'قيد التوصيل': '#ff9ff3',
                    'مرتجع': '#ee5a6f'
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
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<h3 class="chart-title">توزيع المحاولات الأولى حسب SLA</h3>', unsafe_allow_html=True)
        
        if 'حالة_SLA_محاولة_أولى' in df_active.columns:
            sla_attempt_counts = df_active['حالة_SLA_محاولة_أولى'].value_counts()
            
            fig_sla_attempts = go.Figure()
            
            colors = {'قبل SLA': '#00d2d3', 'في SLA': '#5f27cd', 'بعد SLA': '#ee5a6f', 'غير محدد': '#95a5a6'}
            
            for i, (category, count) in enumerate(sla_attempt_counts.items()):
                percentage = (count / len(df_active) * 100)
                fig_sla_attempts.add_trace(go.Bar(
                    x=[category],
                    y=[count],
                    text=[f'{count} ({percentage:.1f}%)'],
                    textposition='outside',
                    marker_color=colors.get(category, '#95a5a6'),
                    showlegend=False,
                    textfont=dict(size=12, color='#2D3748')
                ))
            
            fig_sla_attempts.update_layout(
                height=350,
                font=dict(family="Cairo", size=12),
                xaxis_title="حالة SLA",
                yaxis_title="عدد الشحنات",
                showlegend=False,
                margin=dict(t=30, b=50, l=50, r=20),
                bargap=0.2,
                plot_bgcolor='white',
                yaxis=dict(gridcolor='#E2E8F0', gridwidth=1)
            )
            
            st.plotly_chart(fig_sla_attempts, use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # تحليل المدن الأصلي
    if len(cities_analysis) > 0:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<h3 class="chart-title">أداء المدن (التحليل التقليدي)</h3>', unsafe_allow_html=True)
        
        # فلاتر جدول أداء المدن
        city_table_col1, city_table_col2 = st.columns([3,1])
        with city_table_col1:
            search_city_table = st.text_input("ابحث عن مدينة (أداء المدن)", key="search_city_table")
        with city_table_col2:
            num_rows_cities = st.selectbox(
                "عدد الصفوف",
                [10, 25, 50, "الكل"],
                key="num_rows_cities"
            )
        
        filtered_cities_analysis = cities_analysis.copy()
        if search_city_table:
            filtered_cities_analysis = filtered_cities_analysis[
                filtered_cities_analysis.index.str.contains(search_city_table, case=False, na=False)
            ]
        
        if num_rows_cities != "الكل":
            display_cities_table = filtered_cities_analysis.head(num_rows_cities).reset_index()
        else:
            display_cities_table = filtered_cities_analysis.reset_index()
        
        # تحديد الأعمدة المتاحة للعرض
        display_columns = ['المدينة_الوجهة', 'عدد_الشحنات']
        format_dict = {}
        
        if 'نسبة_التسليم' in display_cities_table.columns:
            display_columns.append('نسبة_التسليم')
            format_dict['نسبة_التسليم'] = '{:.1f}%'
        
        if 'متوسط_أيام_للتوصيل' in display_cities_table.columns:
            display_columns.append('متوسط_أيام_للتوصيل')
            format_dict['متوسط_أيام_للتوصيل'] = '{:.1f}'
        
        if 'متوسط_أيام_المحاولة_الأولى' in display_cities_table.columns:
            display_columns.append('متوسط_أيام_المحاولة_الأولى')
            format_dict['متوسط_أيام_المحاولة_الأولى'] = '{:.1f}'
        
        # تنسيق الجدول
        styled_df = display_cities_table[display_columns].style.format(format_dict, na_rep='-')
        
        if 'نسبة_التسليم' in display_columns:
            styled_df = styled_df.background_gradient(
                subset=['نسبة_التسليم'],
                cmap='Greens',
                vmin=70,
                vmax=100
            ).set_properties(**{'font-weight': 'bold'}, subset=['نسبة_التسليم'])
        
        if 'متوسط_أيام_للتوصيل' in display_columns:
             styled_df = styled_df.background_gradient(
                subset=['متوسط_أيام_للتوصيل'],
                cmap='Reds_r',
                vmin=0,
                vmax=5
            ).set_properties(**{'font-weight': 'bold'}, subset=['متوسط_أيام_للتوصيل'])
        
        if 'متوسط_أيام_المحاولة_الأولى' in display_columns:
             styled_df = styled_df.background_gradient(
                subset=['متوسط_أيام_المحاولة_الأولى'],
                cmap='Reds_r',
                vmin=0,
                vmax=5
            ).set_properties(**{'font-weight': 'bold'}, subset=['متوسط_أيام_المحاولة_الأولى'])

        st.dataframe(styled_df, use_container_width=True, height=400)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # --- قسم البيانات غير المطابقة ---
    if has_samsa_data():
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<h3 class="chart-title">🔍 البيانات غير المطابقة مع SLA</h3>', unsafe_allow_html=True)
        
        # فحص البيانات غير المطابقة
        if has_sla_data():
            sla_info = get_sla_data()
            sla_df = sla_info['sla_df']
            
            # إنشاء قائمة بالمدن الموجودة في SLA
            sla_cities = set(sla_df['المدينة'].str.strip().str.upper())
            
            # فحص المدن في البيانات الرئيسية
            if 'المدينة_الوجهة' in df.columns:
                # البيانات غير المطابقة
                df_unmatched = df[df['SLA_أيام'].isna() & df['المدينة_الوجهة'].notna()].copy()
                
                if len(df_unmatched) > 0:
                    st.error(f"❌ تم العثور على {len(df_unmatched):,} شحنة غير مطابقة مع ملف SLA")
                    
                    # تحليل المدن غير المطابقة
                    unmatched_cities = df_unmatched['المدينة_الوجهة'].value_counts()
                    
                    st.markdown("### 📋 المدن غير المطابقة:")
                    
                    # عرض إحصائيات المدن غير المطابقة
                    unmatched_summary = pd.DataFrame({
                        'المدينة': unmatched_cities.index,
                        'عدد_الشحنات': unmatched_cities.values,
                        'النسبة': (unmatched_cities.values / len(df_unmatched) * 100).round(1)
                    })
                    
                    # تنسيق جدول المدن غير المطابقة
                    st.dataframe(
                        unmatched_summary.style.format({
                            'عدد_الشحنات': '{:,.0f}',
                            'النسبة': '{:.1f}%'
                        }).background_gradient(subset=['عدد_الشحنات'], cmap='Reds'),
                        use_container_width=True,
                        height=200
                    )
                    
                    # فلاتر للبيانات غير المطابقة
                    st.markdown("### 🔍 تفاصيل الشحنات غير المطابقة:")
                    
                    unmatched_col1, unmatched_col2 = st.columns([2, 1])
                    
                    with unmatched_col1:
                        selected_unmatched_city = st.selectbox(
                            "اختر مدينة غير مطابقة:",
                            ['الكل'] + list(unmatched_cities.index),
                            key="unmatched_city_filter"
                        )
                    
                    with unmatched_col2:
                        unmatched_rows_count = st.selectbox(
                            "عدد الصفوف:",
                            [10, 25, 50, "الكل"],
                            key="unmatched_rows_count"
                        )
                    
                    # تطبيق فلتر المدينة
                    display_unmatched = df_unmatched.copy()
                    if selected_unmatched_city != 'الكل':
                        display_unmatched = display_unmatched[
                            display_unmatched['المدينة_الوجهة'] == selected_unmatched_city
                        ]
                    
                    # تحديد عدد الصفوف
                    if unmatched_rows_count != "الكل":
                        display_unmatched = display_unmatched.head(unmatched_rows_count)
                    
                    # أعمدة للعرض
                    unmatched_display_columns = [
                        'رقم_الشحنة', 'المدينة_الوجهة', 'حالة_التسليم'
                    ]
                    
                    # إضافة أعمدة إضافية إن وجدت
                    additional_unmatched_columns = [
                        'اسم_المستلم', 'هاتف_المستلم', 'عنوان_المستلم', 
                        'تاريخ_الاستلام', 'تاريخ_أول_محاولة', 'تاريخ_التسليم',
                        'المبلغ_المستحق', 'المنطقة'
                    ]
                    
                    for col in additional_unmatched_columns:
                        if col in display_unmatched.columns:
                            unmatched_display_columns.append(col)
                    
                    # عرض الجدول
                    if len(display_unmatched) > 0:
                        st.markdown(f"**عرض {len(display_unmatched):,} شحنة غير مطابقة:**")
                        
                        # تنسيق الجدول
                        unmatched_styled = display_unmatched[unmatched_display_columns].style.applymap(
                            lambda x: 'background-color: #ffebee; color: #c62828; font-weight: bold;',
                            subset=['المدينة_الوجهة']
                        )
                        
                        st.dataframe(unmatched_styled, use_container_width=True, height=400)
                        
                        # أزرار الإجراءات
                        action_col1, action_col2, action_col3 = st.columns(3)
                        
                        with action_col1:
                            # تحميل البيانات غير المطابقة
                            csv_unmatched = display_unmatched[unmatched_display_columns].to_csv(
                                index=False, encoding='utf-8-sig'
                            )
                            st.download_button(
                                label="📥 تحميل البيانات غير المطابقة",
                                data=csv_unmatched,
                                file_name=f"unmatched_shipments_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                                mime="text/csv",
                                help="تحميل جميع الشحنات غير المطابقة"
                            )
                        
                        with action_col2:
                            # إنشاء ملف SLA للمدن المفقودة
                            if st.button("📋 إنشاء ملف SLA للمدن المفقودة", key="create_missing_sla"):
                                missing_cities_sla = pd.DataFrame({
                                    'City Name': unmatched_cities.index,
                                    'Region': 'غير محدد',  # يمكن تخصيصها لاحقاً
                                    'SLA': 2  # قيمة افتراضية
                                })
                                
                                csv_missing_sla = missing_cities_sla.to_csv(index=False, encoding='utf-8-sig')
                                st.download_button(
                                    label="💾 تحميل ملف SLA للمدن المفقودة",
                                    data=csv_missing_sla,
                                    file_name=f"missing_cities_sla_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                                    mime="text/csv",
                                    help="ملف SLA جاهز للمدن المفقودة"
                                )
                        
                        with action_col3:
                            # عرض إحصائيات سريعة
                            st.metric(
                                "إجمالي غير مطابق",
                                f"{len(df_unmatched):,}",
                                delta=f"{len(df_unmatched)/len(df)*100:.1f}% من المجموع"
                            )
                    
                    # اقتراحات للحل
                    st.markdown("### 💡 اقتراحات للحل:")
                    
                    suggestions_col1, suggestions_col2 = st.columns(2)
                    
                    with suggestions_col1:
                        st.info("""
                        **خيارات الحل:**
                        1. إضافة المدن المفقودة لملف SLA الحالي
                        2. تحديث أسماء المدن في البيانات الرئيسية
                        3. استخدام ملف SLA المُنشأ تلقائياً
                        """)
                    
                    with suggestions_col2:
                        st.warning("""
                        **تأثير عدم المطابقة:**
                        - عدم احتساب هذه الشحنات في مؤشرات SLA
                        - نقص في دقة التقارير
                        - تأثير على حسابات FDS
                        """)
                    
                    # فحص التشابه في أسماء المدن
                    st.markdown("### 🔍 فحص التشابه مع المدن الموجودة:")
                    
                    similar_matches = []
                    for unmatched_city in unmatched_cities.index[:5]:  # أول 5 مدن
                        unmatched_upper = unmatched_city.upper().strip()
                        for sla_city in sla_df['المدينة']:
                            sla_upper = str(sla_city).upper().strip()
                            if unmatched_upper in sla_upper or sla_upper in unmatched_upper:
                                if unmatched_city != sla_city:
                                    similar_matches.append({
                                        'المدينة_غير_مطابقة': unmatched_city,
                                        'مدينة_مشابهة_في_SLA': sla_city,
                                        'عدد_الشحنات': unmatched_cities[unmatched_city]
                                    })
                    
                    if similar_matches:
                        st.markdown("**مدن قد تكون متشابهة:**")
                        similar_df = pd.DataFrame(similar_matches)
                        st.dataframe(similar_df, use_container_width=True, height=200)
                        st.info("💡 قد تحتاج لتوحيد أسماء هذه المدن")
                    
                else:
                    st.success("✅ جميع البيانات مطابقة مع ملف SLA!")
                    
                    # عرض إحصائيات المطابقة
                    total_with_cities = len(df[df['المدينة_الوجهة'].notna()])
                    matched_count = len(df[df['SLA_أيام'].notna()])
                    match_rate = (matched_count / total_with_cities * 100) if total_with_cities > 0 else 0
                    
                    st.metric(
                        "معدل المطابقة",
                        f"{match_rate:.1f}%",
                        delta=f"{matched_count:,} من {total_with_cities:,}"
                    )
            else:
                st.warning("⚠️ لا يوجد عمود 'المدينة_الوجهة' في البيانات")
        else:
            st.info("📋 يرجى رفع ملف SLA أولاً لفحص البيانات غير المطابقة")
            
        st.markdown('</div>', unsafe_allow_html=True)

else:
    st.info("👆 اضغط على 'رفع Samsa' لبدء التحليل")

# الشريط الجانبي المحدث
add_logout_button()
with st.sidebar:
    st.markdown("### 📊 الحالة")
    
    if has_samsa_data():
        saved_info = get_samsa_data()
        total_rows = saved_info['total_rows']
        
        # حساب الشحنات المستثناة
        df = saved_info['main_df']
        excluded_count = len(df[df.get('مستثنى', False)])
        active_count = total_rows - excluded_count
        
        st.success(f"✓ {total_rows:,} شحنة محملة")
        st.info(f"📦 {active_count:,} شحنة نشطة")
        st.warning(f"🚫 {excluded_count:,} مستثناة")
        
        if has_sla_data():
            sla_info = get_sla_data()
            st.success(f"📋 {sla_info['total_cities']} مدينة SLA")
            
            # عرض إحصائيات المطابقة
            if 'SLA_أيام' in df.columns:
                sla_matches = df['SLA_أيام'].notna().sum()
                sla_match_rate = (sla_matches / len(df)) * 100
                st.info(f"🎯 مطابقة: {sla_match_rate:.1f}%")
        else:
            st.warning("📋 لم يتم رفع ملف SLA")
            st.info("اضغط 'رفع SLA' لتفعيل المؤشرات")
    else:
        st.warning("لا توجد بيانات")
    
    st.markdown("---")
    st.markdown("### ⚡ الإصلاحات الجديدة")
    st.success("✅ البحث الذكي عن الأعمدة")
    st.success("✅ ربط صحيح مع ملف SLA")
    st.success("✅ حساب دقيق للمؤشرات")
    st.success("✅ معالجة أسماء الأعمدة")
    st.success("✅ حساب الأيام الصحيح")
    st.info("📊 تطابق تام مع ملفك الحالي")

# التذييل المبسط
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #999; font-size: 0.8rem;">
    Samsa Analytics - مُصحح وجاهز للعمل مع ملفاتك الحالية - حساب الأيام مُحدث
</div>
""", unsafe_allow_html=True)
