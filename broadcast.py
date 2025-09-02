import asyncio
from database import get_all_users, get_user_count

async def broadcast_message(bot, message_text, admin_id):
    """Invia messaggio broadcast a tutti gli utenti"""
    
    users = get_all_users()
    total_users = len(users)
    
    if total_users == 0:
        await bot.send_message(admin_id, "❌ Nessun utente da contattare")
        return
    
    print(f"📢 Avvio broadcast per {total_users} utenti...")
    await bot.send_message(admin_id, f"📢 Invio messaggio a {total_users} utenti...")
    
    sent_count = 0
    failed_count = 0
    
    for i, user in enumerate(users):
        try:
            await bot.send_message(user['telegram_id'], message_text)
            sent_count += 1
            
            # Progress ogni 100 messaggi
            if (i + 1) % 100 == 0:
                progress_msg = f"📊 Progress: {i + 1}/{total_users} - Inviati: {sent_count}, Falliti: {failed_count}"
                await bot.send_message(admin_id, progress_msg)
                print(progress_msg)
            
            # Rate limiting: pausa ogni 30 messaggi
            if (i + 1) % 30 == 0:
                await asyncio.sleep(1)
                
        except Exception as e:
            failed_count += 1
            print(f"❌ Errore invio a {user['telegram_id']}: {e}")
    
    # Risultato finale
    final_msg = f"✅ Broadcast completato!\n\n📊 Statistiche:\n👥 Totale utenti: {total_users}\n✅ Inviati: {sent_count}\n❌ Falliti: {failed_count}"
    await bot.send_message(admin_id, final_msg)
    print(f"✅ Broadcast completato: {sent_count}/{total_users} inviati")

async def broadcast_contest_results(bot, admin_id, contest_name):
   """Broadcast specifico per annuncio risultati contest"""
   
   message = f"🏁 Il contest {contest_name} è terminato!\n\n"
   message += f"🏆 I risultati sono ora disponibili.\n\n"
   message += f"Usa il bottone qui sotto per vedere la tua posizione finale:"
   
   # Aggiungi bottone per vedere risultati
   from telegram import InlineKeyboardButton, InlineKeyboardMarkup
   keyboard = [[InlineKeyboardButton("📊 I miei risultati", callback_data="show_stats")]]
   reply_markup = InlineKeyboardMarkup(keyboard)
   
   # Broadcast con bottone
   users = get_all_users()
   total_users = len(users)
   
   if total_users == 0:
       await bot.send_message(admin_id, "❌ Nessun utente da contattare per il broadcast")
       return
   
   sent_count = 0
   failed_count = 0
   
   await bot.send_message(admin_id, f"📢 Invio annuncio risultati a {total_users} utenti...")
   
   for i, user in enumerate(users):
       try:
           await bot.send_message(
               user['telegram_id'], 
               message, 
               reply_markup=reply_markup
           )
           sent_count += 1
           
           # Progress ogni 100 utenti
           if (i + 1) % 100 == 0:
               progress_msg = f"📊 Progress: {i + 1}/{total_users} - Inviati: {sent_count}, Falliti: {failed_count}"
               await bot.send_message(admin_id, progress_msg)
               print(progress_msg)
           
           # Rate limiting: pausa ogni 30 messaggi
           if (i + 1) % 30 == 0:
               await asyncio.sleep(1)
               
       except Exception as e:
           failed_count += 1
           print(f"❌ Errore broadcast a {user['telegram_id']}: {e}")
   
   # Risultato finale con fix division by zero
   total_sent_failed = sent_count + failed_count
   success_rate = (sent_count / total_sent_failed * 100) if total_sent_failed > 0 else 0
   
   final_msg = f"✅ Broadcast completato!\n\n"
   final_msg += f"📊 Statistiche broadcast:\n"
   final_msg += f"👥 Totale utenti: {total_users}\n"
   final_msg += f"✅ Inviati: {sent_count}\n"
   final_msg += f"❌ Falliti: {failed_count}\n"
   final_msg += f"📈 Tasso successo: {success_rate:.1f}%"
   
   await bot.send_message(admin_id, final_msg)
   print(f"✅ Broadcast completato: {sent_count}/{total_users} inviati")