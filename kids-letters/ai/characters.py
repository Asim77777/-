"""Fixed character descriptions for the image model.

SDXL reads about 75 tokens per prompt, so the most important words come first:
style, then identity (hair, face, outfit), then setting and light.
Identity follows the chosen 2D design (kids-letters/characters/src/option1.js)."""

STYLE = 'cinematic 3d animated film still, hyperrealistic, detailed skin, volumetric light'
SETTING = 'Jerusalem stone courtyard, blue door, bougainvillea, golden hour'

# Age cues come right after the style: the model otherwise drifts to 8-10 year olds.
# Each garment names one color only; extra colors (shoes, jeans) bleed into the main garment.
NOAM = ('small 5 year old boy, chubby cheeks, round baby face, big brown eyes, fair skin, curly brown hair, '
        'gap-toothed grin, plain bright orange hoodie, jeans, red sneakers')

TAMAR = ('small 5 year old girl, chubby cheeks, round baby face, big brown eyes, brown skin, dark hair in two afro puffs, '
         'plain bright yellow overalls, pink striped shirt, white sneakers')

NEGATIVE = ('photo, photograph, teenager, teen, older child, tall, long legs, mature face, adult, text, letters, words, '
            'watermark, signature, logo, print on clothes, deformed, disfigured, extra fingers, missing fingers, extra limbs, bad hands, '
            'bad anatomy, cross-eyed, blurry face, lowres, cropped head, creepy')

CHARACTERS = {'noam': NOAM, 'tamar': TAMAR}


def prompt(who, framing='full body', extra='', setting=SETTING):
    parts = [STYLE, framing, CHARACTERS[who] if who in CHARACTERS else who]
    if extra:
        parts.append(extra)
    parts.append(setting)
    return ', '.join(p for p in parts if p)
