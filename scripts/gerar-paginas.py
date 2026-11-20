#!/usr/bin/env python3
"""Gera uma página por imóvel em /imovel/<código>/ (para WhatsApp e Google),
a imagem de prévia em /og/<código>.jpg e o sitemap.xml, a partir de dados/imoveis.json.
Roda sozinho no GitHub (Action "Páginas dos imóveis") sempre que o painel salva imóveis."""
import html, json, os, re, shutil, subprocess
from urllib.parse import quote

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://chapadaoimoveis.com.br"
os.chdir(RAIZ)

def ler(p, padrao):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return padrao

cfg = ler("dados/config.json", {})
lista = ler("dados/imoveis.json", [])
ZAP = re.sub(r"\D", "", str(cfg.get("whatsapp") or "")) or "5567996836202"
CRECI = str(cfg.get("creci") or "14735")

# ---- mesmas regras de limpeza do site (index.html: normalizar) ----
def num(v):
    try:
        x = float(str(v if v is not None else "").replace(".", "").replace(",", "."))
        return x if x == x else 0
    except ValueError:
        return 0

def fix_cod(v):
    s = re.sub(r"[^A-Z0-9]", "", str(v or "").upper())
    m = re.match(r"^([A-Z]{2})([A-Z0-9]+)$", s)
    return m.group(1) + m.group(2).replace("O", "0") if m else s

def fix_preco(v, neg):
    return v * 1000 if neg != "Aluguel" and 0 < v < 10000 else v

def foto_ok(u):
    return bool(re.match(r"^(/fotos/|https://)[^\"'<>\s]+$", str(u or "")))

imoveis = []
validos = [i for i in (lista if isinstance(lista, list) else [])
           if isinstance(i, dict) and i.get("publicado") is not False and i.get("titulo")]
for k, i in enumerate(validos):
    neg = i.get("negocio") or "Venda"
    imoveis.append({
        "cod": fix_cod(i.get("cod")) or "IM%03d" % (k + 1),
        "titulo": str(i["titulo"]).strip(),
        "negocio": neg, "tipo": i.get("tipo") or "Casa",
        "cidade": i.get("cidade") or "Chapadão do Sul", "bairro": i.get("bairro") or "",
        "preco": fix_preco(num(i.get("preco")), neg),
        "quartos": num(i.get("quartos")), "suites": num(i.get("suites")),
        "banheiros": num(i.get("banheiros")), "vagas": num(i.get("vagas")),
        "area": num(i.get("area")), "terreno": num(i.get("terreno")),
        "financia": bool(i.get("financia")),
        "status": i.get("status") or "Disponível",
        "descricao": str(i.get("descricao") or "").strip(),
        "fotos": [f for f in (i.get("fotos") or []) if foto_ok(f)],
    })

def brl(v):
    return "R$ " + f"{int(round(v)):,}".replace(",", ".")

def inteiro(v):
    return str(int(v)) if v == int(v) else str(v).replace(".", ",")

def preco_txt(im):
    if im["preco"] <= 0:
        return "Preço sob consulta"
    return brl(im["preco"]) + ("/mês" if im["negocio"] == "Aluguel" else "")

def detalhes(im):
    d = []
    if im["quartos"]: d.append(f'{inteiro(im["quartos"])} quarto' + ("s" if im["quartos"] > 1 else ""))
    if im["suites"]: d.append(f'{inteiro(im["suites"])} suíte' + ("s" if im["suites"] > 1 else ""))
    if im["banheiros"]: d.append(f'{inteiro(im["banheiros"])} banheiro' + ("s" if im["banheiros"] > 1 else ""))
    if im["vagas"]: d.append(f'{inteiro(im["vagas"])} vaga' + ("s" if im["vagas"] > 1 else ""))
    if im["area"]: d.append(f'{inteiro(im["area"])} m² construídos')
    if im["terreno"]: d.append(f'Terreno de {inteiro(im["terreno"])} m²')
    return d

def url_foto(f):
    return f if f.startswith("https://") else SITE + f

def gerar_og(im):
    """Imagem 1200x630 para a prévia do WhatsApp/Facebook. Sem ImageMagick, usa a 1ª foto."""
    local = next((f for f in im["fotos"] if f.startswith("/fotos/") and os.path.isfile(f[1:])), None)
    if not local:
        return url_foto(im["fotos"][0]) if im["fotos"] else SITE + "/og-image.png"
    destino = f'og/{im["cod"].lower()}.jpg'
    conv = shutil.which("magick") or shutil.which("convert")
    if not conv:
        return SITE + local
    os.makedirs("og", exist_ok=True)
    origem = local[1:]
    if not os.path.isfile(destino) or os.path.getmtime(destino) < os.path.getmtime(origem) or os.environ.get("REFAZER_OG"):
        subprocess.run([conv, origem + "[0]", "-auto-orient", "-resize", "1200x630^", "-gravity", "center",
                        "-extent", "1200x630", "-strip", "-quality", "78", destino], check=False)
    return SITE + "/" + destino if os.path.isfile(destino) else SITE + local

LAZY = ' loading="lazy"'
e = lambda s: html.escape(str(s), quote=True)

CSS = """*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:#f6f4ee;color:#1d2b25;line-height:1.5}
a{color:inherit}
.topo{background:#1f4d3a;color:#fff;padding:14px 18px;display:flex;align-items:center;gap:12px}
.topo a{text-decoration:none;display:flex;align-items:center;gap:12px}
.logo{width:40px;height:40px;border-radius:12px;background:#c8963e;display:grid;place-items:center;flex:none}
.topo b{display:block;font-size:18px}.topo small{color:#cfe0d6;font-size:12px}
main{max-width:860px;margin:0 auto;padding:0 0 110px}
.fotos{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;gap:6px;background:#123528}
.fotos img{flex:0 0 100%;width:100%;aspect-ratio:4/3;object-fit:cover;scroll-snap-align:center;display:block}
.semfoto{aspect-ratio:16/9;display:grid;place-items:center;color:#cfe0d6;background:#1f4d3a}
.dica{font-size:13px;color:#5d6b64;padding:6px 18px 0}
.info{padding:18px}
.tag{display:inline-block;font-size:13px;font-weight:700;border-radius:999px;padding:3px 12px;background:#e5f4e4;color:#17663f;margin-bottom:8px}
.tag.res{background:#f9eeda;color:#8a5a00}.tag.vend{background:#fbebeb;color:#a12a2a}
.preco{font-size:30px;font-weight:800;color:#1f4d3a}
h1{font-size:22px;line-height:1.25;margin:4px 0 6px}
.local{color:#5d6b64}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0}
.chips span{background:#fff;border:1px solid #e3ded2;border-radius:10px;padding:6px 12px;font-size:15px}
.desc{white-space:pre-line;margin:8px 0 16px;font-size:16px}
.fin{background:#fff;border:1px solid #e3ded2;border-radius:14px;padding:14px 16px;margin:16px 0}
.fin a{font-weight:700;color:#17663f}
.cod{color:#5d6b64;font-size:13px;margin-top:10px}
.acoes{position:fixed;left:0;right:0;bottom:0;background:#fff;border-top:1px solid #e3ded2;padding:12px 16px;display:flex;gap:10px;justify-content:center}
.btn{flex:1;max-width:400px;text-align:center;text-decoration:none;font-weight:700;border-radius:999px;padding:14px 16px;min-height:48px;font-size:16px}
.zap{background:#1faa59;color:#fff}.ver{background:#f0ece2;color:#1f4d3a;flex:0 1 160px}
.rodape{text-align:center;color:#5d6b64;font-size:13px;padding:10px 18px}
a:focus-visible{outline:3px solid #c8963e;outline-offset:2px}"""

LOGO = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#143528" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/></svg>'

def pagina(im):
    cod = im["cod"]; slug = cod.lower()
    url = f"{SITE}/imovel/{slug}/"
    local = ", ".join(x for x in [im["bairro"] and f'bairro {im["bairro"]}', im["cidade"]] if x)
    det = detalhes(im)
    resumo = " · ".join([preco_txt(im)] + det[:3] + [local])
    desc_meta = (resumo + (". " + im["descricao"] if im["descricao"] else ""))[:300]
    og = gerar_og(im)
    msg = f'Olá! Vi no site o imóvel {cod} - {im["titulo"]} ({preco_txt(im)}). Ainda está disponível?'
    zap = f"https://wa.me/{ZAP}?text=" + quote(msg)
    tag = {"Reservado": '<span class="tag res">Reservado</span>', "Vendido": '<span class="tag vend">Vendido</span>',
           "Alugado": '<span class="tag vend">Alugado</span>'}.get(im["status"], f'<span class="tag">{e(im["negocio"])}</span>')
    if im["fotos"]:
        imgs = "".join(f'<img src="{e(url_foto(f))}" alt="{e(im["titulo"])} - foto {n + 1}"{LAZY if n else ""} decoding="async">'
                       for n, f in enumerate(im["fotos"]))
        fotos = f'<div class="fotos">{imgs}</div>' + ('<p class="dica">Arraste para o lado para ver as ' + str(len(im["fotos"])) + ' fotos.</p>' if len(im["fotos"]) > 1 else "")
    else:
        fotos = '<div class="semfoto">Fotos em breve</div>'
    fin = (f'<div class="fin">Aceita financiamento e FGTS. <a href="{SITE}/#simulador">Veja quanto você consegue financiar</a></div>'
           if im["financia"] and im["negocio"] != "Aluguel" else "")
    ld = {"@context": "https://schema.org", "@type": "Offer", "url": url, "name": im["titulo"],
          "price": int(im["preco"]) if im["preco"] > 0 else None, "priceCurrency": "BRL",
          "availability": "https://schema.org/InStock" if im["status"] == "Disponível" else "https://schema.org/SoldOut",
          "image": og, "seller": {"@type": "RealEstateAgent", "name": "Marcio Veiga · CRECI-MS " + CRECI, "url": SITE},
          "itemOffered": {"@type": "Accommodation", "name": im["titulo"],
                          "address": {"@type": "PostalAddress", "addressLocality": im["cidade"], "addressRegion": "MS", "addressCountry": "BR"}}}
    ld = {k: v for k, v in ld.items() if v is not None}
    titulo_pag = f'{im["titulo"]} · {preco_txt(im)} · Chapadão Imóveis'
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(titulo_pag)}</title>
<meta name="description" content="{e(desc_meta)}">
<link rel="canonical" href="{url}">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; img-src 'self' https: data:; style-src 'unsafe-inline'; script-src https://static.cloudflareinsights.com; connect-src https://cloudflareinsights.com; base-uri 'none'; form-action 'none'">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="theme-color" content="#1f4d3a">
<meta property="og:type" content="website">
<meta property="og:locale" content="pt_BR">
<meta property="og:site_name" content="Chapadão Imóveis">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{e(im["titulo"] + " · " + preco_txt(im))}">
<meta property="og:description" content="{e(resumo)}">
<meta property="og:image" content="{e(og)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")}</script>
<style>{CSS}</style>
</head>
<body>
<header class="topo"><a href="/"><span class="logo">{LOGO}</span><span><b>Chapadão Imóveis</b><small>Marcio Veiga · CRECI-MS {e(CRECI)}</small></span></a></header>
<main>
{fotos}
<div class="info">
{tag}
<p class="preco">{e(preco_txt(im))}</p>
<h1>{e(im["titulo"])}</h1>
<p class="local">{e(local)}</p>
{('<div class="chips">' + "".join(f"<span>{e(x)}</span>" for x in det) + "</div>") if det else ""}
{f'<p class="desc">{e(im["descricao"])}</p>' if im["descricao"] else ""}
{fin}
<p class="cod">Código {e(cod)}</p>
</div>
<p class="rodape">Marcio Veiga · Corretor e construtor · CRECI-MS {e(CRECI)}<br><a href="/">Ver todos os imóveis</a></p>
</main>
<nav class="acoes"><a class="btn ver" href="/#imovel-{slug}">Ver no site</a><a class="btn zap" href="{e(zap)}" target="_blank" rel="noopener">Chamar no WhatsApp</a></nav>
<script defer src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon='{{"token": "6b475550a5b547d493e0ae891062e5c9"}}'></script>
</body>
</html>
"""

# ---- grava as páginas e apaga as de imóveis que saíram do site ----
os.makedirs("imovel", exist_ok=True)
feitos = set()
for im in imoveis:
    slug = im["cod"].lower()
    if slug in feitos:
        continue
    feitos.add(slug)
    os.makedirs(f"imovel/{slug}", exist_ok=True)
    with open(f"imovel/{slug}/index.html", "w", encoding="utf-8") as f:
        f.write(pagina(im))
for d in os.listdir("imovel"):
    if d not in feitos and os.path.isdir(f"imovel/{d}"):
        shutil.rmtree(f"imovel/{d}")
if os.path.isdir("og"):
    for f in os.listdir("og"):
        if f.endswith(".jpg") and f[:-4] not in feitos:
            os.remove(f"og/{f}")

with open("sitemap.xml", "w", encoding="utf-8") as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
    f.write(f"  <url><loc>{SITE}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>\n")
    for slug in sorted(feitos):
        f.write(f"  <url><loc>{SITE}/imovel/{slug}/</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>\n")
    f.write("</urlset>\n")

print(f"{len(feitos)} páginas geradas")
