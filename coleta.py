import asyncio
import csv
from datetime import datetime

try:
    from pysnmp.hlapi.asyncio import (
        get_cmd,
        SnmpEngine,
        CommunityData,
        UdpTransportTarget,
        ContextData,
        ObjectType,
        ObjectIdentity
    )
except ImportError:
    try:
        from pysnmp.hlapi.v3arch.asyncio import (
            get_cmd,
            SnmpEngine,
            CommunityData,
            UdpTransportTarget,
            ContextData,
            ObjectType,
            ObjectIdentity
        )
    except ImportError:
        from pysnmp.hlapi import (
            getCmd as get_cmd,
            SnmpEngine,
            CommunityData,
            UdpTransportTarget,
            ContextData,
            ObjectType,
            ObjectIdentity
        )

# Lista das suas impressoras: (Nome, IP, Setor)
IMPRESSORAS = [
    ("Epson", "192.168.8.20", "RH"),
    ("Brother", "192.168.2.17", "Financeiro"),
    ("Brother", "192.168.4.20", "Recepção SEDE"),
    ("Brother", "192.168.2.19", "Propulsão"),
    ("Epson", "192.168.4.19", "Juridico"),
    ("Brother", "192.168.10.20", "Compras"),
    ("Epson", "192.168.10.19", "Recepção Oficina"),
    ("Epson", "192.168.6.20", "Bisu"),
    ("Brother", "192.168.5.19", "Easy"),
    # Adicione as outras impressoras aqui
]

# OIDs Base (sem o número do cartucho no final)
OID_NOME_COR = '1.3.6.1.2.1.43.11.1.1.6.1'  # Nome do insumo
OID_MAXIMA   = '1.3.6.1.2.1.43.11.1.1.8.1'  # Capacidade máxima
OID_NIVEL    = '1.3.6.1.2.1.43.11.1.1.9.1'  # Nível atual

ENGINE = SnmpEngine()

async def criar_target_snmp(ip, port=161, timeout=1.5, retries=1):
    if hasattr(UdpTransportTarget, 'create'):
        return await UdpTransportTarget.create((ip, port), timeout=timeout, retries=retries)
    return UdpTransportTarget((ip, port), timeout=timeout, retries=retries)

async def consultar_snmp(ip, oid):
    try:
        target = await criar_target_snmp(ip)
        res = get_cmd(
            ENGINE,
            CommunityData('public', mpModel=0),
            target,
            ContextData(),
            ObjectType(ObjectIdentity(oid))
        )
        if asyncio.iscoroutine(res) or hasattr(res, '__await__'):
            error, status, index, varBinds = await res
        elif hasattr(res, '__next__'):
            error, status, index, varBinds = next(res)
        else:
            error, status, index, varBinds = res

        if not error and not status and varBinds:
            val = varBinds[0][1]
            return val.prettyPrint() if hasattr(val, 'prettyPrint') else str(val)
    except Exception:
        pass
    return None

async def processar_impressora(nome, ip, setor, agora):
    dados_impressora = []
    
    # Executa a busca dos 8 índices em paralelo para esta impressora
    async def consultar_indice(idx):
        oid_cor = f"{OID_NOME_COR}.{idx}"
        oid_max = f"{OID_MAXIMA}.{idx}"
        oid_niv = f"{OID_NIVEL}.{idx}"

        nome_cor, maxima, nivel = await asyncio.gather(
            consultar_snmp(ip, oid_cor),
            consultar_snmp(ip, oid_max),
            consultar_snmp(ip, oid_niv)
        )

        if nivel is not None and maxima is not None:
            try:
                v_max = int(maxima)
                v_niv = int(nivel)
                pct = None

                if v_max > 0 and v_niv >= 0:
                    pct = round((v_niv / v_max) * 100, 1)
                elif v_max == -2 and 0 <= v_niv <= 100:
                    pct = float(v_niv)
                elif v_max == -2 and v_niv == -2:
                    pct = 100.0

                if pct is not None:
                    cor_str = str(nome_cor) if (nome_cor and "NoSuch" not in str(nome_cor)) else f"Insumo {idx}"
                    pct_inteiro = int(round(pct))
                    return [nome, setor, ip, cor_str, pct_inteiro, agora]
            except ValueError:
                pass
        return None

    resultados = await asyncio.gather(*(consultar_indice(idx) for idx in range(1, 9)))
    for r in resultados:
        if r:
            dados_impressora.append(r)

    # Fallback para impressora Brother se nenhum insumo padrão responder
    if not dados_impressora:
        for oid_brother_toner in [
            '1.3.6.1.4.1.2435.2.3.9.4.2.1.5.5.10.0',
            '1.3.6.1.4.1.2435.2.3.9.4.2.1.5.5.8.0'
        ]:
            val_brother = await consultar_snmp(ip, oid_brother_toner)
            if val_brother is not None:
                try:
                    v_b = int(val_brother)
                    if 0 <= v_b <= 100:
                        dados_impressora.append([nome, setor, ip, "Toner Preto (Brother)", int(round(v_b)), agora])
                        break
                except ValueError:
                    pass

    return dados_impressora

async def main():
    print("Iniciando coleta SNMP das impressoras...", flush=True)
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Processa TODAS as impressoras simultaneamente em paralelo
    resultados_totais = await asyncio.gather(
        *(processar_impressora(nome, ip, setor, agora) for nome, ip, setor in IMPRESSORAS)
    )

    dados = [item for sublista in resultados_totais for item in sublista]

    # Separa os dados por fabricante
    dados_epson = [item for item in dados if "epson" in item[0].lower()]
    dados_brother = [item for item in dados if "brother" in item[0].lower()]

    cabecalho = ["Impressora", "Setor", "IP", "Cor", "Nivel_Porcentagem", "Ultima_Atualizacao"]

    # Salva relatório Epson
    with open("tintas_epson.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(cabecalho)
        writer.writerows(dados_epson)

    # Salva relatório Brother
    with open("tintas_brother.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(cabecalho)
        writer.writerows(dados_brother)

    print(f"Sucesso!", flush=True)
    print(f"- 'tintas_epson.csv': {len(dados_epson)} insumos coletados.", flush=True)
    print(f"- 'tintas_brother.csv': {len(dados_brother)} insumos coletados.", flush=True)

if __name__ == "__main__":
    asyncio.run(main())