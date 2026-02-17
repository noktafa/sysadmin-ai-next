# GitHub Repository Setup Instructions

Since `gh` CLI is not available, follow these steps to create the GitHub repository:

## Option 1: Using GitHub Web Interface

1. Go to https://github.com/new
2. Enter repository name: `sysadmin-ai-next`
3. Choose visibility (Public or Private)
4. Do NOT initialize with README (we already have one)
5. Click "Create repository"
6. Follow the push instructions:

```bash
cd /root/.openclaw/workspace/sysadmin-ai-next
git remote add origin https://github.com/YOUR_USERNAME/sysadmin-ai-next.git
git branch -M main
git push -u origin main
```

## Option 2: Using curl (if you have a GitHub token)

```bash
# Set your GitHub token
export GITHUB_TOKEN="your_token_here"

# Create the repository
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/user/repos \
  -d '{"name":"sysadmin-ai-next","private":false}'

# Then push
git remote add origin https://github.com/YOUR_USERNAME/sysadmin-ai-next.git
git push -u origin main
```

## Current Status

- Local repository initialized at: `/root/.openclaw/workspace/sysadmin-ai-next`
- Initial branch: `main`
- Ready to push to remote

## After Repository Creation

Once the GitHub repo is created and linked:

```bash
# Push existing code
git push -u origin main

# Enable branch protection (optional)
# - Require pull request reviews
# - Require status checks to pass
```
