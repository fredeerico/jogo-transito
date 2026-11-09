"""
TRANSITO SEGURO - jogo em Pygame sobre seguranca no transito (visual pixel art).

Visao de cima, estilo Road Fighter (NES). A pista tem 3 faixas e voce anda
pelas faixas como em uma grade (1 faixa por toque). As placas aparecem no
acostamento direito; quando a placa chega perto do carro (anel amarelo
piscando), obedeca a ela:

    Velocidade maxima 40 ........ S      (reduzir para 40 km/h ou menos)
    Atencao (perigo) ............ S      (reduzir para 60 km/h ou menos)
    Lombada ..................... S/F    (passar a 30 km/h ou menos)
    Faixa de pedestres .......... F      (PARE e espere todos atravessarem)
    Radar ....................... S      (passar a 50 km/h ou menos)
    Tunel ....................... SHIFT  (ligar o farol ANTES de entrar)
    Neblina ..................... SHIFT  (ligar o farol ANTES de entrar)
    Proibido virar a esquerda ... uma rua sai para a esquerda: NAO aperte A
    Proibido virar a direita .... uma rua sai para a direita: NAO aperte D
    (a tecla de cada placa aparece escrita em cima dela)

Controles:  A / D = trocar de faixa   W / S = acelerar / reduzir
            F = frear                 Q / E = pisca esquerdo / direito
            SHIFT = farol             C = afivelar o cinto (antes de sair!)
            M = musica liga/desliga  P = pausa

Tambem tem transito: carros e caminhoes em velocidades diferentes (e eles tambem
param antes da faixa de pedestres quando tem gente atravessando). Bateu = CNH
penalizada. Mudar de faixa sem ligar a seta (Q/E) custa 1 ponto.
Cada erro soma pontos na CNH (20 pontos = CNH suspensa). Acertos seguidos
dao combo e ate "limpam" pontos da CNH.

A fonte, a pista, a lombada, o tunel, a neblina, as sombras, as particulas e os
sons sao feitos por codigo. As imagens (pixel art) ficam em imagens/placas,
imagens/veiculos, imagens/pedestres e imagens/cenario e precisam estar junto do jogo.

O jogo roda numa tela pequena (150x150 pixels) que e ampliada 4x, e isso que
da o visual "quadradao" de pixel art.
Game loop: INPUT (eventos) -> UPDATE (regras) -> DRAW (desenho).
"""
import math
import os
import random
import sys
import textwrap
from array import array

import pygame

# ---------------------------------------------------------------- configuracao
FAROL_TEMPO = 10.0            # segundos que o farol fica ligado antes de apagar sozinho
EXIGIR_SETA = True            # True = mudar de faixa sem seta custa 1 ponto
TRAFEGO = True                # False = sem carros no cenario (util para testar)
ARQ_MUSICA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "musica", "bordeaux.ogg")
VOL_MUSICA = 0.45
PASTA_IMG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "imagens")

# ---------------------------------------------------------------- constantes
FPS = 60
SC = 4                                    # ampliacao do pixel art
IW = IH = 150                             # tamanho interno da area de jogo
W, H = 800, IH * SC                       # janela (600 de jogo + 200 de painel)
PAINEL_X = IW * SC

LANE_W = 28
LANES = [47, 75, 103]                     # centro de cada faixa (coord. internas)
ROAD_L, ROAD_R = 33, 117
CAR_Y = 122
SIGN_X = 136
ZONA_INI, ZONA_FIM = 60, 112              # janela (y da placa) para agir
MAX_V = 80.0                              # km/h
PXK = 0.75                                # pixels internos por km/h por segundo
LIMITE_CNH = 20
TUNEL_COMP = 130                          # comprimento do tunel (pixels internos)
RAMAL_COMP = 190                          # comprimento da rua lateral (ate o horizonte)
RAMAL_W = 14                              # largura da rua lateral
NEBLINA_COMP = 150                        # comprimento do trecho com neblina
PED_VEL = 30.0                            # velocidade dos pedestres (pixels internos/s)
PED_PERCURSO = ROAD_R - ROAD_L + 12       # quanto cada pedestre anda (de calcada a calcada)
PED_GATILHO = 80                          # distancia (px) em que os pedestres comecam a atravessar

# distancia entre a placa e o objeto que ela anuncia (o objeto fica mais a frente)
OFFSET_OBJ = {"lombada": 60, "tunel": 55, "proibe_esq": 70, "proibe_dir": 70,
              "radar": 60, "neblina": 55, "pedestre": 70}
# espaco minimo (pixels andados) ate a proxima placa: so aparece outra depois que o
# evento anterior (lombada, tunel, divisao da pista) terminou de passar pelo carro
GAP_MIN = {"lombada": 215, "tunel": 330, "proibe_esq": 300, "proibe_dir": 300,
           "radar": 215, "neblina": 330, "pedestre": 260}

# paleta (inspirada no Road Fighter do NES)
BRANCO = (255, 255, 255)
PRETO = (0, 0, 0)
VERDE = (80, 220, 120)
VERMELHO = (235, 70, 70)
AMARELO = (255, 220, 60)
CINZA = (170, 170, 170)
GRAMA = (136, 216, 0)
GRAMA_ESC = (96, 176, 0)
ASFALTO = (104, 104, 104)
ASFALTO_ESC = (92, 92, 92)
ROCHA = (98, 80, 62)
ROCHA_CLARA = (150, 128, 100)

SINAIS = {
    "vel": dict(img="placa_velocidade.png", pts=4, tecla="S",
                curto="MÁX 40: REDUZA PARA 40",
                ok="Velocidade reduzida!",
                regra="Velocidade máxima permitida: ultrapassá-la é infração. Quanto "
                      "maior a velocidade, mais graves são os acidentes."),
    "atencao": dict(img="placa_atencao.png", pts=3, tecla="S",
                    curto="ATENÇÃO: REDUZA PARA 60",
                    ok="Atenção redobrada!",
                    regra="Placa de advertência: avisa de perigo à frente. Reduza a "
                          "velocidade e redobre a atenção."),
    "lombada": dict(img="placa_lombada.png", pts=4, tecla="S",
                    curto="LOMBADA: MÁX 30 KM/H",
                    ok="Lombada vencida com segurança!",
                    regra="Lombadas obrigam a reduzir para proteger pedestres. Em alta "
                          "velocidade o carro pode perder o controle."),
    "pedestre": dict(img="placa_pare.png", pts=5, tecla="F",
                     curto="PEDESTRES: PARE E ESPERE",
                     ok="Esperou os pedestres passarem!",
                     regra="Na faixa de pedestres, quem está a pé tem a preferência. "
                           "Pare antes da faixa e só siga quando todos tiverem passado."),
    "radar": dict(img="placa_radar.png", pts=4, tecla="S",
                  curto="RADAR: MÁX 50 KM/H",
                  ok="Passou no radar dentro do limite!",
                  regra="Radares fiscalizam a velocidade máxima da via. Passar acima do "
                        "limite gera multa e pontos na carteira."),
    "tunel": dict(img="placa_tunel.png", pts=4, tecla="SHIFT",
                  curto="TÚNEL: LIGUE O FAROL",
                  ok="Farol ligado no túnel!",
                  regra="Em túneis, ligue o farol: você enxerga melhor e é visto "
                        "pelos outros motoristas."),
    "neblina": dict(img="placa_neblina.png", pts=4, tecla="SHIFT",
                    curto="NEBLINA: LIGUE O FAROL",
                    ok="Farol ligado na neblina!",
                    regra="Com neblina, ligue o farol baixo e reduza a velocidade: "
                          "a visibilidade cai e os outros carros enxergam menos você."),
    "proibe_esq": dict(img="placa_proibido_esquerda.png", pts=5, tecla="NÃO A",
                       curto="NÃO VIRE À ESQUERDA",
                       ok="Respeitou a proibição!",
                       regra="Placa de proibição: é proibido virar à esquerda. "
                             "Desrespeitar a proibição causa colisões."),
    "proibe_dir": dict(img="placa_proibido_direita.png", pts=5, tecla="NÃO D",
                       curto="NÃO VIRE À DIREITA",
                       ok="Respeitou a proibição!",
                       regra="Placa de proibição: é proibido virar à direita. "
                             "Desrespeitar a proibição causa colisões."),
}


# ================================================================ FONTE PIXEL (5x7)
GLIFOS = {
    " ": ["     "] * 7,
    "A": [" ### ", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    "B": ["#### ", "#   #", "#   #", "#### ", "#   #", "#   #", "#### "],
    "C": [" ####", "#    ", "#    ", "#    ", "#    ", "#    ", " ####"],
    "D": ["#### ", "#   #", "#   #", "#   #", "#   #", "#   #", "#### "],
    "E": ["#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#####"],
    "F": ["#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#    "],
    "G": [" ####", "#    ", "#    ", "#  ##", "#   #", "#   #", " ####"],
    "H": ["#   #", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    "I": [" ### ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", " ### "],
    "J": ["  ###", "   # ", "   # ", "   # ", "   # ", "#  # ", " ##  "],
    "K": ["#   #", "#  # ", "# #  ", "##   ", "# #  ", "#  # ", "#   #"],
    "L": ["#    ", "#    ", "#    ", "#    ", "#    ", "#    ", "#####"],
    "M": ["#   #", "## ##", "# # #", "# # #", "#   #", "#   #", "#   #"],
    "N": ["#   #", "##  #", "# # #", "#  ##", "#   #", "#   #", "#   #"],
    "O": [" ### ", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
    "P": ["#### ", "#   #", "#   #", "#### ", "#    ", "#    ", "#    "],
    "Q": [" ### ", "#   #", "#   #", "#   #", "# # #", "#  # ", " ## #"],
    "R": ["#### ", "#   #", "#   #", "#### ", "# #  ", "#  # ", "#   #"],
    "S": [" ####", "#    ", "#    ", " ### ", "    #", "    #", "#### "],
    "T": ["#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  "],
    "U": ["#   #", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
    "V": ["#   #", "#   #", "#   #", "#   #", " # # ", " # # ", "  #  "],
    "W": ["#   #", "#   #", "#   #", "# # #", "# # #", "## ##", "#   #"],
    "X": ["#   #", "#   #", " # # ", "  #  ", " # # ", "#   #", "#   #"],
    "Y": ["#   #", "#   #", " # # ", "  #  ", "  #  ", "  #  ", "  #  "],
    "Z": ["#####", "    #", "   # ", "  #  ", " #   ", "#    ", "#####"],
    "0": [" ### ", "#   #", "#  ##", "# # #", "##  #", "#   #", " ### "],
    "1": ["  #  ", " ##  ", "  #  ", "  #  ", "  #  ", "  #  ", " ### "],
    "2": [" ### ", "#   #", "    #", "   # ", "  #  ", " #   ", "#####"],
    "3": [" ### ", "#   #", "    #", "  ## ", "    #", "#   #", " ### "],
    "4": ["   # ", "  ## ", " # # ", "#  # ", "#####", "   # ", "   # "],
    "5": ["#####", "#    ", "#### ", "    #", "    #", "#   #", " ### "],
    "6": [" ### ", "#    ", "#    ", "#### ", "#   #", "#   #", " ### "],
    "7": ["#####", "    #", "   # ", "  #  ", " #   ", " #   ", " #   "],
    "8": [" ### ", "#   #", "#   #", " ### ", "#   #", "#   #", " ### "],
    "9": [" ### ", "#   #", "#   #", " ####", "    #", "    #", " ### "],
    ".": ["     ", "     ", "     ", "     ", "     ", "     ", "  #  "],
    ",": ["     ", "     ", "     ", "     ", "     ", "  #  ", " #   "],
    ":": ["     ", "  #  ", "     ", "     ", "     ", "  #  ", "     "],
    "!": ["  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "     ", "  #  "],
    "?": [" ### ", "#   #", "    #", "   # ", "  #  ", "     ", "  #  "],
    "-": ["     ", "     ", "     ", "#####", "     ", "     ", "     "],
    "+": ["     ", "  #  ", "  #  ", "#####", "  #  ", "  #  ", "     "],
    "/": ["    #", "    #", "   # ", "  #  ", " #   ", "#    ", "#    "],
    "(": ["   # ", "  #  ", " #   ", " #   ", " #   ", "  #  ", "   # "],
    ")": [" #   ", "  #  ", "   # ", "   # ", "   # ", "  #  ", " #   "],
    "|": ["  #  "] * 7,
    "=": ["     ", "     ", "#####", "     ", "#####", "     ", "     "],
}
# acentos: letra base + marca (pixels (coluna, linha) com linha -2/-1 acima, 7/8 abaixo)
MARCAS = {
    "acute": [(3, -2), (2, -1)],
    "grave": [(1, -2), (2, -1)],
    "circ": [(2, -2), (1, -1), (3, -1)],
    "tilde": [(0, -1), (1, -2), (2, -1), (3, -2)],
    "cedil": [(2, 7), (1, 8)],
}
ACENTOS = {
    "Á": ("A", "acute"), "À": ("A", "grave"), "Â": ("A", "circ"), "Ã": ("A", "tilde"),
    "É": ("E", "acute"), "Ê": ("E", "circ"), "Í": ("I", "acute"),
    "Ó": ("O", "acute"), "Ô": ("O", "circ"), "Õ": ("O", "tilde"),
    "Ú": ("U", "acute"), "Ç": ("C", "cedil"),
}
_cache_glifo = {}


def glifo(ch, cor, esc):
    chave = (ch, cor, esc)
    if chave in _cache_glifo:
        return _cache_glifo[chave]
    base, marca = ACENTOS.get(ch, (ch, None))
    linhas = GLIFOS.get(base, GLIFOS["?"])
    s = pygame.Surface((5 * esc, 11 * esc), pygame.SRCALPHA)
    for r, linha in enumerate(linhas):
        for c, v in enumerate(linha):
            if v == "#":
                s.fill(cor, ((c * esc), (r + 2) * esc, esc, esc))
    if marca:
        for c, r in MARCAS[marca]:
            s.fill(cor, (c * esc, (r + 2) * esc, esc, esc))
    _cache_glifo[chave] = s
    return s


def largura_texto(txt, esc):
    return max(0, len(txt) * 6 * esc - esc)


def texto(surf, txt, x, y, cor=BRANCO, esc=2, centro=False, sombra=True):
    """Escreve texto com a fonte pixel. (x, y) = canto superior esquerdo
    (ou o centro horizontal, se centro=True)."""
    txt = txt.upper()
    if centro:
        x = x - largura_texto(txt, esc) // 2
    if sombra:
        for i, ch in enumerate(txt):
            surf.blit(glifo(ch, PRETO, esc), (x + i * 6 * esc + esc, y + esc))
    for i, ch in enumerate(txt):
        surf.blit(glifo(ch, cor, esc), (x + i * 6 * esc, y))
    return largura_texto(txt, esc)


def paragrafo(surf, txt, x, y, largura, cor=BRANCO, esc=2, centro=False):
    """Texto com quebra de linha. Devolve o y logo abaixo do paragrafo."""
    for linha in textwrap.wrap(txt.upper(), largura):
        texto(surf, linha, x, y, cor, esc, centro)
        y += 12 * esc
    return y


# ================================================================ SPRITES POR CODIGO
def silhueta(spr, cor=PRETO):
    m = pygame.mask.from_surface(spr)
    return m.to_surface(setcolor=cor + (255,), unsetcolor=(0, 0, 0, 0))


def com_sombra(spr, dx=2, dy=1):
    """Devolve o sprite com uma sombra preta deslocada, como no Road Fighter."""
    w, h = spr.get_size()
    s = pygame.Surface((w + dx, h + dy), pygame.SRCALPHA)
    s.blit(silhueta(spr), (dx, dy))
    s.blit(spr, (0, 0))
    return s


def ampliar(spr, k):
    w, h = spr.get_size()
    return pygame.transform.scale(spr, (w * k, h * k))


def criar_icone_cinto():
    s = pygame.Surface((16, 18), pygame.SRCALPHA)
    pygame.draw.circle(s, (240, 200, 160), (8, 4), 4)
    s.fill((70, 110, 200), (3, 8, 10, 10))
    pygame.draw.line(s, (20, 20, 20), (4, 8), (12, 16), 2)
    s.fill((200, 200, 205), (11, 14, 3, 3))
    return s


def carregar_png(subpasta, nome, fallback=None):
    """Carrega imagens/<subpasta>/<nome>.png (fundo transparente).
    Se o arquivo nao existir, usa o desenho por codigo (so o icone do cinto tem)."""
    caminho = os.path.join(PASTA_IMG, subpasta, nome + ".png")
    if os.path.exists(caminho):
        return pygame.image.load(caminho).convert_alpha()
    if fallback is None:
        raise SystemExit("Imagem nao encontrada: %s\nBaixe a pasta 'imagens' junto com o jogo." % caminho)
    return fallback()


# ================================================================ SONS
def tom(freq, dur, vol=0.4, forma="seno", rate=22050):
    n = int(rate * dur)
    out = []
    for i in range(n):
        v = math.sin(2 * math.pi * freq * i / rate)
        if forma == "quad":
            v = 1.0 if v >= 0 else -1.0
        env = min(1.0, i / (0.01 * rate)) * (1 - i / n)
        out.append(int(32767 * vol * v * env))
    return out


def ruido(dur, vol=0.5, rate=22050):
    rng = random.Random(5)
    n = int(rate * dur)
    return [int(32767 * vol * rng.uniform(-1, 1) * (1 - i / n) ** 2) for i in range(n)]


def criar_sons():
    if not pygame.mixer.get_init():
        return {}

    def som(amostras):
        return pygame.mixer.Sound(buffer=array("h", amostras).tobytes())

    return {
        "ok": som(tom(880, 0.07, 0.3, "quad") + tom(1320, 0.13, 0.3, "quad")),
        "erro": som(tom(140, 0.30, 0.45, "quad")),
        "fim": som(tom(440, 0.2, 0.3, "quad") + tom(330, 0.2, 0.3, "quad") + tom(220, 0.4, 0.3, "quad")),
        "nivel": som(tom(660, 0.08, 0.3, "quad") + tom(880, 0.08, 0.3, "quad") + tom(1100, 0.12, 0.3, "quad")),
        "cinto": som(tom(1800, 0.03, 0.5, "quad") + [0] * 900 + tom(1100, 0.05, 0.5, "quad")),
        "pisca": som(tom(1000, 0.025, 0.25, "quad")),
        "aviso": som(tom(330, 0.12, 0.3, "quad")),
        "batida": som(ruido(0.35, 0.6)),
        "lombada": som(tom(70, 0.18, 0.6, "quad")),
    }


class Obj:
    """Objeto do cenario anunciado por uma placa (lombada, tunel, divisao da pista)."""
    def __init__(self, tipo, y, lado=0):
        self.tipo = tipo          # lombada | pedestre | radar | tunel | neblina | fork
        self.y = float(y)
        self.lado = lado          # fork: -1 = rua sai pela esquerda, +1 = pela direita
        self.feito = False
        self.flash = 0.0          # radar: tempo do flash
        self.peds = []            # faixa de pedestres: quem vai atravessar
        self.ativo = False        # faixa de pedestres: a travessia ja comecou
        self.t = 0.0              # faixa de pedestres: tempo desde o inicio da travessia
        self.dir = 1              # faixa de pedestres: +1 = da esquerda para a direita
        self.sinal = None


class Sinal:
    def __init__(self, tipo):
        self.tipo = tipo
        self.y = -14.0
        self.estado = "ativa"      # ativa | ok | falhou
        self.obj = None            # objeto de cenario ligado a esta placa


class Carro:
    """Carro ou caminhao do transito (anda na propria velocidade, em km/h)."""
    def __init__(self, faixa, y, vel, tipo, cor):
        self.lane = faixa
        self.y = float(y)
        self.speed = vel
        self.tipo = tipo           # carro | caminhao
        self.cor = cor             # indice da cor (carros)
        self.base = vel            # velocidade "de cruzeiro" (oscila em torno dela)
        self.alvo = vel            # velocidade que o motorista quer agora
        self.t_alvo = random.uniform(0.5, 2.0)   # tempo ate mudar de ideia
        self.freia = False         # lanterna acesa quando esta desacelerando

    @property
    def tam(self):                 # (largura, altura) da caixa de colisao
        return (16, 32) if self.tipo == "caminhao" else (12, 22)


NOMES_NPC = ("amarelo", "azul", "branco", "verde")      # cores dos carros (imagens/veiculos/npc_*.png)
N_PED_CORES = 4                                          # pedestres diferentes (pedestre_1..4)


# ================================================================ JOGO
class Game:
    def __init__(self, tela):
        self.tela = tela
        self.mundo = pygame.Surface((IW, IH))
        self.sons = criar_sons()

        # sprites
        # (imagens em imagens/placas, veiculos, pedestres e cenario; a sombra e feita pelo jogo)
        self.img_sinal = {}
        for k in SINAIS:
            spr = carregar_png("placas", SINAIS[k]["img"][:-4])
            self.img_sinal[k] = com_sombra(spr)
            self.img_sinal[k + "_puro"] = spr
        self.img_carro = com_sombra(carregar_png("veiculos", "carro"))
        self.img_npc = [com_sombra(carregar_png("veiculos", "npc_" + nome))
                        for nome in NOMES_NPC]
        self.img_caminhao = com_sombra(carregar_png("veiculos", "caminhao"))
        # pedestres andando para a direita (2 passos); para a esquerda e so espelhar
        self.img_ped = {}
        for i in range(N_PED_CORES):
            for passo, letra in ((0, "a"), (1, "b")):
                base = carregar_png("pedestres", "pedestre_%d_%s" % (i + 1, letra))
                spr = com_sombra(base, 1, 1)
                self.img_ped[(i, passo, 1)] = spr
                self.img_ped[(i, passo, -1)] = pygame.transform.flip(spr, True, False)
        self.img_casa = com_sombra(carregar_png("cenario", "casa"), 4, 2)
        self.img_arv = [com_sombra(carregar_png("cenario", "arvore_%d" % i), 4, 2)
                        for i in (1, 2)]
        self.img_arbusto = com_sombra(carregar_png("cenario", "arbusto"), 2, 1)
        self.img_poste = carregar_png("cenario", "poste")
        self.icone_cinto = ampliar(carregar_png("interface", "icone_cinto", criar_icone_cinto), 4)

        # cenario (posicoes fixas que se repetem a cada 300 px de rolagem)
        rng = random.Random(7)
        self.pontos_grama = [(rng.randint(0, IW - 1), rng.randint(0, IH - 1)) for _ in range(70)]
        self.pontos_asfalto = [(rng.randint(ROAD_L, ROAD_R - 1), rng.randint(0, IH - 1)) for _ in range(40)]
        self.pontos_rocha = [(rng.randint(0, IW - 1), rng.randint(0, TUNEL_COMP)) for _ in range(90)]
        self.deco_esq = [("casa", 1, 20), ("arv0", 14, 90), ("arv1", 12, 128),
                         ("casa", 1, 170), ("arv1", 15, 235), ("arv0", 13, 265)]
        self.deco_dir = [("arv0", 128, 40), ("arbusto", 141, 100), ("arv1", 126, 150),
                         ("arbusto", 140, 215), ("arv0", 131, 255)]

        # musica de fundo (musica/bordeaux.ogg, convertida do arquivo .spc)
        self.tem_musica = False
        self.musica_on = True
        try:
            pygame.mixer.music.load(ARQ_MUSICA)
            pygame.mixer.music.set_volume(VOL_MUSICA)
            pygame.mixer.music.play(-1)               # -1 = repete para sempre
            self.tem_musica = True
        except Exception:
            pass                                      # sem arquivo ou sem audio: segue sem musica

        self.scroll = 0.0
        self.reset()
        self.estado = "menu"

    # ---------- estado
    def reset(self):
        self.score = 0.0
        self.cnh = 0
        self.acertos = 0
        self.erros = 0
        self.combo = 0
        self.melhor_combo = 0
        self.sinais = []
        self.objs = []
        self.npcs = []
        self.parts = []            # particulas (fumaca, faiscas)
        self.ultimo = None
        # sequencia de placas: a 1a e a faixa de pedestres; depois sorteia sem repetir
        # nenhuma placa ate todas terem aparecido (assim todas aparecem com frequencia)
        self.fila = ["pedestre"]
        self.cinto = False
        self.farol = False
        self.farol_t = 0.0
        self.speed = 0.0
        self.freando = False
        self.acelerando = False
        self.car_dy = 0.0          # o carro sobe ao acelerar e desce ao frear
        self.salto_t = 0.0
        self.salto_dur = 0.4
        self.salto_amp = 0
        self.lane = 1
        self.car_x = float(LANES[1])
        self.shift_x = 0.0
        self.virar_lado = 0        # carro escorrega para a rua lateral (so animacao)
        self.virar_t = 0.0
        self.pisca = 0             # -1 esquerda, 0 apagado, +1 direita
        self.pisca_t = 0.0
        self.gap = 200
        self.dist = self.gap * 0.55
        self.npc_t = 2.0
        self.msg = ""
        self.hint = ""
        self.msg_cor = BRANCO
        self.msg_t = 0.0
        self.flash_t = 0.0
        self.flash_cor = VERMELHO

    @property
    def nivel(self):
        return 1 + self.acertos // 5

    @property
    def gap_atual(self):
        return max(130, 200 - 10 * (self.nivel - 1))

    @property
    def mult(self):
        return min(4, 1 + self.combo // 3)

    def tocar(self, nome):
        if nome in self.sons:
            self.sons[nome].play()

    def mostrar(self, msg, cor, hint="", dur=2.2):
        self.msg, self.msg_cor, self.hint, self.msg_t = msg, cor, hint, dur

    # ---------- 1) INPUT
    def evento(self, e):
        if e.type != pygame.KEYDOWN:
            return
        if e.key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()
        if e.key == pygame.K_m:                       # liga/desliga a musica de fundo
            self.musica_on = not self.musica_on
            if self.tem_musica:
                pygame.mixer.music.set_volume(VOL_MUSICA if self.musica_on else 0.0)
            return
        if self.estado in ("menu", "fim"):
            if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.reset()
                self.estado = "jogando"
        elif self.estado == "pausado":
            if e.key == pygame.K_p:
                self.estado = "jogando"
        elif self.estado == "jogando":
            if e.key == pygame.K_p:
                self.estado = "pausado"
            elif not self.cinto:
                if e.key == pygame.K_c:
                    self.cinto = True
                    self.speed = 30.0
                    self.tocar("cinto")
                    self.mostrar("Cinto afivelado! Boa viagem.", VERDE,
                                 "O cinto reduz muito o risco de morte em acidentes. "
                                 "Use sempre, inclusive no banco de trás.", 3.5)
                elif e.key in (pygame.K_a, pygame.K_d, pygame.K_w, pygame.K_s,
                               pygame.K_f, pygame.K_q, pygame.K_e, pygame.K_LSHIFT, pygame.K_RSHIFT):
                    self.mostrar("Não dá para dirigir sem o cinto! Aperte C.", AMARELO, "", 1.5)
            elif e.key == pygame.K_a:
                self.mudar_faixa(-1)
            elif e.key == pygame.K_d:
                self.mudar_faixa(1)
            elif e.key == pygame.K_q:
                self.piscar(-1)
            elif e.key == pygame.K_e:
                self.piscar(1)
            elif e.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                self.farol = not self.farol       # liga por um tempo; apertar de novo desliga
                self.farol_t = FAROL_TEMPO if self.farol else 0.0
                self.tocar("pisca")

    def piscar(self, direcao):
        if self.pisca == direcao:       # apertar de novo desliga
            self.pisca, self.pisca_t = 0, 0.0
        else:
            self.pisca, self.pisca_t = direcao, 5.0
            self.tocar("pisca")

    def mudar_faixa(self, d):
        nova = self.lane + d
        if not 0 <= nova <= 2:
            self.tentar_virar(d)
            return
        sem_seta = EXIGIR_SETA and self.pisca != d
        self.lane = nova
        if self.pisca == d:             # seta se apaga logo depois da manobra
            self.pisca_t = min(self.pisca_t, 0.8)
        if sem_seta:
            self.cnh += 1
            self.tocar("aviso")
            self.mostrar("Mudou de faixa sem sinalizar!  +1 ponto na CNH", AMARELO,
                         "Antes de mudar de faixa, ligue a seta (Q ou E) para avisar "
                         "os outros motoristas.", 2.6)
            self.verificar_fim()

    def tentar_virar(self, d):
        """Apertou A/D na faixa da ponta, saindo da pista: pega a rua lateral se ela estiver ali."""
        for s in self.sinais:
            o = s.obj
            if s.estado == "ativa" and o is not None and o.tipo == "fork" and o.lado == d:
                if -12 <= o.y - CAR_Y <= 32:          # a boca da rua esta ao lado do carro
                    self.virar_lado, self.virar_t = d, 0.6
                    self.falhar(s, "Virou onde era proibido!")
                    return

    def verificar_fim(self):
        if self.cnh >= LIMITE_CNH and self.estado == "jogando":
            self.estado = "fim"
            self.tocar("fim")

    # ---------- 2) UPDATE
    def update(self, dt, keys=None):
        if self.estado == "menu":
            self.scroll += dt * 25
            return
        if self.estado != "jogando":
            return
        self.msg_t = max(0, self.msg_t - dt)
        self.flash_t = max(0, self.flash_t - dt)
        if not self.cinto:               # carro parado ate afivelar o cinto
            self.speed = 0.0
            return
        if keys is None:
            keys = pygame.key.get_pressed()

        # velocidade: W acelera, S reduz, F freia forte; sem tecla mantem
        antes = self.speed
        self.freando = False
        self.acelerando = False
        if keys[pygame.K_f]:
            self.speed -= 90 * dt
            self.freando = antes > 0
        if keys[pygame.K_s]:
            self.speed -= 30 * dt
        if keys[pygame.K_w]:
            self.speed += 22 * dt
            self.acelerando = antes < MAX_V - 0.5
        self.speed = max(0.0, min(MAX_V, self.speed))

        # carro sobe ao acelerar e desce ao frear (efeito de peso)
        alvo_dy = -2.0 * self.speed / MAX_V               # mais rapido = carro mais a frente
        if self.acelerando:
            alvo_dy = -5.0
        elif self.freando or keys[pygame.K_s]:
            alvo_dy = 3.5 if self.speed > 0 else 0.0
        self.car_dy += (alvo_dy - self.car_dy) * min(1, 8 * dt)
        self.salto_t = max(0.0, self.salto_t - dt)

        # carro desliza suavemente ate o centro da faixa
        self.car_x += (LANES[self.lane] - self.car_x) * min(1, 12 * dt)
        alvo_shift = 0.0
        if self.virar_t > 0:
            self.virar_t -= dt
            alvo_shift = self.virar_lado * 22.0
        self.shift_x += (alvo_shift - self.shift_x) * min(1, 12 * dt)

        # farol apaga sozinho (como a seta)
        if self.farol:
            self.farol_t -= dt
            if self.farol_t <= 0:
                self.farol, self.farol_t = False, 0.0
                self.mostrar("Farol apagou sozinho", AMARELO, "", 1.5)

        # seta apaga sozinha
        if self.pisca_t > 0:
            self.pisca_t -= dt
            if self.pisca_t <= 0:
                self.pisca = 0

        # rolagem da pista, das placas e dos objetos
        px = self.speed * PXK * dt
        self.scroll += px
        self.dist += px
        for s in self.sinais:
            s.y += px
        for o in self.objs:
            o.y += px
            o.flash = max(0.0, o.flash - dt)

        # nova placa a cada "gap" pixels andados
        if self.dist >= self.gap:
            self.dist = 0
            self.novo_evento()

        self.atualizar_pedestres(dt)
        self.atualizar_trafego(dt)
        self.atualizar_efeitos(dt, px, keys)
        self.avaliar_sinais()
        if self.estado != "jogando":
            return
        if TRAFEGO:
            self.colisoes()

        # a placa so sai da lista depois de resolvida (a pista dividida resolve bem depois dela)
        self.sinais = [s for s in self.sinais if s.y < IH + 100 or s.estado == "ativa"]
        comp = {"tunel": TUNEL_COMP, "neblina": NEBLINA_COMP, "fork": RAMAL_COMP}
        self.objs = [o for o in self.objs if o.y - comp.get(o.tipo, 0) < IH + 20]

        # pontos por distancia (andar devagar demais rende pouco)
        self.score += self.speed * dt * 0.05

    # ---------- faixa de pedestres
    def ocupada(self, o):
        """True enquanto ainda tem pedestre atravessando (ou esperando para atravessar)."""
        return o.ativo and any(p["trav"] < PED_PERCURSO for p in o.peds)

    def ped_xy(self, o, p):
        x0 = ROAD_L - 6 if o.dir > 0 else ROAD_R + 6
        y = o.y - 6 + p["i"] * 4
        return x0 + o.dir * p["trav"], y

    def atualizar_pedestres(self, dt):
        for o in self.objs:
            if o.tipo != "pedestre":
                continue
            if not o.ativo and o.y >= CAR_Y - PED_GATILHO:        # o carro chegou perto: eles saem
                o.ativo = True
                if o.sinal is not None and o.sinal.estado == "ativa":
                    self.tocar("aviso")
                    self.mostrar("Pedestres atravessando! PARE e espere.", AMARELO,
                                 "Na faixa de pedestres, quem está a pé tem a preferência. "
                                 "Frear (F) antes da faixa e só seguir quando todos passarem.", 3.4)
            if o.ativo:
                o.t += dt
                for p in o.peds:
                    p["trav"] = max(0.0, min(float(PED_PERCURSO), PED_VEL * (o.t - p["delay"])))
            # atropelamento
            pr = pygame.Rect(0, 0, 12, 22)
            pr.center = (int(self.car_x + self.shift_x), CAR_Y)
            if self.speed > 2:
                for p in list(o.peds):
                    if 0 < p["trav"] < PED_PERCURSO:
                        x, y = self.ped_xy(o, p)
                        r = pygame.Rect(0, 0, 6, 5)
                        r.center = (int(x), int(y))
                        if pr.colliderect(r):
                            self.atropelar(o, p, (x, y))
                            return

    def atropelar(self, o, p, pos):
        o.peds.remove(p)
        for _ in range(18):
            ang = random.uniform(0, 6.283)
            v = random.uniform(15, 55)
            self.parts.append([pos[0], pos[1], math.cos(ang) * v, math.sin(ang) * v,
                               random.uniform(0.3, 0.7), random.choice([(230, 40, 40), (255, 90, 60), BRANCO])])
        self.speed = 0.0
        self.combo = 0
        self.erros += 1
        self.cnh += 10
        if o.sinal is not None and o.sinal.estado == "ativa":
            o.sinal.estado = "falhou"
        self.flash_t, self.flash_cor = 0.5, VERMELHO
        self.tocar("batida")
        self.mostrar("ATROPELAMENTO!  +10 pts na CNH", VERMELHO,
                     "Atropelar um pedestre é a infração mais grave. Em faixa de pedestres, "
                     "pare sempre: a vida de quem está a pé vale mais que a pressa.", 4.2)
        self.verificar_fim()

    # ---------- eventos (placas + objetos)
    def novo_evento(self, tipo=None):
        if tipo is None:
            if not self.fila:
                self.fila = list(SINAIS)
                random.shuffle(self.fila)
                if self.fila[0] == self.ultimo:
                    self.fila.append(self.fila.pop(0))
            tipo = self.fila.pop(0)
        self.ultimo = tipo
        s = Sinal(tipo)
        if tipo == "pedestre":
            s.obj = Obj(tipo, s.y - OFFSET_OBJ[tipo])
            s.obj.dir = random.choice((-1, 1))
            n = random.choice((3, 4))
            cores = random.sample(range(N_PED_CORES), n)
            s.obj.peds = [{"i": i, "delay": 0.6 * i, "cor": cores[i], "trav": 0.0} for i in range(n)]
        elif tipo in ("lombada", "radar", "tunel", "neblina"):
            s.obj = Obj(tipo, s.y - OFFSET_OBJ[tipo])
        elif tipo in ("proibe_esq", "proibe_dir"):
            s.obj = Obj("fork", s.y - OFFSET_OBJ[tipo], -1 if tipo == "proibe_esq" else 1)
        if s.obj:
            s.obj.sinal = s
            self.objs.append(s.obj)
        self.sinais.append(s)
        self.gap = max(self.gap_atual, GAP_MIN.get(tipo, 0)) + random.randint(0, 20)
        return s

    def avaliar_sinais(self):
        for s in self.sinais:
            if s.estado != "ativa":
                continue
            t = s.tipo
            if t in ("vel", "atencao"):
                if s.y >= ZONA_INI and self.cumpriu(s):
                    self.acertar(s)
                elif s.y > ZONA_FIM:
                    self.falhar(s, self.motivo(s))
            elif t in ("lombada", "radar"):
                o = s.obj
                if o.y >= CAR_Y and not o.feito:
                    o.feito = True
                    limite = 50 if t == "radar" else 30
                    devagar = self.speed <= limite
                    if t == "lombada":
                        self.efeito_lombada(devagar)
                    if t == "radar":
                        o.flash = 0.25
                    if devagar:
                        self.acertar(s)
                    else:
                        msg = {"lombada": "Passou na lombada em alta velocidade!",
                               "radar": "Radar! Você estava acima do limite!"}[t]
                        self.falhar(s, msg)
            elif t == "pedestre":
                o = s.obj
                if o.y >= CAR_Y - 17 and not o.feito:       # o nariz do carro chegou na faixa
                    o.feito = True
                    if self.ocupada(o):
                        self.falhar(s, "Avançou na faixa com pedestres!")
                    else:
                        self.acertar(s)
            elif t in ("tunel", "neblina"):
                if s.y >= ZONA_INI and self.farol:
                    self.acertar(s)
                elif s.obj.y >= CAR_Y:
                    self.falhar(s, "Entrou no túnel sem farol!" if t == "tunel"
                                else "Entrou na neblina sem farol!")
            else:                                       # rua lateral (proibido virar)
                if s.obj.y - CAR_Y > 32:                # passou da boca da rua sem virar
                    self.acertar(s)
            if self.estado != "jogando":
                return

    def cumpriu(self, s):
        t = s.tipo
        if t == "vel":
            return self.speed <= 40
        if t == "atencao":
            return self.speed <= 60
        return False

    def motivo(self, s):
        if s.tipo == "vel":
            return "Acima da velocidade máxima!"
        return "Perigo à frente e você não reduziu!"

    def efeito_lombada(self, devagar):
        self.tocar("lombada")
        self.salto_t = self.salto_dur = 0.25 if devagar else 0.55
        self.salto_amp = 1 if devagar else 4
        if not devagar:
            self.speed = max(8.0, self.speed * 0.5)

    def acertar(self, s):
        info = SINAIS[s.tipo]
        s.estado = "ok"
        nivel_antes = self.nivel
        self.acertos += 1
        self.combo += 1
        self.melhor_combo = max(self.melhor_combo, self.combo)
        pts = 100 * self.mult
        self.score += pts
        self.flash_t, self.flash_cor = 0.25, VERDE
        self.tocar("ok")
        txt = "%s  +%d" % (info["ok"], pts)
        if self.mult > 1:
            txt += "  (combo x%d)" % self.mult
        hint = ""
        if self.combo % 5 == 0 and self.cnh > 0:
            self.cnh -= 1
            hint = "Bom condutor! -1 ponto na CNH."
        if self.nivel > nivel_antes:
            hint = (hint + " " if hint else "") + "Nível %d: o trânsito está mais intenso!" % self.nivel
            self.tocar("nivel")
        self.mostrar(txt, VERDE, hint)

    def falhar(self, s, motivo):
        info = SINAIS[s.tipo]
        s.estado = "falhou"
        self.erros += 1
        self.combo = 0
        self.cnh += info["pts"]
        self.flash_t, self.flash_cor = 0.35, VERMELHO
        self.tocar("erro")
        self.mostrar("%s  +%d pts na CNH" % (motivo, info["pts"]), VERMELHO,
                     info["regra"], 3.6)
        self.verificar_fim()

    # ---------- transito
    def x_npc(self, n):
        return float(LANES[n.lane])

    def spawn_npc(self):
        if len(self.npcs) >= 5:
            return
        atras = random.random() < 0.25
        faixas = [0, 1, 2]
        if atras:
            faixas.remove(self.lane)           # nunca nasce atras de voce, na sua faixa
        faixa = random.choice(faixas)
        y = IH + 35 if atras else -40
        for n in self.npcs:
            if n.lane == faixa and abs(n.y - y) < 60:
                return
        if atras:
            vel = max(self.speed + 15, 35) + random.uniform(0, 12)
            tipo = "carro"
        elif random.random() < 0.22:
            vel, tipo = random.uniform(15, 30), "caminhao"
        else:
            vel, tipo = random.uniform(22, 55), "carro"
        self.npcs.append(Carro(faixa, y, vel, tipo, random.randrange(len(NOMES_NPC))))

    def atualizar_trafego(self, dt):
        if not TRAFEGO:
            self.npcs = []
            return
        self.npc_t -= dt
        if self.npc_t <= 0:
            self.spawn_npc()
            self.npc_t = max(1.0, 2.6 - 0.2 * (self.nivel - 1)) + random.uniform(0, 1.2)
        for n in self.npcs:
            # o motorista muda de ideia de tempos em tempos: acelera ou alivia
            n.t_alvo -= dt
            if n.t_alvo <= 0:
                n.t_alvo = random.uniform(1.0, 3.2)
                if n.tipo == "caminhao":
                    n.alvo = max(12.0, min(34.0, n.base + random.uniform(-10, 10)))
                else:
                    n.alvo = max(14.0, min(68.0, n.base + random.uniform(-22, 22)))
            antes = n.speed
            passo = 16 * dt                                   # km/h por segundo = ~16
            n.speed += max(-passo, min(passo, n.alvo - n.speed))
            # nao bate no carro da frente (acompanha a velocidade dele)
            for m in self.npcs:
                if m is not n and m.lane == n.lane and 0 < n.y - m.y < 40 and n.speed > m.speed:
                    n.speed = m.speed
            # nao bate em voce por tras (diminui para a sua velocidade)
            if n.lane == self.lane and abs(self.car_x - LANES[n.lane]) < 12 and 0 < n.y - CAR_Y < 46:
                n.speed = min(n.speed, self.speed)
            # respeita a faixa de pedestres: freia antes dela enquanto tem gente atravessando
            for o in self.objs:
                if o.tipo == "pedestre" and self.ocupada(o) and n.y > o.y:
                    gap = (n.y - n.tam[1] / 2) - (o.y + 8)     # distancia do nariz ate a faixa
                    if 0 <= gap < 110:
                        if gap <= 1:
                            n.speed = 0.0
                        elif gap < 0.017 * n.speed * n.speed + 4:
                            n.speed = max(0.0, n.speed - 45 * dt)
            n.freia = n.speed < antes - 0.05
            n.y += (self.speed - n.speed) * PXK * dt
        self.npcs = [n for n in self.npcs if -80 < n.y < IH + 80]

    def colisoes(self):
        pr = pygame.Rect(0, 0, 12, 22)
        pr.center = (int(self.car_x + self.shift_x), CAR_Y)
        for n in self.npcs:
            w, h = n.tam
            nr = pygame.Rect(0, 0, w, h)
            nr.center = (int(self.x_npc(n)), int(n.y))
            if pr.colliderect(nr):
                self.bater(n, nr.center)
                return

    def bater(self, n, pos):
        self.npcs.remove(n)
        for _ in range(16):
            ang = random.uniform(0, 6.283)
            v = random.uniform(15, 55)
            self.parts.append([pos[0], pos[1], math.cos(ang) * v, math.sin(ang) * v,
                               random.uniform(0.3, 0.6), random.choice([(255, 230, 90), BRANCO, (255, 150, 40)])])
        self.speed *= 0.35
        self.combo = 0
        self.erros += 1
        self.cnh += 5
        self.flash_t, self.flash_cor = 0.35, VERMELHO
        self.tocar("batida")
        self.mostrar("COLISÃO!  +5 pts na CNH", VERMELHO,
                     "Mantenha distância segura do carro da frente e olhe antes de mudar "
                     "de faixa. Colisões causam ferimentos graves.", 3.6)
        self.verificar_fim()

    # ---------- efeitos visuais de velocidade
    def atualizar_efeitos(self, dt, px, keys):
        # chama no escapamento ao acelerar
        x = self.car_x + self.shift_x
        if self.acelerando and random.random() < 0.8:
            self.parts.append([x + random.choice((-3, 3)), CAR_Y + 12 + self.car_dy, 0, 30 + self.speed * 0.4,
                               0.18, random.choice([(255, 170, 30), (255, 230, 90), (255, 100, 30)])])
        # fumaca de freada
        if self.freando and self.speed > 20 and random.random() < 0.7:
            for dx in (-7, 7):
                self.parts.append([x + dx, CAR_Y + 8 + self.car_dy, random.uniform(-6, 6), 12 + self.speed * 0.3,
                                   random.uniform(0.35, 0.6), random.choice([(200, 200, 200), (230, 230, 230)])])
        for p in self.parts:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[4] -= dt
        self.parts = [p for p in self.parts if p[4] > 0]

    # ---------- 3) DRAW (mundo em baixa resolucao)
    def desenhar_deco(self, m, lista):
        sc = int(self.scroll)
        for tipo, x, y0 in lista:
            y = (y0 + sc) % 300 - 40
            if y > IH:
                continue
            if tipo == "casa":
                spr = self.img_casa
            elif tipo == "arbusto":
                spr = self.img_arbusto
            else:
                spr = self.img_arv[int(tipo[-1])]
            m.blit(spr, (x, y))

    def desenhar_ramal(self, m, o):
        """Rua lateral: sai da pista em diagonal, segue reta e depois sai da tela pela lateral.
        A pista principal nao muda: ela so passa reto, e a rua fica ao lado."""
        yj = int(o.y)                                   # "boca" da rua, junto a pista
        lado = o.lado

        def f(x, y, w, cor):                            # desenha espelhado se a rua e a da direita
            m.fill(cor, ((x if lado < 0 else IW - x - w), y, w, 1))

        for y in range(max(0, yj - RAMAL_COMP), min(IH, yj + 1)):
            t = yj - y
            if t <= 23:                                 # sai da pista em diagonal
                desl = int(t * 0.7)
            elif t <= 120:                              # segue reta, ao lado da pista
                desl = 16
            else:                                       # e se afasta ate sumir pela lateral da tela
                desl = 16 + int((t - 120) * 0.7)
            w = RAMAL_W
            xr = ROAD_L + 4 - desl                      # borda da rua mais perto da pista
            xl = xr - w
            if t < 10:                                  # boca aberta: apaga a borda da pista
                f(ROAD_L - 3, y, 6, ASFALTO)
            f(xl, y, w, ASFALTO)
            f(xl, y, 1, BRANCO)
            f(xr - 1, y, 1, BRANCO)
            if w >= 8 and ((y + int(self.scroll)) // 4) % 4 == 0:
                f(xl + w // 2, y, 1, BRANCO)            # tracejado central

    def desenhar_lombada(self, m, o):
        y = int(o.y)
        if y < -6 or y > IH + 6:
            return
        m.fill((135, 135, 135), (ROAD_L, y - 3, ROAD_R - ROAD_L, 1))      # luz
        for i, yy in enumerate(range(y - 2, y + 3)):
            for x in range(ROAD_L, ROAD_R, 4):
                cor = AMARELO if ((x - ROAD_L) // 4 + i) % 2 == 0 else PRETO
                m.fill(cor, (x, yy, min(4, ROAD_R - x), 1))
        m.fill((60, 60, 60), (ROAD_L, y + 3, ROAD_R - ROAD_L, 1))          # sombra

    def desenhar_faixa(self, m, o):
        y = int(o.y)
        if y < -14 or y > IH + 14:
            return
        for x in range(ROAD_L + 2, ROAD_R - 3, 8):                # zebra
            m.fill(BRANCO, (x, y - 6, 5, 13))
        if self.ocupada(o) and (pygame.time.get_ticks() // 250) % 2 == 0:
            pygame.draw.rect(m, AMARELO, (ROAD_L, y - 9, ROAD_R - ROAD_L, 19), 1)   # faixa ocupada!
        passo = (pygame.time.get_ticks() // 160) % 2
        for p in o.peds:
            x, yy = self.ped_xy(o, p)
            andando = 0 < p["trav"] < PED_PERCURSO
            spr = self.img_ped[(p["cor"], passo if andando else 0, o.dir)]
            m.blit(spr, (int(x) - 3, int(yy) - 3))

    def desenhar_radar(self, m, o):
        y = int(o.y)
        if y < -10 or y > IH + 10:
            return
        m.fill((60, 60, 70), (ROAD_L - 6, y - 2, ROAD_R - ROAD_L + 12, 3))    # portico
        m.fill((130, 130, 145), (ROAD_L - 6, y - 2, ROAD_R - ROAD_L + 12, 1))
        m.fill((60, 60, 70), (ROAD_L - 7, y - 4, 3, 7))
        m.fill((60, 60, 70), (ROAD_R + 4, y - 4, 3, 7))
        for cx in LANES:                                   # uma camera por faixa
            m.fill(PRETO, (cx - 3, y - 3, 6, 5))
            m.fill((230, 40, 40) if (pygame.time.get_ticks() // 300) % 2 else (120, 20, 20),
                   (cx - 1, y - 2, 2, 2))
        if o.flash > 0:                                    # flash do radar
            luz = pygame.Surface((ROAD_R - ROAD_L, 12), pygame.SRCALPHA)
            luz.fill((255, 255, 255, int(220 * o.flash / 0.25)))
            m.blit(luz, (ROAD_L, y + 2))

    def desenhar_neblina(self, m, o):
        yin = int(o.y)
        yout = yin - NEBLINA_COMP
        topo, base = max(0, yout), min(IH, yin)
        if base <= topo:
            return
        ov = pygame.Surface((IW, base - topo), pygame.SRCALPHA)
        for y in range(topo, base):                        # bordas suaves (fade in/out)
            f = min(1.0, (y - yout) / 26.0, (yin - y) / 26.0)
            ov.fill((218, 222, 230, int(215 * max(0.0, f))), (0, y - topo, IW, 1))
        if self.farol:                                     # farol abre um cone na neblina
            cx = int(self.car_x + self.shift_x)
            cy = CAR_Y - 10 - topo
            pygame.draw.polygon(ov, (218, 222, 230, 110), [(cx - 6, cy), (cx + 6, cy), (cx + 28, cy - 66), (cx - 28, cy - 66)])
            pygame.draw.polygon(ov, (218, 222, 230, 45), [(cx - 4, cy), (cx + 4, cy), (cx + 14, cy - 60), (cx - 14, cy - 60)])
        m.blit(ov, (0, topo))

    def desenhar_tunel_paredes(self, m, o):
        yin = int(o.y)
        yout = yin - TUNEL_COMP
        topo, base = max(0, yout), min(IH, yin)
        if base <= topo:
            return
        m.fill(ROCHA, (0, topo, ROAD_L - 3, base - topo))
        m.fill(ROCHA, (ROAD_R + 3, topo, IW - ROAD_R - 3, base - topo))
        for x, dy in self.pontos_rocha:
            y = yout + dy
            if topo <= y < base and (x < ROAD_L - 3 or x >= ROAD_R + 3):
                m.set_at((x, y), (70, 56, 42) if (x + dy) % 2 else (125, 104, 82))
        m.fill((40, 32, 24), (ROAD_L - 4, topo, 1, base - topo))
        m.fill((40, 32, 24), (ROAD_R + 3, topo, 1, base - topo))

    def desenhar_tunel_escuro(self, m, o):
        yin = int(o.y) - 5
        yout = int(o.y) - TUNEL_COMP
        topo, base = max(0, yout), min(IH, yin)
        if base <= topo:
            return
        ov = pygame.Surface((IW, base - topo), pygame.SRCALPHA)
        ov.fill((0, 0, 12, 228))
        if self.farol:
            cx = int(self.car_x + self.shift_x)
            cy = CAR_Y - 10 - topo
            pygame.draw.polygon(ov, (0, 0, 12, 90), [(cx - 5, cy), (cx + 5, cy), (cx + 26, cy - 60), (cx - 26, cy - 60)])
            pygame.draw.polygon(ov, (0, 0, 12, 30), [(cx - 4, cy), (cx + 4, cy), (cx + 13, cy - 56), (cx - 13, cy - 56)])
        m.blit(ov, (0, topo))

    def desenhar_tunel_bocas(self, m, o):
        for y in (int(o.y), int(o.y) - TUNEL_COMP):
            if -6 < y < IH + 6:
                m.fill(ROCHA_CLARA, (0, y - 5, IW, 2))
                m.fill(ROCHA, (0, y - 3, IW, 2))
                m.fill((40, 32, 24), (0, y - 1, IW, 1))

    def desenhar_mundo(self):
        m = self.mundo
        sc = int(self.scroll)
        m.fill(GRAMA)
        for x, y0 in self.pontos_grama:
            m.set_at((x, (y0 + sc) % IH), GRAMA_ESC)
        # pista
        pygame.draw.rect(m, ASFALTO, (ROAD_L, 0, ROAD_R - ROAD_L, IH))
        for x, y0 in self.pontos_asfalto:
            m.set_at((x, (y0 + sc) % IH), ASFALTO_ESC)
        # zebrado das bordas (linha branca + tracejado preto)
        m.fill(BRANCO, (ROAD_L - 1, 0, 1, IH))
        m.fill(BRANCO, (ROAD_R, 0, 1, IH))
        y = -8 + sc % 8
        while y < IH:
            m.fill(PRETO, (ROAD_L - 3, y, 2, 4))
            m.fill(PRETO, (ROAD_R + 1, y, 2, 4))
            y += 8
        # divisorias tracejadas entre as 3 faixas
        y = -16 + sc % 16
        while y < IH:
            for x in (ROAD_L + LANE_W - 1, ROAD_L + 2 * LANE_W - 1):
                m.fill(BRANCO, (x, y, 2, 8))
            y += 16
        # casas, arvores e arbustos
        self.desenhar_deco(m, self.deco_esq)
        self.desenhar_deco(m, self.deco_dir)
        # objetos do cenario
        for o in self.objs:
            if o.tipo == "fork":
                self.desenhar_ramal(m, o)
            elif o.tipo == "tunel":
                self.desenhar_tunel_paredes(m, o)
        for o in self.objs:
            if o.tipo == "lombada":
                self.desenhar_lombada(m, o)
            elif o.tipo == "pedestre":
                self.desenhar_faixa(m, o)

        # outros carros
        for n in self.npcs:
            spr = self.img_caminhao if n.tipo == "caminhao" else self.img_npc[n.cor]
            w, h = n.tam
            bx = int(self.x_npc(n)) - w // 2 - (1 if n.tipo == "caminhao" else 2)
            by = int(n.y) - h // 2
            m.blit(spr, (bx, by))
            if n.freia:                                      # lanternas acesas ao desacelerar
                ly = by + (32 if n.tipo == "caminhao" else 20)
                lx = (3, 13) if n.tipo == "caminhao" else (3, 10)
                for dx in lx:
                    m.fill((255, 90, 90), (bx + dx, ly, 3, 2))
        # escuridao do tunel e neblina
        for o in self.objs:
            if o.tipo == "tunel":
                self.desenhar_tunel_escuro(m, o)
            elif o.tipo == "neblina":
                self.desenhar_neblina(m, o)
        for o in self.objs:                                  # portico do radar fica por cima de tudo
            if o.tipo == "radar":
                self.desenhar_radar(m, o)
        # farol aceso: feixe de luz na frente do carro (3 faixas escalonadas)
        if self.farol and self.cinto:
            cx = int(self.car_x + self.shift_x)
            luz = pygame.Surface((IW, IH), pygame.SRCALPHA)
            topo = CAR_Y - 10
            for comp, larg in ((46, 15), (32, 11), (18, 7)):
                pygame.draw.polygon(luz, (255, 250, 170, 16),
                                    [(cx - 5, topo), (cx + 5, topo), (cx + larg, topo - comp), (cx - larg, topo - comp)])
            m.blit(luz, (0, 0))
        self.desenhar_placas(m)
        self.desenhar_particulas(m)
        self.desenhar_carro(m)
        for o in self.objs:
            if o.tipo == "tunel":
                self.desenhar_tunel_bocas(m, o)

    def desenhar_placas(self, m):
        piscar = (pygame.time.get_ticks() // 150) % 2 == 0
        for s in self.sinais:
            x, y = SIGN_X - 12, int(s.y) - 12
            m.blit(self.img_poste, (SIGN_X - self.img_poste.get_width() // 2, y + 22))   # poste
            m.blit(self.img_sinal[s.tipo], (x, y))
            if s.estado == "ativa" and s.y >= ZONA_INI and piscar:
                pygame.draw.circle(m, AMARELO, (SIGN_X, int(s.y)), 15, 1)
            elif s.estado == "ok":
                pygame.draw.lines(m, VERDE, False, [(SIGN_X - 6, int(s.y)), (SIGN_X - 2, int(s.y) + 5),
                                                    (SIGN_X + 6, int(s.y) - 5)], 2)
            elif s.estado == "falhou":
                cy = int(s.y)
                pygame.draw.line(m, VERMELHO, (SIGN_X - 6, cy - 6), (SIGN_X + 6, cy + 6), 2)
                pygame.draw.line(m, VERMELHO, (SIGN_X - 6, cy + 6), (SIGN_X + 6, cy - 6), 2)

    def desenhar_teclas(self):
        """Etiqueta com a tecla a apertar, escrita em cima de cada placa ativa."""
        t = self.tela
        pisca = (pygame.time.get_ticks() // 220) % 2 == 0
        for s in self.sinais:
            if s.estado != "ativa":
                continue
            tecla = SINAIS[s.tipo]["tecla"]
            proibe = tecla.startswith("NÃO")
            w = largura_texto(tecla, 2) + 14
            cx = SIGN_X * SC
            x = min(cx - w // 2, PAINEL_X - w - 2)
            y = int((s.y - 12) * SC) - 30
            if y < -24 or y > H:
                continue
            ativa = s.y >= ZONA_INI and pisca
            fundo = BRANCO if ativa else (VERMELHO if proibe else AMARELO)
            letra = PRETO if (ativa or not proibe) else BRANCO
            t.fill(PRETO, (x - 2, y - 2, w + 4, 26))
            t.fill(fundo, (x, y, w, 22))
            texto(t, tecla, x + w // 2, y + 1, letra, 2, centro=True, sombra=False)
            t.fill(PRETO, (cx - 3, y + 24, 6, 4))            # setinha apontando para a placa

    def desenhar_particulas(self, m):
        for x, y, _, _, vida, cor in self.parts:
            tam = 2 if vida > 0.2 else 1
            m.fill(cor, (int(x), int(y), tam, tam))

    def desenhar_carro(self, m):
        salto = 0
        if self.salto_t > 0:
            prog = 1 - self.salto_t / self.salto_dur
            salto = -int(round(self.salto_amp * math.sin(math.pi * prog)))
        x = int(self.car_x + self.shift_x) - 8
        y = CAR_Y - 11 + int(round(self.car_dy)) + salto
        m.blit(self.img_carro, (x, y))
        if self.freando or (self.speed > 0 and self.car_dy > 1.5):      # lanternas acesas
            m.fill((255, 150, 150), (x + 3, y + 20, 3, 2))
            m.fill((255, 150, 150), (x + 10, y + 20, 3, 2))
        if self.pisca and (pygame.time.get_ticks() // 250) % 2 == 0:
            px = x - 2 if self.pisca < 0 else x + 16
            m.fill((255, 170, 0), (px, y + 1, 2, 2))
            m.fill((255, 170, 0), (px, y + 19, 2, 2))

    # ---------- 3) DRAW (interface, em resolucao real)
    def painel(self, rect, alpha=170):
        p = pygame.Surface(rect.size, pygame.SRCALPHA)
        p.fill((0, 0, 0, alpha))
        pygame.draw.rect(p, (255, 255, 255, 220), p.get_rect(), 2)
        self.tela.blit(p, rect.topleft)

    def veu(self, alpha):
        v = pygame.Surface((W, H), pygame.SRCALPHA)
        v.fill((0, 0, 0, alpha))
        self.tela.blit(v, (0, 0))

    def barra(self, x, y, valor, maximo, cor, blocos=20, bw=8, bh=12):
        cheio = int(round(blocos * min(1.0, valor / maximo)))
        for i in range(blocos):
            self.tela.fill(cor if i < cheio else (50, 50, 50), (x + i * (bw + 1), y, bw, bh))

    def desenhar_hud(self):
        t = self.tela
        t.fill(PRETO, (PAINEL_X, 0, W - PAINEL_X, H))
        x = PAINEL_X + 12
        texto(t, "TRÂNSITO", x, 8, AMARELO, 3)
        texto(t, "SEGURO", x, 44, AMARELO, 3)
        texto(t, "PONTOS", x, 92, BRANCO, 2)
        texto(t, str(int(self.score)), x, 114, AMARELO, 3)
        texto(t, "NÍVEL", x, 150, BRANCO, 2)
        texto(t, str(self.nivel), x, 172, AMARELO, 3)
        texto(t, "COMBO", x, 206, BRANCO, 2)
        texto(t, "X%d" % self.mult, x, 228, VERDE if self.mult > 1 else BRANCO, 3)
        texto(t, "CNH %d/%d" % (self.cnh, LIMITE_CNH), x, 264, BRANCO, 2)
        r = self.cnh / LIMITE_CNH
        self.barra(x, 288, min(self.cnh, LIMITE_CNH), LIMITE_CNH,
                   VERDE if r < 0.5 else (AMARELO if r < 0.8 else VERMELHO), blocos=16, bw=9, bh=12)
        texto(t, "VELOCIDADE", x, 312, BRANCO, 2)
        texto(t, "%d KM/H" % int(round(self.speed)), x, 334, BRANCO, 3)
        self.barra(x, 362, self.speed, MAX_V, VERDE if self.speed <= 60 else AMARELO,
                   blocos=16, bw=9, bh=12)
        texto(t, "CINTO: " + ("OK" if self.cinto else "--"), x, 388, VERDE if self.cinto else VERMELHO, 2)
        texto(t, "FAROL: " + ("%ds" % (self.farol_t + 0.99) if self.farol else "OFF"), x, 410, AMARELO if self.farol else CINZA, 2)
        for i, linha in enumerate(("A/D: FAIXA", "W/S: VELOC.", "F: FREAR", "Q/E: SETAS", "SHIFT: FAROL", "M: MUSICA", "P: PAUSA")):
            texto(t, linha, x, 440 + i * 21, CINZA, 2, sombra=False)

        if self.msg_t > 0:
            linhas = textwrap.wrap(self.hint.upper(), 44) if self.hint else []
            alt = 20 + 26 + 24 * len(linhas) + (6 if linhas else 0)
            self.painel(pygame.Rect(12, 12, PAINEL_X - 24, alt))
            texto(t, self.msg, PAINEL_X // 2, 24, self.msg_cor, 2, centro=True)
            for i, l in enumerate(linhas):
                texto(t, l, PAINEL_X // 2, 56 + 24 * i, BRANCO, 2, centro=True, sombra=False)

    def tela_cinto(self):
        self.painel(pygame.Rect(40, 200, PAINEL_X - 80, 210), 215)
        self.tela.blit(self.icone_cinto, (70, 255))
        texto(self.tela, "COLOQUE O CINTO", 170, 232, AMARELO, 3)
        texto(self.tela, "DE SEGURANÇA", 170, 276, AMARELO, 3)
        if (pygame.time.get_ticks() // 450) % 2 == 0:
            texto(self.tela, "APERTE C PARA AFIVELAR", 170, 340, BRANCO, 2)

    def tela_menu(self):
        t = self.tela
        self.veu(205)
        texto(t, "TRÂNSITO SEGURO", W // 2, 20, AMARELO, 5, centro=True)
        texto(t, "OBEDEÇA AS PLACAS ANTES QUE SEJA TARDE!", W // 2, 82, BRANCO, 2, centro=True)
        for n, (tipo, d) in enumerate(SINAIS.items()):
            col, lin = divmod(n, 6)
            x0, y = 20 + col * 400, 108 + lin * 56
            t.blit(ampliar(self.img_sinal[tipo + "_puro"], 2), (x0, y))
            texto(t, d["curto"], x0 + 58, y + 8, BRANCO, 2)
            texto(t, "TECLA: " + d["tecla"], x0 + 58, y + 28, AMARELO, 2)
        texto(t, "A/D FAIXA  W/S VELOC.  F FREAR  Q/E SETAS  SHIFT FAROL", W // 2, 470, AMARELO, 2, centro=True)
        texto(t, "ANTES DE SAIR: APERTE C PARA AFIVELAR O CINTO", W // 2, 496, AMARELO, 2, centro=True)
        texto(t, "CUIDADO COM OS CARROS! BATEU = CNH PENALIZADA", W // 2, 520, VERMELHO, 2, centro=True)
        texto(t, "CADA ERRO SOMA PONTOS NA CNH. 20 = CNH SUSPENSA!", W // 2, 544, VERMELHO, 2, centro=True)
        if (pygame.time.get_ticks() // 500) % 2 == 0:
            texto(t, "ENTER PARA COMEÇAR  |  ESC PARA SAIR", W // 2, 572, BRANCO, 2, centro=True)

    def tela_fim(self):
        t = self.tela
        self.veu(215)
        texto(t, "CNH SUSPENSA!", W // 2, 90, VERMELHO, 5, centro=True)
        texto(t, "PONTOS: %d" % int(self.score), W // 2, 170, AMARELO, 3, centro=True)
        texto(t, "PLACAS OBEDECIDAS: %d   INFRAÇÕES: %d   MAIOR COMBO: %d"
              % (self.acertos, self.erros, self.melhor_combo), W // 2, 230, BRANCO, 2, centro=True)
        paragrafo(t, "No trânsito real, uma distração de poucos segundos pode custar vidas. "
                     "Respeitar a sinalização protege você, os passageiros e os pedestres.",
                  W // 2, 300, 46, BRANCO, 2, centro=True)
        if (pygame.time.get_ticks() // 500) % 2 == 0:
            texto(t, "ENTER JOGAR DE NOVO  |  ESC SAIR", W // 2, 520, AMARELO, 2, centro=True)

    def draw(self):
        t = self.tela
        self.desenhar_mundo()
        pygame.transform.scale(self.mundo, (IW * SC, IH * SC), t.subsurface((0, 0, IW * SC, IH * SC)))
        if self.estado == "jogando" and self.cinto:
            self.desenhar_teclas()
        if self.estado in ("jogando", "pausado"):
            self.desenhar_hud()
        else:
            t.fill(PRETO, (PAINEL_X, 0, W - PAINEL_X, H))
        if self.estado == "jogando" and not self.cinto:
            self.tela_cinto()
        if self.flash_t > 0 and self.estado == "jogando":
            fl = pygame.Surface((PAINEL_X, H), pygame.SRCALPHA)
            fl.fill(self.flash_cor + (int(110 * self.flash_t / 0.3),))
            t.blit(fl, (0, 0))
        if self.estado == "menu":
            self.tela_menu()
        elif self.estado == "pausado":
            self.veu(150)
            texto(t, "PAUSADO", W // 2, H // 2 - 40, BRANCO, 6, centro=True)
            texto(t, "APERTE P PARA CONTINUAR", W // 2, H // 2 + 30, AMARELO, 2, centro=True)
        elif self.estado == "fim":
            self.tela_fim()
        pygame.display.flip()


def main():
    pygame.mixer.pre_init(22050, -16, 1, 512)
    pygame.init()
    tela = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Trânsito Seguro")
    clock = pygame.time.Clock()
    jogo = Game(tela)

    while True:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)
        for e in pygame.event.get():       # 1) input
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            jogo.evento(e)
        jogo.update(dt)                    # 2) update
        jogo.draw()                        # 3) draw


if __name__ == "__main__":
    main()
