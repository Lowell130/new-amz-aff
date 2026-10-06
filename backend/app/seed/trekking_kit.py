"""Dataset DEMO per il Configuratore "Kit trekking".

Riusa le 120 scarpe del Finder e aggiunge 75 prodotti sintetici (marchi inventati):
zaini, bastoncini, giacche, frontali. Gli ASIN iniziano con "DEMK".

Incompatibilità di esempio (realistica): i gilet/zaini da corsa ("vest") possono portare
solo bastoncini pieghevoli a Z, non quelli telescopici.
"""

from __future__ import annotations

import random

from app.models.configurator import ComponentSpec, ConfigurationSEO, ConfigurationTemplate
from app.models.finder import (
    FinderOption,
    FinderQuestion,
    PriorityRule,
    ProfilePatch,
    Requirement,
)
from app.models.product import Product
from app.seed import trekking

R_LIGHT = PriorityRule(key="lightweight", label="Leggerezza", attr="weight_g", direction="lower", unit="g",
                       reason_template="Tra i più leggeri della selezione ({value} {unit})")
R_COMFORT = PriorityRule(key="comfort", label="Comfort", attr="comfort", direction="higher", unit="/5",
                         reason_template="Comfort elevato ({value}{unit} nella nostra valutazione)")
R_DUR = PriorityRule(key="durability", label="Durata", attr="durability", direction="higher", unit="/5",
                     reason_template="Costruzione robusta e durevole ({value}{unit})")
R_WP = PriorityRule(key="waterproof", label="Impermeabilità", attr="waterproof", equals=True,
                    reason_template="Impermeabile: utile con pioggia ed erba bagnata")
R_RAIN = PriorityRule(key="waterproof", label="Protezione pioggia", attr="rain_cover", equals=True,
                      reason_template="Coprizaino antipioggia incluso")
R_LUMEN = PriorityRule(key="brightness", label="Luminosità", attr="lumens", direction="higher", unit="lm",
                       reason_template="Fascio luminoso potente ({value} {unit})")


def template() -> ConfigurationTemplate:
    labels = trekking.USE_CASE_LABELS
    inputs = [
        FinderQuestion(
            id="use", order=10, type="single_choice", question="Che tipo di uscite fai?",
            options=[
                FinderOption(value="walk", label=labels["walk"], patch=ProfilePatch(use_cases=["walk"])),
                FinderOption(value="day_hike", label=labels["day_hike"], patch=ProfilePatch(use_cases=["day_hike"])),
                FinderOption(value="multi_day", label=labels["multi_day"], patch=ProfilePatch(use_cases=["multi_day"])),
                FinderOption(value="alpine", label=labels["alpine"], patch=ProfilePatch(use_cases=["alpine"])),
            ],
        ),
        FinderQuestion(
            id="experience", order=20, type="single_choice", question="Quanta esperienza hai?",
            options=[FinderOption(value=k, label=v, patch=ProfilePatch(experience=k))
                     for k, v in trekking.EXPERIENCE_LABELS.items()],
        ),
        FinderQuestion(
            id="weather", order=30, type="single_choice", question="Che meteo trovi di solito?",
            options=[
                FinderOption(value="dry", label="Bel tempo"),
                FinderOption(value="mixed", label="Variabile", patch=ProfilePatch(priorities=["waterproof"])),
                FinderOption(value="wet", label="Spesso pioggia o neve", patch=ProfilePatch(requirements=[
                    Requirement(attr="waterproof", op="eq", value=True, hard=True, label="impermeabile"),
                    Requirement(attr="rain_cover", op="eq", value=True, label="coprizaino antipioggia"),
                ])),
            ],
        ),
        FinderQuestion(
            id="priorities", order=40, type="multiple_choice", max_choices=2, required=False,
            question="Cosa conta di più per te? (massimo 2)",
            options=[
                FinderOption(value="lightweight", label="Leggerezza", patch=ProfilePatch(priorities=["lightweight"])),
                FinderOption(value="comfort", label="Comfort", patch=ProfilePatch(priorities=["comfort"])),
                FinderOption(value="durability", label="Durata", patch=ProfilePatch(priorities=["durability"])),
            ],
        ),
        FinderQuestion(
            id="budget", order=50, type="range", question="Budget totale per il kit",
            min=100, max=1500, step=10, unit="€", default=450, maps_to="budget_max",
        ),
    ]
    components = [
        ComponentSpec(key="scarpe", default_priorities=["comfort", "durability"], label="Scarpe", category=trekking.CATEGORY, required=True, weight=1.4,
                      priority_rules=[R_LIGHT, R_COMFORT, R_DUR, R_WP], requirement_attrs=["waterproof"],
                      attribute_labels={"cut": "Taglio", "waterproof": "Impermeabile", "weight_g": "Peso (g)"},
                      why="È il componente più importante: comfort e sicurezza dipendono soprattutto dai piedi."),
        ComponentSpec(key="zaino", default_priorities=["comfort", "durability"], label="Zaino", category="zaini", required=True, weight=1.0,
                      priority_rules=[R_LIGHT, R_COMFORT, R_DUR, R_RAIN], requirement_attrs=["rain_cover"],
                      attribute_labels={"volume_l": "Volume (l)", "weight_g": "Peso (g)", "rain_cover": "Coprizaino"},
                      why="Il volume va scelto in base alla durata delle uscite."),
        ComponentSpec(key="giacca", default_priorities=["durability", "comfort"], label="Giacca", category="giacche", required=True, weight=1.0,
                      priority_rules=[R_LIGHT, R_COMFORT, R_DUR, R_WP], requirement_attrs=["waterproof"],
                      attribute_labels={"type": "Tipo", "waterproof": "Impermeabile", "weight_g": "Peso (g)"},
                      why="In montagna il meteo cambia in fretta: una giacca adatta è una questione di sicurezza."),
        ComponentSpec(key="bastoncini", default_priorities=["durability", "lightweight"], label="Bastoncini", category="bastoncini", required=False, weight=0.6,
                      priority_rules=[R_LIGHT, R_DUR], attribute_labels={"type": "Tipo", "weight_g": "Peso (g)"},
                      why="Riducono il carico sulle ginocchia in discesa."),
        ComponentSpec(key="frontale", default_priorities=["brightness", "lightweight"], label="Lampada frontale", category="frontali", required=False, weight=0.5,
                      priority_rules=[R_LIGHT, R_LUMEN], attribute_labels={"lumens": "Lumen", "weight_g": "Peso (g)"},
                      why="Indispensabile se rischi di rientrare col buio."),
    ]
    return ConfigurationTemplate(
        slug="kit-trekking",
        title="Kit trekking",
        short_description="Scarpe, zaino, giacca e accessori: il kit completo entro il tuo budget.",
        inputs=inputs,
        components=components,
        use_case_labels=labels,
        experience_labels=trekking.EXPERIENCE_LABELS,
        seo=ConfigurationSEO(
            title="Kit trekking completo entro il tuo budget | Configuratore",
            description="Indica budget, tipo di uscite e meteo: componiamo un kit trekking coerente "
                        "(scarpe, zaino, giacca, bastoncini, frontale) e ti spieghiamo ogni scelta.",
            h1="Componi il tuo kit da trekking",
            intro="Dicci quanto vuoi spendere e come cammini: scegliamo un prodotto per ogni componente, "
                  "dando la priorità a ciò che conta davvero e senza superare il budget.",
        ),
    )


BRANDS = ["Alpenwerk", "Sentra", "Rockline", "Vettaro", "NordPass", "Kalmo", "Orsaro", "Lumetta"]


def _p(rnd, i, prefix, category, brand, name, attrs, use_cases, levels, price, tags=(), incompatible=(), unsuitable=()):
    slug = f"{brand}-{name}".lower().replace(" ", "-")
    pros = []
    if attrs.get("weight_g", 9999) < {"zaini": 900, "giacche": 300, "bastoncini": 230, "frontali": 80}[category]:
        pros.append("Leggero")
    if attrs.get("durability", 0) >= 4:
        pros.append("Materiali robusti")
    if attrs.get("comfort", 0) >= 4:
        pros.append("Molto confortevole")
    if attrs.get("waterproof"):
        pros.append("Impermeabile")
    if attrs.get("rain_cover"):
        pros.append("Coprizaino incluso")
    cons = []
    if attrs.get("durability", 5) <= 2:
        cons.append("Durata limitata con uso intenso")
    return Product(
        id=slug, slug=slug, asin=f"{prefix}{i:06d}", marketplace="it", brand=brand, category=category, name=name,
        is_demo=True, attributes=attrs, use_cases=list(use_cases), levels=list(levels), tags=list(tags),
        incompatible_with=list(incompatible), unsuitable_for=list(unsuitable),
        reference_price=round(price, 0) - 0.01, pros=pros, cons=cons,
    )


def generate_products(seed: int = 7) -> list[Product]:
    rnd = random.Random(seed)
    out: list[Product] = []
    n = 0
    all_levels = ["beginner", "intermediate", "expert"]

    # --- zaini (25)
    for i in range(25):
        n += 1
        kind = ["vest", "daypack", "daypack", "trekking", "trekking", "expedition"][i % 6]
        vol = {"vest": rnd.choice([8, 12, 15]), "daypack": rnd.choice([18, 22, 25, 28, 32]),
               "trekking": rnd.choice([38, 42, 45, 50]), "expedition": rnd.choice([55, 60, 65])}[kind]
        weight = int(vol * 28 + rnd.randint(-80, 160) + (400 if kind in ("trekking", "expedition") else 0))
        comfort, dur = rnd.randint(2, 5), rnd.randint(2, 5)
        rain = kind != "vest" and rnd.random() < 0.55
        uc = {"vest": ["walk", "day_hike"], "daypack": ["walk", "day_hike"],
              "trekking": ["multi_day", "day_hike"], "expedition": ["multi_day", "alpine"]}[kind]
        uns = {"vest": ["multi_day", "alpine"], "daypack": ["multi_day"], "trekking": [], "expedition": ["walk"]}[kind]
        price = {"vest": 55, "daypack": 45, "trekking": 110, "expedition": 170}[kind] + vol * 0.6 + (comfort + dur) * 6 + (10 if rain else 0)
        out.append(_p(rnd, n, "DEMK", "zaini", BRANDS[i % 8], f"{['Gerla', 'Bisaccia', 'Fardello', 'Sacca'][i % 4]} {vol}{' Vest' if kind == 'vest' else ''} {300 + i}",
                      {"type": kind, "volume_l": vol, "weight_g": weight, "comfort": comfort, "durability": dur, "rain_cover": rain},
                      uc, all_levels, price + rnd.randint(-10, 15), tags=[kind],
                      incompatible=["telescopic"] if kind == "vest" else [], unsuitable=uns))

    # --- bastoncini (15)
    for i in range(15):
        n += 1
        kind = "folding" if i % 3 == 0 else "telescopic"
        carbon = rnd.random() < 0.4
        weight = int((190 if carbon else 250) + rnd.randint(-25, 40) - (15 if kind == "folding" else 0))
        dur = rnd.randint(3, 5) if not carbon else rnd.randint(2, 4)
        price = (35 if not carbon else 75) + (20 if kind == "folding" else 0) + dur * 5
        out.append(_p(rnd, n, "DEMK", "bastoncini", BRANDS[(i + 3) % 8],
                      f"{'Z-Fold' if kind == 'folding' else 'Tele'} {'Carbon' if carbon else 'Alu'} {400 + i}",
                      {"type": "Pieghevoli a Z" if kind == "folding" else "Telescopici", "weight_g": weight,
                       "durability": dur, "material": "carbonio" if carbon else "alluminio"},
                      ["day_hike", "multi_day", "alpine"], all_levels, price + rnd.randint(-8, 12), tags=[kind]))

    # --- giacche (20)
    for i in range(20):
        n += 1
        kind = ["windshell", "softshell", "hardshell", "hardshell"][i % 4]
        wp = kind == "hardshell"
        weight = {"windshell": 110, "softshell": 380, "hardshell": 330}[kind] + rnd.randint(-40, 120)
        comfort, dur = rnd.randint(2, 5), rnd.randint(2, 5)
        uc = {"windshell": ["walk", "day_hike"], "softshell": ["walk", "day_hike", "multi_day"],
              "hardshell": ["day_hike", "multi_day", "alpine"]}[kind]
        uns = {"windshell": ["alpine"], "softshell": ["alpine"], "hardshell": []}[kind]
        price = {"windshell": 50, "softshell": 85, "hardshell": 140}[kind] + (comfort + dur) * 8
        lv = ["intermediate", "expert"] if kind == "hardshell" and dur >= 5 else all_levels
        out.append(_p(rnd, n, "DEMK", "giacche", BRANDS[(i + 5) % 8],
                      f"{['Bufera', 'Raffica', 'Nembo', 'Tormenta', 'Brezza'][i % 5]} {kind.capitalize()} {500 + i}",
                      {"type": kind, "waterproof": wp, "weight_g": weight, "comfort": comfort, "durability": dur},
                      uc, lv, price + rnd.randint(-15, 25), tags=[kind], unsuitable=uns))

    # --- frontali (15)
    for i in range(15):
        n += 1
        lumens = rnd.choice([150, 250, 350, 450, 600, 900])
        weight = int(45 + lumens / 15 + rnd.randint(-10, 20))
        usb = rnd.random() < 0.6
        price = 15 + lumens / 12 + (12 if usb else 0)
        out.append(_p(rnd, n, "DEMK", "frontali", BRANDS[(i + 1) % 8], f"Lucerna {lumens}{' USB' if usb else ''} {600 + i}",
                      {"lumens": lumens, "weight_g": weight, "battery": "USB" if usb else "AAA"},
                      ["day_hike", "multi_day", "alpine"], all_levels, price + rnd.randint(-5, 10)))
    return out
