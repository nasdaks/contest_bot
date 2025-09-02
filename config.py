import os
from dotenv import load_dotenv

load_dotenv()

# Debug per vedere cosa legge
print(f"SUPABASE_URL from env: {os.getenv('SUPABASE_URL')}")
print(f"SUPABASE_KEY from env: {os.getenv('SUPABASE_KEY')}")

# Bot credentials
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Admin IDs (multipli supportati)
admin_ids_str = os.getenv('ADMIN_IDS')
if not admin_ids_str:
    raise ValueError("ADMIN_IDS mancante nel file .env")

ADMIN_IDS = [int(id.strip()) for id in admin_ids_str.split(',') if id.strip()]

# Supabase credentials
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Verifica che i valori non siano None
if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERRORE: Valori Supabase mancanti nel file .env")
    print("Controlla che il file .env sia nella cartella corretta")
else:
    print("✅ Configurazione Supabase caricata correttamente")

# Debug per verificare admin IDs
print(f"👥 Admin IDs configurati: {ADMIN_IDS}")