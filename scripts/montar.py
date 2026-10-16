"""Monta os dados da Plataforma Políticos do AM juntando os repositórios que seguem o contrato comum
(projetos/pesquisa/PLATAFORMA-POLITICOS-AM.md):
  - dossieprefeitosAM (prefeitos, vices, vereadores, municípios, finanças, indicadores)  [Proton]
  - deputadosfederais (deputados federais do AM)                                          [Claude]
  - senadorAM (senadores do AM)                                                            [Claude]
A chave que une tudo é o pessoa_id (sha1 do título de eleitor, 10 caracteres). Nada aqui é coletado: este script só lê
o que os repositórios publicaram e confere a integridade da junção. Repositório ausente ou arquivo ainda não gerado
é pulado e registrado no relatório (a plataforma mostra o que existe).

Saídas (site estático, GitHub Pages):
  data/indice.json         busca: todas as pessoas, municípios, bancada federal
  data/p/<xx>.json         fichas das pessoas, agrupadas pelos 2 primeiros caracteres do pessoa_id
  data/m/<cod_ibge>.json   ficha de cada município
  data/estudos.json        estudos e rankings calculados dos dados
  fotos/<pessoa_id>.jpg    copiadas dos repositórios
  INTEGRIDADE.md           checagens da junção
Uso: python -I scripts/montar.py
"""
import csv
import json
import os
import re
import shutil
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAIZ = os.path.dirname(BASE_DIR)  # projetos/pesquisa
PREF = os.path.join(RAIZ, "dossieprefeitosAM")
PARL = {"deputadosfederais": ("camara", "deputado_federal", "deputados"), "senadorAM": ("senado", "senador", "senadores")}
GITHUB = "https://github.com/leonzordhue/{repo}/blob/main/{caminho}"
DATA = os.path.join(BASE_DIR, "data")
ELEITO = {"ELEITO", "ELEITO POR QP", "ELEITO POR MÉDIA", "MÉDIA"}

checagens, alertas, ausentes = [], [], []


def chk(ok, desc):
    checagens.append((bool(ok), desc))
    return ok


def ler(*partes):
    p = os.path.join(*partes)
    if not os.path.exists(p):
        ausentes.append(os.path.relpath(p, RAIZ).replace("\\", "/"))
        return []
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def num(v, tipo=float):
    try:
        return tipo(float(v)) if v not in ("", None) else None
    except ValueError:
        return None


def slug(s):  # o mesmo de deputadosfederais/scripts/gerar.py e senadorAM/scripts/gerar.py
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def gravar_json(caminho, obj):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))


def main():
    if os.path.exists(DATA):
        shutil.rmtree(DATA)
    pessoas, cand, mand, bens = {}, defaultdict(list), defaultdict(list), defaultdict(list)
    parl = {}
    fotos_origem = {}

    # ------------------------------------------------------------ municípios e prefeituras (Proton)
    muns = {m["cod_ibge"]: m["municipio"] for m in ler(PREF, "dados", "municipios.csv")}
    chk(len(muns) == 62, f"dossieprefeitosAM: {len(muns)} municípios")
    for p in ler(PREF, "dados", "pessoas.csv"):
        pessoas[p["pessoa_id"]] = {"id": p["pessoa_id"], "nome": p["nome"], "nasc": p["nascimento"], "genero": p["genero"],
                                   "natural": "/".join(x for x in (p["municipio_nascimento"], p["uf_nascimento"]) if x)}
        if p.get("foto"):
            fotos_origem[p["pessoa_id"]] = os.path.join(PREF, p["foto"])
    for c in ler(PREF, "dados", "candidaturas_prefeito.csv"):
        cand[c["pessoa_id"]].append([int(c["ciclo"]), "prefeito", c["cod_ibge"], c["partido"], c["numero"], c["resultado"], num(c["votos"], int),
                                     num(c["pct_votos_nominais"]), int(c["turno"]), c["tipo_eleicao"][0], c["data_eleicao"], c["nome_urna"]])
    for c in ler(PREF, "dados", "candidaturas_vereador.csv"):
        cand[c["pessoa_id"]].append([int(c["ciclo"]), "vereador", c["cod_ibge"], c["partido"], c["numero"], c["resultado"], num(c["votos"], int),
                                     num(c["pct_votos_nominais"]), 1, c["tipo_eleicao"][0], c["data_eleicao"], c["nome_urna"]])
    prefeitos = defaultdict(list)
    for m in ler(PREF, "dados", "mandatos.csv"):
        prefeitos[m["cod_ibge"]].append(m)
        if m["pessoa_id"]:
            mand[m["pessoa_id"]].append(["prefeito", m["cod_ibge"], m["inicio"], m["fim_previsto"], m["partido"], m["origem"], m["observacao"]])
        if m["vice_pessoa_id"]:
            mand[m["vice_pessoa_id"]].append(["vice-prefeito", m["cod_ibge"], m["inicio"], m["fim_previsto"], m["vice_partido"], m["origem"],
                                              "mandato do vice acompanha o do prefeito eleito na chapa"])
    camara = defaultdict(lambda: defaultdict(list))
    for m in ler(PREF, "dados", "mandatos_vereador.csv"):
        if m["pessoa_id"]:
            mand[m["pessoa_id"]].append(["vereador", m["cod_ibge"], m["inicio"], m["fim_previsto"], m["partido"], m["origem"], m["observacao"]])
            camara[m["cod_ibge"]][m["ciclo"]].append([m["pessoa_id"], m["vereador"], m["nome_urna"], m["partido"], num(m["votos"], int)])
        else:
            camara[m["cod_ibge"]][m["ciclo"]].append(["", m["vereador"], "", "", None])
    for b in ler(PREF, "dados", "bens_resumo.csv"):
        bens[b["pessoa_id"]].append([int(b["ano"]), b["cargo"], b["cod_ibge"], num(b["patrimonio_sem_implausiveis"]), int(b["n_bens"]), num(b["patrimonio_declarado"]), int(b["n_implausiveis"])])

    tcu = defaultdict(list)
    for r in ler(PREF, "dados", "indicadores", "tcu_inabilitados.csv"):
        tcu[r["pessoa_id"]].append([r["processo"], r["acordao"], r["data_acordao"], r["transito_julgado"], r["inabilitado_ate"], r["fonte"]])
    gest = defaultdict(list)  # gasto por gestão (soma da série anual, R$ corrigidos pelo IPCA)
    gest_cod = defaultdict(list)
    for r in ler(PREF, "dados", "indicadores", "gestoes.csv"):
        g = [int(r["ciclo"]), r["cod_ibge"], r["inicio"], r["fim"], r["anos_atribuidos"], r["anos_sem_dado"], r["em_curso"],
             num(r["receita_orcamentaria_real"]), num(r["despesa_empenhada_real"]), num(r["desp_saude_real"]), num(r["desp_educacao_real"]),
             num(r["desp_administracao_real"]), num(r["desp_urbanismo_real"]), num(r["despesa_real_por_habitante_ano"]), num(r["pessoal_pct_rcl_medio"]),
             r["pessoa_id"], r["prefeito"], int(r["ipca_referencia"])]
        gest[r["pessoa_id"]].append(g)
        gest_cod[r["cod_ibge"]].append(g)
    # ------------------------------------------------------------ Câmaras no SAPL (projetos, normas, votos)
    sapl_pid = {(r["cod_ibge"], r["sapl_id"]): r["pessoa_id"] for r in ler(PREF, "dados", "camaras", "parlamentares.csv")}
    sapl_nome = {(r["cod_ibge"], r["sapl_id"]): r["nome_parlamentar"] or r["nome_completo"] for r in ler(PREF, "dados", "camaras", "parlamentares.csv")}
    materia = {(r["cod_ibge"], r["sapl_id"]): r for r in ler(PREF, "dados", "camaras", "materias.csv")}
    rotulo = lambda r: f"{r['sigla'] or r['tipo']} {r['numero']}/{r['ano']}"  # noqa: E731
    autoria = defaultdict(list)
    for r in ler(PREF, "dados", "camaras", "autorias.csv"):
        pid = sapl_pid.get((r["cod_ibge"], r["sapl_parlamentar_id"]))
        mt = materia.get((r["cod_ibge"], r["materia_id"]))
        if pid and mt:
            autoria[pid].append([mt["data_apresentacao"], mt["tipo"], rotulo(mt), mt["ementa"][:220], mt["url"], 1 if r["primeiro_autor"] == "True" else 0])
    votacao = {(r["cod_ibge"], r["votacao_id"]): r for r in ler(PREF, "dados", "camaras", "votacoes.csv")}
    votos = defaultdict(list)
    for r in ler(PREF, "dados", "camaras", "votos.csv"):
        pid = sapl_pid.get((r["cod_ibge"], r["sapl_parlamentar_id"]))
        vt = votacao.get((r["cod_ibge"], r["votacao_id"]))
        mt = materia.get((r["cod_ibge"], vt["materia_id"])) if vt else None
        if pid and vt:
            votos[pid].append([r["data"] or vt["data"], rotulo(mt) if mt else "", (mt["ementa"][:160] if mt else ""), r["voto"], vt["resultado"],
                               mt["url"] if mt else "", vt["sim"], vt["nao"]])
    normas = defaultdict(list)
    for r in ler(PREF, "dados", "camaras", "normas.csv"):
        normas[r["cod_ibge"]].append([r["data"], r["tipo"], r["numero"], r["ano"], r["ementa"][:220], r["url"]])
    mesa = defaultdict(list)
    for r in ler(PREF, "dados", "camaras", "mesa.csv"):
        mesa[r["cod_ibge"]].append([r["inicio"], r["fim"], r["cargo"], sapl_nome.get((r["cod_ibge"], r["sapl_parlamentar_id"]), ""),
                                    sapl_pid.get((r["cod_ibge"], r["sapl_parlamentar_id"]), "")])
    cam_fin = defaultdict(list)
    for r in ler(PREF, "dados", "indicadores", "camaras_financas.csv"):
        cam_fin[r["cod_ibge"]].append([int(r["ano"]), num(r["legislativa_empenhado"]) or num(r["camara_empenhado"]),  # função Legislativa; MSC onde ela falta
                                    num(r["camara_pessoal"]), num(r["camara_pessoal_pct_rcl"])])
    sapl_casas = {c for c, _ in sapl_pid}
    tcedec = defaultdict(list)  # decisões do TCE-AM desde 2016 (jurisprudência) em que prefeito/vice é parte
    for r in ler(PREF, "dados", "indicadores", "tceam_decisoes.csv"):
        tcedec[r["pessoa_id"]].append([r["data_arquivo"], r["orgao"], r["natureza"], r["processo"], r["decisorio"], r["termos"], r["arquivo"], r["objeto"]])
    tce = defaultdict(list)  # contas julgadas irregulares pelo TCE-AM (ligadas por CPF + nome)
    # relações de 2022+ (portal do TCE-AM) e relações antigas, 2006-2021, recuperadas do Internet Archive (script 23)
    for arq in ("tceam_contas_irregulares.csv", "tceam_listas_antigas.csv"):
        for r in ler(PREF, "dados", "indicadores", arq):
            tce[r["pessoa_id"]].append([r["data_sessao"], r["orgao"], r["natureza"], r["processo"], r["exercicio"], r["acordao"],
                                        r["orgao_julgador"], r["fonte"], r["ligacao"]])
    jul = defaultdict(list)  # fundamentos de julgamento da candidatura na Justiça Eleitoral (TSE, 2016 em diante)
    for r in ler(PREF, "dados", "julgamentos.csv"):
        jul[r["pessoa_id"]].append([int(r["ano"]), r["cargo"], r["cod_ibge"], r["resultado"], r["motivo"], r["categoria"], r["fonte"]])

    # ------------------------------------------------------------ parlamentares (Claude)
    bancada = {}
    for repo, (casa, cargo, pasta) in PARL.items():
        base = os.path.join(RAIZ, repo)
        if not os.path.isdir(base):
            ausentes.append(repo)
            continue
        ps = ler(base, "dados", "pessoas.csv")
        chk(ps, f"{repo}: {len(ps)} pessoas em dados/pessoas.csv")
        ids_ext = {}
        for i in ler(base, "dados", "identificadores.csv"):
            if i["sistema"] == casa:
                ids_ext[i["valor"]] = i["pessoa_id"]
        for p in ps:
            pid = p["pessoa_id"]
            if pid not in pessoas:
                pessoas[pid] = {"id": pid, "nome": p["nome"], "nasc": p["nascimento"], "genero": p["genero"],
                                "natural": "/".join(x for x in (p["municipio_nascimento"], p["uf_nascimento"]) if x)}
            elif pessoas[pid]["nasc"] and p["nascimento"] and pessoas[pid]["nasc"] != p["nascimento"]:
                # o repositório federal só liga quando nome + nascimento batem com o TSE das eleições gerais, e a data confere com a
                # ficha oficial da Casa: duas fontes contra um registro do TSE municipal; prevalece a do repositório federal
                alertas.append(f"resolvido: {p['nome']} ({pid}): nascimento {p['nascimento']} ({repo}: Casa + TSE eleição geral) prevalece "
                               f"sobre {pessoas[pid]['nasc']} (TSE municipal, provável erro de digitação)")
                pessoas[pid]["nasc"] = p["nascimento"]
            if slug(pessoas[pid]["nome"]) == slug(p["nome"]):
                pessoas[pid]["nome"] = p["nome"]  # mesmo nome; o da Casa costuma vir com acentos (o TSE antigo não tem)
            pessoas[pid]["urna_parl"] = p["nome_urna_mais_recente"]
            if p.get("foto") and os.path.exists(os.path.join(base, p["foto"])):
                fotos_origem[pid] = os.path.join(base, p["foto"])  # foto oficial da Casa tem prioridade sobre a do TSE
            bancada[pid] = cargo
            dossie = os.path.join(base, pasta, slug(p["nome_urna_mais_recente"] or p["nome"]) + ".md")
            achado = next((os.path.join(base, pasta, f) for f in (os.listdir(os.path.join(base, pasta)) if os.path.isdir(os.path.join(base, pasta)) else [])
                           if f.endswith(".md") and slug(f[:-3]) in (slug(p["nome"]), slug(p["nome_urna_mais_recente"]))), None)
            dossie = achado or (dossie if os.path.exists(dossie) else None)
            parl[pid] = {"casa": casa, "repo": repo, "dossie": GITHUB.format(repo=repo, caminho=os.path.relpath(dossie, base).replace("\\", "/"))
                         if dossie else "", "resumo": []}
        for c in ler(base, "dados", "candidaturas.csv"):
            cand[c["pessoa_id"]].append([int(c["ano"]), c["cargo"], c["cod_ibge"], c["partido"], c["numero"], c["resultado"].upper(),
                                         num(c["votos"], int), num(c["pct"]), num(c["turno"], int) or 1, (c["tipo_eleicao"] or "o")[0],
                                         "", c["nome_urna"]])
        for m in ler(base, "dados", "mandatos.csv"):
            mand[m["pessoa_id"]].append([m["cargo"], m["cod_ibge"], m["inicio"], m["fim"], m.get("partido", ""), m["origem"], m["observacao"]])
        for r in ler(base, "dados", "resumo.csv"):
            pid = ids_ext.get(r.get("codigo") or r.get("id") or "")
            if pid in parl:
                parl[pid]["resumo"].append(r)
            else:
                alertas.append(f"{repo}/dados/resumo.csv: linha sem pessoa ligada ({r.get('senador') or r.get('deputado') or r})")

    # ------------------------------------------------------------ integridade da junção
    orfaos = [k for k in list(cand) + list(mand) + list(bens) if k not in pessoas]
    chk(not orfaos, f"toda candidatura, mandato e declaração de bens aponta para pessoa conhecida ({len(set(orfaos))} órfãos)")
    for k in sorted(set(orfaos))[:30]:
        alertas.append(f"pessoa_id {k} aparece em candidaturas/mandatos sem cadastro em pessoas.csv")
    cruzam = [p for p in bancada if p in {x for x in cand if any(c[1] in ("prefeito", "vereador") for c in cand[x])}]
    chk(True, f"{len(cruzam)} parlamentares federais também disputaram prefeitura ou câmara municipal no AM (ligados pelo pessoa_id)")
    os.makedirs(os.path.join(BASE_DIR, "fotos"), exist_ok=True)
    for pid, origem in fotos_origem.items():
        if pid in pessoas and os.path.exists(origem):
            destino = os.path.join(BASE_DIR, "fotos", pid + ".jpg")
            if not os.path.exists(destino) or os.path.getsize(destino) != os.path.getsize(origem):
                shutil.copyfile(origem, destino)
            pessoas[pid]["foto"] = 1
    chk(all(os.path.exists(os.path.join(BASE_DIR, "fotos", p + ".jpg")) for p in pessoas if pessoas[p].get("foto")),
        f"{sum(1 for p in pessoas.values() if p.get('foto'))} fotos copiadas e presentes")

    # ------------------------------------------------------------ fichas das pessoas
    shards = defaultdict(dict)
    indice = []
    for pid, p in pessoas.items():
        cs = sorted(cand.get(pid, []), key=lambda c: (c[0], c[10] or "", c[8]))
        ms = sorted(mand.get(pid, []), key=lambda m: m[2] or "")
        ficha = {**p, "cand": cs, "mand": ms, "bens": sorted(bens.get(pid, []))}
        if pid in tcu:
            ficha["tcu"] = tcu[pid]
        if pid in tce:
            ficha["tce"] = sorted(tce[pid], reverse=True)
        if pid in gest:
            ficha["gest"] = sorted(gest[pid])
        if pid in autoria:
            au = sorted(autoria[pid], reverse=True)
            tipos = defaultdict(int)
            for a in au:
                tipos[a[1]] += 1
            ficha["autoria"] = {"n": len(au), "tipos": sorted(tipos.items(), key=lambda z: -z[1]), "lista": au[:150]}
        if pid in votos:
            vs = sorted(votos[pid], reverse=True)
            cont = defaultdict(int)
            for v in vs:
                cont[v[3]] += 1
            ficha["votos"] = {"n": len(vs), "cont": sorted(cont.items(), key=lambda z: -z[1]), "lista": vs[:200]}
        if pid in tcedec:
            ficha["tcedec"] = sorted(tcedec[pid], reverse=True)
        if pid in jul:
            ficha["jul"] = sorted(jul[pid])
        if pid in parl:
            ficha["parl"] = parl[pid]
        shards[pid[:2]][pid] = ficha
        cargos = {m[0] for m in ms}
        flags = "".join(f for f, c in (("P", "prefeito"), ("V", "vice-prefeito"), ("E", "vereador"), ("D", "deputado_federal"), ("S", "senador"))
                        if c in cargos or bancada.get(pid) == c)
        ult = cs[-1] if cs else None
        cod = next((m[1] for m in reversed(ms) if m[1]), None) or next((c[2] for c in reversed(cs) if c[2]), "")
        urna = p.get("urna_parl") or (ult[11] if ult else "")
        indice.append([pid, p["nome"], urna, flags or "c", cod, 1 if p.get("foto") else 0, ult[0] if ult else None])
    for k, v in shards.items():
        gravar_json(os.path.join(DATA, "p", k + ".json"), v)

    # ------------------------------------------------------------ fichas dos municípios
    ibge = defaultdict(list)
    for r in ler(PREF, "dados", "indicadores", "ibge.csv"):
        ibge[r["cod_ibge"]].append([int(r["ano"]), num(r["populacao"], int), num(r["pib_mil_reais"]), num(r["pib_per_capita"])])
    fin = defaultdict(list)
    campos_fin = None
    for r in ler(PREF, "dados", "indicadores", "financas.csv"):
        campos_fin = campos_fin or [c for c in r if c not in ("cod_ibge", "municipio")]
        fin[r["cod_ibge"]].append([num(r[c]) if c not in ("fonte_serie", "situacao_pessoal_lrf") else r[c] for c in campos_fin])
    ideb = defaultdict(list)
    for r in ler(PREF, "dados", "indicadores", "ideb.csv"):
        ideb[r["cod_ibge"]].append([r["etapa"], r["rede"], int(r["ano"]), num(r["ideb"]), num(r["meta"])])
    siope = defaultdict(list)
    for r in ler(PREF, "dados", "indicadores", "siope.csv"):
        siope[r["cod_ibge"]].append([int(r["ano"]), r["indicador"], num(r["valor"]), num(r["minimo"]), r["cumpriu"], r["observacao"]])
    siops = defaultdict(list)
    for r in ler(PREF, "dados", "indicadores", "siops.csv"):
        siops[r["cod_ibge"]].append([int(r["ano"]), r["indicador"], num(r["valor"]), num(r["minimo"]), r["cumpriu"], r["observacao"]])
    idhm = defaultdict(list)
    for r in ler(PREF, "dados", "indicadores", "idhm.csv"):
        idhm[r["cod_ibge"]].append([int(r["ano"]), num(r["idhm"]), num(r["idhm_educacao"]), num(r["idhm_longevidade"]), num(r["idhm_renda"]), r["faixa"]])
    declarado = defaultdict(list)  # prefeito declarado ao SIOPE quando não é o titular/vice do TSE (sinal de interino/sucessão)
    for r in ler(PREF, "dados", "prefeito_declarado.csv"):
        if r["situacao"].startswith(("outra pessoa", "sem mandato", "provável")):
            declarado[r["cod_ibge"]].append([int(r["ano"]), r["periodo"], r["nome_declarado"], r["pessoa_id"], r["titular_tse"], r["situacao"], r["data_declaracao"]])
    # quem assinou atos como prefeito(a) sem ser o titular do TSE, no Diário Oficial (AAM/SIGPub e DOM Manaus; scripts 24 e 25)
    atos = defaultdict(lambda: {"n": 0, "ini": "9999", "fim": "", "fonte": ""})
    for arq in ("prefeito_atos_aam.csv", "prefeito_atos_manaus.csv"):
        for r in ler(PREF, "dados", arq):
            if r["papel"] == "titular":
                continue
            g = atos[(r["cod_ibge"], r["pessoa_id"] or r["nome_no_ato"], r["papel"])]  # grafias diferentes da mesma pessoa numa linha
            g["n"] += 1
            if r["condicao"]:
                g["cond"] = "em exercício" if "exerc" in r["condicao"] else r["condicao"]
            g.setdefault("grafias", Counter())[r["nome_no_ato"] or ""] += 1  # a grafia mais frequente evita "AMÃ ... SEC" colado do cabeçalho
            g["pid"] = r["pessoa_id"]
            if r["data"] < g["ini"]:
                g["ini"], g["fonte"] = r["data"], re.search(r"https?://[^\s),]+", r["fonte"]).group(0)
            g["fim"] = max(g["fim"], r["data"])
    atos_mun = defaultdict(list)
    for (cod, _, papel), g in atos.items():
        cond = g.get("cond", "")
        if g["n"] >= 2 or cond or papel.startswith(("vice (presumido", "presidente")):  # ato isolado sem condição tende a ser ruído
            atos_mun[cod].append([g["grafias"].most_common(1)[0][0], g["pid"], papel, cond, g["n"], g["ini"], g["fim"], g["fonte"]])
    for v in atos_mun.values():
        v.sort(key=lambda x: x[5])
    emendas = defaultdict(lambda: defaultdict(float))
    for r in ler(PREF, "dados", "indicadores", "emendas_recebidas.csv"):
        emendas[r["cod_ibge"]][(int(r["ano"]), r["autor"], r["tipo_emenda"])] += float(r["valor_recebido"])
    eleicoes = defaultdict(lambda: defaultdict(list))
    for pid, cs in cand.items():
        for c in cs:
            if c[1] == "prefeito":
                eleicoes[c[2]][c[0]].append([pid, pessoas[pid]["nome"] if pid in pessoas else "", c[11], c[3], c[6], c[7], c[5], c[8], c[9], c[10]])
    for cod, nome in muns.items():
        pref = [{"ciclo": int(m["ciclo"]), "periodo": m["periodo"], "id": m["pessoa_id"], "nome": m["prefeito"], "urna": m["nome_urna"],
                 "partido": m["partido"], "vice_id": m["vice_pessoa_id"], "vice": m["vice"], "vice_partido": m["vice_partido"],
                 "origem": m["origem"], "inicio": m["inicio"], "fim": m["fim_previsto"], "votos": num(m["votos"], int),
                 "pct": num(m["pct_votos_nominais"]), "seguido": m["mandato_seguido"], "fonte": m["fonte"],
                 "obs": m["observacao"] + ("; fundamento no TSE: " + ", ".join(sorted({j[4] for j in jul.get(m["pessoa_id"], []) if j[0] == int(m["ciclo"])}))
                                           if "interrompido" in m["observacao"] and any(j[0] == int(m["ciclo"]) for j in jul.get(m["pessoa_id"], [])) else "")}
                for m in sorted(prefeitos.get(cod, []), key=lambda m: m["inicio"])]
        gravar_json(os.path.join(DATA, "m", cod + ".json"), {
            "cod": cod, "nome": nome, "prefeitos": pref,
            "camara": {k: sorted(v, key=lambda x: -(x[4] or 0)) for k, v in sorted(camara[cod].items())},
            "eleicoes": {k: sorted(v, key=lambda x: (x[9] or "", x[7], -(x[4] or 0))) for k, v in sorted(eleicoes[cod].items())},
            "ibge": sorted(ibge[cod]), "fin_campos": campos_fin, "fin": fin[cod], "ideb": ideb[cod], "siope": sorted(siope[cod]), "siops": sorted(siops[cod]), "idhm": sorted(idhm[cod]), "declarado": declarado[cod], "atos": atos_mun[cod], "gest": sorted(gest_cod[cod]),
            "normas": {"n": len(normas[cod]), "lista": sorted(normas[cod], reverse=True)[:150]} if normas[cod] else None,
            "mesa": sorted(mesa[cod], reverse=True), "cam_fin": sorted(cam_fin[cod]), "sapl": cod in sapl_casas,
            "emendas": sorted([[a, au, t, round(v, 2)] for (a, au, t), v in emendas[cod].items()], key=lambda x: (x[0], -x[3])),
        })

    # ------------------------------------------------------------ estudos
    estudos = estudos_calc(pessoas, cand, prefeitos, camara, fin, ideb, ibge, emendas, bens, muns)
    # painel comparativo: o último valor disponível de cada indicador, com o ano junto
    def ultimo(serie):
        serie = [x for x in serie if x[1] is not None]
        return max(serie) if serie else (None, None)
    painel = []
    for cod, nome in muns.items():
        pop = ultimo([(r[0], r[1]) for r in ibge[cod] if r[0] == 2022])
        pibpc = ultimo([(r[0], r[3]) for r in ibge[cod]])
        ai = ultimo([(r[2], r[3]) for r in ideb[cod] if r[1] == "Municipal" and r[0].startswith("anos iniciais")])
        af = ultimo([(r[2], r[3]) for r in ideb[cod] if r[1] == "Municipal" and r[0].startswith("anos finais")])
        mde = ultimo([(r[0], r[2]) for r in siope[cod] if r[1] == "mde_pct" and r[2]])
        i_ano, i_dtp = (campos_fin.index("ano"), campos_fin.index("dtp_pct_rcl")) if campos_fin else (0, 0)
        dtp = ultimo([(int(r[i_ano]), r[i_dtp]) for r in fin[cod]]) if campos_fin else (None, None)
        em = sum(v for (a, _, _), v in emendas[cod].items() if a >= 2019)
        asps = ultimo([(r[0], r[2]) for r in siops[cod] if r[1] == "asps_pct" and r[2]])
        idh = ultimo([(r[0], r[1]) for r in idhm[cod] if r[0] == 2010])
        painel.append([nome, cod, pop[1], pibpc[1], pibpc[0], ai[1], ai[0], af[1], af[0], mde[1], mde[0], dtp[1], dtp[0],
                       round(em / pop[1], 2) if pop[1] else None, asps[1], asps[0], idh[1]])
    estudos["painel"] = {"titulo": "Painel comparativo dos 62 municípios (último dado disponível)",
                         "colunas": ["município", "cod", "população 2022", "PIB por habitante", "ano", "IDEB anos iniciais (rede municipal)", "ano",
                                     "IDEB anos finais (rede municipal)", "ano", "MDE (% impostos)", "ano", "pessoal/RCL (%)", "ano",
                                     "emendas por habitante desde 2019", "saúde (% receita própria)", "ano", "IDHM 2010"],
                         "linhas": sorted(painel), "fonte": "IBGE, INEP, SIOPE/FNDE, SIOPS/MS, SICONFI, CGU, Atlas do Desenvolvimento Humano"}
    gravar_json(os.path.join(DATA, "estudos.json"), estudos)
    gravar_json(os.path.join(DATA, "indice.json"), {
        "gerado": datetime.now().isoformat(timespec="minutes"), "pessoas": indice,
        "municipios": sorted([[c, n] for c, n in muns.items()], key=lambda x: x[1]),
        "bancada": [[pid, cargo] for pid, cargo in bancada.items()],
        "ausentes": sorted(set(ausentes)),
    })
    tam = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(DATA) for f in fs)
    chk(tam < 200 * 2 ** 20, f"dados do site: {tam / 2 ** 20:.1f} MB em {sum(len(fs) for _, _, fs in os.walk(DATA))} arquivos")
    ok = sum(1 for o, _ in checagens if o)
    with open(os.path.join(BASE_DIR, "INTEGRIDADE.md"), "w", encoding="utf-8") as f:
        f.write(f"# Integridade da junção (gerado em {datetime.now():%d/%m/%Y %H:%M})\n\n"
                f"- Pessoas: {len(pessoas)}; parlamentares federais: {len(bancada)}; municípios: {len(muns)}\n"
                f"- Checagens: **{ok} de {len(checagens)} passaram**\n\n"
                + "\n".join(f"- {'✅' if o else '❌'} {d}" for o, d in checagens)
                + "\n\n## Arquivos esperados e ainda não publicados pelos repositórios\n\n" + ("\n".join(f"- {a}" for a in ausentes) or "- nenhum")
                + "\n\n## Alertas para verificação humana\n\n" + ("\n".join(f"- ⚠️ {a}" for a in alertas) or "- nenhum") + "\n")
    print(f"pessoas={len(pessoas)} bancada={len(bancada)} checagens={ok}/{len(checagens)} alertas={len(alertas)} ausentes={ausentes}")


def estudos_calc(pessoas, cand, prefeitos, camara, fin, ideb, ibge, emendas, bens, muns):
    """Cada estudo traz a pergunta, o método e a fonte junto com o resultado."""
    est = {}
    # 1. reeleição de prefeitos
    eleito_em = defaultdict(set)   # (cod, ciclo) -> pessoas eleitas prefeito na ordinária
    tentou = defaultdict(set)
    for pid, cs in cand.items():
        for c in cs:
            if c[1] == "prefeito" and c[9] == "o":
                tentou[(c[2], c[0])].add(pid)
                if c[5] in ELEITO:
                    eleito_em[(c[2], c[0])].add(pid)
    linhas = []
    for ciclo in range(2004, 2025, 4):
        n_pref = tent = reel = 0
        for cod in muns:
            for pid in eleito_em.get((cod, ciclo - 4), ()):
                n_pref += 1
                if pid in tentou.get((cod, ciclo), ()):
                    tent += 1
                    reel += pid in eleito_em.get((cod, ciclo), ())
        linhas.append([ciclo, n_pref, tent, reel, round(100 * reel / tent, 1) if tent else None])
    est["reeleicao"] = {"titulo": "Prefeitos que tentaram a reeleição e conseguiram",
                        "metodo": "Eleito na eleição ordinária do ciclo anterior que voltou a concorrer a prefeito no mesmo município.",
                        "colunas": ["eleição", "prefeitos no cargo", "tentaram", "reeleitos", "% de sucesso"], "linhas": linhas,
                        "fonte": "TSE (dossieprefeitosAM/dados/candidaturas_prefeito.csv)"}
    # 2. mulheres eleitas
    linhas = []
    for ciclo in range(2000, 2025, 4):
        pf = [p for (c, ci), ps in eleito_em.items() if ci == ciclo for p in ps]
        vr = [v[0] for cod in camara for v in camara[cod].get(str(ciclo), []) if v[0]]
        fp = sum(1 for p in pf if pessoas.get(p, {}).get("genero", "").startswith("Fem"))
        fv = sum(1 for p in vr if pessoas.get(p, {}).get("genero", "").startswith("Fem"))
        linhas.append([ciclo, len(pf), fp, round(100 * fp / len(pf), 1) if pf else None, len(vr), fv, round(100 * fv / len(vr), 1) if vr else None])
    est["mulheres"] = {"titulo": "Mulheres eleitas nas prefeituras e câmaras", "metodo": "Gênero declarado ao TSE; eleição ordinária.",
                       "colunas": ["eleição", "prefeitos eleitos", "mulheres", "%", "vereadores eleitos", "mulheres", "%"], "linhas": linhas,
                       "fonte": "TSE (consulta_cand)"}
    # 3. partidos que mais elegeram prefeitos
    part = defaultdict(Counter)
    for pid, cs in cand.items():
        for c in cs:
            if c[1] == "prefeito" and c[9] == "o" and c[5] in ELEITO:
                part[c[0]][c[3]] += 1
    est["partidos"] = {"titulo": "Partidos com mais prefeitos eleitos", "metodo": "Eleição ordinária, por partido do prefeito eleito.",
                       "por_ciclo": {str(k): v.most_common(8) for k, v in sorted(part.items())}, "fonte": "TSE"}
    # 4. pessoal acima dos limites da LRF
    linhas = defaultdict(Counter)
    for cod, rows in fin.items():
        for r in rows:
            sit = r[-1]
            if sit:
                linhas[int(r[0])][sit] += 1
    est["pessoal"] = {"titulo": "Prefeituras com despesa de pessoal acima dos limites da LRF",
                      "metodo": "RGF Anexo 1 do Poder Executivo, último período do ano. Limite 54% da RCL (LRF art. 20, III, b); prudencial 51,3%; alerta 48,6%.",
                      "colunas": ["ano", "acima do limite", "acima do prudencial", "acima do alerta", "dentro"],
                      "linhas": [[a, c["acima do limite (54%)"], c["acima do prudencial (51,3%)"], c["acima do alerta (48,6%)"], c["dentro"]]
                                 for a, c in sorted(linhas.items())], "fonte": "SICONFI (Tesouro Nacional)"}
    # 5. IDEB da rede municipal ao longo de cada mandato
    val = {(r[0], r[1], r[2], cod): r[3] for cod, rs in ideb.items() for r in rs if r[3] is not None}
    linhas = []
    for cod, ms in prefeitos.items():
        for m in ms:
            if m["origem"] != "ordinária" or not m["pessoa_id"]:
                continue
            ci = int(m["ciclo"])
            ini = val.get(("anos iniciais (1º ao 5º)", "Municipal", ci - 1, cod)) or val.get(("anos iniciais (1º ao 5º)", "Municipal", ci + 1, cod))
            ano_ini = ci - 1 if val.get(("anos iniciais (1º ao 5º)", "Municipal", ci - 1, cod)) else ci + 1
            fim = val.get(("anos iniciais (1º ao 5º)", "Municipal", ci + 3, cod))
            if ini and fim:
                linhas.append([muns[cod], cod, m["periodo"], m["pessoa_id"], m["prefeito"], m["partido"], ano_ini, ini, ci + 3, fim, round(fim - ini, 1)])
    est["ideb_mandatos"] = {"titulo": "IDEB da rede municipal (anos iniciais) durante cada mandato",
                            "metodo": "Última medição antes da posse (ou a primeira do mandato, se não houver) comparada à última medição dentro do mandato. "
                                      "O IDEB sai a cada 2 anos e mede o ano anterior à divulgação; mudança de IDEB tem muitas causas além do prefeito.",
                            "colunas": ["município", "cod", "mandato", "pessoa_id", "prefeito", "partido", "ano", "IDEB", "ano", "IDEB", "variação"],
                            "linhas": sorted(linhas, key=lambda x: -x[10]), "fonte": "INEP (divulgação 2023)"}
    # 6. emendas recebidas por habitante (2019 em diante)
    popu = {cod: dict((a, p) for a, p, _, _ in rs if p) for cod, rs in ibge.items()}
    linhas = []
    for cod, d in emendas.items():
        tot = sum(v for (a, _, _), v in d.items() if a >= 2019)
        p = popu.get(cod, {}).get(2022)
        if p:
            linhas.append([muns[cod], cod, round(tot, 2), p, round(tot / p, 2)])
    est["emendas_per_capita"] = {"titulo": "Emendas parlamentares federais pagas às prefeituras por habitante (2019 em diante)",
                                 "metodo": "Pagamentos a prefeitura, fundo ou órgão municipal; população do Censo 2022.",
                                 "colunas": ["município", "cod", "total pago", "população 2022", "R$ por habitante"],
                                 "linhas": sorted(linhas, key=lambda x: -x[4]), "fonte": "CGU (Portal da Transparência) e IBGE"}
    # 7. patrimônio declarado de quem estava no mandato e voltou a concorrer
    eleitos = {(pid, c[0]) for pid, cs in cand.items() for c in cs if c[1] in ("prefeito", "vereador") and c[5] in ELEITO}
    linhas = []
    for pid, bs in bens.items():
        por_ano = {}
        for b in bs:  # mesmo ano com duas candidaturas: fica o maior total
            por_ano[b[0]] = max(por_ano.get(b[0], (0, "", ""))[:1] + (b[1], b[2]), (b[3] or 0, b[1], b[2]))
        anos = sorted(por_ano)
        for a0, a1 in zip(anos, anos[1:]):
            if a1 - a0 == 4 and (pid, a0) in eleitos and por_ano[a0][0] > 0:
                v0, v1 = por_ano[a0][0], por_ano[a1][0]
                cargo0 = next(c[1] for c in cand[pid] if c[0] == a0 and c[5] in ELEITO)
                linhas.append([pid, pessoas[pid]["nome"] if pid in pessoas else pid, cargo0, por_ano[a0][2], a0, round(v0, 2), a1, round(v1, 2),
                               round(v1 - v0, 2)])
    est["patrimonio"] = {"titulo": "Patrimônio declarado ao TSE: quem estava no mandato e voltou a concorrer",
                         "metodo": "Total declarado na eleição em que foi eleito(a) prefeito(a) ou vereador(a) e na eleição seguinte (4 anos depois). "
                                   "Valores nominais, sem correção, informados pelo próprio candidato, em geral pelo valor de compra. "
                                   "Herança, venda, atualização de valores ou erro de declaração explicam muitas variações. Não é indício de irregularidade por si.",
                         "colunas": ["pessoa_id", "nome", "cargo", "cod", "eleição", "declarado", "eleição", "declarado", "variação"],
                         "linhas": sorted(linhas, key=lambda x: -x[8])[:40], "n_total": len(linhas), "fonte": "TSE (bem_candidato)"}
    # 8. participação de saúde e educação no gasto (média do mandato)
    est["avisos"] = ["Estudos descrevem os dados oficiais; não são juízo sobre pessoas. Confira a fonte antes de citar.",
                     "Patrimônio declarado ao TSE é o informado pelo candidato, em geral pelo valor de compra."]
    return est


if __name__ == "__main__":
    main()
