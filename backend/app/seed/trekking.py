"""Dataset DEMO: finder "scarpe da trekking" + 120 prodotti sintetici.

Marchi e modelli sono INVENTATI (nessun riferimento a prodotti reali) e gli ASIN
iniziano con "DEMO": servono solo a sviluppare e testare l'intero sistema prima di
collegare la Creators API.
"""

from __future__ import annotations

import random

from app.models.finder import (
    Condition,
    FinderDefinition,
    FinderOption,
    FinderQuestion,
    FinderSEO,
    PriorityRule,
    ProfilePatch,
    Requirement,
    ScoringWeights,
)
from app.models.product import Product

CATEGORY = "scarpe-trekking"

USE_CASE_LABELS = {
    "walk": "Passeggiate e sentieri facili",
    "day_hike": "Escursioni in giornata",
    "multi_day": "Trekking di più giorni",
    "alpine": "Alta montagna",
}
EXPERIENCE_LABELS = {"beginner": "Principiante", "intermediate": "Intermedio", "expert": "Esperto"}


def finder_definition() -> FinderDefinition:
    q = [
        FinderQuestion(
            id="use",
            order=10,
            type="single_choice",
            question="Dove userai principalmente le scarpe?",
            options=[
                FinderOption(value="walk", label=USE_CASE_LABELS["walk"], hint="Parchi, colline, sterrati battuti",
                             patch=ProfilePatch(use_cases=["walk"])),
                FinderOption(value="day_hike", label=USE_CASE_LABELS["day_hike"], hint="Sentieri di montagna, 5-8 ore",
                             patch=ProfilePatch(use_cases=["day_hike"])),
                FinderOption(value="multi_day", label=USE_CASE_LABELS["multi_day"], hint="Rifugio in rifugio, zaino pesante",
                             patch=ProfilePatch(use_cases=["multi_day"])),
                FinderOption(value="alpine", label=USE_CASE_LABELS["alpine"], hint="Ghiacciai, neve, ramponi",
                             patch=ProfilePatch(use_cases=["alpine"])),
            ],
        ),
        FinderQuestion(
            id="experience",
            order=20,
            type="single_choice",
            question="Quanta esperienza hai?",
            options=[
                FinderOption(value=k, label=v, patch=ProfilePatch(experience=k)) for k, v in EXPERIENCE_LABELS.items()
            ],
        ),
        FinderQuestion(
            id="weather",
            order=30,
            type="single_choice",
            question="In che condizioni esci di solito?",
            options=[
                FinderOption(value="dry", label="Quasi sempre col bel tempo"),
                FinderOption(value="mixed", label="Capita pioggia o erba bagnata",
                             patch=ProfilePatch(priorities=["waterproof"])),
                FinderOption(value="wet", label="Spesso pioggia, fango o neve",
                             patch=ProfilePatch(requirements=[Requirement(attr="waterproof", op="eq", value=True, hard=True, label="impermeabile")])),
            ],
        ),
        FinderQuestion(
            id="ankle",
            order=40,
            type="single_choice",
            question="Preferisci una scarpa bassa o uno scarponcino?",
            help="Più alta = più protezione alla caviglia, ma anche più peso.",
            condition=Condition(question="use", **{"in": ["day_hike", "multi_day"]}),
            options=[
                FinderOption(value="low", label="Bassa, agile",
                             patch=ProfilePatch(requirements=[Requirement(attr="cut", op="in", value=["low"], label="taglio basso")])),
                FinderOption(value="mid", label="Media, a metà caviglia",
                             patch=ProfilePatch(requirements=[Requirement(attr="cut", op="in", value=["mid"], label="taglio medio")])),
                FinderOption(value="high", label="Alta, massimo sostegno",
                             patch=ProfilePatch(requirements=[Requirement(attr="cut", op="in", value=["high"], label="scarponcino alto")])),
                FinderOption(value="any", label="Non ho preferenze"),
            ],
        ),
        FinderQuestion(
            id="crampons",
            order=45,
            type="single_choice",
            question="Userai i ramponi?",
            condition=Condition(question="use", **{"in": ["alpine"]}),
            options=[
                FinderOption(value="no", label="No"),
                FinderOption(value="semi", label="Sì, semi-automatici",
                             patch=ProfilePatch(requirements=[Requirement(attr="crampon", op="in", value=["semi", "auto"], hard=True, label="compatibile con ramponi semi-automatici")])),
                FinderOption(value="auto", label="Sì, automatici",
                             patch=ProfilePatch(requirements=[Requirement(attr="crampon", op="eq", value="auto", hard=True, label="compatibile con ramponi automatici")])),
            ],
        ),
        FinderQuestion(
            id="priorities",
            order=50,
            type="multiple_choice",
            max_choices=2,
            question="Cosa conta di più per te? (massimo 2)",
            options=[
                FinderOption(value="lightweight", label="Leggerezza", patch=ProfilePatch(priorities=["lightweight"])),
                FinderOption(value="comfort", label="Comfort", patch=ProfilePatch(priorities=["comfort"])),
                FinderOption(value="grip", label="Aderenza", patch=ProfilePatch(priorities=["grip"])),
                FinderOption(value="durability", label="Durata nel tempo", patch=ProfilePatch(priorities=["durability"])),
            ],
        ),
        FinderQuestion(
            id="wide",
            order=60,
            type="boolean",
            question="Hai il piede largo?",
            required=True,
            patch_if_true=ProfilePatch(requirements=[Requirement(attr="wide_fit", op="eq", value=True, label="calzata per pianta larga")]),
        ),
        FinderQuestion(
            id="budget",
            order=70,
            type="range",
            question="Quanto vuoi spendere al massimo?",
            min=40, max=400, step=10, unit="€", default=150, maps_to="budget_max",
        ),
    ]
    rules = [
        PriorityRule(key="lightweight", label="Leggerezza", attr="weight_g", direction="lower", unit="g",
                     reason_template="Tra le più leggere della selezione ({value} {unit} a scarpa)"),
        PriorityRule(key="comfort", label="Comfort", attr="comfort", direction="higher", unit="/5",
                     reason_template="Comfort elevato ({value}{unit} nella nostra valutazione)"),
        PriorityRule(key="grip", label="Aderenza", attr="grip", direction="higher", unit="/5",
                     reason_template="Ottima aderenza su terreni difficili ({value}{unit})"),
        PriorityRule(key="durability", label="Durata", attr="durability", direction="higher", unit="/5",
                     reason_template="Costruzione robusta e durevole ({value}{unit})"),
        PriorityRule(key="waterproof", label="Impermeabilità", attr="waterproof", equals=True,
                     reason_template="Impermeabile: utile con pioggia ed erba bagnata"),
    ]
    seo = FinderSEO(
        title="Quale scarpa da trekking fa per te? Trovala in 8 domande",
        description="Rispondi a poche domande su uso, esperienza, meteo e budget: ti mostriamo le scarpe da trekking più adatte e ti spieghiamo perché.",
        h1="Quale scarpa da trekking fa per te?",
        intro="Non esiste la scarpa da trekking migliore in assoluto: esiste quella giusta per come cammini tu. "
              "Rispondi a qualche domanda e confrontiamo per te i modelli in base a uso, terreno, meteo e budget.",
        guide_sections=[
            {"title": "Bassa, media o alta?",
             "body": "Le scarpe basse sono leggere e agili, ideali su sentieri facili. Il taglio medio protegge meglio la caviglia "
                     "sui sentieri sassosi. Gli scarponcini alti danno il massimo sostegno con zaino pesante e su terreni impegnativi."},
            {"title": "Serve la membrana impermeabile?",
             "body": "Se esci spesso con pioggia, fango o neve, sì. Se cammini quasi sempre col bel tempo e fa caldo, una scarpa "
                     "non impermeabile traspira di più e asciuga prima."},
            {"title": "Ramponi e alta montagna",
             "body": "Per ghiacciai e neve dura servono scarponi rigidi compatibili con ramponi semi-automatici o automatici. "
                     "Una scarpa da escursionismo non è adatta, anche se è alta."},
            {"title": "Quanto spendere",
             "body": "Per sentieri facili non serve spendere molto. Per trekking di più giorni conviene investire in durata e "
                     "sostegno: una scarpa che dura tre stagioni costa meno di due che ne durano una."},
        ],
        faq=[
            {"q": "Le scarpe da trekking vanno prese di una misura in più?",
             "a": "Spesso mezza misura in più aiuta in discesa e con calze spesse. Provale nel pomeriggio, quando il piede è più gonfio."},
            {"q": "Posso usare scarpe da trail running per fare trekking?",
             "a": "Su sentieri facili e con zaino leggero sì; con carichi pesanti o terreni sassosi una scarpa da trekking protegge meglio."},
            {"q": "Quanto durano le scarpe da trekking?",
             "a": "Dipende dall'uso e dalla costruzione: la suola è di solito la prima parte a consumarsi."},
        ],
    )
    return FinderDefinition(
        slug="scarpe-trekking",
        category=CATEGORY,
        title="Scarpe da trekking",
        short_description="Trova la scarpa giusta in base a sentieri, meteo, esperienza e budget.",
        questions=q,
        priority_rules=rules,
        use_case_labels=USE_CASE_LABELS,
        experience_labels=EXPERIENCE_LABELS,
        attribute_labels={
            "cut": "Taglio", "waterproof": "Impermeabile", "weight_g": "Peso (g)", "grip": "Aderenza",
            "comfort": "Comfort", "durability": "Durata", "wide_fit": "Pianta larga", "crampon": "Ramponi",
        },
        weights=ScoringWeights(),
        seo=seo,
    )


BRANDS = ["Alpenwerk", "Sentra", "Rockline", "Vettaro", "NordPass", "Kalmo", "Orsaro", "Lumetta"]
MODELS = ["Cresta", "Forcella", "Rifugio", "Ghiaione", "Crinale", "Valico", "Larice", "Camoscio", "Torrente", "Pietra"]
CUT_LABEL = {"low": "Low", "mid": "Mid", "high": "High"}


def _pros_cons(a: dict) -> tuple[list[str], list[str]]:
    pros, cons = [], []
    if a["weight_g"] < 420:
        pros.append("Molto leggera")
    elif a["weight_g"] > 650:
        cons.append("Peso elevato")
    if a["waterproof"]:
        pros.append("Membrana impermeabile")
    else:
        cons.append("Non impermeabile")
    if a["grip"] >= 4:
        pros.append("Suola molto aderente")
    if a["comfort"] >= 4:
        pros.append("Comoda fin da subito")
    elif a["comfort"] <= 2:
        cons.append("Richiede rodaggio")
    if a["durability"] >= 4:
        pros.append("Materiali robusti")
    elif a["durability"] <= 2:
        cons.append("Durata limitata con uso intenso")
    if a["wide_fit"]:
        pros.append("Calzata ampia")
    if a["crampon"] != "none":
        pros.append("Compatibile con ramponi " + ("automatici" if a["crampon"] == "auto" else "semi-automatici"))
    return pros, cons


def generate_products(n: int = 120, seed: int = 42) -> list[Product]:
    rnd = random.Random(seed)
    out: list[Product] = []
    for i in range(n):
        kind = rnd.choices(["low", "mid", "high", "alpine"], weights=[30, 35, 25, 10])[0]
        cut = "high" if kind == "alpine" else kind
        waterproof = kind == "alpine" or rnd.random() < (0.45 if cut == "low" else 0.7)
        base_w = {"low": 340, "mid": 470, "high": 600, "alpine": 760}[kind]
        weight = int(base_w + rnd.randint(-60, 80))
        grip = rnd.randint(3, 5) if kind in ("high", "alpine") else rnd.randint(2, 5)
        comfort = rnd.randint(2, 5)
        durability = rnd.randint(3, 5) if kind in ("high", "alpine") else rnd.randint(1, 5)
        crampon = rnd.choice(["semi", "auto"]) if kind == "alpine" else ("semi" if cut == "high" and rnd.random() < 0.15 else "none")
        wide_fit = rnd.random() < 0.25

        use_cases = {"low": ["walk", "day_hike"], "mid": ["walk", "day_hike"], "high": ["day_hike", "multi_day"],
                     "alpine": ["multi_day", "alpine"]}[kind][:]
        if kind == "mid" and durability >= 4:
            use_cases.append("multi_day")
        unsuitable = []
        if crampon == "none":
            unsuitable.append("alpine")
        if cut == "low":
            unsuitable.append("multi_day")
        if kind == "alpine":
            unsuitable.append("walk")

        if kind == "alpine":
            levels = ["intermediate", "expert"]
        elif kind == "low" and durability <= 3:
            levels = ["beginner", "intermediate"]
        elif grip >= 5 and durability >= 4:
            levels = ["intermediate", "expert"]
        else:
            levels = ["beginner", "intermediate", "expert"]

        base_price = {"low": 70, "mid": 110, "high": 150, "alpine": 260}[kind]
        quality = (grip + comfort + durability - 9) * 9 + (15 if waterproof else 0)
        price = max(39.0, round(base_price + quality + rnd.randint(-15, 25), 0) - 0.01)

        brand = BRANDS[i % len(BRANDS)]
        model = MODELS[(i * 7 + rnd.randint(0, 9)) % len(MODELS)]
        name = f"{model} {CUT_LABEL[cut]}{' WP' if waterproof else ''} {100 + i}"
        slug = f"{brand}-{name}".lower().replace(" ", "-")
        attrs = {"cut": cut, "waterproof": waterproof, "weight_g": weight, "grip": grip, "comfort": comfort,
                 "durability": durability, "wide_fit": wide_fit, "crampon": crampon}
        pros, cons = _pros_cons(attrs)
        out.append(
            Product(
                id=slug, slug=slug, asin=f"DEMO{i + 1:06d}", marketplace="it", brand=brand, category=CATEGORY,
                name=name, is_demo=True, attributes=attrs, use_cases=use_cases, unsuitable_for=unsuitable,
                levels=levels, tags=[kind], reference_price=price, pros=pros, cons=cons,
            )
        )
    return out
