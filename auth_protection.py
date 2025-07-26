import streamlit as st

def check_authentication():
    """التحقق من تسجيل الدخول"""
    if "password_correct" not in st.session_state or not st.session_state.get("password_correct", False):
        st.markdown("""
        <div style="background: #e74c3c; padding: 2rem; border-radius: 15px; 
                    text-align: center; color: white; margin: 2rem 0;">
            <h1>🚫 وصول غير مصرح</h1>
            <p>يجب تسجيل الدخول أولاً للوصول لهذه الصفحة</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🏠 العودة للصفحة الرئيسية", type="primary"):
            st.switch_page("main_dashboard.py")
        
        st.stop()
        return False
    return True

def add_logout_button():
    """زر تسجيل الخروج"""
    with st.sidebar:
        st.markdown("### 🔐 الأمان")
        st.success("✅ تم تسجيل الدخول")
        
        if st.button("🚪 تسجيل خروج", use_container_width=True):
            if "password_correct" in st.session_state:
                del st.session_state["password_correct"]
            st.switch_page("main_dashboard.py")
        
        if st.button("🏠 الصفحة الرئيسية", use_container_width=True):
            st.switch_page("main_dashboard.py")
        
        st.markdown("---")