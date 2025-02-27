import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import re
import json
from concurrent.futures import ThreadPoolExecutor

# Set page configuration
st.set_page_config(
    page_title="Price Comparison Tool",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .main-header {
        color: #1E88E5;
        text-align: center;
    }
    .search-results {
        margin-top: 20px;
        padding: 10px;
        border-radius: 5px;
        background-color: #f0f2f6;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session states
if 'products' not in st.session_state:
    st.session_state.products = pd.DataFrame(columns=['Product Name', 'SKU', 'Your Price', 'Competitor', 'Competitor Price', 'Price Difference', 'Date Added'])
if 'search_results' not in st.session_state:
    st.session_state.search_results = []

def search_retailer(retailer, sku):
    """
    Search for product prices at a specific retailer
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    retailers = {
        'Amazon': f'https://www.amazon.com/s?k={sku}',
        'Walmart': f'https://www.walmart.com/search?q={sku}',
        'Best Buy': f'https://www.bestbuy.com/site/searchpage.jsp?st={sku}'
    }
    
    try:
        url = retailers[retailer]
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return {
                'Retailer': retailer,
                'URL': url,
                'Status': 'Available'
            }
    except Exception as e:
        return {
            'Retailer': retailer,
            'URL': retailers[retailer],
            'Status': 'Error checking availability'
        }

def search_all_retailers(sku):
    """
    Search all retailers concurrently
    """
    retailers = ['Amazon', 'Walmart', 'Best Buy']
    results = []
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(search_retailer, retailer, sku) for retailer in retailers]
        for future in futures:
            result = future.result()
            if result:
                results.append(result)
    
    return results

# App header
st.markdown("<h1 class='main-header'>Product Price Comparison Tool</h1>", unsafe_allow_html=True)

# Create tabs for different functionalities
tab1, tab2 = st.tabs(["Manual Price Tracking", "SKU Search"])

with tab1:
    # Original manual price tracking functionality
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Product Price Comparison")
        if not st.session_state.products.empty:
            def highlight_price_difference(val):
                if isinstance(val, float):
                    color = 'red' if val > 0 else 'green'
                    return f'color: {color}'
                return ''
            
            styled_df = st.session_state.products.style.applymap(
                highlight_price_difference,
                subset=['Price Difference']
            )
            st.dataframe(styled_df, use_container_width=True)
        else:
            st.info("No products added yet. Use the sidebar to add products.")

    with col2:
        if not st.session_state.products.empty:
            st.subheader("Price Analysis")
            total_products = len(st.session_state.products)
            competitive_prices = len(st.session_state.products[st.session_state.products['Price Difference'] <= 0])
            
            st.metric("Total Products", total_products)
            st.metric("Competitive Prices", competitive_prices)
            st.metric("Need Review", total_products - competitive_prices)
            
            avg_price_diff = st.session_state.products['Price Difference'].mean()
            st.metric("Average Price Difference", f"${avg_price_diff:.2f}")

with tab2:
    st.subheader("Search by SKU")
    col1, col2 = st.columns([3, 1])
    
    with col1:
        sku_input = st.text_input("Enter Product SKU", placeholder="Enter SKU number...")
    
    with col2:
        retailers_to_search = st.multiselect(
            "Select Retailers",
            ["Amazon", "Walmart", "Best Buy"],
            default=["Amazon", "Walmart", "Best Buy"]
        )
    
    if st.button("Search Prices", type="primary"):
        if sku_input:
            with st.spinner("Searching retailers..."):
                results = search_all_retailers(sku_input)
                
                if results:
                    st.success(f"Found product listings for SKU: {sku_input}")
                    
                    # Display results in a nice format
                    st.markdown("### Available at:")
                    for result in results:
                        with st.container():
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.write(f"**{result['Retailer']}** - {result['Status']}")
                            with col2:
                                st.markdown(f"[View Product]({result['URL']})")
                            st.markdown("---")
                    
                    st.info("Note: Due to retailer restrictions, exact prices are not shown. Click the links to view current prices on each website.")
                else:
                    st.warning("No results found for this SKU. Try another SKU number.")
        else:
            st.error("Please enter a SKU number")

# Sidebar for adding new products
with st.sidebar:
    st.header("Add New Product")
    product_name = st.text_input("Product Name")
    sku = st.text_input("SKU")
    your_price = st.number_input("Your Price", min_value=0.0, value=0.0, step=0.01)
    competitor = st.text_input("Competitor Name")
    competitor_price = st.number_input("Competitor Price", min_value=0.0, value=0.0, step=0.01)
    
    if st.button("Add Product"):
        if product_name and competitor:
            new_product = {
                'Product Name': product_name,
                'SKU': sku,
                'Your Price': your_price,
                'Competitor': competitor,
                'Competitor Price': competitor_price,
                'Price Difference': round(your_price - competitor_price, 2),
                'Date Added': datetime.now().strftime("%Y-%m-%d")
            }
            st.session_state.products = pd.concat([
                st.session_state.products,
                pd.DataFrame([new_product])
            ], ignore_index=True)
            st.success("Product added successfully!")

# Add export functionality
if not st.session_state.products.empty:
    st.download_button(
        label="Export Data to CSV",
        data=st.session_state.products.to_csv(index=False).encode('utf-8'),
        file_name=f"price_comparison_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
