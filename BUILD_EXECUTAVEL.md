# JARVIS - Guia de Criação de Executável

## 📦 Como criar o executável (.exe)

### Método 1: Script Automático (Recomendado)

1. **Execute o script:**
   ```cmd
   build_exe.bat
   ```

2. **Aguarde o processo** (pode levar 2-5 minutos)

3. **Encontre o executável:**
   - Localização: `dist\JARVIS.exe`
   - Tamanho aproximado: 150-300 MB (inclui todos os modelos)

### Método 2: Manual

```powershell
# Limpar builds anteriores
Remove-Item -Path "dist" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "build" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "*.spec" -Force -ErrorAction SilentlyContinue

# Criar executável
python -m PyInstaller `
    --name="JARVIS" `
    --onefile `
    --windowed `
    --add-data="piper;piper" `
    --add-data="vosk-model-small-pt-0.3;vosk-model-small-pt-0.3" `
    --add-data="config.py;." `
    --hidden-import="vosk" `
    --hidden-import="piper" `
    --hidden-import="sounddevice" `
    --hidden-import="pyqtgraph" `
    --hidden-import="psutil" `
    --hidden-import="ollama" `
    --collect-all="vosk" `
    --collect-all="piper" `
    --collect-all="sounddevice" `
    --collect-all="pyqtgraph" `
    main_vosk.py
```

---

## 📋 O que está incluído no executável

✅ **Modelos de IA:**
- Piper TTS (pt_BR-faber-medium.onnx) - Síntese de voz
- Vosk STT (vosk-model-small-pt-0.3) - Reconhecimento de voz

✅ **Bibliotecas Python:**
- PyQt6 (Interface gráfica)
- Vosk (Reconhecimento de voz)
- Piper-TTS (Síntese de voz)
- sounddevice (Áudio)
- psutil (Sistema)
- pyqtgraph (Gráficos)
- ollama (IA - requer instalação separada)

✅ **Código fonte compilado:**
- Todos os arquivos .py transformados em bytecode

---

## 🚀 Como distribuir

### Opção 1: Executável Único
- **Arquivo:** `dist\JARVIS.exe`
- **Tamanho:** ~150-300 MB
- **Vantagem:** Um único arquivo, fácil de distribuir
- **Desvantagem:** Tamanho grande

### Opção 2: Instalador (Avançado)
Para criar um instalador `.msi` ou `.exe` com interface:
1. Use **Inno Setup** (gratuito): https://jrsoftware.org/isinfo.php
2. Use **NSIS**: https://nsis.sourceforge.io/

---

## ⚙️ Requisitos no computador destino

### ✅ Já incluso no executável:
- Python (runtime embutido)
- Todas as bibliotecas Python
- Modelos de IA (Vosk STT + Piper TTS)
- Interface gráfica (PyQt6)

### ❌ Precisa instalar separadamente:
1. **Ollama** (para respostas da IA): https://ollama.ai/
   - Após instalar: `ollama pull llama3`
   
2. **Microsoft Visual C++ Redistributable** (se não tiver):
   - Download: https://aka.ms/vs/17/release/vc_redist.x64.exe

### ⚠️ Importante:
- O executável carrega os modelos da pasta temporária do Windows
- Primeira execução pode levar 10-30 segundos (descompactação)
- Os arquivos `vosk-model-small-pt-0.3` e `piper` são embutidos automaticamente

---

## 🐛 Resolução de Problemas

### Erro: "DLL load failed"
**Solução:** Instale o **Microsoft Visual C++ Redistributable**
- Download: https://aka.ms/vs/17/release/vc_redist.x64.exe

### Erro: "Ollama not found"
**Solução:** 
1. Instalar Ollama: https://ollama.ai/
2. Executar: `ollama pull llama3`
3. Verificar que o serviço está rodando

### Erro: "Vosk model not found"
**Solução:** O modelo deve estar na mesma pasta do executável
- Estrutura esperada:
  ```
  JARVIS.exe
  vosk-model-small-pt-0.3/
      final.mdl
      ...
  piper/
      models/
          pt_BR-faber-medium.onnx
      ...
  ```

### Executável muito lento para iniciar
**Normal:** Primeira execução pode levar 10-30 segundos
- PyInstaller descompacta arquivos em pasta temporária
- Execuções seguintes são mais rápidas

---

## 📏 Otimizações de Tamanho

### Reduzir tamanho do executável:

1. **Usar modelo Vosk menor** (já está usando o small)

2. **Remover bibliotecas não usadas:**
   ```powershell
   --exclude-module="matplotlib"
   --exclude-module="scipy"
   --exclude-module="pandas"
   ```

3. **Compactar com UPX:**
   ```powershell
   # Baixar UPX: https://upx.github.io/
   --upx-dir="C:\path\to\upx"
   ```

---

## 🔐 Segurança

### Antivírus pode bloquear
**Por quê:** Executáveis PyInstaller são frequentemente marcados como falso positivo

**Soluções:**
1. **Assinar digitalmente** o executável (requer certificado)
2. **Adicionar exceção** no antivírus
3. **Enviar para análise** (VirusTotal, Microsoft, etc.)

### Código fonte
- O código **não** fica completamente protegido
- É possível descompilar (com dificuldade)
- Para proteção máxima: usar Cython ou ofuscadores

---

## 📦 Distribuição Profissional

### Criar Instalador Completo

**Usando Inno Setup:**

```iss
[Setup]
AppName=JARVIS
AppVersion=1.0
DefaultDirName={pf}\JARVIS
DefaultGroupName=JARVIS
OutputDir=installer
OutputBaseFilename=JARVIS_Setup

[Files]
Source: "dist\JARVIS.exe"; DestDir: "{app}"
Source: "vosk-model-small-pt-0.3\*"; DestDir: "{app}\vosk-model-small-pt-0.3"; Flags: recursesubdirs
Source: "piper\*"; DestDir: "{app}\piper"; Flags: recursesubdirs

[Icons]
Name: "{group}\JARVIS"; Filename: "{app}\JARVIS.exe"
Name: "{userdesktop}\JARVIS"; Filename: "{app}\JARVIS.exe"

[Run]
Filename: "{app}\JARVIS.exe"; Description: "Iniciar JARVIS"; Flags: nowait postinstall skipifsilent
```

---

## ✅ Checklist Final

Antes de distribuir:

- [ ] Executável criado com sucesso
- [ ] Testado em máquina limpa (sem Python)
- [ ] Ollama instalado e modelo llama3 baixado
- [ ] Ícone personalizado adicionado (opcional)
- [ ] Antivírus não bloqueia
- [ ] Documentação incluída (ROTINAS.md, INSTRUÇÕES_VOSK.md)
- [ ] Versão documentada
- [ ] README com instruções de instalação

---

## 📄 Exemplo de README para Distribuição

```markdown
# JARVIS - Assistente Virtual

## Instalação Rápida

1. Execute `JARVIS_Setup.exe` (ou copie `JARVIS.exe` para uma pasta)
2. Instale Ollama: https://ollama.ai/
3. Abra PowerShell e execute: `ollama pull llama3`
4. Execute `JARVIS.exe`
5. Diga "Olá" para ativar!

## Requisitos
- Windows 10/11 (64-bit)
- Microfone
- Ollama instalado
- 4GB RAM mínimo

## Problemas?
Consulte ROTINAS.md para lista completa de comandos.
```

---

**Pronto para criar o executável!**
Execute `build_exe.bat` e aguarde o processo.
