
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
# إخفاء عناصر Streamlit غير المرغوبة
st.markdown("""
<style>
    /* إخفاء أيقونة GitHub Fork */
    .stActionButton {
        display: none !important;
    }
    
    /* إخفاء زر Deploy */
    .stDeployButton {
        display: none !important;
    }
    
    /* إخفاء القائمة الرئيسية */
    #MainMenu {
        visibility: hidden !important;
    }
    
    /* إخفاء التذييل */
    footer {
        visibility: hidden !important;
    }
    
    /* إخفاء أيقونة GitHub في الزاوية */
    .stApp > header {
        display: none !important;
    }
    
    /* إخفاء شريط Streamlit العلوي بالكامل */
    .stApp > div:first-child {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)
# 🔒 نظام الحماية بكلمة مرور
def check_password():
    """التحقق من كلمة المرور"""
    
    def password_entered():
        """فحص كلمة المرور المدخلة"""
        # يمكنك تغيير كلمة المرور هنا
        CORRECT_PASSWORD = "shipping2024"
        
        if st.session_state["password"] == CORRECT_PASSWORD:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # لا نحفظ كلمة المرور
        else:
            st.session_state["password_correct"] = False

    # إذا لم يتم التحقق من كلمة المرور بعد
    if "password_correct" not in st.session_state:
        # عرض صفحة تسجيل الدخول
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 3rem; border-radius: 15px; margin: 2rem auto; 
                    text-align: center; max-width: 500px;
                    box-shadow: 0 8px 25px rgba(0,0,0,0.15);">
            <h1 style="color: white; margin: 0; font-size: 2.5rem; font-weight: 700;">
                🔒 نظام تحليل الشحن
            </h1>
            <p style="color: #ecf0f1; margin: 1rem 0; font-size: 1.1rem; opacity: 0.9;">
                نظام محمي - يرجى إدخال كلمة المرور
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # حقل كلمة المرور
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.text_input(
                "🔑 كلمة المرور:",
                type="password",
                on_change=password_entered,
                key="password",
                placeholder="أدخل كلمة المرور للدخول",
                help="اتصل بمدير النظام للحصول على كلمة المرور"
            )
            
            st.markdown("""
            <div style="background: #e3f2fd; padding: 1rem; border-radius: 8px; 
                        border-left: 4px solid #2196f3; margin-top: 1rem;">
                <h4 style="color: #1565c0; margin: 0 0 0.5rem 0;">📞 للوصول للنظام:</h4>
                <p style="margin: 0; color: #1976d2;">
                    اتصل بمدير النظام للحصول على كلمة المرور<br>
                    أو راجع مدير تكنولوجيا المعلومات
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        return False
    
    # إذا كانت كلمة المرور خاطئة
    elif not st.session_state["password_correct"]:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 3rem; border-radius: 15px; margin: 2rem auto; 
                    text-align: center; max-width: 500px;
                    box-shadow: 0 8px 25px rgba(0,0,0,0.15);">
            <h1 style="color: white; margin: 0; font-size: 2.5rem; font-weight: 700;">
                🔒 نظام تحليل الشحن
            </h1>
            <p style="color: #ecf0f1; margin: 1rem 0; font-size: 1.1rem; opacity: 0.9;">
                نظام محمي - يرجى إدخال كلمة المرور
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.text_input(
                "🔑 كلمة المرور:",
                type="password",
                on_change=password_entered,
                key="password",
                placeholder="أدخل كلمة المرور للدخول"
            )
            st.error("❌ كلمة المرور غير صحيحة - حاول مرة أخرى")
        
        return False
    
    # كلمة المرور صحيحة
    else:
        return True

# 🔐 التحقق من كلمة المرور قبل عرض النظام
if not check_password():
    st.stop()

# ==================== بقية النظام (بعد التحقق من كلمة المرور) ====================

# إعداد الصفحة الرئيسية
st.set_page_config(
    page_title="🚚 Shipping Analytics Hub",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# إضافة زر تسجيل الخروج في الشريط الجانبي
with st.sidebar:
    st.markdown("### 🔐 تسجيل الخروج")
    if st.button("🚪 تسجيل خروج", use_container_width=True, type="secondary"):
        # مسح حالة تسجيل الدخول
        if "password_correct" in st.session_state:
            del st.session_state["password_correct"]
        st.rerun()
    
    st.markdown("---")

# CSS للصفحة الرئيسية
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700&display=swap');
    
    * {
        font-family: 'Cairo', sans-serif !important;
    }
    
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
        padding: 1rem;
    }
    
    .hero-section {
        background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.85) 100%);
        backdrop-filter: blur(10px);
        padding: 3rem 2rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        border: 1px solid rgba(255,255,255,0.3);
    }
    
    .hero-title {
        font-size: 3.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    
    .hero-subtitle {
        font-size: 1.3rem;
        color: #6c757d;
        margin-bottom: 2rem;
        line-height: 1.6;
    }
    
    .company-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 2rem;
        margin: 2rem 0;
    }
    
    .company-card {
        background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.85) 100%);
        backdrop-filter: blur(10px);
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        border: 1px solid rgba(255,255,255,0.3);
        transition: all 0.3s ease;
        cursor: pointer;
        text-decoration: none;
        color: inherit;
    }
    
    .company-card:hover {
        transform: translateY(-10px) scale(1.02);
        box-shadow: 0 15px 40px rgba(0,0,0,0.25);
        border: 1px solid rgba(102, 126, 234, 0.5);
    }
    
    .company-logo {
        font-size: 3rem;
        margin-bottom: 1rem;
        display: block;
    }
    
    .company-name {
        font-size: 1.5rem;
        font-weight: 700;
        color: #2c3e50;
        margin-bottom: 0.5rem;
    }
    
    .company-description {
        font-size: 1rem;
        color: #6c757d;
        margin-bottom: 1.5rem;
        line-height: 1.5;
    }
    
    .company-status {
        display: inline-block;
        padding: 0.3rem 1rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    
    .status-active {
        background: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    
    .status-setup {
        background: #fff3cd;
        color: #856404;
        border: 1px solid #ffeaa7;
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
        .hero-title {
            font-size: 2.5rem;
        }
        
        .company-grid {
            grid-template-columns: 1fr;
        }
    }
</style>
""", unsafe_allow_html=True)

# بيانات الشركات - محدث للـ hosting
companies_data = {
    "NiceOne": {
        "logo": "🚚",
        "name": "NiceOne",
        "description": "شركة شحن محلية متخصصة في التوصيل السريع",
        "status": "active",
        "features": ["تحليل المحاولات", "تتبع المناديب", "إحصائيات الفروع", "تقارير تنفيذية"],
        "page_file": "pages/niceone_dashboard.py",
        "color": "#3498db"
    },
    "Aramex": {
        "logo": "📦",
        "name": "Aramex",
        "description": "شركة شحن عالمية رائدة في منطقة الشرق الأوسط",
        "status": "active",
        "features": ["شحن دولي", "تتبع عالمي", "خدمات الأعمال", "شحن سريع"],
        "page_file": "pages/aramex_dashboard.py",
        "color": "#e74c3c"
    },
    "SMSA": {
        "logo": "🌟",
        "name": "SMSA Express",
        "description": "شركة البريد السعودي السريع",
        "status": "active",
        "features": ["شحن محلي", "خدمات حكومية", "التجارة الإلكترونية", "تتبع محلي"],
        "page_file": "pages/smsa_dashboard.py",
        "color": "#27ae60"
    },
    "Postage": {
        "logo": "✉️",
        "name": "Postage",
        "description": "خدمات البريد والشحن المتكاملة",
        "status": "setup",
        "features": ["بريد تقليدي", "شحن تجاري", "خدمات لوجستية", "حلول مخصصة"],
        "page_file": "pages/postage_dashboard.py",
        "color": "#9b59b6"
    },
    "DHL": {
        "logo": "🌍",
        "name": "DHL Express",
        "description": "الشحن السريع العالمي والخدمات اللوجستية",
        "status": "setup",
        "features": ["شحن عالمي", "خدمات الأعمال", "لوجستيات", "تتبع دولي"],
        "page_file": "pages/dhl_dashboard.py",
        "color": "#f39c12"
    },
    "QuickSilver": {
        "logo": "⚡",
        "name": "QuickSilver",
        "description": "التوصيل فائق السرعة للمدن الكبرى",
        "status": "setup",
        "features": ["توصيل سريع", "خدمة 24/7", "تتبع فوري", "توصيل متخصص"],
        "page_file": "pages/quicksilver_dashboard.py",
        "color": "#34495e"
    },
    "RedBox": {
        "logo": "📮",
        "name": "RedBox Delivery",
        "description": "صناديق التوصيل الذكية والخدمات المبتكرة",
        "status": "setup",
        "features": ["صناديق ذكية", "توصيل آمن", "خدمات ذاتية", "تقنيات حديثة"],
        "page_file": "pages/redbox_dashboard.py",
        "color": "#e67e22"
    }
}

# العنوان الرئيسي مع إشارة للحماية
st.markdown("""
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            padding: 2rem; border-radius: 15px; margin-bottom: 2rem; text-align: center;
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);">
    <h1 style="color: white; margin: 0; font-size: 2.5rem; font-weight: 700;">
        🚚 نظام تحليل الشحن المحمي
    </h1>
    <p style="color: #ecf0f1; margin: 1rem 0 0 0; font-size: 1.1rem; opacity: 0.9;">
        🔒 نظام محمي - اختر الشركة لعرض تحليلاتها
    </p>
</div>
""", unsafe_allow_html=True)

# عرض إشعار الأمان
st.success("🔐 تم تسجيل الدخول بنجاح - مرحباً بك في النظام المحمي")

# شبكة الشركات
st.markdown('<div class="company-grid">', unsafe_allow_html=True)

# إنشاء الأعمدة
cols = st.columns(3)
col_index = 0

for company_id, company in companies_data.items():
    with cols[col_index % 3]:
        # تحديد حالة الشركة
        status_text = "متاح" if company['status'] == 'active' else "قريباً"
        status_color = "#27ae60" if company['status'] == 'active' else "#f39c12"
        
        # بطاقة الشركة
        st.markdown(f"""
        <div style="background: white; padding: 2rem; border-radius: 15px; 
                    text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                    border-left: 5px solid {company['color']}; margin-bottom: 1rem;">
            <div style="font-size: 4rem; margin-bottom: 1rem;">{company['logo']}</div>
            <h3 style="color: {company['color']}; margin: 0.5rem 0; font-size: 1.5rem;">{company['name']}</h3>
            <div style="background: {status_color}20; color: {status_color}; 
                        padding: 0.5rem 1rem; border-radius: 20px; font-weight: 600;
                        display: inline-block; margin-bottom: 1rem;">
                {status_text}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # زر الانتقال للشركة
        if company['status'] == 'active':
            if st.button(f"📊 عرض تحليلات {company['name']}", 
                        key=f"btn_{company_id}",
                        use_container_width=True,
                        type="primary"):
                st.switch_page(company['page_file'])
        else:
            st.button(f"🔒 {company['name']} - قريباً", 
                     key=f"setup_{company_id}",
                     use_container_width=True,
                     disabled=True)
    
    col_index += 1

st.markdown('</div>', unsafe_allow_html=True)

# استيراد مدير البيانات المشتركة مع معالجة الأخطاء
try:
    from shared_data import get_data_manager, show_data_status
    data_manager = get_data_manager()
    has_shared_system = True
except ImportError:
    has_shared_system = False

# الشريط الجانبي
with st.sidebar:
    st.markdown("### 🎯 الشركات المتاحة")
    
    # عرض حالة البيانات إذا كان النظام المشترك متاح
    if has_shared_system:
        st.markdown("### 💾 حالة البيانات المحفوظة")
        
        companies_data_status = {
            'NiceOne': data_manager.has_company_data('niceone'),
            'Aramex': data_manager.has_company_data('aramex'),
            'SMSA': data_manager.has_company_data('smsa')
        }
        
        any_data = False
        for company, has_data in companies_data_status.items():
            if has_data:
                st.success(f"✅ {company} - بيانات محفوظة")
                any_data = True
            else:
                st.info(f"📋 {company} - لا توجد بيانات")
        
        if any_data:
            if st.button("🗑️ مسح جميع البيانات", use_container_width=True):
                if st.button("⚠️ تأكيد المسح", use_container_width=True, key="confirm_clear"):
                    data_manager.clear_all_data()
                    st.rerun()
    
    st.markdown("---")
    
    # قائمة الشركات في الشريط الجانبي
    for company_id, company in companies_data.items():
        status_emoji = "✅" if company['status'] == 'active' else "🔒"
        
        # إضافة مؤشر البيانات المحفوظة
        if has_shared_system and company['status'] == 'active':
            has_saved_data = data_manager.has_company_data(company_id.lower())
            data_indicator = " 💾" if has_saved_data else ""
        else:
            data_indicator = ""
        
        if company['status'] == 'active':
            if st.button(f"{company['logo']} {company['name']}{data_indicator}", 
                        key=f"sidebar_{company_id}",
                        use_container_width=True):
                st.switch_page(company['page_file'])
        else:
            st.button(f"{company['logo']} {company['name']} {status_emoji}", 
                     key=f"sidebar_disabled_{company_id}",
                     use_container_width=True,
                     disabled=True)
    
    st.markdown("---")
    
    # معلومات النظام المحمي
    st.markdown("### 🔐 معلومات الأمان")
    st.success("✅ النظام محمي بكلمة مرور")
    st.info(f"""
    **الشركات النشطة:** {len([c for c in companies_data.values() if c['status'] == 'active'])}
    
    **قيد التطوير:** {len([c for c in companies_data.values() if c['status'] == 'setup'])}
    
    **المجموع:** {len(companies_data)}
    """)
    
    if has_shared_system:
        st.markdown("### 🔄 نظام البيانات المشتركة")
        st.success("✅ نشط - البيانات محفوظة بين الصفحات")
    
    # معلومات الاستضافة
    st.markdown("### 🌐 معلومات الاستضافة")
    st.info("""
    **المنصة:** Streamlit Cloud  
    **الحالة:** محمي بكلمة مرور  
    **التحديث:** تلقائي من GitHub
    """)

# تذييل مع معلومات الحماية
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 1rem; color: #6c757d;">
    <p style="margin: 0; font-size: 0.9rem;">
        🔒 <strong>نظام تحليل الشحن المحمي</strong> - متاح مجاناً على Streamlit Cloud
    </p>
    <p style="margin: 0.5rem 0 0 0; font-size: 0.8rem; opacity: 0.8;">
        🛡️ محمي بكلمة مرور | 🔄 تحديث تلقائي | 💾 بيانات آمنة
    </p>
</div>
""", unsafe_allow_html=True)
