import os
from dotenv import load_dotenv

load_dotenv()

# Hardcode temporaneo per Railway bug
TELEGRAM_BOT_TOKEN = "8218796110:AAF9GRTIJFpNkhTapDDMa0-jAJnyAz5N5lE"
ADMIN_IDS = [75439420, 446978945]
SUPABASE_URL = "https://ihsoxvqeeyxdnvijzmux.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imloc294dnFlZXl4ZG52aWp6bXV4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY3MDkzNzYsImV4cCI6MjA3MjI4NTM3Nn0.TtgZFlxmWJBsfAB_WvLqD7K23oURgsuPxaEEzoZuUzM"

print("✅ Configurazione hardcoded caricata")
print(f"👥 Admin IDs configurati: {ADMIN_IDS}")
