import sys
import os
import csv
import queue
import asyncio
from nicegui import ui, run

dossier_script = os.path.dirname(os.path.abspath(__file__))
if dossier_script not in sys.path:
    sys.path.insert(0, dossier_script)

import deploy_network

# --- SAUVEGARDE DU VRAI TERMINAL VS CODE ---
original_stdout = sys.stdout
original_stderr = sys.stderr
log_queue = queue.Queue()

class SafeLogRedirector:
    def __init__(self, is_stderr=False):
        self.original = original_stderr if is_stderr else original_stdout
        
    def write(self, text):
        self.original.write(text)
        self.original.flush()
        if text:
            for line in text.split('\n'):
                clean_line = line.rstrip('\r\n')
                if clean_line.strip() or " " in line:
                    log_queue.put(clean_line)
            
    def flush(self): 
        self.original.flush()
        
    def isatty(self):
        if hasattr(self.original, 'isatty'):
            return self.original.isatty()
        return False
        
    def __getattr__(self, name):
        return getattr(self.original, name)

sys.stdout = SafeLogRedirector(is_stderr=False)
sys.stderr = SafeLogRedirector(is_stderr=True)

# --- CONFIGURATION GLOBALE ET THÈME ---
ui.dark_mode().enable()
ui.colors(primary='#00796B', secondary='#009688', accent='#4DB6AC')
ui.query('body').classes('bg-slate-900 overflow-hidden') 

# --- GESTIONNAIRE DE TÂCHES (QUEUE SYSTEM) ---
class TaskManager:
    def __init__(self):
        self.queue = []
        self.is_running = False
        self.current_task = None
        self.abort_requested = False

    def add_task(self, name, func, spinner=None, card=None, is_manual=False):
        task_data = {'name': name, 'func': func, 'spinner': spinner, 'card': card, 'is_manual': is_manual}
        
        if self.is_running:
            self.queue.append(task_data)
            if not is_manual:
                ui.notify(f"Mis en attente : {name}", type='info')
            if spinner: spinner.classes(remove='hidden')
            if card: card.classes(add='animate-pulse border-orange-500')
            update_queue_ui()
        else:
            if not is_manual:
                terminal.clear()
                while not log_queue.empty(): log_queue.get()
                
            self.queue.append(task_data)
            if spinner: spinner.classes(remove='hidden')
            if card: card.classes(add='animate-pulse border-teal-500')
            ui.timer(0.1, self.process_queue, once=True)

    async def process_queue(self):
        if self.is_running or not self.queue:
            return

        self.is_running = True
        self.abort_requested = False
        self.current_task = self.queue.pop(0)
        update_queue_ui()
        
        name = self.current_task['name']
        func = self.current_task['func']
        is_manual = self.current_task['is_manual']
        
        abort_btn.classes(remove='hidden')
        
        if not is_manual:
            ui.notify(f'Préparation de la tâche : {name}', type='info', position='bottom-right')
            terminal.push(f"⏳ [{name}] Préparation... Exécution dans 3 secondes.")
            for i in range(3, 0, -1):
                if self.abort_requested:
                    terminal.push(f"🛑 [{name}] Annulé par l'utilisateur.")
                    self.finish_task()
                    return
                terminal.push(f"... {i}")
                await asyncio.sleep(1)

            if self.abort_requested:
                terminal.push(f"🛑 [{name}] Annulé par l'utilisateur.")
                self.finish_task()
                return

            abort_btn.classes(add='hidden') 
            terminal.push(f"🚀 [{name}] Initialisation de la connexion SSH...\n" + "="*45)
            print(f"[{name}] Lancement de la tâche...\n" + "="*45)
        else:
            abort_btn.classes(add='hidden')

        try:
            await run.io_bound(func)
            if not is_manual:
                ui.notify(f'{name} exécuté avec succès.', type='positive', position='bottom-right')
        except Exception as e:
            print(f"[ERREUR CRITIQUE] {e}")
            ui.notify(f'Échec : {name}', type='negative', position='bottom-right')
        finally:
            if not is_manual:
                print(f"="*45 + f"\n[ FIN DE LA TÂCHE : {name} ]\n")
            self.finish_task()

    def finish_task(self):
        if self.current_task:
            if self.current_task['spinner']: 
                self.current_task['spinner'].classes(add='hidden')
            if self.current_task['card']: 
                self.current_task['card'].classes(remove='animate-pulse border-teal-500 border-orange-500')
        
        self.is_running = False
        self.current_task = None
        abort_btn.classes(add='hidden')
        
        if self.queue:
            ui.timer(0.1, self.process_queue, once=True)

    def request_abort(self):
        self.abort_requested = True

    def remove_from_queue(self, task_data):
        if task_data in self.queue:
            self.queue.remove(task_data)
            if task_data['spinner']: task_data['spinner'].classes(add='hidden')
            if task_data['card']: task_data['card'].classes(remove='animate-pulse border-orange-500 border-teal-500')
            update_queue_ui()

task_manager = TaskManager()

def get_inventory_hosts():
    chemin_inventaire = os.path.join(dossier_script, 'inventaire.csv')
    hosts = []
    if os.path.exists(chemin_inventaire):
        try:
            with open(chemin_inventaire, mode='r', encoding='utf-8') as f:
                # SÉCURITÉ : Ne liste que les équipements cisco pour le terminal manuel
                hosts = [row['hostname'] for row in csv.DictReader(f) if row.get('device_type') == 'cisco_ios']
        except Exception:
            pass
    return hosts if hosts else ['C1', 'C2', 'Dist1', 'Dist2', 'A1', 'A2', 'A3', 'A4']

# --- EN-TÊTE (HEADER) ---
with ui.header().classes('bg-teal-900 justify-between items-center px-6 py-4 shadow-xl border-b border-teal-700'):
    ui.label('🛡️ OCP - Network Operations Center').classes('text-2xl font-bold tracking-wider text-white')
    ui.label('Supervision & Automatisation v2.0').classes('text-teal-200 text-sm italic')

# --- LAYOUT PRINCIPAL ---
with ui.row().classes('w-full max-w-[1400px] mx-auto h-[85vh] mt-6 gap-8 flex-nowrap'):
    
    # ==========================================
    # ZONE GAUCHE : PANNEAU D'ADMINISTRATION
    # ==========================================
    with ui.column().classes('w-2/3 h-full pr-4 overflow-y-auto scrollbar-hide'):
        
        ui.label('⚙️ Outils de Déploiement').classes('text-xl font-bold text-teal-400 mb-2 mt-2')
        
        def create_card(icon_name, title, desc, task_func, color_class):
            with ui.card().classes(f'w-[48%] bg-slate-800 shadow-md hover:shadow-[0_0_15px_rgba(0,150,136,0.3)] hover:-translate-y-1 transition-all duration-300 cursor-pointer border-l-4 border-{color_class}-500') as card:
                with ui.row().classes('items-center justify-between w-full no-wrap'):
                    with ui.row().classes('items-center no-wrap'):
                        ui.icon(f'sym_o_{icon_name}').classes(f'text-4xl text-{color_class}-400 mr-3')
                        with ui.column().classes('gap-0'):
                            ui.label(title).classes('text-lg font-bold text-slate-100')
                            ui.label(desc).classes('text-xs text-slate-400')
                    local_spinner = ui.spinner(size='1.5em', color=color_class).classes('hidden')
                
                card.on('click', lambda: task_manager.add_task(title, task_func, local_spinner, card, is_manual=False))

        with ui.row().classes('w-full gap-4 mb-4 justify-between'):
            create_card('lan', '1. Déployer VLANs', 'Création des réseaux virtuels', deploy_network.deploy_vlans, 'blue')
            create_card('router', '2. Routage & HSRP', 'Passerelles et redondance', deploy_network.deploy_hsrp, 'blue')
        with ui.row().classes('w-full gap-4 mb-4 justify-between'):
            create_card('cable', '3. Liens Trunk', 'Interconnexion des switchs', deploy_network.deploy_trunks, 'orange')
            create_card('computer', "4. Ports d'Accès", 'Configuration finaux', deploy_network.deploy_access, 'orange')
        with ui.row().classes('w-full gap-4 mb-4 justify-between'):
            create_card('admin_panel_settings', '5. Management', 'Adresses IP VLAN 1', deploy_network.deploy_management, 'teal')
            create_card('wifi_tethering', '6. Serveur DHCP', 'Attribution dynamique', deploy_network.deploy_dhcp, 'teal')
        with ui.row().classes('w-full gap-4 mb-8 justify-between'):
            create_card('save', "7. Sauvegarde", 'Sauvegarde running-config', deploy_network.backup_configs, 'red')

        ui.label('📊 Diagnostics en Temps Réel').classes('text-xl font-bold text-teal-400 mb-2 mt-4')
        
        with ui.row().classes('w-full gap-4 mb-4 justify-between'):
            create_card('speed', '8. État HSRP', 'Vérification routeur actif', deploy_network.check_hsrp, 'purple')
            create_card('troubleshoot', '9. Scanner Pannes', 'Recherche liens DOWN', deploy_network.check_interfaces, 'purple')
        with ui.row().classes('w-full gap-4 mb-4 justify-between'):
            create_card('network_ping', '10. Connectivité', 'Ping global depuis C1', deploy_network.check_connectivity, 'purple')
            create_card('description', '11. Audit Complet', 'Générer rapport texte', deploy_network.generate_audit_report, 'red')

    # ==========================================
    # ZONE DROITE : TERMINAL INTELLIGENT AVEC CLI
    # ==========================================
    terminal_wrapper = ui.column().classes('w-1/3 h-[95%] bg-[#050505] rounded-xl border border-slate-700 shadow-2xl relative overflow-hidden flex flex-col transition-all duration-500 ease-in-out')
    
    with terminal_wrapper:
        with ui.row().classes('w-full bg-slate-800 p-2 border-b border-slate-600 items-center justify-between shrink-0'):
            ui.label('>_ Sortie Standard').classes('text-sm font-mono text-slate-300 font-bold ml-2')
            
            with ui.row().classes('gap-2 items-center mr-1'):
                abort_btn = ui.button('STOP', on_click=task_manager.request_abort).props('color=red size=sm outline').classes('hidden font-bold h-6 py-0 px-2')
                ui.button(icon='delete', on_click=lambda: terminal.clear()).props('flat round size=sm color=white').tooltip('Effacer la console')
                
                def toggle_expand():
                    if not hasattr(toggle_expand, 'expanded'): toggle_expand.expanded = False
                    if not toggle_expand.expanded:
                        terminal_wrapper.classes(remove='w-1/3 h-[95%] relative', add='absolute top-4 left-4 right-4 bottom-4 z-50 w-auto h-auto')
                        expand_btn._props['icon'] = 'fullscreen_exit'; expand_btn.update()
                    else:
                        terminal_wrapper.classes(remove='absolute top-4 left-4 right-4 bottom-4 z-50 w-auto h-auto', add='w-1/3 h-[95%] relative')
                        expand_btn._props['icon'] = 'fullscreen'; expand_btn.update()
                    toggle_expand.expanded = not toggle_expand.expanded

                expand_btn = ui.button(icon='fullscreen', on_click=toggle_expand).props('flat round size=sm color=white').tooltip('Plein écran')
        
        queue_container = ui.column().classes('w-full px-4 pt-2 gap-1 shrink-0')
        
        terminal = ui.log(max_lines=1000).classes('w-full flex-grow bg-transparent text-[#00FF00] font-mono text-sm p-4 whitespace-pre-wrap scrollbar-hide')

        # --- BARRE DE COMMANDE CLI INTÉGRÉE ---
        with ui.row().classes('w-full bg-slate-900 p-2 border-t border-slate-700 items-center no-wrap shrink-0'):
            hosts = get_inventory_hosts()
            target_select = ui.select(options=hosts, value=hosts[0] if hosts else None).classes('w-24').props('dark dense standout outline label-color="teal-200"')
            
            def submit_cmd(e=None):
                cmd = cmd_input.value
                target = target_select.value
                if not cmd or not target: return
                
                cmd_input.value = ''
                
                def manual_func():
                    deploy_network.run_manual_command(target, cmd)
                    
                task_manager.add_task(f"{target}# {cmd}", manual_func, is_manual=True)

            cmd_input = ui.input(placeholder='Commande CLI (Entrée pour valider)...').classes('flex-grow').props('dark dense standout outline').on('keydown.enter', submit_cmd)
            ui.button(icon='keyboard_return', on_click=submit_cmd).props('flat round color=teal size=sm')

def update_queue_ui():
    queue_container.clear()
    with queue_container:
        for item in task_manager.queue:
            with ui.row().classes('w-full bg-slate-800 py-1 px-3 rounded items-center justify-between border border-slate-600'):
                ui.label(f"⏳ En attente : {item['name']}").classes('text-xs text-slate-300')
                ui.button(icon='close', on_click=lambda t=item: task_manager.remove_from_queue(t)).props('flat round size=xs color=red').tooltip('Annuler cette tâche')

ui.timer(0.1, lambda: [terminal.push(log_queue.get()) for _ in range(log_queue.qsize())])

ui.run(title='NOC Dashboard', port=8282, dark=True, reload=False, show=True)