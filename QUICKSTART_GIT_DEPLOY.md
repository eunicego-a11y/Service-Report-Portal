# Quick Git & Deployment Setup

## 1. Version Control (Git) — Quick Start

Your repo is already initialized. Here's how to use it from **VS Code**:

### From VS Code GUI (Easiest)

1. Open Source Control panel (Ctrl+Shift+G)
2. You'll see "Changes" with modified files
3. Click `+` next to files to "stage" them
4. Enter a commit message at the top
5. Click the checkmark to commit

### From Terminal (Alternative)

```powershell
cd "C:\Users\MCBTSI\Documents\MONDAY.COM\Web\service_report_app"

# Stage all changes
git add .

# Commit
git commit -m "Your message here"

# See commit history
git log --oneline

# Check status
git status
```

### Recommended First Commit

```powershell
git add .
git commit -m "Add DEPLOYMENT.md, Procfile, runtime.txt, and .env.example for production setup"
```

---

## 2. Push to GitHub (For Backup & Deployment)

1. Create a free GitHub account: https://github.com/signup
2. Create a new repository (don't add README, we have one)
3. In VS Code Terminal:
   ```powershell
   # Add GitHub as remote (replace YOUR_USERNAME/YOUR_REPO)
   git remote add origin https://github.com/YOUR_USERNAME/service_report_app.git
   git branch -M main
   git push -u origin main
   ```
4. Now your code is backed up on GitHub

---

## 3. Deploy to Production (Choose One)

### **Easiest: Railway.app**

1. Sign up: https://railway.app
2. Install Railway CLI: `npm install -g @railway/cli`
3. In project directory:
   ```powershell
   railway login
   railway link     # Create new project
   railway up       # Deploy
   ```
4. Set environment variables:
   ```powershell
   railway variables:add MONDAY_API_KEY=your_token
   railway variables:add SECRET_KEY=your_secret
   railway variables:add MONDAY_OAUTH_CLIENT_ID=your_id
   railway variables:add MONDAY_OAUTH_CLIENT_SECRET=your_secret
   railway variables:add MAIN_BOARD_ID=your_board
   railway variables:add LINKED_BOARD_ID=your_board
   # ... add other COL_* variables
   ```
5. Get your app URL and **update OAuth redirect URLs** in Monday.com and Google OAuth

### **Or: Heroku**

1. Sign up: https://heroku.com
2. Install Heroku CLI
3. In project directory:
   ```powershell
   heroku login
   heroku create your-app-name
   heroku config:set MONDAY_API_KEY=your_token
   heroku config:set SECRET_KEY=your_secret
   # ... add all environment variables
   git push heroku main
   ```
4. Get your app URL: `heroku open`

---

## 4. Access Deployed App

After deployment, your app will be at:

- **Railway**: `https://your-project-railway-app.up.railway.app`
- **Heroku**: `https://your-app-name.herokuapp.com`
- **Both**: Update these URLs in:
  - Monday.com OAuth settings
  - Google OAuth settings
  - Any other configs that reference localhost:5000

---

## 5. Daily Workflow

```powershell
# Before deployment
git add .
git commit -m "Brief description of changes"
git push origin main   # Back up to GitHub

# Deploy changes
railway up            # Railway.app
# or
git push heroku main  # Heroku
```

---

## 6. Troubleshooting

### "git is not recognized"

- Install Git: https://git-scm.com/download/win
- Restart VS Code terminal after install

### "Can't push to GitHub"

- Generate SSH key: https://docs.github.com/en/authentication/connecting-to-github-with-ssh
- Or use Personal Access Token instead of password

### App won't start

- Check logs: `railway logs` or `heroku logs --tail`
- Verify all environment variables are set
- Ensure `requirements.txt` is up to date
