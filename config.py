import os
from dotenv import load_dotenv

# Load .env solo in locale, Railway usa variabili d'ambiente native
load_dotenv()

# Bot credentials
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN mancante nelle variabili d'ambiente")

# Admin IDs (multipli supportati)
admin_ids_str = os.getenv('ADMIN_IDS')
if not admin_ids_str:
    raise ValueError("ADMIN_IDS mancante nelle variabili d'ambiente")

ADMIN_IDS = [int(id.strip()) for id in admin_ids_str.split(',') if id.strip()]

# Supabase credentials
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Verifica che i valori non siano None
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Credenziali Supabase mancanti nelle variabili d'ambiente")

print("✅ Configurazione caricata correttamente")
print(f"👥 Admin IDs configurati: {ADMIN_IDS}")
