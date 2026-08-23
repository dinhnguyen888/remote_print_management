Remote & Direct Print Management in Odoo
========================================

This application enables fast, silent, and zero-cloud direct printing for physical and remote printers directly from Odoo.

It eliminates the need to download PDF files or open browser print dialogs, sending print jobs straight to local or network printers upon record validation or manual trigger.

Moreover, it provides a real-time analytics dashboard for printer stations, heartbeat monitoring, and granular report-to-printer routing.


Key Features :
--------------

    * Zero-Click Silent Printing
    * Multi-Node Print Station Management (WebSocket-based)
    * Real-time Analytics Dashboard & Status Tracking
    * Interactive Drag & Drop PDF Test Dropzone
    * Role-Based Access Control (ACL)
    * Optional Preview Modal Before Printing
    * Automated Print Job Lifecycle (Pending, Printing, Done, Error)


Supported Printers & Environments :
-----------------------------------

    * Category : Standard Physical Printers
        * USB Printers
        * Network / LAN / WiFi Printers (IP/TCP)
        * Shared Workstation Printers (Windows Spooler / CUPS)

    * Category : POS & Thermal Printers
        * Thermal Receipt Printers (via OS Driver / Spooler)
        * Barcode & Label Printers (Shipping Labels, Picking Lists)

    * Category : Supported Client Platforms (Agent Daemon)
        * Microsoft Windows (10 / 11 / Server)
        * Linux (Ubuntu / Debian / CentOS / Arch)
        * macOS (Apple Silicon & Intel)
        * Raspberry Pi OS (ARMv7 / ARM64)


How to Configure :
------------------

1. Install the Module :
    * Go to **Apps**, search for ``Remote & Direct Print Management`` and click **Install**.

2. Generate API Key in Agent Management :
    * Navigate to **Printer Dashboard > Agent Management**.
    * Create and copy the **API Key** (Node Token) for agent authentication.

3. Configure & Start Print Agent :
    * Open the Print Agent application on your target machine / mobile device.
    * Enter the required configuration parameters (Odoo Server URL and API Key).
    * Click **Start service** to connect the agent node and auto-sync local printers in real-time.

4. Set Default Printer in Configuration :
    * Navigate to **Printer Dashboard > Configuration**.
    * Select your **Default Printer** (and optionally enable silent direct printing).
    * Setup is complete and ready for instant printing!
