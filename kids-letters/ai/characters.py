"""Fixed character descriptions for the image model.

SDXL reads about 75 tokens per prompt, so the most important words come first:
style, then identity (hair, face, outfit), then setting and light.
Identity follows the chosen 2D design (kids-letters/characters/src/option1.js)."""

STYLE = '3d animated movie still, cgi cartoon character, big expressive eyes, octane render'
SETTING = 'Jerusalem stone courtyard, blue door, bougainvillea, golden hour'

NOAM = ('happy 6 year old boy, fair skin, curly brown hair, brown eyes, toothy grin with a missing front tooth, '
        'bright orange hoodie, blue jeans, red sneakers')

TAMAR = ('happy 6 year old girl wearing bright yellow overalls over a pink and white striped shirt, brown skin, '
         'dark brown hair in two big afro puff pigtails, side bangs, purple sneakers')

NEGATIVE = ('photo, photograph, photorealistic, real child, text, letters, words, watermark, signature, artist name, logo, deformed, disfigured, '
            'extra fingers, missing fingers, extra limbs, bad hands, bad anatomy, cross-eyed, blurry face, lowres, '
            'cropped head, creepy, scary, adult')

CHARACTERS = {'noam': NOAM, 'tamar': TAMAR}


def prompt(who, framing='full body shot', extra='', setting=SETTING):
    parts = [STYLE, framing, CHARACTERS[who] if who in CHARACTERS else who]
    if extra:
        parts.append(extra)
    parts.append(setting)
    return ', '.join(p for p in parts if p)
