from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from config import TELEGRAM_BOT_TOKEN, ADMIN_IDS
from database import (get_current_contest, user_exists, create_user, get_user, 
                     create_pending_referral, get_user_by_referral_code, complete_referral,
                     get_pending_referral, get_contest_status, start_final_verification,
                     announce_results, check_contest_end, get_contest_with_status,
                     check_contest_should_start, activate_scheduled_contest)
from verification import run_final_verification
from broadcast import broadcast_contest_results
import asyncio
from datetime import datetime

# Dizionario globale per tenere traccia dei messaggi da cancellare
pending_share_messages = {}

def get_full_prize_text(contest):
    """Restituisce il testo completo dei premi (1°-5° posto)"""
    prize_text = f"🏆 Premio: {contest['prize_description']}\n"
    prize_text += f"🥈 2° posto → Bonus 50€\n"
    prize_text += f"🥉 3° posto → Bonus 25€\n"
    prize_text += f"4️⃣ 4° posto → Bonus 15€\n"
    prize_text += f"5️⃣ 5° posto → Bonus 10€"
    return prize_text

async def periodic_contest_check(bot, admin_id):
    """Controllo periodico integrato nel bot"""
    while True:
        try:
            print(f"🕐 Controllo contest: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Controllo se contest schedulato deve iniziare
            if check_contest_should_start():
                print("🚀 Attivando contest automaticamente...")
                if activate_scheduled_contest():
                    await bot.send_message(admin_id, "🚀 Contest avviato automaticamente!")
                    print("✅ Contest attivato")
                else:
                    print("❌ Errore attivazione contest")
            
            # Controllo se contest attivo deve terminare
            if check_contest_end():
                print("🕐 Contest scaduto - avvio verifica automatica")
                if start_final_verification():
                    print("🔍 Avvio verifica finale automatica...")
                    await run_final_verification(bot, admin_id)
                else:
                    print("❌ Errore avvio verifica finale")
            
            # Attendi 1 ora prima del prossimo controllo (3600 secondi)
            # Per test puoi usare 60 secondi
            await asyncio.sleep(3600)
            
        except Exception as e:
            print(f"❌ Errore controllo periodico: {e}")
            await asyncio.sleep(300)  # Se errore, riprova dopo 5 minuti

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
   user_id = update.effective_user.id
   username = update.effective_user.username
   first_name = update.effective_user.first_name
   
   contest = get_current_contest()
   if not contest:
       await update.message.reply_text("❌ Nessun contest configurato al momento.")
       return
   
   # USA SOLO LO STATO DEL DATABASE
   contest_status = contest['status']
   results_announced = contest.get('results_announced', False)
   
   # Gestisci contest non ancora iniziato
   if contest_status == 'scheduled':
       start_date_str = contest['start_date'].split('T')[0]  
       start_time = contest['start_date'].split('T')[1][:5]  
    
       # Aggiungi 2 ore
       hour, minute = start_time.split(':')
       hour = int(hour) + 2
       start_time = f"{hour:02d}:{minute}"
    
       message = f"⏰ Contest non ancora iniziato\n\n"
       message += f"📅 Inizio: {start_date_str} alle {start_time}\n\n"
       message += get_full_prize_text(contest) + "\n\n"
       message += f"Torna quando il contest sarà attivo!"
    
       await update.message.reply_text(message)
       return
   # Controllo altri stati
   if contest_status == 'verification_in_progress':
       await update.message.reply_text("🔄 Verifica finale in corso. Risultati disponibili a breve.")
       return
   elif contest_status == 'completed' and not results_announced:
       await update.message.reply_text("🏁 Contest terminato. Attendi l'annuncio ufficiale dei risultati.")
       return
   
   # Controlla referral code
   referral_code = None
   if context.args and len(context.args) > 0:
       referral_code = context.args[0]
       print(f"🔗 Utente {user_id} arriva tramite: {referral_code}")
   
   if user_exists(user_id):
       # Utente esistente
       await handle_existing_user(update, context, contest)
   else:
       if referral_code:
           # Contest terminato - non accettare nuovi referral
           if contest_status == 'completed':
               await update.message.reply_text("❌ Contest terminato. Non è più possibile iscriversi tramite referral.")
               return
           await handle_referral_user(update, context, referral_code, contest)
       else:
           # Contest terminato - non accettare nuovi utenti diretti
           if contest_status == 'completed':
               await update.message.reply_text("❌ Contest terminato. Non è più possibile registrarsi.")
               return
           await handle_direct_user(update, context, contest)

async def handle_existing_user(update, context, contest):
    user_id = update.effective_user.id
    contest_status, results_announced = get_contest_status()
    
    # Se contest completato e risultati annunciati, mostra direttamente le stats finali
    if contest_status == 'completed' and results_announced:
        user_data = get_user(user_id)
        
        keyboard = [[InlineKeyboardButton("🔙 Menu principale", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Messaggio speciale per il vincitore (primo posto) - INVARIATO
        if user_data.get('final_position') == 1:
            message = f"🥇 CONGRATULAZIONI! SEI IL VINCITORE!\n\n"
            message += f"🎉 Hai vinto il contest {contest['contest_name']}!\n\n"
            message += f"💥 Tuoi inviti validi: {user_data['total_invites']}\n"
            message += f"🏆 Posizione: #1\n\n"
            message += f"🎁 Hai vinto: {contest['prize_description']}\n\n"
            message += "Verrai contattato a breve per avere i dati e procedere con gli spostamenti per le due persone!"
        elif user_data.get('final_position') in [2, 3, 4, 5]:
            # Messaggi personalizzati per top 5
            position = user_data.get('final_position')
            position_emojis = {2: "🥈", 3: "🥉", 4: "🏅", 5: "🌟"}
            
            message = f"{position_emojis[position]} COMPLIMENTI! SEI NELLA TOP 5!\n\n"
            message += f"🎉 Fantastico risultato nel contest {contest['contest_name']}!\n\n"
            message += f"💥 Tuoi inviti validi: {user_data['total_invites']}\n"
            message += f"🏆 Posizione: #{position}\n\n"
            message += f"Un risultato eccezionale! Sei nella top 5!"
        else:
            # Messaggio normale per tutti gli altri
            message = f"📊 RISULTATI FINALI\n\n"
            message += f"💥 Tuoi inviti validi: {user_data['total_invites']}\n\n"
            if user_data.get('final_position'):
                message += f"🏆 La tua posizione: #{user_data['final_position']}\n\n"
            message += f"Il contest {contest['contest_name']} è terminato.\nGrazie per la partecipazione!"
        
        await update.message.reply_text(message, reply_markup=reply_markup)
        return
    
    # Controlla se ha referral pending (processo incompleto)
    pending_referral = get_pending_referral(user_id)
    if pending_referral:
        # Utente ha processo incompleto - mostra di nuovo i bottoni
        referrer = get_user(pending_referral['referrer_telegram_id'])
        
        keyboard = [[InlineKeyboardButton("🔗 ISCRIVITI AL CANALE", url=contest['channel_invite_link'])]]
        keyboard.append([InlineKeyboardButton("✅ PARTECIPA", callback_data="verify_subscription")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = f"🎯 Hai un invito in sospeso da {referrer['first_name']}!\n\n"
        message += f"Completa l'iscrizione al canale per partecipare al contest.\n\n"
        message += "Prima iscriviti al canale, poi clicca 'PARTECIPA'"
        
        await update.message.reply_text(message, reply_markup=reply_markup)
        return
    
    # Utente normale già registrato - contest attivo
    user_data = get_user(user_id)
    referral_link = f"https://t.me/{context.bot.username}?start={user_data['referral_code']}"
    
    # NUOVO: Keyboard con pulsanti condivisione e stats
    keyboard = [
        [InlineKeyboardButton("📊 Le mie statistiche", callback_data="show_stats")],
        [InlineKeyboardButton("🚀 Condividi il mio link", callback_data="share_link")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = f"🎉 Bentornato al Contest {contest['contest_name']}! 🎉\n\n"
    message += f"📜 Il regolamento è semplicissimo: vince chi porta più iscritti al canale Telegram di Vivio!\n\n"
    message += get_full_prize_text(contest) + "\n"
    message += f"💥 Persone invitate: {user_data['total_invites']}\n\n"
    message += f"👉 Condividi il tuo link d'invito tramite il tasto qui sotto con tutti i tuoi amici… e che vinca il migliore! 🚀"
    
    await update.message.reply_text(message, reply_markup=reply_markup)

async def handle_direct_user(update, context, contest):
    user_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    
    # MESSAGGIO 1: Benvenuto
    message1 = f"🎉 Benvenuto al contest {contest['contest_name']}!\n\n"
    message1 += f"Per partecipare al contest segui questi due passaggi ⬇️"
    
    await update.message.reply_text(message1)
    
    # MESSAGGIO 2: Iscrizione canale
    message2 = f"1️⃣ SEGUI IL CANALE TELEGRAM DI VIVIO\n\n"
    message2 += f"(una volta seguito clicca sulla freccia ⬅️ in alto a sinistra per tornare qui)"
    
    keyboard2 = [[InlineKeyboardButton("🔗 ISCRIVITI AL CANALE", url=contest['channel_invite_link'])]]
    reply_markup2 = InlineKeyboardMarkup(keyboard2)
    
    await update.message.reply_text(message2, reply_markup=reply_markup2)
    
    # MESSAGGIO 3: Verifica
    message3 = f"2️⃣ CLICCA QUI PER ACCEDERE AL CONTEST⬇️"
    
    keyboard3 = [[InlineKeyboardButton("✅ PARTECIPA", callback_data="verify_direct_subscription")]]
    reply_markup3 = InlineKeyboardMarkup(keyboard3)
    
    await update.message.reply_text(message3, reply_markup=reply_markup3)

async def handle_referral_user(update, context, referral_code, contest):
    user_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    
    referrer = get_user_by_referral_code(referral_code)
    if not referrer:
        await update.message.reply_text("❌ Link di invito non valido.")
        return
    
    new_user = create_user(user_id, username, first_name)
    if not new_user:
        await update.message.reply_text("❌ Errore durante la registrazione.")
        return
    
    create_pending_referral(referrer['telegram_id'], user_id)
    
    # MESSAGGIO 1: Invito da referrer
    message1 = f"🎯 Sei stato invitato da {referrer['first_name']}!\n\n"
    message1 += f"Per partecipare al contest segui questi due passaggi ⬇️"
    
    await update.message.reply_text(message1)
    
    # MESSAGGIO 2: Iscrizione canale
    message2 = f"1️⃣ SEGUI IL CANALE TELEGRAM DI VIVIO\n\n"
    message2 += f"(una volta seguito clicca sulla freccia ⬅️ in alto a sinistra per tornare qui)"
    
    keyboard2 = [[InlineKeyboardButton("🔗 ISCRIVITI AL CANALE", url=contest['channel_invite_link'])]]
    reply_markup2 = InlineKeyboardMarkup(keyboard2)
    
    await update.message.reply_text(message2, reply_markup=reply_markup2)
    
    # MESSAGGIO 3: Verifica
    message3 = f"2️⃣ CLICCA QUI PER ACCEDERE AL CONTEST⬇️"
    
    keyboard3 = [[InlineKeyboardButton("✅ PARTECIPA", callback_data="verify_subscription")]]
    reply_markup3 = InlineKeyboardMarkup(keyboard3)
    
    await update.message.reply_text(message3, reply_markup=reply_markup3)

async def verify_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    contest = get_current_contest()
    
    # Controllo stato contest
    contest_status, _ = get_contest_status()
    if contest_status != 'active':
        await query.edit_message_text("🔄 Contest terminato. Non è più possibile completare iscrizioni.")
        return
    
    try:
        member = await context.bot.get_chat_member(contest['channel_id'], user_id)
        if member.status in ['member', 'administrator', 'creator']:
            # Utente iscritto - completa referral
            pending_referral = get_pending_referral(user_id)
            if pending_referral:
                success = complete_referral(pending_referral['referrer_telegram_id'], user_id)
                if success:
                    user_data = get_user(user_id)
                    referral_link = f"https://t.me/{context.bot.username}?start={user_data['referral_code']}"
                    
                    # NUOVO: Keyboard con pulsanti condivisione e stats
                    keyboard = [
                        [InlineKeyboardButton("📊 Le mie statistiche", callback_data="show_stats")],
                        [InlineKeyboardButton("🚀 Condividi il mio link", callback_data="share_link")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    message = f"🎉 Benvenuto al Contest! 🎉\n\n"
                    message += f"✅ Sei ora registrato al contest {contest['contest_name']}\n\n"
                    message += f"📜 Il regolamento è semplicissimo: vince chi porta più iscritti al canale Telegram di Vivio!\n\n"
                    message += get_full_prize_text(contest) + "\n\n"
                    message += f"👉 Condividi il tuo link d'invito tramite il tasto qui sotto con tutti i tuoi amici… e che vinca il migliore! 🚀"
                    
                    await query.edit_message_text(message, reply_markup=reply_markup)
                else:
                    await query.edit_message_text("❌ Errore nel completamento. Contatta il supporto.")
            else:
                await query.edit_message_text("❌ Nessun referral in sospeso trovato.")
        else:
            # NON iscritto - messaggio diverso ogni volta per evitare errore Telegram
            import time
            timestamp = int(time.time()) % 100  # Ultimi 2 cifre del timestamp
            
            keyboard = [[InlineKeyboardButton("🔗 ISCRIVITI AL CANALE", url=contest['channel_invite_link'])]]
            keyboard.append([InlineKeyboardButton("✅ PARTECIPA", callback_data="verify_subscription")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"❌ Non risulti iscritto al canale.\n\nIscriviti prima di continuare. [{timestamp}]",
                reply_markup=reply_markup
            )
    except Exception as e:
        print(f"❌ Errore verifica: {e}")
        keyboard = [[InlineKeyboardButton("🔗 ISCRIVITI AL CANALE", url=contest['channel_invite_link'])]]
        keyboard.append([InlineKeyboardButton("✅ PARTECIPA", callback_data="verify_subscription")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            "❌ Errore durante la verifica. Iscriviti al canale e riprova:",
            reply_markup=reply_markup
        )

async def verify_direct_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    username = query.from_user.username
    first_name = query.from_user.first_name
    contest = get_current_contest()
    
    try:
        member = await context.bot.get_chat_member(contest['channel_id'], user_id)
        if member.status in ['member', 'administrator', 'creator']:
            # Utente iscritto - registra come utente diretto
            new_user = create_user(user_id, username, first_name)
            if new_user:
                referral_link = f"https://t.me/{context.bot.username}?start={new_user['referral_code']}"
                
                # NUOVO: Keyboard con pulsanti condivisione e stats
                keyboard = [
                    [InlineKeyboardButton("📊 Le mie statistiche", callback_data="show_stats")],
                    [InlineKeyboardButton("🚀 Condividi il mio link", callback_data="share_link")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                message = f"🎉 Benvenuto al Contest! 🎉\n\n"
                message += f"✅ Sei ora registrato al contest {contest['contest_name']}\n\n"
                message += f"📜 Il regolamento è semplicissimo: vince chi porta più iscritti al canale Telegram di Vivio!\n\n"
                message += get_full_prize_text(contest) + "\n\n"
                message += f"👉 Condividi il tuo link d'invito tramite il tasto qui sotto con tutti i tuoi amici… e che vinca il migliore! 🚀"
                
                await query.edit_message_text(message, reply_markup=reply_markup)
            else:
                await query.edit_message_text("❌ Errore durante la registrazione.")
        else:
            # NON iscritto
            import time
            timestamp = int(time.time()) % 100
            
            keyboard = [[InlineKeyboardButton("🔗 ISCRIVITI AL CANALE", url=contest['channel_invite_link'])]]
            keyboard.append([InlineKeyboardButton("✅ PARTECIPA", callback_data="verify_direct_subscription")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"❌ Non risulti iscritto al canale.\n\nIscriviti prima di continuare. [{timestamp}]",
                reply_markup=reply_markup
            )
    except Exception as e:
        print(f"❌ Errore verifica diretta: {e}")
        await query.edit_message_text("❌ Errore durante la verifica. Riprova.")

async def show_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not user_exists(user_id):
        await query.edit_message_text("❌ Non sei registrato. Usa /start per registrarti.")
        return
    
    # Controllo stato contest e accesso stats
    contest_status, results_announced = get_contest_status()
    
    if contest_status == 'verification_in_progress':
        # Durante verifica - nessun dato accessibile
        keyboard = [[InlineKeyboardButton("🔙 Torna indietro", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🔄 Verifica finale in corso...\n\nI risultati saranno disponibili a breve.",
            reply_markup=reply_markup
        )
        return
    
    if contest_status == 'completed' and not results_announced:
        # Contest finito ma risultati non ancora annunciati
        keyboard = [[InlineKeyboardButton("🔙 Torna indietro", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🏁 Contest terminato.\n\nAttendi l'annuncio ufficiale dei risultati.",
            reply_markup=reply_markup
        )
        return
    
    # Stats normali o finali (se annunciati)
    user_data = get_user(user_id)
    contest = get_current_contest()

    if user_data and contest:
        keyboard = [[InlineKeyboardButton("🔙 Torna indietro", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if contest_status == 'completed' and results_announced:
            # Messaggio per il vincitore - INVARIATO
            if user_data.get('final_position') == 1:
                message = f"🥇 CONGRATULAZIONI! SEI IL VINCITORE!\n\n"
                message += f"🎉 Hai vinto il contest {contest['contest_name']}!\n\n"
                message += f"💥 Tuoi inviti validi: {user_data['total_invites']}\n"
                message += f"🏆 Posizione: #1\n\n"
                message += f"🎁 Hai vinto: {contest['prize_description']}\n\n"
                message += "Verrai contattato a breve per avere i dati e procedere con gli spostamenti per le due persone!"
            elif user_data.get('final_position') in [2, 3, 4, 5]:
                # Messaggi personalizzati per top 5
                position = user_data.get('final_position')
                position_emojis = {2: "🥈", 3: "🥉", 4: "🏅", 5: "🌟"}
                
                message = f"{position_emojis[position]} COMPLIMENTI! SEI NELLA TOP 5!\n\n"
                message += f"🎉 Fantastico risultato nel contest {contest['contest_name']}!\n\n"
                message += f"💥 Tuoi inviti validi: {user_data['total_invites']}\n"
                message += f"🏆 Posizione: #{position}\n\n"
                message += f"Un risultato eccezionale! Sei nella top 5!"
            else:
                # Risultati finali normali
                message = f"📊 RISULTATI FINALI\n\n"
                message += f"💥 Tuoi inviti validi: {user_data['total_invites']}\n\n"
                if user_data.get('final_position'):
                    message += f"🏆 La tua posizione: #{user_data['final_position']}\n\n"
                message += f"Il contest {contest['contest_name']} è terminato.\nGrazie per la partecipazione!"
        else:
            # Stats durante contest attivo con link per copia manuale
            referral_link = f"https://t.me/{context.bot.username}?start={user_data['referral_code']}"
            message = f"📊 **LE TUE STATISTICHE**\n\n"
            message += f"💥 Persone invitate: {user_data['total_invites']}\n\n"
            message += f"🔗 Il tuo link referral:\n`{referral_link}`\n\n"
            message += get_full_prize_text(contest)
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def share_link_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    contest = get_current_contest()
    
    if not user_exists(user_id):
        await query.edit_message_text("❌ Non sei registrato. Usa /start per registrarti.")
        return
    
    # Cancella eventuale messaggio precedente per questo utente
    if user_id in pending_share_messages:
        old_message_id = pending_share_messages[user_id]
        try:
            await context.bot.delete_message(
                chat_id=query.message.chat_id, 
                message_id=old_message_id
            )
            print(f"🧹 Messaggio precedente cancellato per utente {user_id}")
        except Exception as e:
            print(f"⚠️ Impossibile cancellare messaggio precedente: {e}")
    
    user_data = get_user(user_id)
    referral_link = f"https://t.me/{context.bot.username}?start={user_data['referral_code']}"
    
    # Prima invia un messaggio di istruzioni
    keyboard = [[InlineKeyboardButton("🔙 Torna indietro", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    instruction_message = f"📢 **CONDIVIDI IL TUO LINK**\n\n"
    instruction_message += f"Il prossimo messaggio contiene il tuo link di invito già pronto.\n\n"
    instruction_message += f"📱 **Come fare:**\n"
    instruction_message += f"1️⃣ Tieni premuto sul messaggio qui sotto\n"
    instruction_message += f"2️⃣ Seleziona 'Copia'\n"
    instruction_message += f"3️⃣ Incolla su WhatsApp, Instagram, Facebook o ovunque vuoi!"
    
    await query.edit_message_text(instruction_message, reply_markup=reply_markup, parse_mode='Markdown')
    
    # Poi invia il messaggio da copiare come messaggio separato
    share_text = f"🎉 Partecipa al contest {contest['contest_name']} e vinci {contest['prize_description']}!\n\nUsa il mio link per partecipare:\n{referral_link}\n\nNon perdere questa opportunità!"
    
    # Invia il messaggio e salva l'ID per cancellarlo quando necessario
    share_message = await query.message.reply_text(share_text)
    
    # Salva solo l'ID del messaggio nel dizionario
    pending_share_messages[user_id] = share_message.message_id
    
    print(f"📤 Messaggio condivisione creato per utente {user_id}: {share_message.message_id}")

async def auto_delete_messages(bot, chat_id, message_ids, delay_seconds):
    """Cancella automaticamente i messaggi dopo il tempo specificato - FUNZIONE LEGACY"""
    # Questa funzione è mantenuta per compatibilità ma non più utilizzata
    # Il nuovo sistema usa pending_share_messages e cleanup_old_message
    pass

async def delete_message_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Messaggi cancellati! ✅")
    
    # Estrai l'ID del messaggio dal callback_data
    message_id = query.data.split('_')[2]  # delete_message_123 -> 123
    chat_id = query.message.chat_id
    
    try:
        # Cancella il messaggio da copiare
        await context.bot.delete_message(chat_id=chat_id, message_id=int(message_id))
        
        # Cancella anche questo messaggio con il pulsante cancella
        await context.bot.delete_message(chat_id=chat_id, message_id=query.message.message_id)
        
        print(f"✅ Messaggi cancellati manualmente dall'utente")
        
    except Exception as e:
        print(f"❌ Errore durante cancellazione manuale: {e}")
        # Se non riesce a cancellare, almeno modifica il messaggio
        try:
            await query.edit_message_text("✅ Messaggi cancellati!")
        except:
            pass

async def back_to_main_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    contest = get_current_contest()
    contest_status, results_announced = get_contest_status()
    
    # Cancella il messaggio da copiare se presente
    if user_id in pending_share_messages:
        message_id = pending_share_messages[user_id]
        try:
            await context.bot.delete_message(
                chat_id=query.message.chat_id, 
                message_id=message_id
            )
            del pending_share_messages[user_id]
            print(f"🧹 Messaggio condivisione cancellato per utente {user_id}")
        except Exception as e:
            print(f"⚠️ Impossibile cancellare messaggio condivisione: {e}")
            # Rimuovi comunque l'entry per evitare accumulo
            del pending_share_messages[user_id]
    
    user_data = get_user(user_id)
    
    # Se contest completato, mostra menu semplificato
    if contest_status == 'completed':
        keyboard = [[InlineKeyboardButton("📊 Le mie statistiche", callback_data="show_stats")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = f"🏁 Contest {contest['contest_name']} terminato\n\n"
        message += get_full_prize_text(contest) + "\n\n"
        message += f"Grazie per la partecipazione!"
        
        await query.edit_message_text(message, reply_markup=reply_markup)
        return
    
    # Menu normale per contest attivo con pulsante condivisione
    referral_link = f"https://t.me/{context.bot.username}?start={user_data['referral_code']}"
    
    keyboard = [
        [InlineKeyboardButton("📊 Le mie statistiche", callback_data="show_stats")],
        [InlineKeyboardButton("🚀 Condividi il mio link", callback_data="share_link")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = f"🎉 Bentornato al Contest {contest['contest_name']}! 🎉\n\n"
    message += f"📜 Il regolamento è semplicissimo: vince chi porta più iscritti al canale Telegram di Vivio!\n\n"
    message += get_full_prize_text(contest) + "\n"
    message += f"💥 Persone invitate: {user_data['total_invites']}\n\n"
    message += f"👉 Condividi il tuo link d'invito tramite il tasto qui sotto con tutti i tuoi amici… e che vinca il migliore! 🚀"
    
    await query.edit_message_text(message, reply_markup=reply_markup)

# COMANDI ADMIN
async def admin_end_contest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Solo gli admin possono usare questo comando")
        return
    
    contest_status, _ = get_contest_status()
    if contest_status != 'active':
        await update.message.reply_text(f"❌ Contest non attivo (stato: {contest_status})")
        return
    
    # Avvia verifica finale
    if start_final_verification():
        await update.message.reply_text("🔍 Verifica finale avviata manualmente...")
        
        # Esegui verifica in background
        asyncio.create_task(run_final_verification(context.bot, user_id))
    else:
        await update.message.reply_text("❌ Errore nell'avvio della verifica finale")

async def admin_announce_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Solo gli admin possono usare questo comando")
        return
    
    contest_status, results_announced = get_contest_status()
    if contest_status != 'completed':
        await update.message.reply_text(f"❌ Contest non completato (stato: {contest_status})")
        return
    
    if results_announced:
        await update.message.reply_text("ℹ️ Risultati già annunciati")
        return
    
    if announce_results():
        await update.message.reply_text("✅ Risultati annunciati! Avvio broadcast...")
        
        # Avvia broadcast automatico
        contest = get_current_contest()
        asyncio.create_task(broadcast_contest_results(context.bot, user_id, contest['contest_name']))
    else:
        await update.message.reply_text("❌ Errore nell'annuncio risultati")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Comando testuale di backup
    await show_stats_callback(update, context)

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Comandi utente
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    
    # Comandi admin
    app.add_handler(CommandHandler("admin_end_contest", admin_end_contest))
    app.add_handler(CommandHandler("admin_announce_results", admin_announce_results))
    
    # Callback handlers
    app.add_handler(CallbackQueryHandler(verify_subscription_callback, pattern="verify_subscription"))
    app.add_handler(CallbackQueryHandler(verify_direct_subscription_callback, pattern="verify_direct_subscription"))
    app.add_handler(CallbackQueryHandler(show_stats_callback, pattern="show_stats"))
    app.add_handler(CallbackQueryHandler(share_link_callback, pattern="share_link"))
    app.add_handler(CallbackQueryHandler(back_to_main_callback, pattern="back_to_main"))
    
    # Funzione per avviare il controllo periodico dopo che il bot è pronto
    async def post_init(application):
        if ADMIN_IDS:
            asyncio.create_task(periodic_contest_check(application.bot, ADMIN_IDS[0]))
            print("📅 Controllo periodico contest attivato")
    
    # Aggiungi post_init callback
    app.post_init = post_init
    
    # Railway usa PORT environment variable
    import os
    port = int(os.environ.get("PORT", 8000))
    
    print("🤖 Bot avviato su Railway...")
    
    # Per Railway, usa polling invece di webhooks
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
