import os
from dotenv import load_dotenv

# Load .env file only if it exists (for local development)
load_dotenv()

# Debug: print all environment variables that start with our prefixes
print("=== DEBUG: Environment Variables ===")
for key in os.environ:
    if key.startswith(('TELEGRAM_', 'ADMIN_', 'SUPABASE_')):
        print(f"{key} = {'*' * len(str(os.environ[key])) if 'TOKEN' in key or 'KEY' in key else os.environ[key]}")

# Bot credentials
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_BOT_TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN not found")
    print("Available env vars:", [k for k in os.environ.keys() if 'TELEGRAM' in k])
    raise ValueError("TELEGRAM_BOT_TOKEN mancante nelle variabili d'ambiente")

# Admin IDs
admin_ids_str = os.environ.get('ADMIN_IDS')
if not admin_ids_str:
    print("ERROR: ADMIN_IDS not found")
    print("Available env vars:", [k for k in os.environ.keys() if 'ADMIN' in k])
    raise ValueError("ADMIN_IDS mancante nelle variabili d'ambiente")

ADMIN_IDS = [int(id.strip()) for id in admin_ids_str.split(',') if id.strip()]

# Supabase credentials
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: Supabase credentials not found")
    print("SUPABASE vars:", [k for k in os.environ.keys() if 'SUPABASE' in k])
    raise ValueError("Credenziali Supabase mancanti nelle variabili d'ambiente")

print("✅ Configurazione caricata correttamente")
print(f"👥 Admin IDs configurati: {ADMIN_IDS}")
