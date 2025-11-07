<p align="center">
  <img src="https://img.shields.io/badge/Version-2.0.0-blue?style=for-the-badge&logo=telegram" alt="Version">
  <img src="https://img.shields.io/badge/Python-3.9%2B-green?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Telegram-Bot-blue?style=for-the-badge&logo=telegram" alt="Telegram Bot">
  <img src="https://img.shields.io/badge/Privacy-Focused-red?style=for-the-badge&logo=lock" alt="Privacy">
</p>

<h1 align="center">
  🤖 Telegram Email Alias Manager
</h1>
<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
</p>

<p align="center">
  <b>Developed with ❤️ by <a href="https://github.com/Devil-bgmi">EVIL</a></b><br>
  📬 Manage Gmail aliases, plus-addressing, and custom domain emails — all from Telegram!
</p>

<p align="center">
  <strong>Generate unlimited email aliases instantly! Protect your privacy with disposable email addresses.</strong>
</p>

<p align="center">
  <img src="https://avatars.githubusercontent.com/u/184248010?v=4" alt="Banner" width="800">
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#commands">Commands</a> •
  <a href="#deployment">Deployment</a> •
  <a href="#contributing">Contributing</a>
</p>

---

## 🚀 Features

<div align="center">

| Feature | Description | Status |
|---------|-------------|--------|
| 🔒 **Plus Addressing** | `email+tag@domain.com` (Gmail-friendly) | ✅ Working |
| ⚡ **Dot Variants** | `e.mail@domain.com` (Limited variants) | ✅ Working |
| 🎯 **Custom Aliases** | `tag@yourdomain.com` (Catch-all domains) | ✅ Working |
| 📊 **Export Data** | Download all aliases as CSV | ✅ Working |
| 🛡️ **Rate Limiting** | Prevent abuse with smart limits | ✅ Working |
| 👑 **Admin Tools** | Owner commands for management | ✅ Working |

</div>

## ⚡ Quick Start

```bash
git clone https://github.com/YourUsername/telegram-alias-bot.git
cd telegram-alias-bot
pip install -r requirements.txt
echo "TELEGRAM_BOT_TOKEN=your_token_here" > .env
python3 alias_bot.py
