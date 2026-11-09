# Trânsito Seguro

Jogo educativo de trânsito feito em Python com Pygame, visto de cima e em pixel art. Dirija pela pista, obedeça às placas e evite infrações para não perder a CNH (limite de 20 pontos).

## Como rodar

1. Instale o Python 3.
2. Instale o Pygame:

```
pip install pygame-ce
```

3. Dentro da pasta do jogo, execute:

```
python transito_seguro.py
```

## Importante: baixe os sprites

O jogo usa imagens PNG e uma música que ficam em pastas ao lado do `transito_seguro.py`. **Baixe o repositório inteiro, com as pastas `imagens/` e `musica/`**, e mantenha a estrutura abaixo:

```
transito_seguro.py
imagens/
  placas/
  veiculos/
  pedestres/
  cenario/
musica/
  bordeaux.ogg
```

Sem a pasta `imagens/` o jogo não abre e mostra qual arquivo está faltando. Sem a música, ele roda normalmente, só sem som de fundo.

## Controles

| Tecla | Ação |
|---|---|
| C | Afivelar o cinto (obrigatório para começar) |
| A / D | Mudar de faixa |
| W / S | Acelerar / reduzir |
| F | Frear |
| Q / E | Seta esquerda / direita |
| SHIFT | Ligar o farol (apaga sozinho depois de 10 s) |
| M | Ligar/desligar a música |
| P | Pausar |
| ESC | Sair |

## Placas e o que fazer

- **Velocidade máxima / Atenção / Radar:** reduza a velocidade (S).
- **Lombada:** passe a 30 km/h ou menos.
- **Túnel e neblina:** ligue o farol (SHIFT) antes de entrar.
- **Proibido virar:** não entre na rua lateral.
- **Faixa de pedestres:** pare (F) e espere todos atravessarem.

A tecla certa aparece acima de cada placa.

## Pontuação

Cada erro soma pontos na CNH: batida (+5), atropelamento (+10), mudar de faixa sem seta (+1) e descumprir uma placa (valor depende da placa). Ao chegar a 20 pontos, o jogo acaba. Acertos em sequência geram combo e devolvem pontos da CNH.
