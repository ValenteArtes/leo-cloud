# AI Telegram Bot Setup (Render)

Deploy your own ultra-fast, intelligent Telegram assistant using Groq and Microsoft Edge Text-to-Speech! 

Click the button below to **deploy for free** on Render. The system will prompt you for your API Keys, the Bot's name, and the Voice type!

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/ValenteArtes/leo-cloud)

## How to Configure

When you click "Deploy to Render", fill out the Environment Variables:
1. **TELEGRAM_BOT_TOKEN**: Your Telegram Bot token from [@BotFather](https://t.me/botfather).
2. **GROQ_API_KEY**: Your insanely fast Llama 3 API Key from [Groq Cloud](https://console.groq.com/keys).
3. **OWNER_TELEGRAM_ID**: Your personal Telegram ID (Get it from `@userinfobot`). If set to `0`, everyone can use the bot.
4. **AGENT_NAME**: The name of your AI (e.g., *Léo*, *Maria*).
5. **AGENT_VOICE**: The TTS voice to use (e.g., `pt-BR-AntonioNeural` for Male, `pt-BR-FranciscaNeural` for Female).
6. **GOOGLE_CREDENTIALS**: (Optional) Open the `credentials.json` file from your Google API Service Account, copy everything, and paste the raw JSON text here to enable Google Sheets integration!

Done! The bot will be online forever 24h a day automatically.
