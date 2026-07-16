require('dotenv').config();
const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

const PERFIS_PATH = path.join(__dirname, 'data', 'perfis.json');

function carregarPerfis() {
  const raw = fs.readFileSync(PERFIS_PATH, 'utf-8');
  return JSON.parse(raw);
}

// Lista os perfis para popular o dropdown
app.get('/api/perfis', (req, res) => {
  try {
    const perfis = carregarPerfis();
    // Envia só o essencial pro dropdown (id, nome, cargo)
    const resumo = perfis.map(p => ({ id: p.id, nome: p.nome, cargo_atual: p.cargo_atual }));
    res.json(resumo);
  } catch (err) {
    console.error(err);
    res.status(500).json({ erro: 'Não foi possível carregar os perfis.' });
  }
});

// Recebe o perfil escolhido + o problema, e devolve a análise
app.post('/api/analisar', async (req, res) => {
  const { perfilId, problema } = req.body;

  if (!perfilId || !problema || !problema.trim()) {
    return res.status(400).json({ erro: 'Selecione um perfil e descreva o problema.' });
  }

  let perfis;
  try {
    perfis = carregarPerfis();
  } catch (err) {
    return res.status(500).json({ erro: 'Não foi possível carregar os perfis.' });
  }

  const perfil = perfis.find(p => p.id === perfilId);
  if (!perfil) {
    return res.status(404).json({ erro: 'Perfil não encontrado.' });
  }

  if (!process.env.OPENAI_API_KEY || process.env.OPENAI_API_KEY === 'coloque_sua_chave_aqui') {
    return res.status(400).json({
      erro: 'A chave da API (OPENAI_API_KEY) ainda não foi configurada no arquivo .env.'
    });
  }

  try {
    const OpenAI = require('openai');
    const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

    const prompt = montarPrompt(perfil, problema);

    const resposta = await client.chat.completions.create({
      model: process.env.OPENAI_MODEL || 'gpt-4o-mini',
      messages: [
        { role: 'system', content: 'Você é um consultor especializado em analisar problemas organizacionais a partir do perfil profissional e acadêmico de uma pessoa específica, sugerindo como essa pessoa, com suas competências, poderia contribuir para resolver o problema.' },
        { role: 'user', content: prompt }
      ],
      temperature: 0.4
    });

    const analise = resposta.choices[0].message.content;
    res.json({ analise });
  } catch (err) {
    console.error(err);
    res.status(500).json({ erro: 'Erro ao chamar a API do ChatGPT. Verifique a chave e tente novamente.' });
  }
});

function montarPrompt(perfil, problema) {
  return `
PERFIL DA PESSOA
Nome: ${perfil.nome}
Cargo atual: ${perfil.cargo_atual}

Experiência profissional:
${perfil.experiencia.map(e => `- ${e}`).join('\n')}

Formação acadêmica:
${perfil.formacao.map(f => `- ${f}`).join('\n')}

Competências-chave: ${perfil.competencias_chave.join(', ')}

PROBLEMA DA EMPRESA
${problema}

TAREFA
Com base exclusivamente na experiência, formação e competências dessa pessoa, analise o problema acima e aponte:
1. Quais aspectos do problema essa pessoa está mais qualificada para identificar/diagnosticar.
2. Ações concretas que ela poderia tomar, dado seu histórico.
3. Limitações do olhar dela (o que ficaria de fora, exigindo outro perfil).
Seja direto e objetivo.
`.trim();
}

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Servidor rodando em http://localhost:${PORT}`);
});
