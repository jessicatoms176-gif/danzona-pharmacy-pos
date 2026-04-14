# Deploy DANZONA PHARMACY POS to Render.com

## Steps:

### 1. Create GitHub Repository
1. Go to https://github.com
2. Create new repository: "danzona-pharmacy-pos"
3. Upload these files:
   - `app.py`
   - `requirements.txt`
   - `Procfile`
   - `templates/` (entire folder)
   - `README.md`

### 2. Deploy on Render
1. Go to https://render.com
2. Click "Sign Up" → Use GitHub
3. Click "New" → "Web Service"
4. Select your GitHub repo
5. Configure:
   - **Name**: danzona-pharmacy
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
6. Click "Create Web Service"

### 3. Your app is live!
- Access at: `https://danzona-pharmacy.onrender.com`
- Login: `admin` / `admin123`

## Note:
The database will reset on free tier. For persistent storage, connect a Render PostgreSQL database in the dashboard.

---

## For Development (Local)
```bash
pip install flask gunicorn
python app.py
```
Open http://localhost:5000