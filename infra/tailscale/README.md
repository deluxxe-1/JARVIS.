# Configuración de Tailscale para ARIA

Tailscale proporciona una red segura punto a punto (VPN basada en WireGuard) para comunicar los clientes móviles/escritorio con el servidor de ARIA sin exponer puertos en Internet ni configurar cortafuegos complejos o DDNS.

---

## 1. Instalación de Tailscale

### En el Servidor (Ubuntu / Debian)
Si se ejecutó el script `scripts/setup-server.sh`, Tailscale ya estará instalado. Si no, instálalo con:
```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

### En Clientes (Android, iOS, Windows, macOS, Linux)
Descarga e instala la aplicación oficial de Tailscale para cada dispositivo:
- **Android**: Disponible en Google Play Store / F-Droid.
- **Windows / macOS**: Descargable desde [tailscale.com/download](https://tailscale.com/download).
- **Linux**: Vía script oficial o gestor de paquetes de la distribución.

---

## 2. Iniciar sesión y autenticar el servidor

Inicia el servicio y autentica la máquina en tu red Tailscale:
```bash
sudo tailscale up
```
Tailscale mostrará un enlace en la terminal (ejemplo: `https://login.tailscale.com/a/...`). Abre este enlace en un navegador para autorizar el servidor en tu red (tailnet).

---

## 3. Obtener la IP de Tailscale del Servidor

Una vez conectado, obtén la dirección IP asignada dentro de la red privada:
```bash
tailscale ip -4
```
La IP asignada tendrá el formato `100.x.y.z` (por ejemplo: `100.85.12.34`).

---

## 4. Configuración del Cliente y App Móvil (Flutter)

1. Conecta tu dispositivo cliente (teléfono Android, portátil, etc.) a la misma cuenta de Tailscale.
2. Comprueba conectividad desde el cliente haciendo ping o accediendo a la IP del servidor:
   ```bash
   ping 100.x.y.z
   ```
3. En la aplicación Flutter de ARIA, configura la URL base de la API apuntando a la IP de Tailscale:
   ```
   http://100.x.y.z:8000
   ```

---

## 5. Ventajas de Seguridad

- **Cifrado de extremo a extremo:** Todo el tráfico entre clientes y el backend de ARIA viaja cifrado con WireGuard.
- **Sin puertos abiertos al público:** No requiere abrir los puertos 8000, 5432 o 6379 en el router/firewall hacia la red pública.
- **Acceso seguro desde cualquier lugar:** Conexión continua tanto en red local como en redes móviles o WiFi externas.
