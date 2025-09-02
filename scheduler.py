import schedule
import threading
import time
import asyncio
from database import check_contest_end, start_final_verification, check_contest_should_start, activate_scheduled_contest

# Variabile globale per riferimenti bot
_bot_instance = None
_admin_id = None

def schedule_contest_checks(bot, admin_id):
    """Programma controlli automatici del contest"""
    
    global _bot_instance, _admin_id
    _bot_instance = bot
    _admin_id = admin_id
    
    def check_contest_lifecycle():
        """Controllo sincrono che può triggerare azioni asincrone"""
        try:
            print(f"Controllo scheduler: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Controllo inizio contest
            if check_contest_should_start():
                print("Contest deve iniziare - attivazione...")
                if activate_scheduled_contest():
                    print("Contest attivato automaticamente")
                    # Programma notifica asincrona
                    schedule_async_notification("Contest avviato automaticamente!")
            
            # Controllo fine contest
            if check_contest_end():
                print("Contest scaduto - avvio verifica automatica")
                if start_final_verification():
                    print("Verifica finale programmata")
                    # Programma verifica asincrona
                    schedule_async_verification()
                    
        except Exception as e:
            print(f"Errore controllo: {e}")
    
    # Controllo ogni ora
    schedule.every(1).minutes.do(check_contest_lifecycle)
    
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(300)  # Check ogni 5 minuti
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("Scheduler attivato (controlli ogni ora)")

def schedule_async_notification(message):
    """Programma invio notifica asincrona"""
    def send_notification():
        try:
            # Usa il loop principale del bot invece di crearne uno nuovo
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Se il loop è già in esecuzione, crea un task
                asyncio.create_task(_bot_instance.send_message(_admin_id, message))
            else:
                # Se non c'è un loop attivo, eseguine uno
                loop.run_until_complete(_bot_instance.send_message(_admin_id, message))
        except Exception as e:
            print(f"Errore invio notifica: {e}")
    
    # Esegui in thread separato per evitare conflitti
    notification_thread = threading.Thread(target=send_notification, daemon=True)
    notification_thread.start()

def schedule_async_verification():
    """Programma verifica finale asincrona"""
    def run_verification():
        try:
            from verification import run_final_verification
            # Stesso approccio per la verifica
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run_final_verification(_bot_instance, _admin_id))
            loop.close()
        except Exception as e:
            print(f"Errore verifica asincrona: {e}")
    
    verification_thread = threading.Thread(target=run_verification, daemon=True)
    verification_thread.start()