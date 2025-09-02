from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

# Connessione Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def test_connection():
    try:
        result = supabase.table('contest_settings').select("*").execute()
        print("✅ Connessione Supabase OK!")
        print(f"📊 Trovati {len(result.data)} contest nel database")
        return True
    except Exception as e:
        print(f"❌ Errore connessione: {e}")
        return False

def get_current_contest():
    """Ottieni il contest attivo"""
    try:
        result = supabase.table('contest_settings').select("*").eq('is_active', True).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Errore lettura contest: {e}")
        return None

def user_exists(telegram_id):
    """Controlla se utente esiste già"""
    try:
        result = supabase.table('users').select("telegram_id").eq('telegram_id', telegram_id).execute()
        return len(result.data) > 0
    except Exception as e:
        print(f"❌ Errore controllo utente: {e}")
        return False

def create_user(telegram_id, username, first_name, referred_by=None):
    """Crea nuovo utente"""
    try:
        referral_code = f"REF_{telegram_id}"
        
        user_data = {
            'telegram_id': telegram_id,
            'username': username,
            'first_name': first_name,
            'referral_code': referral_code,
            'referred_by': referred_by
        }
        
        result = supabase.table('users').insert(user_data).execute()
        print(f"✅ Utente creato: {telegram_id}")
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Errore creazione utente: {e}")
        return None

def get_user(telegram_id):
    """Ottieni dati utente"""
    try:
        result = supabase.table('users').select("*").eq('telegram_id', telegram_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Errore lettura utente: {e}")
        return None

def create_pending_referral(referrer_id, new_user_id):
    """Crea referral in stato pending"""
    try:
        referral_data = {
            'referrer_telegram_id': referrer_id,
            'referred_telegram_id': new_user_id,
            'status': 'pending'
        }
        
        result = supabase.table('referrals').insert(referral_data).execute()
        print(f"✅ Referral pending creato: {referrer_id} → {new_user_id}")
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Errore creazione referral: {e}")
        return None

def get_user_by_referral_code(referral_code):
    """Trova utente dal suo codice referral"""
    try:
        result = supabase.table('users').select("*").eq('referral_code', referral_code).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Errore ricerca referral code: {e}")
        return None

def complete_referral(referrer_id, new_user_id):
    """Completa referral e incrementa counter"""
    try:
        # Aggiorna il nuovo utente per indicare chi l'ha riferito
        supabase.table('users').update({
            'referred_by': referrer_id
        }).eq('telegram_id', new_user_id).execute()
        
        # Aggiorna referral da pending a completed
        supabase.table('referrals').update({
            'status': 'completed',
            'completed_at': 'NOW()'
        }).eq('referrer_telegram_id', referrer_id).eq('referred_telegram_id', new_user_id).execute()
        
        # Incrementa total_invites del referrer
        current_user = supabase.table('users').select('total_invites').eq('telegram_id', referrer_id).execute()
        new_count = current_user.data[0]['total_invites'] + 1
        
        supabase.table('users').update({
            'total_invites': new_count
        }).eq('telegram_id', referrer_id).execute()
        
        print(f"✅ Referral completato: {referrer_id} → {new_user_id}")
        return True
    except Exception as e:
        print(f"❌ Errore completamento referral: {e}")
        return False

def get_pending_referral(referred_user_id):
    """Trova referral pending per un utente"""
    try:
        result = supabase.table('referrals').select("*").eq('referred_telegram_id', referred_user_id).eq('status', 'pending').execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Errore ricerca referral pending: {e}")
        return None

def get_contest_status():
    """Ottieni stato attuale del contest"""
    try:
        result = supabase.table('contest_settings').select("status, results_announced").eq('is_active', True).execute()
        if result.data:
            return result.data[0]['status'], result.data[0]['results_announced']
        return None, False
    except Exception as e:
        print(f"❌ Errore lettura stato contest: {e}")
        return None, False

def start_final_verification():
    """Avvia processo di verifica finale"""
    try:
        supabase.table('contest_settings').update({
            'status': 'verification_in_progress',
            'final_verification_started_at': 'NOW()'
        }).eq('is_active', True).execute()
        
        print("✅ Verifica finale avviata")
        return True
    except Exception as e:
        print(f"❌ Errore avvio verifica: {e}")
        return False

def get_all_completed_referrals():
    """Ottieni tutti i referral da verificare"""
    try:
        result = supabase.table('referrals').select("*").eq('status', 'completed').execute()
        return result.data
    except Exception as e:
        print(f"❌ Errore lettura referrals: {e}")
        return []

def invalidate_referral(referrer_id, referred_id):
    """Marca referral come non valido"""
    try:
        supabase.table('referrals').update({
            'status': 'invalid',
            'final_verification_status': 'left_channel'
        }).eq('referrer_telegram_id', referrer_id).eq('referred_telegram_id', referred_id).execute()
        
        return True
    except Exception as e:
        print(f"❌ Errore invalidazione referral: {e}")
        return False

def recalculate_final_scores():
    """Ricalcola punteggi finali e posizioni"""
    try:
        # Reset tutti i punteggi
        supabase.table('users').update({'total_invites': 0}).neq('id', 0).execute()
        
        # Conta referral validi per ogni utente
        valid_referrals = supabase.table('referrals').select("referrer_telegram_id").eq('status', 'completed').execute()
        
        user_scores = {}
        for referral in valid_referrals.data:
            referrer_id = referral['referrer_telegram_id']
            user_scores[referrer_id] = user_scores.get(referrer_id, 0) + 1
        
        # Aggiorna punteggi nel database
        for user_id, score in user_scores.items():
            supabase.table('users').update({'total_invites': score}).eq('telegram_id', user_id).execute()
        
        # Calcola posizioni finali
        users_ranked = supabase.table('users').select("telegram_id, total_invites").order('total_invites', desc=True).execute()
        
        for position, user in enumerate(users_ranked.data, 1):
            supabase.table('users').update({'final_position': position}).eq('telegram_id', user['telegram_id']).execute()
        
        print(f"✅ Punteggi finali ricalcolati per {len(users_ranked.data)} utenti")
        return True
    except Exception as e:
        print(f"❌ Errore ricalcolo punteggi: {e}")
        return False

def complete_contest_verification():
    """Completa il processo di verifica"""
    try:
        supabase.table('contest_settings').update({
            'status': 'completed',
            'final_verification_completed_at': 'NOW()'
        }).eq('is_active', True).execute()
        
        print("✅ Contest completato")
        return True
    except Exception as e:
        print(f"❌ Errore completamento contest: {e}")
        return False

def get_top_5_users():
    """Ottieni top 5 utenti per notifica admin"""
    try:
        result = supabase.table('users').select("first_name, total_invites, final_position").order('total_invites', desc=True).limit(5).execute()
        return result.data
    except Exception as e:
        print(f"❌ Errore lettura top 5: {e}")
        return []

def get_total_participants():
    """Ottieni numero totale partecipanti"""
    try:
        result = supabase.table('users').select("id", count='exact').execute()
        return result.count
    except Exception as e:
        print(f"❌ Errore conteggio partecipanti: {e}")
        return 0

def announce_results():
    """Abilita visualizzazione risultati per gli utenti"""
    try:
        supabase.table('contest_settings').update({
            'results_announced': True
        }).eq('is_active', True).execute()
        
        print("✅ Risultati annunciati - stats sbloccate per tutti")
        return True
    except Exception as e:
        print(f"❌ Errore annuncio risultati: {e}")
        return False

def check_contest_end():
    """Controlla se il contest deve terminare automaticamente"""
    try:
        from datetime import datetime
        
        contest = get_current_contest()
        if not contest or contest['status'] != 'active':
            return False
        
        end_date = datetime.fromisoformat(contest['end_date'].replace('Z', '+00:00'))
        now = datetime.now(end_date.tzinfo)
        
        if now > end_date:
            print(f"🕐 Contest scaduto automaticamente: {end_date}")
            return True
        
        return False
    except Exception as e:
        print(f"❌ Errore controllo scadenza: {e}")
        return False

def get_all_users():
    """Ottieni tutti gli utenti registrati"""
    try:
        result = supabase.table('users').select("telegram_id, first_name").execute()
        return result.data
    except Exception as e:
        print(f"❌ Errore lettura utenti: {e}")
        return []

def get_user_count():
    """Ottieni numero totale utenti"""
    try:
        result = supabase.table('users').select("telegram_id", count='exact').execute()
        return result.count
    except Exception as e:
        print(f"❌ Errore conteggio utenti: {e}")
        return 0

def check_contest_should_start():
    """Controlla se un contest schedulato deve iniziare"""
    try:
        from datetime import datetime, timezone
        
        contest = get_current_contest()
        if not contest or contest['status'] != 'scheduled':
            return False
        
        # Parse date assumendo che sia UTC (senza timezone info)
        start_date_str = contest['start_date'].replace('Z', '').replace('+00:00', '')
        start_date = datetime.fromisoformat(start_date_str).replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        
        if now >= start_date:
            print(f"🚀 Contest deve iniziare: {start_date}")
            return True
        
        return False
    except Exception as e:
        print(f"❌ Errore controllo inizio: {e}")
        return False

def check_contest_end():
    """Controlla se il contest deve terminare automaticamente"""
    try:
        from datetime import datetime, timezone
        
        contest = get_current_contest()
        if not contest or contest['status'] != 'active':
            return False
        
        # Parse date assumendo che sia UTC (senza timezone info)
        end_date_str = contest['end_date'].replace('Z', '').replace('+00:00', '')
        end_date = datetime.fromisoformat(end_date_str).replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        
        if now > end_date:
            print(f"🕐 Contest scaduto automaticamente: {end_date}")
            return True
        
        return False
    except Exception as e:
        print(f"❌ Errore controllo scadenza: {e}")
        return False

def activate_scheduled_contest():
    """Attiva un contest schedulato"""
    try:
        supabase.table('contest_settings').update({
            'status': 'active'
        }).eq('status', 'scheduled').eq('is_active', True).execute()
        
        print("✅ Contest attivato automaticamente")
        return True
    except Exception as e:
        print(f"❌ Errore attivazione contest: {e}")
        return False

def get_contest_with_status():
    """Ottieni contest con controllo stato basato su date"""
    try:
        from datetime import datetime
        
        contest = get_current_contest()
        if not contest:
            return None, None
        
        now = datetime.now()
        start_date = datetime.fromisoformat(contest['start_date'].replace('Z', '+00:00').replace('+00:00', ''))
        end_date = datetime.fromisoformat(contest['end_date'].replace('Z', '+00:00').replace('+00:00', ''))
        
        # Determina stato reale basato su date
        if now < start_date:
            real_status = 'scheduled'
        elif now > end_date and contest['status'] == 'active':
            real_status = 'expired'  # Scaduto ma non ancora processato
        else:
            real_status = contest['status']
        
        return contest, real_status
    except Exception as e:
        print(f"❌ Errore calcolo stato: {e}")
        return contest, contest['status'] if contest else None

# Test temporaneo - aggiungi questa funzione
def test_date_check():
    contest = get_current_contest()
    if contest:
        from datetime import datetime
        start_date = datetime.fromisoformat(contest['start_date'].replace('Z', '+00:00'))
        now = datetime.now(start_date.tzinfo)
        print(f"DEBUG: Start date: {start_date}")
        print(f"DEBUG: Now: {now}")
        print(f"DEBUG: Now >= Start: {now >= start_date}")