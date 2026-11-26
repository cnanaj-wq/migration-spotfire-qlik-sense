"""Compose le bandeau de présentation « Migration Spotfire vers Qlik Sense ».

Deux cartes arrondies (illustration Spotfire, logo Qlik Sense) reliées par un double
chevron dégradé du bleu Spotfire vers le vert Qlik Sense. Sortie : bandeau_migration.png
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ICI = Path(__file__).parent
L, H = 1600, 760
CARTE, RAYON, Y_CARTE = 420, 44, 60
BLEU, VERT, ENCRE, GRIS = (58, 76, 240), (0, 152, 69), (31, 41, 55), (107, 114, 128)
POLICES = Path("C:/Windows/Fonts")


def police(nom, taille):
    return ImageFont.truetype(str(POLICES / nom), taille)


def carte(fond, image, x, marge):
    """Colle une carte blanche arrondie avec ombre douce, l'image centrée dedans."""
    ombre = Image.new("RGBA", fond.size, (0, 0, 0, 0))
    ImageDraw.Draw(ombre).rounded_rectangle(
        (x, Y_CARTE + 14, x + CARTE, Y_CARTE + CARTE + 14), RAYON, fill=(31, 41, 90, 60)
    )
    fond.alpha_composite(ombre.filter(ImageFilter.GaussianBlur(22)))
    ImageDraw.Draw(fond).rounded_rectangle(
        (x, Y_CARTE, x + CARTE, Y_CARTE + CARTE),
        RAYON,
        fill="white",
        outline=(222, 226, 235),
        width=2,
    )
    place = CARTE - 2 * marge
    # marge nulle : l'image remplit toute la carte (rognage centré) ; sinon elle est contenue
    choix = max if marge == 0 else min
    ratio = choix(place / image.width, place / image.height)
    img = image.resize(
        (round(image.width * ratio), round(image.height * ratio)), Image.LANCZOS
    )
    gx, gy = max(0, (img.width - CARTE) // 2), max(0, (img.height - CARTE) // 2)
    img = img.crop((gx, gy, min(img.width, gx + CARTE), min(img.height, gy + CARTE)))
    masque = Image.new("L", (CARTE, CARTE), 0)
    ImageDraw.Draw(masque).rounded_rectangle((0, 0, CARTE, CARTE), RAYON, fill=255)
    calque = Image.new("RGBA", (CARTE, CARTE), (0, 0, 0, 0))
    calque.alpha_composite(img, ((CARTE - img.width) // 2, (CARTE - img.height) // 2))
    fond.paste(
        calque,
        (x, Y_CARTE),
        Image.composite(calque, Image.new("RGBA", calque.size), masque),
    )


def chevrons(fond, x0, x1, yc):
    """Double chevron « >> » dégradé du bleu au vert."""
    masque = Image.new("L", fond.size, 0)
    d = ImageDraw.Draw(masque)
    haut, epais, pas = 78, 30, 86
    depart = (x0 + x1) // 2 - (pas + 60) // 2
    for i in range(2):
        x = depart + i * pas
        pts = [(x, yc - haut), (x + 60, yc), (x, yc + haut)]
        d.line(pts, fill=255, width=epais, joint="curve")
        for px, py in pts:
            d.ellipse(
                (px - epais // 2, py - epais // 2, px + epais // 2, py + epais // 2),
                fill=255,
            )
    degrade = Image.new("RGBA", fond.size)
    dd = ImageDraw.Draw(degrade)
    for x in range(x0, x1):
        t = (x - x0) / (x1 - x0)
        dd.line(
            [(x, 0), (x, H)],
            fill=tuple(round(a + (b - a) * t) for a, b in zip(BLEU, VERT)),
        )
    fond.paste(degrade, (0, 0), masque)


fond = Image.new("RGBA", (L, H), (248, 249, 253, 255))
x_gauche, x_droite = 250, L - 250 - CARTE
carte(fond, Image.open(ICI / "spotfire_illustration.png").convert("RGBA"), x_gauche, 0)
carte(fond, Image.open(ICI / "qlik_logo.png").convert("RGBA"), x_droite, 80)
chevrons(fond, x_gauche + CARTE, x_droite, Y_CARTE + CARTE // 2)

d = ImageDraw.Draw(fond)
d.text(
    (L // 2, 580),
    "Migration Spotfire vers Qlik Sense Cloud",
    font=police("seguisb.ttf", 56),
    fill=ENCRE,
    anchor="mm",
)
d.text(
    (L // 2, 652),
    "Tableau de bord de contrôle de gestion  ·  Cédric NANA",
    font=police("segoeui.ttf", 30),
    fill=GRIS,
    anchor="mm",
)
fond.convert("RGB").save(ICI / "bandeau_migration.png")
print("Bandeau écrit :", ICI / "bandeau_migration.png")
