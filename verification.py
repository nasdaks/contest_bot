import asyncio
import time
from database import (get_all_completed_referrals, invalidate_referral, 
                     recalculate_final_scores, complete_contest_verification,
                     get_top_5_users, get_total_participants, get_current_contest)

async def run_final_verification(bot, admin_id):
    """Esegue la verifica finale completa del contest"""
    
    print("🔍 Inizio verifica finale...")
    contest = get_current_contest()
    
    if not contest:
        print("❌ Nessun contest attivo")
        return False
    
    # Ottieni tutti i referral da verificare
    referrals = get_all_completed_referrals()
    total_referrals = len(referrals)
    
    if total_referrals == 0:
        print("ℹ️ Nessun referral da verificare")
        await complete_final_verification(bot, admin_id, 0, 0)
        return True
    
    print(f"📊 Verifica di {total_referrals} referral in corso...")
    
    # Notifica admin inizio verifica
    await bot.send_message(admin_id, f"🔍 Verifica finale avviata\n\nReferral da controllare: {total_referrals}")
    
    verified_count = 0
    invalidated_count = 0
    
    # Verifica ogni referral con rate limiting
    for i, referral in enumerate(referrals):
        try:
            # Controlla se utente è ancora nel canale
            member = await bot.get_chat_member(contest['channel_id'], referral['referred_telegram_id'])
            
            if member.status in ['member', 'administrator', 'creator']:
                # Utente ancora nel canale - referral valido
                verified_count += 1
            else:
                # Utente non nel canale - invalida referral
                invalidate_referral(referral['referrer_telegram_id'], referral['referred_telegram_id'])
                invalidated_count += 1
            
            # Progress update ogni 50 verifiche
            if (i + 1) % 50 == 0:
                progress = f"Progress: {i + 1}/{total_referrals} verificati"
                await bot.send_message(admin_id, f"⏳ {progress}")
                print(f"⏳ {progress}")
            
            # Rate limiting: pausa ogni 25 verifiche
            if (i + 1) % 25 == 0:
                await asyncio.sleep(1)  # Pausa 1 secondo ogni 25 verifiche
                
        except Exception as e:
            print(f"❌ Errore verifica utente {referral['referred_telegram_id']}: {e}")
            # In caso di errore, consideriamo il referral come non valido
            invalidate_referral(referral['referrer_telegram_id'], referral['referred_telegram_id'])
            invalidated_count += 1
    
    # Completa la verifica
    await complete_final_verification(bot, admin_id, verified_count, invalidated_count)
    return True

async def complete_final_verification(bot, admin_id, valid_count, invalid_count):
    """Completa il processo di verifica e notifica admin"""
    
    print("📊 Ricalcolo punteggi finali...")
    recalculate_final_scores()
    
    print("✅ Completamento contest...")
    complete_contest_verification()
    
    # Ottieni risultati finali
    top_5 = get_top_5_users()
    total_participants = get_total_participants()
    
    # Crea messaggio per admin
    message = "🏆 CONTEST TERMINATO - TOP 5\n\n"
    
    for i, user in enumerate(top_5, 1):
        message += f"{i}. {user['first_name']} - {user['total_invites']} inviti\n"
    
    message += f"\n📊 STATISTICHE FINALI:\n"
    message += f"👥 Totale partecipanti: {total_participants:,}\n"
    message += f"✅ Referral validi: {valid_count:,}\n"
    message += f"❌ Referral invalidati: {invalid_count:,}\n"
    message += f"📈 Tasso validità: {(valid_count/(valid_count+invalid_count)*100):.1f}%\n"
    
    message += f"\nUsa /admin_announce_results per sbloccare i risultati per tutti gli utenti."
    
    await bot.send_message(admin_id, message)
    print("✅ Verifica finale completata!")