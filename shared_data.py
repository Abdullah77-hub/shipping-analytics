# shared_data.py - مدير البيانات المشتركة بين الصفحات
import streamlit as st
import pandas as pd
import pickle
import os
from datetime import datetime

class SharedDataManager:
    """مدير البيانات المشتركة بين جميع صفحات النظام"""
    
    def __init__(self):
        self.data_key = "shared_shipping_data"
        self.init_shared_state()
    
    def init_shared_state(self):
        """تهيئة البيانات المشتركة"""
        if self.data_key not in st.session_state:
            st.session_state[self.data_key] = {
                'niceone_data': None,
                'aramex_data': None, 
                'smsa_data': None,
                'postage_data': None,
                'dhl_data': None,
                'quicksilver_data': None,
                'redbox_data': None,
                'upload_times': {},
                'data_sources': {},
                'branch_files': {},
                'last_updated': None
            }
    
    def save_company_data(self, company_name, main_data, branch_files=None, source="manual"):
        """حفظ بيانات شركة معينة"""
        company_key = f"{company_name.lower()}_data"
        
        # حفظ البيانات الرئيسية
        st.session_state[self.data_key][company_key] = main_data
        
        # حفظ ملفات الفروع
        if branch_files:
            st.session_state[self.data_key]['branch_files'][company_name.lower()] = branch_files
        
        # حفظ معلومات التحميل
        st.session_state[self.data_key]['upload_times'][company_name.lower()] = datetime.now()
        st.session_state[self.data_key]['data_sources'][company_name.lower()] = source
        st.session_state[self.data_key]['last_updated'] = datetime.now()
        
        # إظهار رسالة نجاح
        st.success(f"✅ تم حفظ بيانات {company_name} بنجاح! ستبقى متاحة في جميع الصفحات.")
    
    def get_company_data(self, company_name):
        """استرجاع بيانات شركة معينة"""
        company_key = f"{company_name.lower()}_data"
        return st.session_state[self.data_key].get(company_key, None)
    
    def get_branch_files(self, company_name):
        """استرجاع ملفات فروع شركة معينة"""
        return st.session_state[self.data_key]['branch_files'].get(company_name.lower(), None)
    
    def get_data_info(self, company_name):
        """استرجاع معلومات البيانات (مصدر، تاريخ التحميل)"""
        company_lower = company_name.lower()
        upload_time = st.session_state[self.data_key]['upload_times'].get(company_lower, None)
        data_source = st.session_state[self.data_key]['data_sources'].get(company_lower, "تجريبي")
        
        return {
            'upload_time': upload_time,
            'source': data_source,
            'has_data': self.has_company_data(company_name)
        }
    
    def has_company_data(self, company_name):
        """التحقق من وجود بيانات لشركة معينة"""
        data = self.get_company_data(company_name)
        return data is not None and len(data) > 0
    
    def clear_company_data(self, company_name):
        """مسح بيانات شركة معينة"""
        company_key = f"{company_name.lower()}_data"
        company_lower = company_name.lower()
        
        st.session_state[self.data_key][company_key] = None
        
        if company_lower in st.session_state[self.data_key]['branch_files']:
            del st.session_state[self.data_key]['branch_files'][company_lower]
        
        if company_lower in st.session_state[self.data_key]['upload_times']:
            del st.session_state[self.data_key]['upload_times'][company_lower]
        
        if company_lower in st.session_state[self.data_key]['data_sources']:
            del st.session_state[self.data_key]['data_sources'][company_lower]
        
        st.success(f"✅ تم مسح بيانات {company_name}")
    
    def clear_all_data(self):
        """مسح جميع البيانات"""
        st.session_state[self.data_key] = {
            'niceone_data': None,
            'aramex_data': None,
            'smsa_data': None, 
            'postage_data': None,
            'dhl_data': None,
            'quicksilver_data': None,
            'redbox_data': None,
            'upload_times': {},
            'data_sources': {},
            'branch_files': {},
            'last_updated': None
        }
        st.success("✅ تم مسح جميع البيانات")
    
    def get_all_companies_status(self):
        """الحصول على حالة جميع الشركات"""
        companies = ['niceone', 'aramex', 'smsa', 'postage', 'dhl', 'quicksilver', 'redbox']
        status = {}
        
        for company in companies:
            status[company] = {
                'has_data': self.has_company_data(company),
                'data_info': self.get_data_info(company)
            }
        
        return status
    
    def display_data_status(self, company_name=None):
        """عرض حالة البيانات"""
        if company_name:
            # عرض حالة شركة معينة
            info = self.get_data_info(company_name)
            if info['has_data']:
                upload_time = info['upload_time'].strftime('%Y-%m-%d %H:%M:%S') if info['upload_time'] else "غير محدد"
                st.info(f"""
                📊 **حالة بيانات {company_name}:**
                - ✅ البيانات متاحة ومحفوظة
                - 📅 تاريخ التحميل: {upload_time}
                - 🔗 المصدر: {info['source']}
                - 🔄 متاحة في جميع الصفحات
                """)
            else:
                st.warning(f"⚠️ لا توجد بيانات محفوظة لـ {company_name}")
        else:
            # عرض حالة جميع الشركات
            all_status = self.get_all_companies_status()
            companies_with_data = [name for name, status in all_status.items() if status['has_data']]
            
            if companies_with_data:
                st.success(f"✅ الشركات المحفوظة: {', '.join(companies_with_data).upper()}")
            else:
                st.info("📋 لا توجد بيانات محفوظة حالياً")

# إنشاء مثيل واحد للاستخدام في جميع الصفحات
def get_data_manager():
    """الحصول على مدير البيانات المشتركة"""
    return SharedDataManager()

# دوال مساعدة للاستخدام السهل
def save_data(company_name, data, branch_files=None, source="manual"):
    """حفظ بيانات شركة - دالة مبسطة"""
    manager = get_data_manager()
    manager.save_company_data(company_name, data, branch_files, source)

def get_data(company_name):
    """استرجاع بيانات شركة - دالة مبسطة"""
    manager = get_data_manager()
    return manager.get_company_data(company_name)

def has_data(company_name):
    """التحقق من وجود بيانات - دالة مبسطة"""
    manager = get_data_manager()
    return manager.has_company_data(company_name)

def clear_data(company_name):
    """مسح بيانات شركة - دالة مبسطة"""
    manager = get_data_manager()
    manager.clear_company_data(company_name)

def show_data_status(company_name=None):
    """عرض حالة البيانات - دالة مبسطة"""
    manager = get_data_manager()
    manager.display_data_status(company_name)

# دالة تحميل البيانات مع الحفظ المشترك
def load_and_save_data(company_name, uploaded_file, branch_files=None):
    """تحميل البيانات وحفظها في النظام المشترك"""
    try:
        # قراءة الملف
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, encoding='utf-8')
        else:
            df = pd.read_excel(uploaded_file)
        
        # معالجة البيانات
        df = fix_duplicate_columns(df)
        
        # حفظ البيانات في النظام المشترك
        save_data(company_name, df, branch_files, "manual")
        
        return df
        
    except Exception as e:
        st.error(f"خطأ في تحميل البيانات: {str(e)}")
        return None

def fix_duplicate_columns(df):
    """إصلاح الأعمدة المكررة"""
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