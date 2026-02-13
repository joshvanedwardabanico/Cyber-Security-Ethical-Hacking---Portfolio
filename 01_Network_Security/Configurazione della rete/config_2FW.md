# Configurazione Doppio Firewall
**Obiettivo:** Costruire un'architettura di rete sicura con due firewall (pfSense) in cascata.
**Scopo:** Isolare il Web Server (Meta2) in una DMZ e proteggere la rete di Theta (Kali) in una rete interna separata.
**Testato?** Sì 

---

## 1. Schema degli Indirizzi IP (Piano di indirizzamento)

Per evitare conflitti, useremo questi indirizzi **Statici**:

* **Zona 1: WAN (Internet/Casa)**
    * Rete: `192.168.1.x` (o quella del tuo router di casa)
    * **pfSense1 WAN:** DHCP (assegnato dal router di casa) `192.168.1.16` nel mio caso

* **Zona 2: DMZ (Rete Intermedia)**
    * Rete: `192.168.100.0/24`
    * **pfSense1 LAN:** `192.168.100.1` (Gateway per la DMZ)
    * **Meta2 (Server):** `192.168.100.50`
    * **pfSense2 WAN:** `192.168.100.2`

* **Zona 3: Internal (Rete Sicura)**
    * Rete: `192.168.150.0/24`
    * **pfSense2 LAN:** `192.168.150.1` (Gateway per Kali)
    * **Kali Linux:** DHCP (range `.10-.200`) o Statico

---

## 2. Configurazione su VirtualBox

Prima di avviare le macchine, configura le schede di rete virtuali

### VM: pfSense 1 (Firewall Perimetrale)
* **Adapter 1:** Scheda con Bridge (Bridged Adapter) -> *Verso Internet*
* **Adapter 2:** Rete Interna (Internal Network) -> Nome: `DMZ_net`

### VM: Meta2 (Metasploitable)
* **Adapter 1:** Rete Interna (Internal Network) -> Nome: `DMZ_net`

### VM: pfSense 2 (Firewall Interno)
* **Adapter 1:** Rete Interna (Internal Network) -> Nome: `DMZ_net`
* **Adapter 2:** Rete Interna (Internal Network) -> Nome: `theta_net`

### VM: Kali Linux
* **Adapter 1:** Rete Interna (Internal Network) -> Nome: `theta_net`

---

## 3. Configurazione pfSense 1 (Il Perimetrale)

Avvia la VM `pfSense 1`.

### A. Assegnazione Interfacce (Console)
1.  Seleziona **Option 1** (Assign Interfaces).
2.  **WAN:** `vtnet0` (o la tua interfaccia bridged).
3.  **LAN:** `vtnet1` (o la tua interfaccia DMZ_net).

### B. Impostazione IP (Console)
1.  Seleziona **Option 2** (Set interface IP address).
2.  **Configura WAN:** Lascia DHCP (scrivi `y`) per connetterti a Internet facilmente.
3.  **Configura LAN:**
    * IP Address: `192.168.100.1`
    * Subnet mask: `24`
    * Gateway: *Premi Invio (Nessuno)*
    * DHCP Server on LAN: **n** (No, useremo IP statici nella DMZ).

### C. Sblocco Traffico (Interfaccia Web)
Accedi da un browser (dal tuo PC fisico se la WAN è raggiungibile, o temporaneamente da una VM).
1.  Vai su **Interfaces > WAN**.
2.  In fondo, **deseleziona** (togli la spunta):
    * `Block private networks and loopback addresses`
    * `Block bogon networks`
3.  Clicca **Save** e **Apply Changes**.

---

## 4. Configurazione Metaspoiltable2 (Il Web Server)

Avvia la VM `Metasploitable2`. Login: `msfadmin` / `msfadmin`.

### Impostazione IP Statico
Dobbiamo modificare il file di configurazione perché non c'è DHCP nella DMZ.

1.  Apri il file:
    `sudo nano /etc/network/interfaces`
2.  Modifica la sezione `eth0` per renderla identica a questa:

```bash
auto eth0
iface eth0 inet static
address 192.168.100.50
netmask 255.255.255.0
gateway 192.168.100.1
dns-nameservers 8.8.8.8
````

3. Salva: `Ctrl+O` -> `Invio`.
    
4. Esci: `Ctrl+X`.
    
5. Riavvia la rete: `sudo /etc/init.d/networking restart` (o riavvia la VM `sudo reboot`).
    
6. **Test:** Digita `ping 8.8.8.8`. Se risponde, Meta2 è online.
    

---

## 5. Configurazione pfSense 2 (L'Interno)

Avvia la VM `pfSense 2`.

### A. Assegnazione Interfacce (Console)

1. **WAN:** `vtnet0` (Interfaccia su `DMZ_net`).
    
2. **LAN:** `vtnet1` (Interfaccia su `theta_net`).
    

### B. Impostazione IP (Console - Cruciale)

Seleziona **Option 2**.

1. **Configura WAN (Interfaccia 1):**
    
    - DHCP? **n**
        
    - IPv4 Address: `192.168.100.2`
        
    - Subnet: `24`
        
    - **Upstream Gateway:** `192.168.100.1` (Punta a pfSense 1). **Importante!**
        
2. **Configura LAN (Interfaccia 2):**
    
    - IPv4 Address: `192.168.150.1`
        
    - Subnet: `24`
        
    - Gateway: _Premi Invio_
        
    - DHCP Server: **y** (Comodo per Kali).
        
    - Range: `192.168.150.10` - `192.168.150.200`.
        

### C. Configurazione Web (da Kali Linux)

Accedi a Kali. Apri Firefox e vai su `https://192.168.150.1`. Login: `admin` / `pfsense`.

1. **Sblocco WAN:**
    
    - Vai su **Interfaces > WAN**.
        
    - Togli la spunta a `Block private networks`.
        
    - **Save & Apply**.
        
2. **Fix DNS (Per navigare):**
    
    - Vai su **System > General Setup**.
        
    - DNS Servers: `8.8.8.8` e `1.1.1.1`.
        
    - **Togli la spunta** a "Allow DNS server list to be overridden...".
        
    - **Save**.
        
    - Vai su **Services > DNS Resolver**: Togli la spunta "Enable". Save.
        
    - Vai su **Services > DNS Forwarder**: Metti la spunta "Enable". Save & Apply.
        

---

## 6. Configurazione Regole Firewall (Security Rules)

Ora rendiamo la rete sicura secondo la consegna.

### Su pfSense 1 (Perimetrale)

**Obiettivo:** Far entrare traffico Web verso Meta2.

1. **Port Forwarding (NAT):**
    
    - Vai su **Firewall > NAT > Port Forward**.
        
    - Add New Rule:
        
        - Interface: `WAN`
            
        - Protocol: `TCP`
            
        - Dest. Port Range: `HTTP (80)`
            
        - Redirect Target IP: `192.168.100.50` (IP Statico Meta2)
            
        - Redirect Target Port: `HTTP (80)`
            
    - **Save & Apply**.
        
2. **Verifica Regole LAN:**
    
    - Vai su **Firewall > Rules > LAN**.
        
    - Assicurati che ci sia la regola "Default allow LAN to any" (passa tutto in uscita).
        

### Su pfSense 2 (Interno)

**Obiettivo:** Proteggere Kali. Niente entra, tutto esce.

1. **Blocco WAN (Default Deny):**
    
    - Vai su **Firewall > Rules > WAN**.
        
    - Assicurati che la lista sia **VUOTA** (o che ci siano solo regole di blocco). Nessuna regola "Pass".
        
    - _Risultato:_ La DMZ non può iniziare connessioni verso Kali.
        
2. **Permesso LAN:**
    
    - Vai su **Firewall > Rules > LAN**.
        
    - Assicurati che ci sia "Default allow LAN to any".
        
    - _Risultato:_ Kali può uscire.
        

---

## 7. Test Finale

1. **Da Kali (Browser):** Vai su `google.com`. Deve funzionare. se non funziona, stacca e riattacca il cavo da kali
    
2. **Da Kali (Ping):** `ping 192.168.100.50` (Meta2). Deve funzionare (attacco possibile).
    
3. **Da Meta2 (Ping):** `ping 192.168.11.1` (pfSense2) o `192.168.11.100` (Kali). **NON DEVE funzionare** (bloccato dal firewall).
    
4. **Dall'Esterno (Browser PC Fisico):** Vai su `http://192.168.1.X` (L'IP WAN di pfSense1). Dovresti vedere la pagina di Meta2 (DVWA/Metasploitable).
