# services/print_service.py
import tempfile
import os
import subprocess
from datetime import datetime
from escpos.printer import Usb, Network, File
import tempfile

def print_receipt_text(receipt_text: str, printer_name: str = None):
    """
    Imprime un texto formateado en una impresora térmica.
    Si printer_name es None, usa la impresora predeterminada.
    """
    try:
        import win32print
        import win32ui
    except ImportError:
        # Fallback: guardar como archivo .txt y abrir con bloc de notas
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(receipt_text)
            temp_path = f.name
        subprocess.run(['notepad', '/pt', temp_path], shell=True)
        os.unlink(temp_path)
        return

    # Obtener la impresora
    if printer_name:
        hprinter = win32print.OpenPrinter(printer_name)
    else:
        # Impresora predeterminada
        default_printer = win32print.GetDefaultPrinter()
        hprinter = win32print.OpenPrinter(default_printer)
    
    try:
        # Iniciar trabajo de impresión
        job = win32print.StartDocPrinter(hprinter, 1, ("Ticket", None, "RAW"))
        try:
            win32print.StartPagePrinter(hprinter)
            # Enviar texto como raw (la impresora térmica normalmente acepta texto)
            win32print.WritePrinter(hprinter, receipt_text.encode('cp850', errors='replace'))
            win32print.EndPagePrinter(hprinter)
        finally:
            win32print.EndDocPrinter(hprinter)
    finally:
        win32print.ClosePrinter(hprinter)
 def print_receipt_escpos(receipt_text: str, printer_config: dict = None):
    """
    Imprime usando ESC/POS. printer_config puede ser:
    {'type': 'usb', 'vendor_id': 0x0416, 'product_id': 0x5011}
    o {'type': 'network', 'host': '192.168.1.100', 'port': 9100}
    """
    try:
        if printer_config and printer_config.get('type') == 'usb':
            printer = Usb(printer_config['vendor_id'], printer_config['product_id'], 0, 0x81, 0x03)
        elif printer_config and printer_config.get('type') == 'network':
            printer = Network(printer_config['host'], printer_config.get('port', 9100))
        else:
            # Intenta encontrar impresora USB automáticamente
            from escpos.printer import Dummy
            printer = Dummy()  # fallback, no imprime
            return
    except Exception as e:
        # Fallback: guardar archivo
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(receipt_text)
        return

    printer.text(receipt_text)
    printer.cut()