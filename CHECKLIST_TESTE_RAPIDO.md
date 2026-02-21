# Checklist rápido de teste (Fases 1 a 4)

Tempo estimado: 5 a 8 minutos

## 0) Pré-check
- [ ] `GROQ_API_KEY` configurada no ambiente
- [ ] Microfone funcionando
- [ ] Projeto iniciado normalmente
- [ ] Arquivos `piper/piper.exe` e `piper/models/pt_BR-faber-medium.onnx` presentes

## 0.1) Sanidade da voz (TTS)
1. Diga: **"olá"**
   - Esperado: voz mais natural (Piper), sem timbre robótico do sintetizador padrão.
2. Diga: **"fale mais devagar"** (ou uma frase longa para ouvir prosódia)
   - Esperado: fala contínua, sem cortes, e interrupção por comando "pare" continua funcionando.

## 1) Ativação e continuidade (Fase 1)
1. Diga: **"olá"**
   - Esperado: JARVIS ativa e responde saudação.
2. Sem repetir hotword, diga uma pergunta simples (ex: **"que horas são?"**)
   - Esperado: responde dentro da janela de continuidade.
3. Diga: **"obrigado"**
   - Esperado: encerra o contexto e volta a aguardar hotword.

## 2) Memória de sessão e longo prazo (Fase 2)
1. Diga: **"lembre que eu prefiro respostas curtas"**
   - Esperado: "Certo, vou lembrar disso."
2. Diga: **"como você deve me responder?"**
   - Esperado: usa a memória recém-guardada.
3. Diga: **"meu nome é João"**
   - Esperado: memória de perfil registrada e uso em contexto posterior.

## 3) Tom adaptativo e confirmação sensível (Fase 3)
1. Diga: **"modo informal"**
   - Esperado: confirma troca de tom.
2. Faça uma pergunta curta.
   - Esperado: resposta mais natural/informal.
3. Diga: **"modo formal"**
   - Esperado: volta ao tom formal.
4. Diga: **"desligar computador"**
   - Esperado: pede confirmação sensível.

## 4) Fluxo multi-turno de clarificação (Fase 4)
1. Diga: **"abrir"**
   - Esperado: pergunta qual app abrir.
2. Responda: **"chrome"**
   - Esperado: executa abertura do app.
3. Diga: **"pesquisar"**
   - Esperado: pergunta o que pesquisar.
4. Responda: **"python fastapi tutorial"**
   - Esperado: abre busca web com o termo.

## 5) Energia segura (suspender por padrão)
1. Diga: **"encerrar por agora"**
   - Esperado: pede confirmação e entra em suspensão.
2. Diga: **"desligar totalmente em 10 minutos"**
   - Esperado: exige confirmação verbal mais explícita para desligamento.

## Critérios de aceite
- [ ] Voz neural (Piper) ativa por padrão
- [ ] Continuidade sem hotword funciona
- [ ] Memória explícita funciona
- [ ] Troca de tom formal/informal funciona
- [ ] Clarificação de comando incompleto funciona
- [ ] Ações sensíveis pedem confirmação
- [ ] Suspensão é o padrão para energia
