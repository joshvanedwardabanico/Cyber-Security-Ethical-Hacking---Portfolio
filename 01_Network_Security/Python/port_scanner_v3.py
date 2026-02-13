import socket
import subprocess
import sys
from datetime import datetime

# ---PING MACCHINA BERSAGLIO ---
def check_host_up(ip):
    """
    Invia un singolo pacchetto PING all'IP target.
    Ritorna True se risponde, False se non risponde.
    """
    try:
        output = subprocess.run( # Eseguiamo il comando ping; -c 1: Invia solo 1 pacchetto; -W 1: Aspetta massimo 1 secondo per la risposta.
            ['ping', '-c', '1', '-W', '1', ip],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL # stdout/stderr=DEVNULL serve a nascondere l'output del ping nel terminale.
        )

        return output.returncode == 0 # Se il codice di ritorno è 0, il ping ha avuto successo (fa un return True)
    except Exception:
        return False # Se il ping NON ha avuto successo (fa un return False)

# ---TEMPO PER LO SCAN DI OGNI PORTA---
def scan_time(target_ip, port, timeout=0.3):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((target_ip, port))
        sock.close()

        if result == 0:
            return True
        else:
            return False
    except socket.error:
        print('Connessione interrotta!')
        return False

# ---SCAN E OUTPUT SU TERMINALE---
def port_scan(target, start_port, end_port):
    try:
        target_ip = socket.gethostbyname(target)
    except socket.gaierror:
        print("\n[!] Errore: Hostname non risolvibile o non valido.")
        return

    # --- NUOVO BLOCCO: CONTROLLO HOST ---
    print(f"\n[*] Verifica stato host {target_ip} in corso...")

    if  not check_host_up(target_ip):
        print(f"[!] Host {target_ip} non raggiungibile (sembra spento o blocca i ping).")
        print("[!] Scansione annullata.")
        return
    else:
        print(f"[*] Host attivo! Inizio scansione...")
    # ------------------------------------

    print(f"[*] Scansione porte {start_port}–{end_port}")
    print("[*] Ora di inizio:", datetime.now())


    open_ports = []

    try:
        for port in range(start_port, end_port + 1):
            # Opzionale: stampa un puntino per far vedere che sta lavorando
            # print(".", end="", flush=True)

            if scan_time(target_ip, port):
                # \n serve per andare a capo se stavi stampando i puntini
                print(f"\n[+] Porta {port} APERTA")
                open_ports.append(port)

    except KeyboardInterrupt:
        print("\n\n[!] Scansione interrotta dall'utente.")
        sys.exit()

    print("\nScansione completata:", datetime.now())

    if open_ports:
        print(f"Totale porte aperte trovate: {len(open_ports)}")
    else:
        print("\nNessuna porta aperta trovata")


if __name__ == "__main__":
    try:
        target_host = input("Inserisci IP o hostname: ")
        start = int(input("Porta iniziale: "))
        end = int(input("Porta finale: "))

        port_scan(target_host, start, end)
    except ValueError:
        print("Errore: Le porte devono essere numeri interi.")
    except KeyboardInterrupt:
        print("\nProgramma terminato.")
