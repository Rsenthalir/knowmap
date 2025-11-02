

import streamlit as st
import requests
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from pyvis.network import Network
import streamlit.components.v1 as components
import json
import os
import time
from datetime import datetime

# Configure the page
st.set_page_config(
    page_title="KnowMap - Knowledge Graph Platform",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #4B4DED;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #2E8B57;
        margin-bottom: 1rem;
        font-weight: 600;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #4B4DED;
    }
    .success-box {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        border: 1px solid #c3e6cb;
    }
    .warning-box {
        background-color: #fff3cd;
        color: #856404;
        padding: 1rem;
        border-radius: 5px;
        border: 1px solid #ffeaa7;
    }
    .error-box {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 5px;
        border: 1px solid #f5c6cb;
    }
    .info-box {
        background-color: #d1ecf1;
        color: #0c5460;
        padding: 1rem;
        border-radius: 5px;
        border: 1px solid #bee5eb;
    }
    .admin-badge {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .crud-section {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        border: 1px solid #e9ecef;
    }
</style>
""", unsafe_allow_html=True)

import os
API_URL = os.getenv("API_URL", "http://127.0.0.1:5010")

if 'token' not in st.session_state:
    st.session_state.token = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Dashboard"

# Test connection
try:
    response = requests.get(f"{API_URL}/health", timeout=5)
    st.session_state.api_connected = response.status_code == 200
except:
    st.session_state.api_connected = False

# Helper functions
def safe_json(resp):
    try:
        return resp.json()
    except ValueError as e:
        return {"error": f"JSON decode error: {str(e)}", "raw_text": resp.text[:500]}

def get_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"} if st.session_state.token else {}

def make_request(endpoint, method='GET', json_data=None, files=None):
    headers = get_headers()
    try:
        if method.upper() == 'GET':
            resp = requests.get(f"{API_URL}/{endpoint}", headers=headers, timeout=30)
        elif method.upper() == 'POST':
            if files:
                resp = requests.post(f"{API_URL}/{endpoint}", files=files, headers=headers, timeout=30)
            else:
                resp = requests.post(f"{API_URL}/{endpoint}", json=json_data, headers=headers, timeout=30)
        elif method.upper() == 'DELETE':
            resp = requests.delete(f"{API_URL}/{endpoint}", headers=headers, timeout=30)
        else:
            return {"error": f"Unsupported method: {method}"}, 400

        return safe_json(resp), resp.status_code
    except requests.exceptions.Timeout:
        return {"error": "Request timed out"}, 408
    except requests.exceptions.ConnectionError:
        return {"error": f"Cannot connect to Flask server at {API_URL}. Make sure it's running."}, 503
    except Exception as e:
        return {"error": f"Request failed: {str(e)}"}, 500

def is_user_admin():
    """Check if current user has admin privileges"""
    return st.session_state.user_role == 'admin'

def check_admin_access():
    """Check if user can access admin features"""
    if not st.session_state.token:
        return False, "Not logged in"
    
    try:
        # Try to access admin stats to check permissions
        headers = get_headers()
        resp = requests.get(f"{API_URL}/admin/stats", headers=headers, timeout=10)
        return resp.status_code == 200, "Access granted" if resp.status_code == 200 else "Admin access required"
    except Exception as e:
        return False, f"Error checking access: {e}"

def fetch_knowledge_base():
    """Fetch all knowledge base entries"""
    try:
        data, status = make_request("api/kb/triples")
        if status == 200:
            return data.get("triples", [])
        return []
    except Exception as e:
        st.error(f"Error fetching knowledge base: {e}")
        return []

def add_kb_triple(entity1, relation, entity2):
    """Add a new triple to knowledge base"""
    try:
        data, status = make_request("api/kb/triples", 'POST', {
            "entity1": entity1,
            "relation": relation,
            "entity2": entity2
        })
        return status == 201
    except Exception as e:
        st.error(f"Error adding triple: {e}")
        return False

def delete_kb_triple(triple_id):
    """Delete a triple from knowledge base"""
    try:
        data, status = make_request(f"api/kb/triples/{triple_id}", 'DELETE')
        return status == 200
    except Exception as e:
        st.error(f"Error deleting triple: {e}")
        return False

def update_kb_triple(triple_id, entity1, relation, entity2):
    """Update a triple in knowledge base"""
    try:
        data, status = make_request(f"api/kb/triples/{triple_id}", 'PUT', {
            "entity1": entity1,
            "relation": relation,
            "entity2": entity2
        })
        return status == 200
    except Exception as e:
        st.error(f"Error updating triple: {e}")
        return False

# Sidebar Navigation
with st.sidebar:
    st.markdown("<h1 style='text-align: center; color: #4B4DED;'>🧠 KnowMap</h1>", unsafe_allow_html=True)
    
    # User status with role badge
    if st.session_state.token:
        user_display = f"👤 Welcome {st.session_state.username}"
        if st.session_state.user_role == 'admin':
            user_display += " <span class='admin-badge'>ADMIN</span>"
        st.markdown(f"<div style='margin-bottom: 1rem;'>{user_display}</div>", unsafe_allow_html=True)
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    else:
        st.warning("🔒 Not logged in")

    st.markdown("---")

    # Navigation menu - show admin option only to admins
    nav_options = [
        "🏠 Dashboard",
        "🔐 Authentication",
        "👤 User Profile",
        "📤 Upload Dataset",
        "📊 Manage Datasets",
        "🔗 Extract Knowledge Graph",
        "🔍 Semantic Search",
        "💬 Feedback System",
    ]
    
    # Add admin option only for admin users
    if st.session_state.token and is_user_admin():
        nav_options.append("⚙️ Admin Dashboard")

    selected_nav = st.radio("Navigation", nav_options, index=0)

    # Update current page
    st.session_state.current_page = selected_nav

    st.markdown("---")
    st.markdown("### 💡 Quick Tips")
    
    tips_text = """
    1. Upload your dataset first
    2. Extract knowledge graph
    3. Explore with semantic search
    4. Analyze relationships
    5. Provide feedback to improve
    """
    
    if st.session_state.token and is_user_admin():
        tips_text += "\n6. Use Admin Dashboard for system management"
    
    st.info(tips_text)

# Dashboard Page
if st.session_state.current_page == "🏠 Dashboard":
    st.markdown("<div class='main-header'>🧠 KnowMap Dashboard</div>", unsafe_allow_html=True)

    # Quick actions
    st.markdown("<div class='sub-header'>🚀 Quick Actions</div>", unsafe_allow_html=True)

    if st.session_state.token and is_user_admin():
        cols = st.columns(6)
        actions = [
            ("🔐 Authenticate", "🔐 Authentication"),
            ("📤 Upload", "📤 Upload Dataset"),
            ("🔗 Extract", "🔗 Extract Knowledge Graph"),
            ("🔍 Search", "🔍 Semantic Search"),
            ("💬 Feedback", "💬 Feedback System"),
            ("⚙️ Admin", "⚙️ Admin Dashboard")
        ]
    else:
        cols = st.columns(5)
        actions = [
            ("🔐 Authentication", "🔐 Authentication"),
            ("📤 Upload", "📤 Upload Dataset"),
            ("🔗 Extract", "🔗 Extract Knowledge Graph"),
            ("🔍 Search", "🔍 Semantic Search"),
            ("💬 Feedback", "💬 Feedback System")
        ]

    for col, (icon, page) in zip(cols, actions):
        with col:
            if st.button(icon, use_container_width=True):
                st.session_state.current_page = page
                st.rerun()

    st.markdown("---")

    # Welcome message based on user role
    if st.session_state.token:
        if is_user_admin():
            st.success("👑 Welcome back, Administrator! You have full system access.")
        else:
            st.success("👤 Welcome back! Explore knowledge graphs and provide feedback.")
    else:
        st.info("🔐 Please login to access all features")

    # Features overview
    st.markdown("<div class='sub-header'>✨ Key Features</div>", unsafe_allow_html=True)

    features_col1, features_col2 = st.columns(2)

    with features_col1:
        st.markdown("""
        ### 🔗 Knowledge Graph Extraction
        - **Automatic Triple Extraction** from various file formats
        - **Smart CSV Processing** with semantic understanding
        - **Relationship Discovery** using advanced NLP
        - **Interactive Visualization** of knowledge graphs
        """)

        st.markdown("""
        ### 🔍 Semantic Search
        - **Intelligent Node Search** using sentence transformers
        - **Subgraph Exploration** with configurable radius
        - **Similarity Scoring** for relevant results
        - **Connected Knowledge Discovery**
        """)

    with features_col2:
        st.markdown("""
        ### 📊 Data Management
        - **Multiple Format Support** (CSV, JSON, TXT)
        - **Data Preprocessing** and cleaning
        - **Dataset Preview** and management
        - **Secure User Isolation**
        """)

        st.markdown("""
        ### 🎯 Advanced Analytics
        - **Graph Statistics** and metrics
        - **Relationship Analysis**
        - **Pattern Discovery**
        - **Export Capabilities**
        """)
        
        if st.session_state.token and is_user_admin():
            st.markdown("""
            ### ⚙️ Admin Features
            - **System Monitoring** and statistics
            - **Knowledge Base Management**
            - **User Feedback Review**
            - **Data Integrity Controls**
            """)

    # Getting started guide
    if not st.session_state.token:
        st.markdown("---")
        st.markdown("<div class='sub-header'>🎯 Getting Started</div>", unsafe_allow_html=True)

        steps_col1, steps_col2, steps_col3, steps_col4 = st.columns(4)

        with steps_col1:
            st.markdown("""
            ### 1. 🔐 Authentication
            - Create an account or login
            - Secure token-based authentication
            """)

        with steps_col2:
            st.markdown("""
            ### 2. 📤 Upload Data
            - Upload CSV, JSON, or text files
            - Preview and preprocess data
            - Multiple dataset support
            """)

        with steps_col3:
            st.markdown("""
            ### 3. 🔗 Create Knowledge Graph
            - Extract entities and relationships
            - Build interactive knowledge graphs
            - Analyze graph structure
            """)

        with steps_col4:
            st.markdown("""
            ### 4. 🔍 Explore & Improve
            - Semantic search capabilities
            - Provide feedback for improvements
            - Export your results
            """)

# Authentication Page
elif st.session_state.current_page == "🔐 Authentication":
    st.markdown("<div class='sub-header'>🔐 User Authentication</div>", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["🚀 Login", "📝 Create Account", "👑 Admin Setup"])

    with tab1:
        with st.form("login_form"):
            st.markdown("### Existing User Login")
            login_username = st.text_input("👤 Username", placeholder="Enter your username")
            login_password = st.text_input("🔑 Password", type="password", placeholder="Enter your password")
            login_btn = st.form_submit_button("🚀 Login", use_container_width=True)

            if login_btn:
                if not login_username or not login_password:
                    st.error("❌ Please enter both username and password")
                else:
                    with st.spinner("Authenticating..."):
                        data, status = make_request("login", 'POST', {"username": login_username, "password": login_password})

                        if status == 200 and 'token' in data:
                            st.session_state.token = data['token']
                            st.session_state.username = data['user']['username']
                            st.session_state.user_role = data['user']['role']
                            st.success("✅ Login successful!")
                            if st.session_state.user_role == 'admin':
                                st.success("👑 Administrator privileges granted!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ Login failed: {data.get('error', 'Unknown error')}")

    with tab2:
        with st.form("signup_form"):
            st.markdown("### New User Registration")
            signup_username = st.text_input("👤 Choose Username", placeholder="Enter unique username")
            signup_email = st.text_input("📧 Email Address", placeholder="Enter your email")
            signup_password = st.text_input("🔑 Create Password", type="password", placeholder="Create a strong password")
            confirm_password = st.text_input("🔑 Confirm Password", type="password", placeholder="Re-enter your password")
            signup_btn = st.form_submit_button("📝 Create Account", use_container_width=True)

            if signup_btn:
                if not all([signup_username, signup_email, signup_password, confirm_password]):
                    st.error("❌ Please fill all fields")
                elif signup_password != confirm_password:
                    st.error("❌ Passwords do not match")
                else:
                    with st.spinner("Creating account..."):
                        data, status = make_request("signup", 'POST', {
                            "username": signup_username,
                            "email": signup_email,
                            "password": signup_password
                        })

                        if status == 201:
                            st.success("✅ Account created successfully! Please login.")
                        else:
                            st.error(f"❌ Registration failed: {data.get('error', 'Unknown error')}")

    with tab3:
        st.markdown("### 👑 Admin Account Setup")
        st.info("""
        **Create the first administrator account for the system.**
        - This can only be done once
        - The admin account will have full system access
        - Regular users cannot access admin features
        """)
        
        with st.form("admin_setup_form"):
            admin_username = st.text_input("👑 Admin Username", placeholder="Choose admin username")
            admin_email = st.text_input("📧 Admin Email", placeholder="Admin email address")
            admin_password = st.text_input("🔑 Admin Password", type="password", placeholder="Create admin password")
            admin_confirm = st.text_input("🔑 Confirm Password", type="password", placeholder="Confirm admin password")
            admin_btn = st.form_submit_button("👑 Create Admin Account", use_container_width=True)
            
            if admin_btn:
                if not all([admin_username, admin_email, admin_password, admin_confirm]):
                    st.error("❌ Please fill all fields")
                elif admin_password != admin_confirm:
                    st.error("❌ Passwords do not match")
                else:
                    with st.spinner("Creating admin account..."):
                        try:
                            resp = requests.post(f"{API_URL}/admin/register", json={
                                "username": admin_username,
                                "email": admin_email,
                                "password": admin_password
                            })
                            if resp.status_code == 201:
                                st.success("✅ Admin account created successfully!")
                                st.info("You can now login with the admin credentials.")
                            else:
                                error_data = resp.json()
                                st.error(f"❌ Admin setup failed: {error_data.get('error', 'Unknown error')}")
                        except Exception as e:
                            st.error(f"❌ Setup error: {e}")

# User Profile Page
elif st.session_state.current_page == "👤 User Profile":
    if not st.session_state.token:
        st.warning("🔒 Please log in to access your profile")
        st.session_state.current_page = "🔐 Authentication"
        st.rerun()
    else:
        st.markdown("<div class='sub-header'>👤 User Profile</div>", unsafe_allow_html=True)

        # Get current profile
        data, status = make_request("profile")

        if status == 200:
            profile_data = data
        else:
            profile_data = {}
            st.error(f"Failed to load profile: {data.get('error', 'Unknown error')}")

        col1, col2 = st.columns([1, 2])

        with col1:
            st.markdown("### 📊 Profile Info")
            
            # Display user role with badge
            role_display = profile_data.get('role', 'user')
            if role_display == 'admin':
                st.markdown("<div class='admin-badge' style='display: inline-block; margin-bottom: 1rem;'>ADMINISTRATOR</div>", unsafe_allow_html=True)
            
            st.json(profile_data)

            st.markdown("### 🔑 Account Details")
            st.info(f"**Username:** {profile_data.get('username', 'N/A')}")
            st.info(f"**Email:** {profile_data.get('email', 'N/A')}")
            st.info(f"**Role:** {role_display.title()}")

        with col2:
            st.markdown("### ✏️ Update Profile")
            with st.form("update_profile"):
                language = st.text_input("🗣️ Preferred Language",
                                       value=profile_data.get('language', ''),
                                       placeholder="e.g., English, Spanish, French")

                interests = st.text_area("🎯 Interests & Domains",
                                       value=profile_data.get('interests', ''),
                                       placeholder="e.g., AI, Medicine, Science, Technology...",
                                       height=100)

                update_btn = st.form_submit_button("💾 Save Profile", use_container_width=True)

                if update_btn:
                    with st.spinner("Updating profile..."):
                        update_data, update_status = make_request("profile", 'POST', {
                            "language": language,
                            "interests": interests
                        })

                        if update_status == 200:
                            st.success("✅ Profile updated successfully!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ Update failed: {update_data.get('error', 'Unknown error')}")

# Upload Dataset Page
elif st.session_state.current_page == "📤 Upload Dataset":
    if not st.session_state.token:
        st.warning("🔒 Please log in to upload datasets")
        st.session_state.current_page = "🔐 Authentication"
        st.rerun()
    else:
        st.markdown("<div class='sub-header'>📤 Upload Dataset</div>", unsafe_allow_html=True)

        col1, col2 = st.columns([2, 1])

        with col1:
            uploaded_file = st.file_uploader(
                "Choose a file to upload",
                type=["csv", "txt", "json"],
                help="Supported formats: CSV, TXT, JSON"
            )

            if uploaded_file:
                st.info(f"**Selected File:** {uploaded_file.name}")
                st.info(f"**File Size:** {len(uploaded_file.getvalue()) / 1024:.2f} KB")
                st.info(f"**File Type:** {uploaded_file.type}")

        if uploaded_file and st.button("🚀 Upload Dataset", type="primary", use_container_width=True):
            with st.spinner("Uploading your dataset..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                data, status = make_request("upload", 'POST', files=files)

                if status == 200:
                    st.success("✅ Dataset uploaded successfully!")

                    # Show preview if it's a CSV
                    if uploaded_file.name.endswith('.csv'):
                        try:
                            uploaded_file.seek(0)
                            df = pd.read_csv(uploaded_file)
                            st.markdown("### 📋 Data Preview")
                            st.dataframe(df.head(10))

                            # Basic stats
                            col1, col2, col3 = st.columns(3)
                            col1.metric("Rows", len(df))
                            col2.metric("Columns", len(df.columns))
                            col3.metric("Memory Usage", f"{df.memory_usage(deep=True).sum() / 1024:.1f} KB")

                        except Exception as e:
                            st.warning(f"Could not preview CSV: {e}")

                    st.balloons()
                else:
                    st.error(f"❌ Upload failed: {data.get('error', 'Unknown error')}")

# Manage Datasets Page
elif st.session_state.current_page == "📊 Manage Datasets":
    if not st.session_state.token:
        st.warning("🔒 Please log in to manage datasets")
        st.session_state.current_page = "🔐 Authentication"
        st.rerun()
    else:
        st.markdown("<div class='sub-header'>📊 Manage Datasets</div>", unsafe_allow_html=True)

        # Load datasets
        data, status = make_request("datasets")

        if status != 200:
            st.error(f"Failed to load datasets: {data.get('error', 'Unknown error')}")
            datasets = []
        else:
            datasets = data.get("datasets", [])

        if not datasets:
            st.info("📭 No datasets uploaded yet. Go to **Upload Dataset** to get started!")
        else:
            st.success(f"📁 Found {len(datasets)} dataset(s)")

            for filename in datasets:
                with st.expander(f"📄 {filename}", expanded=False):
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        if st.button("👁️ Preview", key=f"preview-{filename}", use_container_width=True):
                            preview_data, preview_status = make_request(f"datasets/preview/{filename}")
                            if preview_status == 200:
                                st.markdown("**Preview:**")
                                if isinstance(preview_data, list):
                                    st.dataframe(pd.DataFrame(preview_data).head(10))
                                else:
                                    st.json(preview_data)
                            else:
                                st.error(f"Preview failed: {preview_data.get('error', 'Unknown error')}")

                    with col2:
                        if st.button("🔧 Preprocess", key=f"preprocess-{filename}", use_container_width=True):
                            with st.spinner("Preprocessing..."):
                                process_data, process_status = make_request(f"datasets/preprocess/{filename}", 'POST')
                                if process_status == 200:
                                    st.success("✅ Preprocessing completed!")
                                    st.write(process_data.get("preprocessed_preview", "Check processed file"))
                                else:
                                    st.error(f"Preprocessing failed: {process_data.get('error', 'Unknown error')}")

                    with col3:
                        if st.button("🗑️ Delete", key=f"delete-{filename}", use_container_width=True):
                            delete_data, delete_status = make_request(f"datasets/{filename}", 'DELETE')
                            if delete_status == 200:
                                st.success("✅ Dataset deleted!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"Delete failed: {delete_data.get('error', 'Unknown error')}")

                    with col4:
                        if st.button("📥 Download", key=f"download-{filename}", use_container_width=True):
                            try:
                                headers = get_headers()
                                resp = requests.get(f"{API_URL}/datasets/download/{filename}", headers=headers, stream=True)
                                if resp.status_code == 200:
                                    st.download_button(
                                        "💾 Download File",
                                        resp.content,
                                        file_name=filename,
                                        mime="application/octet-stream",
                                        key=f"dl-{filename}"
                                    )
                                else:
                                    st.error("Download failed")
                            except Exception as e:
                                st.error(f"Download error: {e}")

# Extract Knowledge Graph Page
elif st.session_state.current_page == "🔗 Extract Knowledge Graph":
    if not st.session_state.token:
        st.warning("🔒 Please log in to extract knowledge graphs")
        st.session_state.current_page = "🔐 Authentication"
        st.rerun()
    else:
        st.markdown("<div class='sub-header'>🔗 Extract Knowledge Graph</div>", unsafe_allow_html=True)

        # Load datasets
        data, status = make_request("datasets")
        datasets = data.get("datasets", []) if status == 200 else []

        if not datasets:
            st.error("❌ No datasets available. Please upload a dataset first.")
            st.info("Go to **Upload Dataset** to add your data")
        else:
            col1, col2 = st.columns([2, 1])

            with col1:
                selected_dataset = st.selectbox(
                    "📁 Select Dataset for Extraction",
                    datasets,
                    help="Choose a dataset to extract knowledge graph from"
                )

            if st.button("🚀 Extract Knowledge Graph", type="primary", use_container_width=True):
                with st.spinner("🔄 Extracting knowledge graph... This may take a while for large datasets."):
                    extract_data, extract_status = make_request(f"datasets/extract/{selected_dataset}", 'POST')

                    if extract_status == 200:
                        st.success("✅ Knowledge graph extracted successfully!")

                        triples = extract_data.get("triples", [])
                        stats = extract_data.get("graph_stats", {})

                        # Display statistics
                        st.markdown("### 📊 Graph Statistics")
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("Nodes", stats.get("nodes", 0))
                        col2.metric("Edges", stats.get("edges", 0))
                        col3.metric("Density", f"{stats.get('density', 0):.4f}")
                        col4.metric("Connected", "✅ Yes" if stats.get("is_connected") else "❌ No")
                        
                        # Show KB save info
                        if stats.get("kb_saved", 0) > 0:
                            st.success(f"💾 Saved {stats['kb_saved']} triples to knowledge base")

                        # Show top entities
                        if stats.get("top_degree_entities"):
                            st.markdown("### 🏆 Top Entities (by connections)")
                            top_entities = stats["top_degree_entities"][:10]
                            for i, entity in enumerate(top_entities, 1):
                                st.write(f"**#{i}** `{entity['node']}` - {entity['degree']} connections")

                        # Display triples
                        if triples:
                            st.markdown(f"### 🔗 Extracted Triples ({len(triples)} total)")

                            # Sample triples
                            df_triples = pd.DataFrame(triples[:50])  # Show first 50
                            st.dataframe(df_triples, use_container_width=True)

                            # Interactive visualization
                            st.markdown("### 🎨 Interactive Knowledge Graph")

                            try:
                                # Create network
                                net = Network(
                                    height="600px",
                                    width="100%",
                                    bgcolor="#ffffff",
                                    font_color="black",
                                    directed=True
                                )

                                # Limit for performance
                                display_triples = triples[:100]

                                # Add nodes and edges
                                all_nodes = set()
                                for t in display_triples:
                                    e1, rel, e2 = t["entity1"], t["relation"], t["entity2"]
                                    all_nodes.add(e1)
                                    all_nodes.add(e2)

                                # Add nodes with sizing based on degree
                                node_degrees = {}
                                for t in display_triples:
                                    e1, e2 = t["entity1"], t["entity2"]
                                    node_degrees[e1] = node_degrees.get(e1, 0) + 1
                                    node_degrees[e2] = node_degrees.get(e2, 0) + 1

                                for node in all_nodes:
                                    degree = node_degrees.get(node, 1)
                                    size = max(20, min(50, degree * 5))
                                    net.add_node(
                                        node,
                                        label=node[:25],
                                        size=size,
                                        color="#4B4DED",
                                        title=f"{node}\nConnections: {degree}"
                                    )

                                # Add edges
                                for t in display_triples:
                                    e1, rel, e2 = t["entity1"], t["relation"], t["entity2"]
                                    net.add_edge(e1, e2, label=rel[:20], color="#666666", title=rel)

                                # Configure physics
                                net.set_options("""
                                var options = {
                                  "physics": {
                                    "enabled": true,
                                    "stabilization": {"iterations": 100},
                                    "barnesHut": {
                                      "gravitationalConstant": -8000,
                                      "springConstant": 0.04,
                                      "damping": 0.09
                                    }
                                  }
                                }
                                """)

                                # Save and display
                                net.save_graph("knowledge_graph.html")
                                with open("knowledge_graph.html", "r", encoding="utf-8") as f:
                                    html_content = f.read()
                                components.html(html_content, height=600, scrolling=False)

                            except Exception as e:
                                st.error(f"Could not create visualization: {e}")
                                st.info("Showing raw triples data instead")
                                st.dataframe(pd.DataFrame(triples))

                            # Download options
                            st.markdown("### 📥 Export Options")
                            col1, col2 = st.columns(2)

                            with col1:
                                # CSV download
                                csv_data = pd.DataFrame(triples).to_csv(index=False)
                                st.download_button(
                                    "💾 Download Triples as CSV",
                                    csv_data,
                                    file_name=f"triples_{selected_dataset.split('.')[0]}.csv",
                                    mime="text/csv",
                                    use_container_width=True
                                )

                            with col2:
                                # JSON download
                                json_data = json.dumps(triples, indent=2)
                                st.download_button(
                                    "💾 Download Triples as JSON",
                                    json_data,
                                    file_name=f"triples_{selected_dataset.split('.')[0]}.json",
                                    mime="application/json",
                                    use_container_width=True
                                )

                        else:
                            st.warning("⚠️ No triples were extracted from the dataset.")

                    else:
                        st.error(f"❌ Extraction failed: {extract_data.get('error', 'Unknown error')}")

# Semantic Search Page
elif st.session_state.current_page == "🔍 Semantic Search":
    if not st.session_state.token:
        st.warning("🔒 Please log in to use semantic search")
        st.session_state.current_page = "🔐 Authentication"
        st.rerun()
    else:
        st.markdown("<div class='sub-header'>🔍 Semantic Search & Exploration</div>", unsafe_allow_html=True)

        headers = get_headers()

        # Check system status
        try:
            status_resp = requests.get(f"{API_URL}/semantic/status", headers=headers)
            if status_resp.status_code == 200:
                status_data = status_resp.json()
                search_ready = status_data.get("search_ready", False)
                graph_available = status_data.get("graph_available", False)
                graph_files = status_data.get("graph_files", [])
            else:
                search_ready = False
                graph_available = False
                graph_files = []
        except:
            search_ready = False
            graph_available = False
            graph_files = []

        # Graph Loading Section
        st.markdown("### 📁 Load Knowledge Graph")

        if graph_files:
            st.success(f"✅ Found {len(graph_files)} graph file(s)")

            # Graph selection and loading
            col1, col2 = st.columns([2, 1])

            with col1:
                selected_graph = st.selectbox(
                    "Select a knowledge graph to load:",
                    graph_files,
                    help="Choose which extracted knowledge graph to load for semantic search"
                )

            with col2:
                if st.button("🔄 Load Graph", type="primary", use_container_width=True):
                    with st.spinner("Loading graph into semantic search..."):
                        try:
                            load_resp = requests.post(f"{API_URL}/semantic/load_graph", headers=headers)
                            if load_resp.status_code == 200:
                                load_data = load_resp.json()
                                st.success("✅ Graph loaded successfully!")
                                time.sleep(2)
                                st.rerun()
                            else:
                                error_data = load_resp.json()
                                st.error(f"❌ Failed to load graph: {error_data.get('error', 'Unknown error')}")
                        except Exception as e:
                            st.error(f"❌ Load error: {e}")

            # Show current status
            col3, col4, col5 = st.columns(3)

            with col3:
                if graph_available:
                    st.success("✅ Graph Files Available")
                else:
                    st.error("❌ No Graph Files")

            with col4:
                if search_ready:
                    st.success("✅ Search Ready")
                    if status_data.get("search_nodes"):
                        st.info(f"Nodes: {status_data['search_nodes']}")
                else:
                    st.warning("⚠️ Search Not Loaded")

            with col5:
                if st.button("🔄 Refresh Status", type="secondary", use_container_width=True):
                    st.rerun()

        else:
            st.error("""
            ## ❌ No Knowledge Graph Found!

            To use semantic search, you need to:

            1. **Upload a dataset** in the Upload section
            2. **Extract knowledge graph** in the Extract section
            3. **Return here** to load and search

            The system needs an extracted knowledge graph to perform semantic search.
            """)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🚀 Go to Upload Dataset", use_container_width=True):
                    st.session_state.current_page = "📤 Upload Dataset"
                    st.rerun()
            with col2:
                if st.button("🔗 Go to Extract KG", use_container_width=True):
                    st.session_state.current_page = "🔗 Extract Knowledge Graph"
                    st.rerun()

            st.stop()

        # Only show search interface if search is ready
        if not search_ready:
            st.warning("""
            ## ⚠️ Search Not Ready

            Please load a knowledge graph using the options above to enable semantic search.

            **If you just extracted a graph:**
            - Make sure the extraction completed successfully
            - Click the **🔄 Load Graph** button above
            - Wait for the confirmation message
            """)
            st.stop()

        # Search Interface (only shown when search is ready)
        st.markdown("---")
        st.markdown("### 🎯 Search Configuration")

        # Display current graph info
        if status_data.get("search_nodes", 0) > 0:
            st.success(f"🔍 Ready to search! Loaded graph has **{status_data.get('search_nodes', 0)}** nodes")

        col1, col2 = st.columns([3, 1])

        with col1:
            search_query = st.text_input(
                "🔍 Enter your search query:",
                placeholder="e.g., countries in Europe, medical treatments, AI applications...",
                help="Describe what you're looking for in natural language"
            )

        with col2:
            top_k = st.number_input(
                "Top K results",
                min_value=1,
                max_value=20,
                value=5,
                help="Number of most relevant results to show"
            )

        col3, col4 = st.columns(2)

        with col3:
            search_mode = st.radio(
                "Search Mode",
                ["🔎 Node Search", "🕸️ Subgraph Exploration"],
                help="Search individual nodes or explore connected subgraphs"
            )

        with col4:
            if search_mode == "🕸️ Subgraph Exploration":
                exploration_radius = st.slider(
                    "Exploration Radius",
                    min_value=1,
                    max_value=3,
                    value=1,
                    help="How many hops away from results to explore"
                )

        if st.button("🚀 Perform Search", type="primary", use_container_width=True):
            if not search_query.strip():
                st.warning("⚠️ Please enter a search query")
            else:
                with st.spinner("🔍 Searching knowledge graph..."):
                    if search_mode == "🔎 Node Search":
                        # Node search
                        search_data = {"query": search_query, "top_k": top_k}
                        try:
                            result_resp = requests.post(f"{API_URL}/semantic/search", json=search_data, headers=headers)
                            if result_resp.status_code == 200:
                                result_data = result_resp.json()
                                results = result_data.get("results", [])

                                if results:
                                    st.success(f"🎉 Found {len(results)} relevant nodes")

                                    # Display results
                                    for i, result in enumerate(results, 1):
                                        with st.expander(f"#{i} {result['node']} (Score: {result['score']:.3f})", expanded=i==1):
                                            col_a, col_b, col_c = st.columns(3)
                                            col_a.metric("Similarity", f"{result['score']:.3f}")
                                            col_b.metric("Connections", result['degree'])
                                            col_c.metric("Rank", i)

                                else:
                                    st.info("🤷 No relevant nodes found. Try a different query.")
                            else:
                                error_data = result_resp.json()
                                st.error(f"❌ Search failed: {error_data.get('error', 'Unknown error')}")
                        except Exception as e:
                            st.error(f"❌ Search error: {e}")

                    else:  # Subgraph Exploration
                        # Subgraph search
                        subgraph_data = {
                            "query": search_query,
                            "top_k": top_k,
                            "radius": exploration_radius
                        }
                        try:
                            result_resp = requests.post(f"{API_URL}/semantic/subgraph", json=subgraph_data, headers=headers)
                            if result_resp.status_code == 200:
                                result_data = result_resp.json()
                                top_nodes = result_data.get("top_nodes", [])
                                subgraph = result_data.get("subgraph")

                                if top_nodes:
                                    st.success(f"🎉 Found {len(top_nodes)} relevant nodes")

                                    # Display top nodes
                                    st.markdown("### 🏆 Top Matching Nodes")
                                    for i, node in enumerate(top_nodes, 1):
                                        st.write(f"**#{i}** `{node['node']}` - Score: {node['score']:.3f}, Connections: {node['degree']}")

                                    # Visualize subgraph if available
                                    if subgraph and subgraph.get('nodes'):
                                        st.markdown("### 🕸️ Connected Subgraph")

                                        node_count = len(subgraph['nodes'])
                                        edge_count = len(subgraph['links'])

                                        col_x, col_y = st.columns(2)
                                        col_x.metric("Nodes in Subgraph", node_count)
                                        col_y.metric("Relationships", edge_count)

                                        # Simple visualization
                                        try:
                                            # Create network
                                            net = Network(
                                                height="600px",
                                                width="100%",
                                                bgcolor="#ffffff",
                                                font_color="black",
                                                directed=True
                                            )

                                            # Highlight top nodes
                                            top_node_names = [node['node'] for node in top_nodes]

                                            for node in subgraph['nodes']:
                                                node_id = node['id']
                                                if node_id in top_node_names:
                                                    # Highlight search results
                                                    net.add_node(
                                                        node_id,
                                                        label=node_id,
                                                        color="#FF6B6B",
                                                        size=30,
                                                        font={"size": 16}
                                                    )
                                                else:
                                                    net.add_node(node_id, label=node_id, color="#4B4DED", size=20)

                                            # Add edges
                                            for link in subgraph['links']:
                                                source = link['source']
                                                target = link['target']
                                                relation = link.get('label', link.get('relation', 'related'))
                                                net.add_edge(
                                                    source,
                                                    target,
                                                    label=relation[:15],
                                                    color="#666666",
                                                    title=relation
                                                )

                                            # Configure layout
                                            net.set_options("""
                                            var options = {
                                              "physics": {
                                                "enabled": true,
                                                "stabilization": {"iterations": 100}
                                              }
                                            }
                                            """)

                                            net.save_graph("search_subgraph.html")

                                            # Display
                                            with open("search_subgraph.html", "r", encoding="utf-8") as f:
                                                html_content = f.read()
                                            components.html(html_content, height=600, scrolling=False)

                                        except Exception as e:
                                            st.error(f"Visualization error: {e}")
                                            st.json(subgraph)

                                else:
                                    st.info("🤷 No relevant nodes found. Try a different query.")
                            else:
                                error_data = result_resp.json()
                                st.error(f"❌ Subgraph search failed: {error_data.get('error', 'Unknown error')}")
                        except Exception as e:
                            st.error(f"❌ Search error: {e}")

# Feedback System Page
elif st.session_state.current_page == "💬 Feedback System":
    if not st.session_state.token:
        st.warning("🔒 Please log in to submit feedback")
        st.session_state.current_page = "🔐 Authentication"
        st.rerun()
    else:
        st.markdown("<div class='sub-header'>💬 Feedback System</div>", unsafe_allow_html=True)
        
        st.markdown("""
        ### Help Improve KnowMap!
        Your feedback helps us improve the knowledge graph accuracy and user experience.
        Please share your thoughts about search results, interface, or any issues you encountered.
        """)
        
        with st.form("feedback_form"):
            query = st.text_input("🔍 Query you searched for:", placeholder="Enter the query you used")
            rating = st.slider("⭐ Rate your experience (1-5):", 1, 5, 3, 
                             help="1 = Poor, 5 = Excellent")
            comments = st.text_area("💭 Additional comments:", 
                                  placeholder="Any suggestions or issues you encountered...",
                                  height=100)
            
            submit_feedback = st.form_submit_button("📤 Submit Feedback", use_container_width=True)
            
            if submit_feedback:
                if not query.strip():
                    st.error("❌ Please enter the query you searched for")
                else:
                    with st.spinner("Submitting feedback..."):
                        feedback_data = {
                            "query": query,
                            "rating": int(rating),
                            "comments": comments
                        }
                        data, status = make_request("feedback", 'POST', feedback_data)
                        
                        
                        if status in (200, 201):

                            st.success("✅ Thank you for your feedback!")
                            st.balloons()
                            time.sleep(1)  
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to submit feedback: {data.get('error', 'Unknown error')}")
        

# Admin Dashboard Page
elif st.session_state.current_page == "⚙️ Admin Dashboard":
    if not st.session_state.token:
        st.warning("🔒 Please log in to access admin features")
        st.session_state.current_page = "🔐 Authentication"
        st.rerun()
    else:
        # Check admin access
        has_access, message = check_admin_access()
        
        if not has_access:
            st.error("🚫 Access Denied")
            st.warning("""
            **Admin privileges required!**
            
            You need administrator permissions to access this section.
            
            **If you are the system administrator:**
            - Use the **Admin Setup** tab in the Authentication page
            - Or contact your system administrator for access
            """)
            
            # Show regular user statistics instead
            st.markdown("### 📊 Your Statistics")
            stats_data, stats_status = make_request("feedback/stats")
            if stats_status == 200:
                col1, col2 = st.columns(2)
                col1.metric("Your Feedback", stats_data.get("total_feedback", 0))
                col2.metric("Your Avg Rating", f"{stats_data.get('average_rating', 0):.1f} ⭐")
            
            st.stop()
        
        # If we get here, user is admin
        st.markdown("<div class='sub-header'>⚙️ Admin Dashboard</div>", unsafe_allow_html=True)
        st.success("👑 Welcome, Administrator!")
        
        # Admin statistics
        try:
            stats_resp = requests.get(f"{API_URL}/admin/stats", headers=get_headers())
            if stats_resp.status_code == 200:
                stats_data = stats_resp.json()
                
                # Display metrics
                st.markdown("### 📈 System Overview")
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Users", stats_data.get("total_users", 0))
                col2.metric("Knowledge Triples", stats_data.get("total_triples", 0))
                col3.metric("Unique Entities", stats_data.get("total_entities", 0))
                
                
                col5, col6, col7= st.columns(3)
                col5.metric("Unique Relations", stats_data.get("total_relations", 0))
                col6.metric("Admin Users", stats_data.get("admin_users", 0))
                col7.metric("Regular Users", stats_data.get("regular_users", 0))
            else:
                st.error("Failed to load admin statistics")
        except Exception as e:
            st.error(f"Error connecting to admin API: {e}")
        
        # CRUD Operations Section
        st.markdown("---")
        st.markdown("### 🔧 Knowledge Base Management")
        
        tab1, tab2, tab3 = st.tabs(["📋 View All Triples", "➕ Add New Triple", "🗑️ Delete Triple"])
        
        with tab1:
            st.markdown("#### All Knowledge Base Triples")
            triples = fetch_knowledge_base()
            if triples:
                df = pd.DataFrame(triples)
                st.dataframe(df, use_container_width=True)
                st.info(f"Total triples in knowledge base: {len(triples)}")
            else:
                st.info("No triples found in knowledge base")
        
        with tab2:
            st.markdown("#### Add New Knowledge Triple")
            with st.form("add_triple_form"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    entity1 = st.text_input("Entity 1", placeholder="e.g., Paris")
                with col2:
                    relation = st.text_input("Relation", placeholder="e.g., capital_of")
                with col3:
                    entity2 = st.text_input("Entity 2", placeholder="e.g., France")
                
                add_btn = st.form_submit_button("➕ Add Triple", use_container_width=True)
                
                if add_btn:
                    if not all([entity1, relation, entity2]):
                        st.error("Please fill all fields")
                    else:
                        if add_kb_triple(entity1, relation, entity2):
                            st.success("✅ Triple added successfully!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Failed to add triple")
        
        with tab3:
            st.markdown("#### Delete Knowledge Triple")
            triples = fetch_knowledge_base()
            if triples:
                triple_options = {f"{t['id']}: {t['entity1']} - {t['relation']} - {t['entity2']}": t['id'] for t in triples}
                selected_triple = st.selectbox("Select triple to delete:", list(triple_options.keys()))
                
                if st.button("🗑️ Delete Selected Triple", type="primary", use_container_width=True):
                    triple_id = triple_options[selected_triple]
                    if delete_kb_triple(triple_id):
                        st.success("✅ Triple deleted successfully!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Failed to delete triple")
            else:
                st.info("No triples available to delete")
        # Show recent feedback (if available)
        st.markdown("---")
        st.markdown("### 📝 Recent User Feedback")
        try:
            if os.path.exists('feedback.csv'):
                df = pd.read_csv('feedback.csv')
                # Normalize column names for safety
                df.columns = [c.strip().lower() for c in df.columns]

               # Ensure all expected columns exist
                for col in ["username", "query", "rating", "comment", "timestamp"]:
                    if col not in df.columns:
                        df[col] = None

                if 'comment' in df.columns and 'comments' not in df.columns:
                    df['comments'] = df['comment']
                    
                if not df.empty:
                    recent_feedback = df.tail(10)[['timestamp', 'username', 'query', 'rating', 'comments']]
                    st.dataframe(recent_feedback, use_container_width=True)
                else:
                    st.info("No feedback data available yet")
            else:
                st.info("No feedback data available yet")
        except Exception as e:
            st.error(f"Error loading feedback: {e}")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>"
    "🧠 KnowMap - Knowledge Graph Platform | "
    "Built with Streamlit & Flask | "
    f"© {datetime.now().year}"
    "</div>",
    unsafe_allow_html=True
)