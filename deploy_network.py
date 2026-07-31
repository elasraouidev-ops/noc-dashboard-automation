#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import os
import datetime
from netmiko import ConnectHandler

DOSSIER_SCRIPT = os.path.dirname(os.path.abspath(__file__))

def deploy_vlans():
    vlans_commands = []
    chemin_vlans = os.path.join(DOSSIER_SCRIPT, 'vlans.csv')
    chemin_inventaire = os.path.join(DOSSIER_SCRIPT, 'inventaire.csv')
    
    with open(chemin_vlans, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            vlans_commands.append(f"vlan {row['vlan_id']}")
            vlans_commands.append(f"name {row['name']}")
            vlans_commands.append("exit")

    with open(chemin_inventaire, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for device in reader:
            # SÉCURITÉ : On ignore les PC Linux et le Pare-feu pour cette tâche Cisco
            if device.get('device_type') != 'cisco_ios': 
                continue
                
            print(f"[*] Connexion à {device['hostname']} pour les VLANs...")
            cisco_device = {'device_type': device['device_type'], 'host': device['ip'], 
                            'port': int(device['port']), 'username': device['username'], 
                            'password': device['password'], 'secret': device['password'], 
                            'global_delay_factor': 4}
            try:
                net_connect = ConnectHandler(**cisco_device)
                net_connect.send_config_set(vlans_commands)
                print(f"[+] VLANs appliqués sur {device['hostname']}")
                net_connect.save_config()
                net_connect.disconnect()
            except Exception as e:
                print(f"[-] Erreur avec {device['hostname']}: {e}")

def deploy_hsrp():
    configs_par_routeur = {}
    chemin_hsrp = os.path.join(DOSSIER_SCRIPT, 'hsrp_config.csv')
    chemin_inventaire = os.path.join(DOSSIER_SCRIPT, 'inventaire.csv')

    with open(chemin_hsrp, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            hostname = row['hostname']
            if hostname not in configs_par_routeur:
                configs_par_routeur[hostname] = []
            commands = [
                f"interface vlan {row['vlan_id']}",
                f"ip address {row['ip_address']} {row['subnet_mask']}",
                f"standby {row['vlan_id']} ip {row['standby_ip']}"
            ]
            if row['priority'] != '100':
                commands.append(f"standby {row['vlan_id']} priority {row['priority']}")
            if row['preempt'].lower() == 'yes':
                commands.append(f"standby {row['vlan_id']} preempt")
            commands.append("no shutdown")
            commands.append("exit")
            configs_par_routeur[hostname].extend(commands)

    with open(chemin_inventaire, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for device in reader:
            hostname = device['hostname']
            if hostname in configs_par_routeur:
                print(f"[*] Connexion à {hostname} pour HSRP & Routage...")
                cisco_device = {'device_type': device['device_type'], 'host': device['ip'], 
                                'port': int(device['port']), 'username': device['username'], 
                                'password': device['password'], 'secret': device['password'], 
                                'global_delay_factor': 4}
                try:
                    net_connect = ConnectHandler(**cisco_device)
                    net_connect.send_config_set([
                        "ip routing", 
                        "ip route 192.168.10.0 255.255.255.0 10.0.1.50"
                    ]) 
                    net_connect.send_config_set(configs_par_routeur[hostname])
                    print(f"[+] HSRP et Routage OT appliqués sur {hostname}")
                    net_connect.save_config()
                    net_connect.disconnect()
                except Exception as e:
                    print(f"[-] Erreur HSRP avec {hostname}: {e}")

def deploy_trunks():
    configs_par_equipement = {}
    chemin_trunks = os.path.join(DOSSIER_SCRIPT, 'trunks.csv')
    chemin_inventaire = os.path.join(DOSSIER_SCRIPT, 'inventaire.csv')

    with open(chemin_trunks, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            hostname = row['hostname']
            if hostname not in configs_par_equipement:
                configs_par_equipement[hostname] = []
            commands = [
                f"interface {row['interface']}",
                "switchport trunk encapsulation dot1q", 
                "switchport mode trunk",
                "switchport nonegotiate",
                "no shutdown",
                "exit"
            ]
            configs_par_equipement[hostname].extend(commands)

    with open(chemin_inventaire, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for device in reader:
            hostname = device['hostname']
            if hostname in configs_par_equipement:
                print(f"[*] Configuration des Trunks sur {hostname}...")
                cisco_device = {'device_type': device['device_type'], 'host': device['ip'], 
                                'port': int(device['port']), 'username': device['username'], 
                                'password': device['password'], 'secret': device['password'], 
                                'global_delay_factor': 4}
                try:
                    net_connect = ConnectHandler(**cisco_device)
                    net_connect.send_config_set(configs_par_equipement[hostname])
                    print(f"[+] Trunks appliqués sur {hostname}")
                    net_connect.save_config()
                    net_connect.disconnect()
                except Exception as e:
                    print(f"[-] Erreur Trunk avec {hostname}: {e}")

def deploy_access():
    configs_par_equipement = {}
    chemin_access = os.path.join(DOSSIER_SCRIPT, 'access.csv')
    chemin_inventaire = os.path.join(DOSSIER_SCRIPT, 'inventaire.csv')

    with open(chemin_access, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            hostname = row['hostname']
            if hostname not in configs_par_equipement:
                configs_par_equipement[hostname] = []
            commands = [
                f"interface {row['interface']}",
                "switchport mode access",
                f"switchport access vlan {row['vlan_id']}"
            ]
            if 'voice_vlan_id' in row and row['voice_vlan_id'].strip():
                commands.append(f"switchport voice vlan {row['voice_vlan_id']}")
            commands.extend(["spanning-tree portfast", "no shutdown", "exit"])
            configs_par_equipement[hostname].extend(commands)

    with open(chemin_inventaire, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for device in reader:
            hostname = device['hostname']
            if hostname in configs_par_equipement:
                print(f"[*] Configuration des accès sur {hostname}...")
                cisco_device = {'device_type': device['device_type'], 'host': device['ip'], 
                                'port': int(device['port']), 'username': device['username'], 
                                'password': device['password'], 'secret': device['password'], 
                                'global_delay_factor': 4}
                try:
                    net_connect = ConnectHandler(**cisco_device)
                    net_connect.send_config_set(configs_par_equipement[hostname])
                    print(f"[+] Ports d'accès appliqués sur {hostname}")
                    net_connect.save_config()
                    net_connect.disconnect()
                except Exception as e:
                    print(f"[-] Erreur Accès avec {hostname}: {e}")

def deploy_management():
    chemin_inventaire = os.path.join(DOSSIER_SCRIPT, 'inventaire.csv')
    switchs = ['Dist1', 'Dist2', 'A1', 'A2', 'A3', 'A4']

    with open(chemin_inventaire, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for device in reader:
            hostname = device['hostname']
            if hostname in switchs:
                print(f"[*] Configuration du Management (VLAN 1) sur {hostname}...")
                commands = [
                    "interface vlan 1",
                    f"ip address {device['ip']} 255.255.255.0",
                    "no shutdown",
                    "exit",
                    "ip default-gateway 10.0.1.254"
                ]
                cisco_device = {'device_type': device['device_type'], 'host': device['ip'], 
                                'port': int(device['port']), 'username': device['username'], 
                                'password': device['password'], 'secret': device['password'], 
                                'global_delay_factor': 4}
                try:
                    net_connect = ConnectHandler(**cisco_device)
                    net_connect.send_config_set(commands)
                    print(f"[+] Interface VLAN 1 et Passerelle configurées sur {hostname}")
                    net_connect.save_config()
                    net_connect.disconnect()
                except Exception as e:
                    print(f"[-] Erreur Management avec {hostname}: {e}")

def deploy_dhcp():
    chemin_inventaire = os.path.join(DOSSIER_SCRIPT, 'inventaire.csv')
    dhcp_c1 = [
        "ip dhcp excluded-address 10.0.10.100 10.0.10.254",
        "ip dhcp excluded-address 10.0.20.100 10.0.20.254",
        "ip dhcp excluded-address 10.0.30.100 10.0.30.254",
        "ip dhcp excluded-address 10.0.40.100 10.0.40.254",
        "ip dhcp pool DHCP_VLAN10", "network 10.0.10.0 255.255.255.0", "default-router 10.0.10.254", "dns-server 8.8.8.8", "exit",
        "ip dhcp pool DHCP_VLAN20", "network 10.0.20.0 255.255.255.0", "default-router 10.0.20.254", "dns-server 8.8.8.8", "exit",
        "ip dhcp pool DHCP_VLAN30", "network 10.0.30.0 255.255.255.0", "default-router 10.0.30.254", "dns-server 8.8.8.8", "exit",
        "ip dhcp pool DHCP_VLAN40", "network 10.0.40.0 255.255.255.0", "default-router 10.0.40.254", "dns-server 8.8.8.8", "exit"
    ]
    dhcp_c2 = [
        "ip dhcp excluded-address 10.0.10.1 10.0.10.100",
        "ip dhcp excluded-address 10.0.10.200 10.0.10.254",
        "ip dhcp excluded-address 10.0.20.1 10.0.20.100",
        "ip dhcp excluded-address 10.0.20.200 10.0.20.254",
        "ip dhcp excluded-address 10.0.30.1 10.0.30.100",
        "ip dhcp excluded-address 10.0.30.200 10.0.30.254",
        "ip dhcp excluded-address 10.0.40.1 10.0.40.100",
        "ip dhcp excluded-address 10.0.40.200 10.0.40.254",
        "ip dhcp pool DHCP_VLAN10", "network 10.0.10.0 255.255.255.0", "default-router 10.0.10.254", "dns-server 8.8.8.8", "exit",
        "ip dhcp pool DHCP_VLAN20", "network 10.0.20.0 255.255.255.0", "default-router 10.0.20.254", "dns-server 8.8.8.8", "exit",
        "ip dhcp pool DHCP_VLAN30", "network 10.0.30.0 255.255.255.0", "default-router 10.0.30.254", "dns-server 8.8.8.8", "exit",
        "ip dhcp pool DHCP_VLAN40", "network 10.0.40.0 255.255.255.0", "default-router 10.0.40.254", "dns-server 8.8.8.8", "exit"
    ]
    with open(chemin_inventaire, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for device in reader:
            if device['hostname'] in ['C1', 'C2']:
                print(f"[*] Configuration DHCP sur {device['hostname']}...")
                cisco_device = {'device_type': device['device_type'], 'host': device['ip'], 
                                'port': int(device['port']), 'username': device['username'], 
                                'password': device['password'], 'secret': device['password'], 
                                'global_delay_factor': 4}
                try:
                    net_connect = ConnectHandler(**cisco_device)
                    if device['hostname'] == 'C1':
                        net_connect.send_config_set(dhcp_c1)
                    else:
                        net_connect.send_config_set(dhcp_c2)
                    print(f"[+] Serveur DHCP déployé sur {device['hostname']}")
                    net_connect.save_config()
                    net_connect.disconnect()
                except Exception as e:
                    print(f"[-] Erreur DHCP avec {device['hostname']}: {e}")

def backup_configs():
    chemin_inventaire = os.path.join(DOSSIER_SCRIPT, 'inventaire.csv')
    dossier_backup = os.path.join(DOSSIER_SCRIPT, 'backups')
    if not os.path.exists(dossier_backup):
        os.makedirs(dossier_backup)
    with open(chemin_inventaire, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for device in reader:
            # SÉCURITÉ : Ignorer les hôtes non-Cisco pour la sauvegarde IOS
            if device.get('device_type') != 'cisco_ios':
                continue
                
            print(f"[*] Sauvegarde de {device['hostname']}...")
            cisco_device = {'device_type': device['device_type'], 'host': device['ip'], 
                            'port': int(device['port']), 'username': device['username'], 
                            'password': device['password'], 'secret': device['password'], 
                            'global_delay_factor': 4}
            try:
                net_connect = ConnectHandler(**cisco_device)
                output = net_connect.send_command("show running-config")
                with open(os.path.join(dossier_backup, f"{device['hostname']}_backup.txt"), 'w', encoding='utf-8') as f:
                    f.write(output)
                print(f"[+] Fichier créé : {device['hostname']}_backup.txt")
                net_connect.disconnect()
            except Exception as e:
                print(f"[-] Échec de sauvegarde pour {device['hostname']}: {e}")

def check_hsrp():
    chemin_inventaire = os.path.join(DOSSIER_SCRIPT, 'inventaire.csv')
    with open(chemin_inventaire, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for device in reader:
            if device['hostname'] in ["C1", "C2"]:
                cisco_device = {'device_type': device['device_type'], 'host': device['ip'], 
                                'port': int(device['port']), 'username': device['username'], 
                                'password': device['password'], 'secret': device['password'], 
                                'global_delay_factor': 4}
                try:
                    net_connect = ConnectHandler(**cisco_device)
                    print(f"==== ETAT HSRP : {device['hostname']} ====\n{net_connect.send_command('show standby brief')}\n")
                    net_connect.disconnect()
                except Exception as e:
                    print(f"[-] Impossible de joindre {device['hostname']}: {e}\n")

def check_interfaces():
    chemin_inventaire = os.path.join(DOSSIER_SCRIPT, 'inventaire.csv')
    interfaces_attendues = {}
    
    for fichier in ['trunks.csv', 'access.csv']:
        chemin = os.path.join(DOSSIER_SCRIPT, fichier)
        if os.path.exists(chemin):
            with open(chemin, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    host = row['hostname']
                    if host not in interfaces_attendues:
                        interfaces_attendues[host] = []
                    interfaces_attendues[host].append(row['interface'])

    with open(chemin_inventaire, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for device in reader:
            hostname = device['hostname']
            if hostname not in interfaces_attendues:
                continue
            cisco_device = {
                'device_type': device['device_type'],
                'host': device['ip'],
                'port': int(device['port']),
                'username': device['username'],
                'password': device['password'],
                'secret': device['password'],
                'global_delay_factor': 4
            }
            try:
                net_connect = ConnectHandler(**cisco_device)
                output = net_connect.send_command("show ip interface brief")
                pannes = []
                lignes = output.split('\n')
                for intf_attendue in interfaces_attendues[hostname]:
                    num_port = intf_attendue.replace("GigabitEthernet", "")
                    for ligne in lignes:
                        if (intf_attendue in ligne or f"Gi{num_port}" in ligne) and 'down' in ligne.lower():
                            pannes.append(ligne.strip())
                if pannes:
                    print(f"[!] {hostname} : AVERTISSEMENT - Interfaces DOWN !")
                    for panne in pannes:
                        print(f"    -> {panne}")
                else:
                    print(f"[+] {hostname} : OK (Interfaces câblées actives).")
                net_connect.disconnect()
            except Exception as e:
                print(f"[-] Erreur avec {hostname}: {e}")

def check_connectivity():
    chemin_inventaire = os.path.join(DOSSIER_SCRIPT, 'inventaire.csv')
    c1_params, autres_ips = None, {}
    with open(chemin_inventaire, mode='r', encoding='utf-8') as file:
        for device in csv.DictReader(file):
            if device['hostname'] == 'C1': c1_params = device
            else: autres_ips[device['hostname']] = device['ip']
    if not c1_params:
        print("[-] Erreur : C1 introuvable."); return
    try:
        print("[*] Connexion au cœur de réseau (C1)...")
        net_connect = ConnectHandler(device_type=c1_params['device_type'], host=c1_params['ip'], 
                                     port=int(c1_params['port']), username=c1_params['username'], 
                                     password=c1_params['password'], secret=c1_params['password'], 
                                     global_delay_factor=4)
        print("\n[*] Test des passerelles locales...")
        
        # AJOUT DE read_timeout=20 POUR LAISSER LE TEMPS AU PING D'ÉCHOUER PROPREMENT
        for ip in ['10.0.10.254', '10.0.20.254', '10.0.30.254', '10.0.40.254', '10.0.1.254']:
            print(f"  [+] SVI {ip} : UP" if "!" in net_connect.send_command(f"ping {ip}", read_timeout=20) else f"  [-] SVI {ip} : DOWN")
        
        print("\n[*] Test de l'infrastructure globale...")
        for host, ip in autres_ips.items():
            print(f"  [+] {host} ({ip}) : UP" if "!" in net_connect.send_command(f"ping {ip}", read_timeout=20) else f"  [-] {host} ({ip}) : DOWN")
            
        net_connect.disconnect()
        print("\n[*] Diagnostic terminé.")
    except Exception as e:
        print(f"[-] Erreur depuis C1 : {e}")

def generate_audit_report():
    dossier_rapports = os.path.join(DOSSIER_SCRIPT, 'rapports')
    os.makedirs(dossier_rapports, exist_ok=True)
    chemin_fichier = os.path.join(dossier_rapports, f"audit_complet_{datetime.datetime.now().strftime('%Y-%m-%d_%Hh%M')}.txt")
    with open(chemin_fichier, 'w', encoding='utf-8') as f_out:
        f_out.write(f"=== RAPPORT D'AUDIT RÉSEAU - {datetime.datetime.now().strftime('%d/%m/%Y')} ===\n\n")
    print(f"[*] Génération du fichier...")
    with open(os.path.join(DOSSIER_SCRIPT, 'inventaire.csv'), mode='r', encoding='utf-8') as file:
        for device in csv.DictReader(file):
            if device.get('device_type') != 'cisco_ios': continue
            print(f"    -> Collecte sur {device['hostname']}...")
            try:
                net_connect = ConnectHandler(device_type=device['device_type'], host=device['ip'], 
                                             port=int(device['port']), username=device['username'], 
                                             password=device['password'], secret=device['password'], 
                                             global_delay_factor=4)
                uptime, version = net_connect.send_command("show version | include uptime"), net_connect.send_command("show version | include Version")
                with open(chemin_fichier, 'a', encoding='utf-8') as f_out:
                    f_out.write(f"--- {device['hostname']} ({device['ip']}) ---\nSystème : {version.split(chr(10))[0]}\nStatut  : {uptime.strip()}\n\n")
                net_connect.disconnect()
            except Exception as e:
                print(f"    [!] Impossible de joindre {device['hostname']}")
                with open(chemin_fichier, 'a', encoding='utf-8') as f_out:
                    f_out.write(f"--- {device['hostname']} ({device['ip']}) ---\nStatut  : HORS LIGNE\nErreur  : {e}\n\n")
    print(f"\n[+] TERMINE ! Rapport sauvegardé dans 'rapports'.")

def run_manual_command(hostname, command):
    chemin_inventaire = os.path.join(DOSSIER_SCRIPT, 'inventaire.csv')
    target_device = None
    
    with open(chemin_inventaire, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for device in reader:
            if device['hostname'] == hostname:
                target_device = device
                break
    
    if not target_device:
        print(f"[-] Erreur : L'hôte '{hostname}' est introuvable.")
        return

    # SÉCURITÉ : Interdire l'envoi de commandes Cisco vers un hôte Linux
    if target_device.get('device_type') != 'cisco_ios':
        print(f"[-] Action refusée : L'hôte '{hostname}' n'est pas un équipement Cisco (Console incompatible).")
        return

    cisco_device = {
        'device_type': target_device['device_type'], 
        'host': target_device['ip'], 
        'port': int(target_device['port']), 
        'username': target_device['username'], 
        'password': target_device['password'], 
        'secret': target_device['password'], 
        'global_delay_factor': 4
    }
    
    try:
        net_connect = ConnectHandler(**cisco_device)
        output = net_connect.send_command(command)
        
        print(f"{hostname}# {command}")
        print(f"{output}")
        
        net_connect.disconnect()
    except Exception as e:
        print(f"{hostname}# {command}")
        print(f"% SSH Connection Error : {e}")

if __name__ == "__main__":
    print("Test local...")