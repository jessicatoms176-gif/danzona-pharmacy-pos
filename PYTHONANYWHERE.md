# DANZONA PHARMACY POS - PythonAnywhere Deployment

## Step 1: Upload Files
1. Go to https://pythonanywhere.com → Login
2. Click "Files" tab
3. Upload these files:
   - app.py
   - requirements.txt

## Step 2: Create templates folder
1. Click "New directory" → name: `templates`
2. Go into templates folder
3. Upload all HTML files:
   - index.html
   - pos.html
   - product.html
   - inventory.html
   - customer.html
   - customers.html
   - sales.html
   - reports.html
   - messages.html
   - dashboard.html
   - login.html
   - receipt.html
   - settings.html
   - customer_display.html
   - custom_fields.html
   - work_order.html
   - account_payment.html
   - import_sales.html

## Step 3: Install and Run
1. Click "Consoles" → "Bash"
2. Run: 
```
pip install -r requirements.txt
python app.py
```

## Step 4: Access
Click "Web" tab → Your app URL is shown!

## Login
- Username: admin
- Password: admin123