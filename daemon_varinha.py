import time
import threading
import pyautogui
import keyboard
import winsound
import sys
import win32clipboard
from openai import OpenAI

BANNER = r"""
  ██████╗ ██████╗  █████╗ ███╗   ███╗ █████╗ ████████╗██╗
 ██╔════╝ ██╔══██╗██╔══██╗████╗ ████║██╔══██╗╚══██╔══╝██║
 ██║  ███╗██████╔╝███████║██╔████╔██║███████║   ██║   ██║
 ██║   ██║██╔══██╗██╔══██║██║╚██╔╝██║██╔══██║   ██║   ██║
 ╚██████╔╝██║  ██║██║  ██║██║ ╚═╝ ██║██║  ██║   ██║   ██║
  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝   ╚═╝
──────────────────────────────────────────────────────────
  Corretor Gramatical Inteligente   [ v3.0 - By github.com/lumingues ]
──────────────────────────────────────────────────────────
"""

class GerenciadorClipboard:
    """Isola a manipulação da API C++ do Windows com tolerância a falhas (Spinlock)"""
    def __init__(self):
        self.backup_dados = {}

    def _tentar_acesso(self, operacao, max_tentativas=10):
        # [ARQUITETURA] Polling Ativo. 
        # Se o SO trancar a memória (ex: antivírus lendo junto), dissipamos a colisão esperando 50ms.
        for _ in range(max_tentativas):
            try:
                operacao()
                return True
            except Exception:
                time.sleep(0.05) 
            finally:
                try: win32clipboard.CloseClipboard()
                except: pass
        return False

    def fazer_backup(self):
        self.backup_dados.clear()
        def op():
            win32clipboard.OpenClipboard()
            formato = win32clipboard.EnumClipboardFormats(0)
            while formato:
                try: self.backup_dados[formato] = win32clipboard.GetClipboardData(formato)
                except: pass
                formato = win32clipboard.EnumClipboardFormats(formato)
        self._tentar_acesso(op)

    def restaurar_backup(self):
        if not self.backup_dados: return
        def op():
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            for fmt, dado in self.backup_dados.items():
                try: win32clipboard.SetClipboardData(fmt, dado)
                except: pass
        self._tentar_acesso(op)

    def ler_texto_puro(self):
        resultado = [""]
        def op():
            win32clipboard.OpenClipboard()
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                resultado[0] = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
        self._tentar_acesso(op)
        return resultado[0]

    def escrever_texto_puro(self, texto):
        def op():
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, texto)
        self._tentar_acesso(op)


class CorretorAssincrono:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)
        self.buffer_memoria = ""
        self.lock = threading.Lock()
        self.running = True
        self.clipboard = GerenciadorClipboard()
        
        # Token para evitar race conditions se o usuário flanquear o F9
        self.id_requisicao_atual = 0 

    def gatilho_f9(self):
        with self.lock:
            self.id_requisicao_atual += 1
            id_desta_thread = self.id_requisicao_atual
            
        threading.Thread(target=self._executar_captura_isolada, args=(id_desta_thread,), daemon=True).start()

    def _executar_captura_isolada(self, id_thread):
        print(f"\n>> [SISTEMA] Iniciando job #{id_thread}...")
        
        self.clipboard.fazer_backup()
        
        tentativas_de_captura = 5
        texto_bruto = ""
        
        # [LÓGICA CORE] O Loop de Inércia do IPC. 
        # O Windows demora para jogar os bytes do Ctrl+C pro Heap. Se vier vazio, tenta de novo.
        for tentativa in range(tentativas_de_captura):
            self.clipboard.escrever_texto_puro("") 
            
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.3) 
            
            texto_bruto = self.clipboard.ler_texto_puro().strip()
            
            if texto_bruto:
                break 
                
            print(f"   [!] Vazio na tentativa {tentativa + 1}. Reiniciando captura...")
            time.sleep(0.2)
        
        self.clipboard.restaurar_backup()
        
        if not texto_bruto:
            print(f">> [ABORTADO] Job #{id_thread}: Tempo esgotado ou seleção vazia. O loop permanece vivo.")
            winsound.Beep(300, 200)
            return 

        self._processar_na_nuvem(texto_bruto, id_thread)

    def _processar_na_nuvem(self, texto, id_thread):
        print(f">> [REDE] Job #{id_thread} roteando payload para LLM...")
        try:
            resposta = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Corrija a gramática e ortografia. Retorne APENAS o texto corrigido, mantendo quebras de linha exatas e estrutura original. Sem aspas ou comentários extras."},
                    {"role": "user", "content": texto}
                ],
                temperature=0.0
            )
            
            texto_corrigido = resposta.choices[0].message.content.strip()
            
            with self.lock:
                # [SEGURANÇA] Se o crachá desta thread for menor que o do sistema, ela morre silenciosamente.
                if self.id_requisicao_atual != id_thread:
                    print(f">> [CANCELADO] Job #{id_thread} descartado por obsolescência.")
                    return 
                
                self.buffer_memoria = texto_corrigido
            
            winsound.Beep(800, 100) 
            print(f">> [SUCESSO] Job #{id_thread} na memória. Dispare 'F10' para ejetar.")
            
        except Exception as erro:
            print(f">> [FALHA DE REDE] Erro na API (Job #{id_thread}): {erro}")
            winsound.Beep(300, 500)

    def injetar_texto(self):
        with self.lock:
            if not self.buffer_memoria:
                print("\n>> [ERRO] Buffer nulo.")
                winsound.Beep(300, 200)
                return
            
            print("\n>> [SISTEMA] Injetando matriz de correção...")
            self.clipboard.fazer_backup() 
            
            self.clipboard.escrever_texto_puro(self.buffer_memoria)
            pyautogui.hotkey('ctrl', 'v')
            
            winsound.Beep(2000, 150)
            
            self.buffer_memoria = "" 
            time.sleep(0.3) 
            
            self.clipboard.restaurar_backup() 
    
    def encerrar(self):
        print("\n>> [SISTEMA] Desativando hooks e fechando malha...")
        self.running = False
        sys.exit(0)

if __name__ == "__main__":
    print(BANNER)
    MINHA_API_KEY = "SUA-API-KEY-AQUI" 
    
    daemon = CorretorAssincrono(MINHA_API_KEY)
    
    keyboard.add_hotkey('f9', daemon.gatilho_f9, suppress=True)
    keyboard.add_hotkey('f10', daemon.injetar_texto, suppress=True)
    keyboard.add_hotkey('esc', daemon.encerrar, suppress=True)
    
    print("[SISTEMA] Motor de Correção v3.0 Operacional.")
    print(" -> Blindagem Win32 Ativa.")
    print(" -> Loop de Captura e Polling Habilitados.\n")
    
    try:
        while daemon.running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        daemon.encerrar()