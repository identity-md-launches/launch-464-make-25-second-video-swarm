#!/usr/bin/env python3
"""Build the 25-second Swarm Pepe film from verified on-chain SVG bytes."""

import json
import math
from pathlib import Path
import struct
import subprocess
import wave


ROOT = Path(__file__).resolve().parent.parent
WIDTH, HEIGHT, FPS, SECONDS = 960, 540, 30, 25
BG = (10, 19, 24)
PANEL = (22, 34, 39)
LINE = (48, 72, 70)
LIME = (202, 244, 101)
CREAM = (237, 232, 204)
MUTED = (117, 145, 139)
ORANGE = (252, 137, 79)

# Seven-row bitmap alphabet for cards and titles. Pixel portraits
# themselves come exclusively from the SVGs returned by the Ethereum renderer.
TOKEN_IDS = (13, 21, 34, 55, 89, 144, 233, 377)

FONT = {
    'A': ('01110','10001','10001','11111','10001','10001','10001'),
    'B': ('11110','10001','10001','11110','10001','10001','11110'),
    'C': ('01111','10000','10000','10000','10000','10000','01111'),
    'D': ('11110','10001','10001','10001','10001','10001','11110'),
    'E': ('11111','10000','10000','11110','10000','10000','11111'),
    'F': ('11111','10000','10000','11110','10000','10000','10000'),
    'G': ('01111','10000','10000','10111','10001','10001','01111'),
    'H': ('10001','10001','10001','11111','10001','10001','10001'),
    'I': ('11111','00100','00100','00100','00100','00100','11111'),
    'J': ('00111','00010','00010','00010','10010','10010','01100'),
    'K': ('10001','10010','10100','11000','10100','10010','10001'),
    'L': ('10000','10000','10000','10000','10000','10000','11111'),
    'M': ('10001','11011','10101','10101','10001','10001','10001'),
    'N': ('10001','11001','10101','10011','10001','10001','10001'),
    'O': ('01110','10001','10001','10001','10001','10001','01110'),
    'P': ('11110','10001','10001','11110','10000','10000','10000'),
    'Q': ('01110','10001','10001','10001','10101','10010','01101'),
    'R': ('11110','10001','10001','11110','10100','10010','10001'),
    'S': ('01111','10000','10000','01110','00001','00001','11110'),
    'T': ('11111','00100','00100','00100','00100','00100','00100'),
    'U': ('10001','10001','10001','10001','10001','10001','01110'),
    'V': ('10001','10001','10001','10001','10001','01010','00100'),
    'W': ('10001','10001','10001','10101','10101','10101','01010'),
    'X': ('10001','10001','01010','00100','01010','10001','10001'),
    'Y': ('10001','10001','01010','00100','00100','00100','00100'),
    'Z': ('11111','00001','00010','00100','01000','10000','11111'),
    '0': ('01110','10001','10011','10101','11001','10001','01110'),
    '1': ('00100','01100','00100','00100','00100','00100','01110'),
    '2': ('01110','10001','00001','00010','00100','01000','11111'),
    '3': ('11110','00001','00001','01110','00001','00001','11110'),
    '4': ('00010','00110','01010','10010','11111','00010','00010'),
    '5': ('11111','10000','10000','11110','00001','00001','11110'),
    '6': ('01111','10000','10000','11110','10001','10001','01110'),
    '7': ('11111','00001','00010','00100','01000','01000','01000'),
    '8': ('01110','10001','10001','01110','10001','10001','01110'),
    '9': ('01110','10001','10001','01111','00001','00001','11110'),
    '#': ('01010','11111','01010','01010','11111','01010','00000'),
    '/': ('00001','00001','00010','00100','01000','10000','10000'),
    ':': ('00000','00100','00100','00000','00100','00100','00000'),
    '.': ('00000','00000','00000','00000','00000','00110','00110'),
    '$': ('00100','01111','10100','01110','00101','11110','00100'),
    '-': ('00000','00000','00000','11111','00000','00000','00000'),
    '(': ('00010','00100','01000','01000','01000','00100','00010'),
    ')': ('01000','00100','00010','00010','00010','00100','01000'),
    'c': ('00000','01111','10000','10000','10000','10000','01111'),
    'i': ('00100','00000','01100','00100','00100','00100','01110'),
    'l': ('01100','00100','00100','00100','00100','00100','01110'),
    'a': ('00000','01110','00001','01111','10001','10001','01111'),
    'b': ('10000','10000','11110','10001','10001','10001','11110'),
    'd': ('00001','00001','01111','10001','10001','10001','01111'),
    'e': ('00000','01110','10001','11111','10000','10001','01110'),
    'g': ('00000','01111','10001','10001','01111','00001','01110'),
    'm': ('00000','11010','10101','10101','10101','10101','10101'),
    'n': ('00000','11110','10001','10001','10001','10001','10001'),
    'r': ('00000','10110','11001','10000','10000','10000','10000'),
    's': ('00000','01111','10000','01110','00001','00001','11110'),
    't': ('00100','00100','11111','00100','00100','00101','00010'),
    'w': ('00000','10001','10001','10101','10101','10101','01010'),
    'y': ('00000','10001','10001','10001','01111','00001','01110'),
    ' ': ('00000',)*7,
}


class Canvas:
    def __init__(self, background):
        self.pixels = bytearray(background)

    def rect(self, x, y, w, h, color):
        if w <= 0 or h <= 0:
            return
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(WIDTH, x+w), min(HEIGHT, y+h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(color) * (x1-x0)
        for yy in range(y0, y1):
            start = (yy*WIDTH+x0)*3
            self.pixels[start:start+len(row)] = row

    def border(self, x, y, w, h, color, thickness=2):
        self.rect(x, y, w, thickness, color)
        self.rect(x, y+h-thickness, w, thickness, color)
        self.rect(x, y, thickness, h, color)
        self.rect(x+w-thickness, y, thickness, h, color)

    def text(self, s, x, y, scale, color):
        for ch in s:
            glyph = FONT.get(ch, FONT[' '])
            for gy, row in enumerate(glyph):
                for gx, bit in enumerate(row):
                    if bit == '1':
                        self.rect(x+gx*scale, y+gy*scale, scale, scale, color)
            x += 6*scale

    def sprite(self, sprite, x, y, size):
        data = sprite[size]
        for yy in range(size):
            if y+yy < 0 or y+yy >= HEIGHT:
                continue
            x0, x1 = max(0, x), min(WIDTH, x+size)
            if x1 <= x0:
                continue
            src_start = (yy*size+x0-x)*3
            dst_start = ((y+yy)*WIDTH+x0)*3
            self.pixels[dst_start:dst_start+(x1-x0)*3] = data[src_start:src_start+(x1-x0)*3]


def width_of(text, scale):
    return len(text)*6*scale


def background():
    c = Canvas(bytes(BG) * (WIDTH*HEIGHT))
    for x in range(0, WIDTH, 24):
        c.rect(x, 0, 1, HEIGHT, (17, 29, 32))
    for y in range(0, HEIGHT, 24):
        c.rect(0, y, WIDTH, 1, (17, 29, 32))
    c.border(21, 20, 918, 500, LINE, 1)
    c.rect(30, 44, 900, 1, LINE)
    c.rect(30, 494, 900, 1, LINE)
    c.text('SWARM / PEPE', 42, 28, 2, LIME)
    c.text('ETHEREUM MAINNET', 726, 28, 2, MUTED)
    c.text('MINT SLOT / ON CHAIN', 42, 505, 2, MUTED)
    return bytes(c.pixels)


def load_sprites():
    provenance = json.loads((ROOT/'assets/provenance.json').read_text())
    records = {r['token_id']: r for r in provenance['tokens']}
    if any(i not in records for i in TOKEN_IDS):
        raise RuntimeError('Missing required on-chain token SVG')
    sprites = {}
    for token_id in TOKEN_IDS:
        svg = ROOT/'assets'/records[token_id]['svg']
        raw = subprocess.check_output([
            'ffmpeg', '-v', 'error', '-i', str(svg), '-frames:v', '1',
            '-vf', 'scale=24:24:flags=neighbor', '-f', 'rawvideo',
            '-pix_fmt', 'rgb24', '-'])
        if len(raw) != 24*24*3:
            raise RuntimeError(f'Bad raster size for #{token_id}')
        sprites[token_id] = {}
        for size in (96, 168, 240, 288, 336):
            scale = size//24
            rows = []
            for y in range(24):
                row = b''.join(raw[(y*24+x)*3:(y*24+x+1)*3]*scale for x in range(24))
                rows.extend([row]*scale)
            sprites[token_id][size] = b''.join(rows)
    return sprites


def common(c, frame):
    # The lower border is a 25-second playback ruler.
    c.rect(30, 493, round(900*frame/(FPS*SECONDS-1)), 3, LIME)
    c.text(f'{frame//FPS:02d} / 25 SEC', 770, 505, 2, CREAM)
    blink = (frame//12) % 2 == 0
    c.rect(914, 32, 8, 8, ORANGE if blink else LINE)



def card(c, x, y, token_id, sprite, accent=LIME):
    c.rect(x, y, 178, 226, PANEL)
    c.border(x, y, 178, 226, accent, 2)
    c.sprite(sprite, x+5, y+10, 168)
    c.rect(x+13, y+185, 152, 2, LINE)
    c.text(f'#{token_id:04d}', x+17, y+195, 2, CREAM)
    c.rect(x+149, y+198, 12, 8, accent)


def scene_slot(c, local, sprites):
    c.text('YOUR SLOT', 62, 115, 6, CREAM)
    c.text('IS LIVE', 62, 190, 7, LIME)
    c.rect(63, 278, 350, 3, ORANGE)
    c.text('NEW BATCH GRANTED', 63, 310, 3, CREAM)
    c.text('PICKED FOR WORK SENT TO THE SWARM', 63, 364, 2, MUTED)
    c.text('STATUS / READY TO CLAIM', 63, 422, 2, LIME)
    c.rect(549, 86, 339, 371, PANEL)
    c.border(549, 86, 339, 371, LIME if (local//12)%2 == 0 else LINE, 2)
    c.sprite(sprites[13], 575, 102, 288)
    c.text('#0013 / ON CHAIN', 578, 414, 2, CREAM)
    c.rect(64, 461, min(354, 4*local), 4, LIME)


def scene_grant(c, local, sprites):
    c.text('GRANTED. NEVER SOLD.', 61, 76, 4, CREAM)
    c.text('WALLETS PICKED FOR THE WORK THEY SEND', 62, 128, 2, MUTED)
    c.text('978', 60, 203, 8, LIME)
    c.rect(62, 283, 253, 3, ORANGE)
    c.text('OF 5000 MINTED', 62, 305, 3, CREAM)
    c.text('SO FAR / ETHEREUM MAINNET', 63, 361, 2, MUTED)
    c.text('SLOTS ARE EARNED', 63, 415, 2, LIME)
    for idx, token_id in enumerate((21, 34, 55)):
        if local >= idx*12:
            card(c, 385+idx*181, 205, token_id, sprites[token_id],
                 ORANGE if idx == (local//24)%3 else LIME)


def scene_price(c, local, sprites):
    c.text('MINT PRICE', 62, 84, 4, CREAM)
    c.text('0 ETH', 60, 165, 9, LIME)
    c.rect(62, 260, 321, 3, ORANGE)
    c.text('GAS ONLY', 62, 287, 4, CREAM)
    c.text('NO TOKEN PAYMENT', 63, 370, 2, MUTED)
    c.text('YOUR FULL ALLOCATION WAITS', 63, 410, 2, LIME)
    c.rect(552, 91, 336, 363, PANEL)
    c.border(552, 91, 336, 363, LIME, 2)
    c.sprite(sprites[89], 576, 103, 288)
    c.text('#0089 / MINTED', 578, 413, 2, CREAM)
    for idx in range(10):
        c.rect(63+idx*27, 458, 16, 3, LIME if local >= idx*6 else LINE)


def step(c, number, y, heading, detail, active):
    accent = LIME if active else LINE
    c.border(61, y, 52, 53, accent, 2)
    c.text(number, 72, y+12, 3, accent)
    c.text(heading, 137, y+4, 3, CREAM)
    c.text(detail, 138, y+40, 2, MUTED)


def scene_claim(c, local, sprites):
    c.text('TAKE YOUR SLOT', 62, 76, 4, CREAM)
    c.rect(62, 122, 455, 3, ORANGE)
    step(c, '01', 150, 'OPEN SWARM PEPE', 'ON A BLOCK EXPLORER', local < 55)
    step(c, '02', 246, 'WRITE CONTRACT', 'SELECT THE MINT FUNCTION', 55 <= local < 110)
    c.border(61, 342, 52, 79, LIME if local >= 110 else LINE, 2)
    c.text('03', 72, 363, 3, LIME if local >= 110 else LINE)
    c.text('CALL', 137, 343, 3, CREAM)
    c.text('claim()', 137, 379, 4, LIME)
    c.text('NO ARGUMENTS / CONFIRM TRANSACTION', 62, 450, 2, MUTED)
    c.rect(581, 139, 302, 309, PANEL)
    c.border(581, 139, 302, 309, LINE, 2)
    c.sprite(sprites[144], 612, 157, 240)
    c.text('#0144', 608, 413, 2, CREAM)
    c.rect(790, 416, 63, 3, ORANGE)


def scene_zero(c, local, sprites):
    c.text('ANOTHER WAY', 62, 78, 4, CREAM)
    c.text('SEND 0 ETH', 62, 158, 6, LIME)
    c.rect(63, 229, 381, 3, ORANGE)
    c.text('TO THE CONTRACT', 62, 258, 3, CREAM)
    c.text('FULL ALLOCATION MINTS', 62, 318, 3, CREAM)
    c.text('GAS IS THE ONLY COST', 63, 390, 2, MUTED)
    c.text('USE THE VERIFIED SWARM PEPE CONTRACT', 63, 421, 2, LIME)
    c.rect(548, 92, 339, 365, PANEL)
    c.border(548, 92, 339, 365, ORANGE if (local//10)%2 else LIME, 2)
    c.sprite(sprites[233], 574, 105, 288)
    c.text('#0233 / MINTED', 578, 414, 2, CREAM)


def scene_future(c, local, sprites):
    c.text('ART COMES LATER', 62, 67, 4, CREAM)
    c.text('FROM A BLOCK THAT DID NOT EXIST', 63, 121, 2, LIME)
    c.text('WHEN YOUR MINT WAS SENT', 63, 147, 2, MUTED)
    for idx, token_id in enumerate((13, 21, 34, 377)):
        if local >= idx*9:
            card(c, 79+idx*202, 200, token_id, sprites[token_id],
                 ORANGE if idx == (local//15)%4 else LINE)
    c.text('CLAIM YOUR SLOT', 62, 457, 3, LIME)
    if local >= 90:
        c.rect(285, 499, 390, 20, BG)
        c.text('generated by $IMD swarm', 335, 505, 2, CREAM)


def write_audio(path):
    """Original synthesized 120 BPM chip score, generated without samples."""
    rate = 22050
    melody = (440.0, 523.25, 659.25, 783.99, 659.25, 523.25, 392.0, 493.88,
              440.0, 523.25, 587.33, 659.25, 783.99, 659.25, 523.25, 392.0)
    bassline = (110.0, 130.81, 98.0, 146.83, 110.0, 130.81, 98.0, 164.81)
    cuts = (0, 4, 8, 11.5, 17, 21)
    pcm = bytearray()
    for i in range(SECONDS*rate):
        t = i/rate
        beat = t*2
        eighth = int(beat*2)
        step_age = (beat*2-eighth)/4
        note = melody[eighth % len(melody)]
        phase = (t*note)%1
        triangle = 1-4*abs(phase-0.5)
        lead = 0.23*triangle*math.exp(-step_age*8)
        root = bassline[(int(t/2))%len(bassline)]
        bass = 0.27*math.sin(2*math.pi*root*t)*math.exp(-(beat%1)*1.8)
        kick_age = (beat%1)/2
        kick = 0.26*math.sin(2*math.pi*(55+80*math.exp(-kick_age*28))*kick_age)*math.exp(-kick_age*20)
        hat_age = ((beat*2)%1)/4
        noise = math.sin(i*12.9898)*math.sin(i*78.233)
        hat = 0.07*noise*math.exp(-hat_age*90)
        snare_age = (beat%2-1)/2
        snare = 0.0
        if snare_age >= 0:
            snare = 0.09*noise*math.exp(-snare_age*27)
        cue = 0.0
        for cut in cuts:
            age = t-cut
            if 0 <= age < .16:
                cue += 0.07*math.sin(2*math.pi*880*age)*math.exp(-age*22)
        fade = min(1.0, t/.18, (SECONDS-t)/.38)
        sample = max(-1.0, min(1.0, (lead+bass+kick+hat+snare+cue)*fade))
        pcm.extend(struct.pack('<h', int(sample*28000)))
    with wave.open(str(path), 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(pcm)


def main():
    (ROOT/'artifacts').mkdir(exist_ok=True)
    (ROOT/'test/scratch').mkdir(parents=True, exist_ok=True)
    sound = ROOT/'test/scratch'/'original_score.wav'
    write_audio(sound)
    sprites = load_sprites()
    base = background()
    out = ROOT/'artifacts'/'video.mp4'
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
           '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{WIDTH}x{HEIGHT}',
           '-r', str(FPS), '-i', '-', '-i', str(sound),
           '-c:v', 'libx264', '-preset', 'medium', '-crf', '15',
           '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k',
           '-movflags', '+faststart', '-t', str(SECONDS), str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    scenes = ((0, 120, scene_slot), (120, 240, scene_grant),
              (240, 345, scene_price), (345, 510, scene_claim),
              (510, 630, scene_zero), (630, 750, scene_future))
    try:
        for frame in range(FPS*SECONDS):
            c = Canvas(base)
            for start, end, draw in scenes:
                if start <= frame < end:
                    draw(c, frame-start, sprites)
                    break
            common(c, frame)
            proc.stdin.write(c.pixels)
            if frame%150 == 0:
                print(f'frame {frame}/{FPS*SECONDS}', flush=True)
    finally:
        proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError('ffmpeg encoding failed')
    print(out)


if __name__ == '__main__':
    main()
