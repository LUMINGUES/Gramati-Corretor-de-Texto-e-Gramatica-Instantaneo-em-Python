# Gramati-Corretor-de-Texto-e-Gramatica-Instantaneo-em-Python
Daemon assíncrono em Python que opera como uma camada invisível de correção gramatical (OpenAI API). Ele intercepta, processa e injeta texto em qualquer interface do Windows via hooks de teclado (F9/F10) e manipulação de clipboard.
Corretor Gramatical Assíncrono (v1.2.1)
Um daemon local de baixa latência que atua como uma camada invisível de correção gramatical em nível de Sistema Operacional (Windows). Ele intercepta seleções de texto em qualquer aplicação via simulação de I/O, delega o processamento semântico para a nuvem (OpenAI) e injeta o resultado de volta, tudo orquestrado por atalhos globais.

🏗️ Arquitetura do Sistema (Top-Down)
O sistema opera em um modelo de Desacoplamento de UI/Kernel e Processamento Assíncrono. A arquitetura se divide em três camadas lógicas:

Camada de Interceptação (OS Hooking): A biblioteca keyboard cria hooks diretamente no kernel do Windows. Para evitar travamentos (congelamento de input do usuário), o gatilho principal (F9) atua apenas como um despachante.

Camada de Processamento (Worker Thread): O heavy-lifting (manipulação de clipboard e requisição HTTP para a API) é isolado em uma Thread separada (Daemon).

Camada de Injeção (Simulação HID): Após o processamento seguro em um buffer com Lock (Mutex), o sistema usa pyautogui para simular fisicamente a digitação (Ctrl+V) de volta no software alvo.

⚙️ A Lógica por Trás da Engenharia (O "Porquê")
Por que não usar a API de Acessibilidade do Windows (UIAutomation)? Ler e escrever texto nativamente requer integração profunda e complexa com APIs do SO, que variam por aplicativo (Word funciona diferente do Chrome). A solução: Usar o Clipboard (Área de Transferência) via atalhos de teclado (Ctrl+C / Ctrl+V) é um hack universal. Funciona em 99% das interfaces de usuário.

A Necessidade da Thread e do Mutex (self.lock): Requisições de rede têm latência imprevisível. Se F9 bloqueasse a thread principal, o Windows mataria o processo por inatividade ("Não Respondendo"). O Lock garante que o usuário não tente injetar (F10) enquanto a OpenAI ainda está escrevendo na variável de memória (buffer_memoria), prevenindo Race Conditions.

Feedback Acústico (Beeps): Como o script é "invisível" (Headless UI), os beeps substituem os logs visuais, criando uma comunicação máquina-humano de baixa fricção. Frequências e durações específicas codificam estados (sucesso, falha de rede, seleção vazia).

🚀 Setup e Execução
Dependências:

Bash
pip install pyperclip pyautogui keyboard openai
Configuração:

Isole a Credencial: Remova a variável MINHA_API_KEY do código-fonte. Utilize variáveis de ambiente (ex: os.environ.get("OPENAI_API_KEY")) ou um arquivo .env.

Execução: Rode o script (preferencialmente sem console anexado usando pythonw no Windows, para total invisibilidade).

Bash
python corretor.py
Uso:

Selecione o texto -> F9 (Extrai e processa).

Aguarde o Bipe -> F10 (Injeta a correção).

ESC (Mata o daemon e libera os hooks).
