#! /usr/bin/python3
# src: https://github.com/diegofelipece/mussum-ipsum/blob/master/src/mipsum.js

import random

mussumMainQuote = "Mussum Ipsum, cacilds vidis litro abertis."
mussumQuotes = [
  "Pra lá , depois divoltis porris, paradis.",
  "Paisis, filhis, espiritis santis.",
  "Mé faiz elementum girarzis, nisi eros vermeio.",
  "Manduma pindureta quium dia nois paga.",
  "Sapien in monti palavris qui num significa nadis i pareci latim.",
  "Interessantiss quisso pudia ce receita de bolis, mais bolis eu num gostis.",
  "Suco de cevadiss, é um leite divinis, qui tem lupuliz, matis, aguis e fermentis.",
  "Interagi no mé, cursus quis, vehicula ac nisi.",
  "Casamentiss faiz malandris se pirulitá.",
  "Cevadis im ampola pa arma uma pindureta.",
  "Atirei o pau no gatis, per gatis num morreus.",
  "Viva Forevis aptent taciti sociosqu ad litora torquent.",
  "Copo furadis é disculpa de bebadis, arcu quam euismod magna.",
  "Delegadis gente finis, bibendum egestas augue arcu ut est.",
  "In elementis mé pra quem é amistosis quis leo.",
  "Não sou faixa preta cumpadi, sou preto inteiris, inteiris.",
  "Mais vale um bebadis conhecidiss, que um alcoolatra anonimis.",
  "Suco de cevadiss deixa as pessoas mais interessantis.",
  "Tá deprimidis, eu conheço uma cachacis que pode alegrar sua vidis.",
  "Todo mundo vê os porris que eu tomo, mas ninguém vê os tombis que eu levo!",
  "Quem manda na minha terra sou euzis!",
  "Si num tem leite então bota uma pinga aí cumpadi!",
  "Diuretics paradis num copo é motivis de denguis.",
  "Em pé sem cair, deitado sem dormir, sentado sem cochilar e fazendo pose.",
  "A ordem dos tratores não altera o pão duris.",
  "Quem num gosta di mim que vai caçá sua turmis!",
  "Quem num gosta di mé, boa gentis num é.",
  "Si u mundo tá muito paradis? Toma um mé que o mundo vai girarzis!",
  "Per aumento de cachacis, eu reclamis.",
  "Detraxit consequat et quo num tendi nada.",
  "Admodum accumsan disputationi eu sit. Vide electram sadipscing et per.",
  "Leite de capivaris, leite de mula manquis sem cabeça.",
  "Aenean aliquam molestie leo, vitae iaculis nisl.",
  "Praesent vel viverra nisi. Mauris aliquet nunc non turpis scelerisque, eget.",
  "Posuere libero varius. Nullam a nisl ut ante blandit hendrerit. Aenean sit amet nisi.",
  "Nec orci ornare consequat. Praesent lacinia ultrices consectetur. Sed non ipsum felis.",
  "Praesent malesuada urna nisi, quis volutpat erat hendrerit non. Nam vulputate dapibus.",
  "Nullam volutpat risus nec leo commodo, ut interdum diam laoreet. Sed non consequat odio.",
  "Mauris nec dolor in eros commodo tempor. Aenean aliquam molestie leo, vitae iaculis nisl.",
  "Vehicula non. Ut sed ex eros. Vivamus sit amet nibh non tellus tristique interdum."
]

quotes_size = len(mussumQuotes)

class MussumLorum:
    # returns: string
    # parameters: nr_lines := int
    def get_text(self, nr_lines=None):
        if nr_lines is None:
            nr_lines = random.randint(1,30)
        text = mussumMainQuote + "\n"
        while nr_lines > 0:
            position = random.randint(0, quotes_size - 1)
            text += mussumQuotes[position] + "\n"
            nr_lines -= 1
        return text

    # returns: array
    # parameters: nr_paragraphs := int
    def get_paragraph(self, nr_paragraphs=None):
        if nr_paragraphs is None:
            nr_paragraphs = random.randint(1, 10)
        blocks = []
        while nr_paragraphs > 0:
            blocks.append(self.get_text())
            nr_paragraphs -= 1
        return blocks

if __name__ == '__main__':
    m = MussumLorum()
    for quote in m.get_paragraph():
        print(quote)
