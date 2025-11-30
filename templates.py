"""
HTML templates for product dashboard
"""

def get_dashboard_css():
    """Get CSS styles for dashboard"""
    return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 900px;
            margin: 40px auto;
            background: white;
            padding: 2.5rem;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.15);
        }

        h1 {
            color: #2d3748;
            margin-bottom: 0.5rem;
            font-size: 2.25rem;
            font-weight: 700;
        }

        .product-meta {
            color: #718096;
            font-size: 0.875rem;
            margin-bottom: 2rem;
            padding-bottom: 1.5rem;
            border-bottom: 2px solid #e2e8f0;
        }

        .details-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        .detail-item {
            background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
            padding: 1.5rem;
            border-radius: 12px;
            border-left: 4px solid #667eea;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .detail-item:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
        }

        .detail-label {
            font-size: 0.75rem;
            color: #718096;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
            font-weight: 600;
        }

        .detail-value {
            font-size: 1.5rem;
            color: #2d3748;
            font-weight: 600;
        }

        .detail-value.price {
            color: #48bb78;
        }

        .detail-value.quantity {
            color: #4299e1;
        }

        .links-section {
            margin-top: 2.5rem;
            padding-top: 2rem;
            border-top: 2px solid #e2e8f0;
        }

        .links-section h2 {
            font-size: 1.5rem;
            color: #2d3748;
            margin-bottom: 1rem;
            font-weight: 600;
        }

        .link-item {
            display: block;
            padding: 1rem 1.25rem;
            margin-bottom: 0.75rem;
            background: #f7fafc;
            border-radius: 8px;
            text-decoration: none;
            color: #667eea;
            transition: all 0.2s;
            border: 1px solid #e2e8f0;
            word-break: break-all;
        }

        .link-item:hover {
            background: #edf2f7;
            transform: translateX(8px);
            border-color: #667eea;
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.1);
        }

        .footer {
            margin-top: 3rem;
            padding-top: 2rem;
            border-top: 1px solid #e2e8f0;
            text-align: center;
            color: #a0aec0;
            font-size: 0.875rem;
        }

        .error-container {
            text-align: center;
            padding: 3rem 0;
        }

        .error-icon {
            font-size: 4rem;
            margin-bottom: 1rem;
        }

        .error-title {
            font-size: 1.5rem;
            color: #e53e3e;
            margin-bottom: 1rem;
        }

        .error-message {
            color: #718096;
            font-size: 1.125rem;
        }

        @media (max-width: 768px) {
            body {
                padding: 10px;
            }

            .container {
                padding: 1.5rem;
                margin: 20px auto;
                border-radius: 12px;
            }

            h1 {
                font-size: 1.75rem;
            }

            .details-grid {
                grid-template-columns: 1fr;
                gap: 1rem;
            }

            .detail-value {
                font-size: 1.25rem;
            }
        }
    """

def render_product_dashboard(product: dict) -> str:
    """Render product dashboard HTML"""

    # Format currency
    cost = f"${product['cost_per_unit']:.2f}" if product.get('cost_per_unit') else 'N/A'
    tax = f"${product['tax']:.2f}" if product.get('tax') else 'N/A'
    retail = f"${product['retail_price']:.2f}" if product.get('retail_price') else 'N/A'

    # Parse links
    links_html = ""
    if product.get('links'):
        links_html = "<div class='links-section'><h2>📎 Related Links</h2>"
        for link in product['links'].split('\n'):
            link = link.strip()
            if link:
                links_html += f"<a href='{link}' target='_blank' rel='noopener noreferrer' class='link-item'>{link}</a>"
        links_html += "</div>"

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="description" content="Product dashboard for {product['product_name']}">
        <meta name="robots" content="noindex, nofollow">
        <title>{product['product_name']} - Product Dashboard</title>
        <style>{get_dashboard_css()}</style>
    </head>
    <body>
        <div class="container">
            <h1>📦 {product['product_name']}</h1>
            <div class="product-meta">
                Product ID: {product['uuid']}
            </div>

            <div class="details-grid">
                <div class="detail-item">
                    <div class="detail-label">📅 Purchase Date</div>
                    <div class="detail-value">{product.get('date_purchased', 'N/A')}</div>
                </div>

                <div class="detail-item">
                    <div class="detail-label">📊 Quantity Available</div>
                    <div class="detail-value quantity">{product.get('qty_available', 'N/A')}</div>
                </div>

                <div class="detail-item">
                    <div class="detail-label">💵 Cost Per Unit</div>
                    <div class="detail-value price">{cost}</div>
                </div>

                <div class="detail-item">
                    <div class="detail-label">🏪 Store</div>
                    <div class="detail-value">{product.get('store', 'N/A')}</div>
                </div>

                <div class="detail-item">
                    <div class="detail-label">💰 Tax</div>
                    <div class="detail-value">{tax}</div>
                </div>

                <div class="detail-item">
                    <div class="detail-label">🏷️ Retail Price</div>
                    <div class="detail-value price">{retail}</div>
                </div>
            </div>

            {links_html}

            <div class="footer">
                <p>🤖 Product Dashboard • Powered by Discord Inventory Bot</p>
            </div>
        </div>
    </body>
    </html>
    """

def render_error_page(error_message: str) -> str:
    """Render error page"""
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Error - Product Dashboard</title>
        <style>{get_dashboard_css()}</style>
    </head>
    <body>
        <div class="container">
            <div class="error-container">
                <div class="error-icon">⚠️</div>
                <h1 class="error-title">Error</h1>
                <p class="error-message">{error_message}</p>
            </div>
            <div class="footer">
                <p>🤖 Product Dashboard • Powered by Discord Inventory Bot</p>
            </div>
        </div>
    </body>
    </html>
    """
