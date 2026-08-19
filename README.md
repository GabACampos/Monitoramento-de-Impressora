# Monitoramento de Impressora

Script em Python para monitorar automaticamente o nível de tinta/toner de impressoras em rede via protocolo **SNMP**, gerando relatórios em CSV separados por fabricante.

## 📋 O que ele faz

- Consulta uma lista de impressoras cadastradas (nome, IP e setor) via SNMP.
- Coleta o nível de cada insumo (tinta ou toner) de cada impressora, incluindo o nome do cartucho/cor.
- Calcula automaticamente a porcentagem restante de cada insumo.
- Possui um fallback específico para impressoras **Brother** (via OIDs proprietários), caso a consulta padrão não retorne dados.
- Executa as consultas de forma **assíncrona e em paralelo**, tornando a coleta rápida mesmo com várias impressoras.
- Gera dois arquivos CSV com os resultados:
  - `tintas_epson.csv`
  - `tintas_brother.csv`

## 🖨️ Impressoras monitoradas

As impressoras são cadastradas diretamente no início do script, na lista `IMPRESSORAS`, no formato `(Nome, IP, Setor)`:

```python
IMPRESSORAS = [
    ("Epson", "192.168.8.20", "RH"),
    ("Brother", "192.168.2.17", "Financeiro"),
    # ...
]
```

Para adicionar novas impressoras, basta incluir uma nova tupla nessa lista.

## 📦 Requisitos

- Python 3.8+
- Biblioteca [`pysnmp`](https://pypi.org/project/pysnmp/)

Instale as dependências com:

```bash
pip install pysnmp
```

> As impressoras precisam ter o agente **SNMP habilitado** (comunidade padrão `public`, somente leitura) e estar acessíveis na rede a partir da máquina que executa o script.

## ▶️ Como usar

1. Edite a lista `IMPRESSORAS` em `coleta.py` com o nome, IP e setor de cada impressora da sua rede.
2. Execute o script:

```bash
python coleta.py
```

3. Ao final, os arquivos `tintas_epson.csv` e `tintas_brother.csv` serão gerados (ou sobrescritos) no mesmo diretório, com as colunas:

| Coluna | Descrição |
|---|---|
| `Impressora` | Fabricante (Epson/Brother) |
| `Setor` | Setor onde a impressora está localizada |
| `IP` | Endereço IP da impressora |
| `Cor` | Nome do insumo/cor do cartucho |
| `Nivel_Porcentagem` | Nível restante do insumo (0–100%) |
| `Ultima_Atualizacao` | Data e hora da coleta |

## ⚙️ Como funciona por baixo dos panos

O script consulta os seguintes OIDs SNMP padrão (MIB *Printer-MIB*) para cada índice de insumo (1 a 8):

| OID | Descrição |
|---|---|
| `1.3.6.1.2.1.43.11.1.1.6.1.X` | Nome do insumo/cor |
| `1.3.6.1.2.1.43.11.1.1.8.1.X` | Capacidade máxima |
| `1.3.6.1.2.1.43.11.1.1.9.1.X` | Nível atual |

Caso nenhum desses índices retorne dados válidos (comum em algumas impressoras Brother), o script tenta como fallback os seguintes OIDs proprietários da Brother para o nível do toner preto:

- `1.3.6.1.4.1.2435.2.3.9.4.2.1.5.5.10.0`
- `1.3.6.1.4.1.2435.2.3.9.4.2.1.5.5.8.0`

## 💡 Possíveis melhorias futuras

- Agendamento automático da coleta (ex: via `cron` ou tarefa agendada).
- Envio de alertas (e-mail/Slack/Telegram) quando um insumo atingir nível crítico.
- Suporte a outros fabricantes além de Epson e Brother.
- Dashboard web para visualização dos dados em tempo real.
- Histórico de coletas (atualmente cada execução sobrescreve o CSV anterior).

## 📄 Licença

Defina aqui a licença do projeto (ex: MIT), caso deseje tornar o uso e a modificação explícitos para terceiros.
