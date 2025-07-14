from kivy.core.window import Window
Window.softinput_mode = 'below_target'
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import ObjectProperty, ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.metrics import dp

import sqlite3
from datetime import datetime
import os
import shutil

# Classe base para obter o diretório de dados do usuário
class AtelierEttyApp(App):
    carrinho = ListProperty([])  

    def build(self):
        return Builder.load_file('telas.kv')

    def get_user_data_path(self):
        return self.user_data_dir

# Conexão com banco SQLite
# O banco de dados será copiado para o diretório de dados do usuário na primeira execução
# ou criado se não existir.
app_instance = AtelierEttyApp() # Instancia temporária para acessar user_data_dir
caminho_banco_destino = os.path.join(app_instance.user_data_dir, "atelier_etty.db")
caminho_banco_fonte = os.path.join(os.path.dirname(__file__), "atelier_etty.db")

# Garante que o diretório de dados do usuário exista
if not os.path.exists(app_instance.user_data_dir):
    os.makedirs(app_instance.user_data_dir)

# Copia o banco de dados da pasta do aplicativo para o diretório de dados do usuário, se não existir
if not os.path.exists(caminho_banco_destino):
    if os.path.exists(caminho_banco_fonte):
        shutil.copyfile(caminho_banco_fonte, caminho_banco_destino)
        print(f"Banco de dados '{os.path.basename(caminho_banco_fonte)}' copiado para: {caminho_banco_destino}")
    else:
        print(f"AVISO: Arquivo de banco de dados inicial '{os.path.basename(caminho_banco_fonte)}' não encontrado. Criando um novo banco em: {caminho_banco_destino}")
        # Se o banco inicial não for encontrado, crie a estrutura do banco aqui
        conn_init = sqlite3.connect(caminho_banco_destino)
        cursor_init = conn_init.cursor()
        cursor_init.execute('''
            CREATE TABLE IF NOT EXISTS produtos (
                id_produto INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                preco REAL NOT NULL
            )
        ''')
        cursor_init.execute('''
            CREATE TABLE IF NOT EXISTS estoque (
                id_produto INTEGER PRIMARY KEY,
                quantidade_disponivel INTEGER NOT NULL,
                FOREIGN KEY (id_produto) REFERENCES produtos(id_produto)
            )
        ''')
        cursor_init.execute('''
            CREATE TABLE IF NOT EXISTS servicos (
                id_servico INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo_servico TEXT NOT NULL UNIQUE,
                custo REAL NOT NULL
            )
        ''')
        cursor_init.execute('''
            CREATE TABLE IF NOT EXISTS vendas (
                id_venda INTEGER PRIMARY KEY AUTOINCREMENT,
                data_venda TEXT NOT NULL,
                total REAL NOT NULL,
                forma_pagamento TEXT NOT NULL,
                valor_pago REAL NOT NULL,
                tipo_venda TEXT NOT NULL
            )
        ''')
        cursor_init.execute('''
            CREATE TABLE IF NOT EXISTS itens_venda (
                id_item_venda INTEGER PRIMARY KEY AUTOINCREMENT,
                id_venda INTEGER NOT NULL,
                id_produto INTEGER,
                id_servico INTEGER,
                quantidade INTEGER NOT NULL,
                preco_unitario REAL NOT NULL,
                FOREIGN KEY (id_venda) REFERENCES vendas(id_venda),
                FOREIGN KEY (id_produto) REFERENCES produtos(id_produto),
                FOREIGN KEY (id_servico) REFERENCES servicos(id_servico)
            )
        ''')
        conn_init.commit()
        conn_init.close()
        print("Estrutura do banco de dados criada com sucesso.")
else:
    print(f"Banco de dados já existe em: {caminho_banco_destino}")

con = sqlite3.connect(caminho_banco_destino)
cur = con.cursor()


class TelaProduto(Screen):
    pass

class CadastrarProduto(Screen):
    nome_input = ObjectProperty(None)
    preco_input = ObjectProperty(None)
    quantidade_input = ObjectProperty(None)
    status_label = ObjectProperty(None)

    def salvar_produto(self):
        nome = self.nome_input.text.strip()
        try:
            preco = float(self.preco_input.text)
            quantidade = int(self.quantidade_input.text)
        except ValueError:
            self.status_label.text = "Erro: preço ou quantidade inválidos."
            return

        if not nome:
            self.status_label.text = "Erro: nome é obrigatório."
            return

        # Verifica se o produto já existe ANTES de tentar inserir
        cur.execute("SELECT id_produto FROM produtos WHERE nome = ?", (nome,))
        if cur.fetchone() is not None:
            self.status_label.text = "Erro: Produto com este nome já existe."
            return

        try:
            cur.execute("INSERT INTO produtos (nome, preco, quantidade) VALUES (?, ?, ?)", 
                       (nome, preco, quantidade))
            id_produto = cur.lastrowid
            cur.execute("INSERT INTO estoque (id_produto, quantidade_disponivel) VALUES (?, ?)", 
                       (id_produto, quantidade))
            con.commit()
            self.status_label.text = "Produto cadastrado com sucesso!"
            self.nome_input.text = ""
            self.preco_input.text = ""
            self.quantidade_input.text = ""
        except Exception as e:
            self.status_label.text = f"Erro ao salvar: {e}"
            con.rollback()

class LocalizarProduto(Screen):
    busca_input = ObjectProperty(None)
    nome_label = ObjectProperty(None)
    preco_input = ObjectProperty(None)
    quantidade_input = ObjectProperty(None)
    status_label = ObjectProperty(None)
    id_encontrado = None

    def buscar_produto(self):
        nome = self.busca_input.text.strip()
        if not nome:
            self.status_label.text = "Digite um nome para buscar."
            self.nome_label.text = ""
            self.preco_input.text = ""
            self.quantidade_input.text = ""
            self.id_encontrado = None
            return

        cur.execute("""
            SELECT p.id_produto, p.nome, p.preco, e.quantidade_disponivel
            FROM produtos p
            JOIN estoque e ON p.id_produto = e.id_produto
            WHERE p.nome LIKE ?
            LIMIT 1
        """, (f'%{nome}%',))
        resultado = cur.fetchone()

        if resultado:
            self.id_encontrado = resultado[0]
            self.nome_label.text = f"Produto: {resultado[1]}"
            self.preco_input.text = str(resultado[2])
            self.quantidade_input.text = str(resultado[3])
            self.status_label.text = ""
        else:
            self.status_label.text = "Produto não encontrado."
            self.nome_label.text = ""
            self.preco_input.text = ""
            self.quantidade_input.text = ""
            self.id_encontrado = None

    def atualizar_produto(self):
        if not self.id_encontrado:
            self.status_label.text = "Busque um produto primeiro."
            return
        try:
            novo_preco = float(self.preco_input.text)
            nova_qtd = int(self.quantidade_input.text)
        except ValueError:
            self.status_label.text = "Erro nos dados inseridos."
            return

        try:
            cur.execute("UPDATE produtos SET preco = ? WHERE id_produto = ?", (novo_preco, self.id_encontrado))
            cur.execute("UPDATE estoque SET quantidade_disponivel = ? WHERE id_produto = ?", (nova_qtd, self.id_encontrado))
            con.commit()
            self.status_label.text = "Produto atualizado com sucesso!"
        except Exception as e:
            self.status_label.text = f"Erro ao atualizar: {e}"


class TelaServico(Screen):
    pass

class CadastrarServico(Screen):
    tipo_servico_input = ObjectProperty(None)
    custo_input = ObjectProperty(None)
    status_label = ObjectProperty(None)

    def salvar_servico(self):
        tipo = self.tipo_servico_input.text.strip()
        try:
            custo = float(self.custo_input.text)
        except ValueError:
            self.status_label.text = "Erro: custo inválido."
            return

        if not tipo:
            self.status_label.text = "Erro: nome do serviço obrigatório."
            return

        try:
            cur.execute("INSERT INTO servicos (tipo_servico, custo) VALUES (?, ?)", (tipo, custo))
            con.commit()
            self.status_label.text = "Serviço cadastrado com sucesso!"
            self.tipo_servico_input.text = ""
            self.custo_input.text = ""
        except sqlite3.IntegrityError:
            self.status_label.text = "Erro: Serviço com este nome já existe."
        except Exception as e:
            self.status_label.text = f"Erro ao salvar: {e}"

class LocalizarServico(Screen):
    busca_input = ObjectProperty(None)
    custo_input = ObjectProperty(None)
    status_label = ObjectProperty(None)
    id_encontrado = None

    def mostrar_resultados(self, mostrar):
        resultados_box = self.ids.resultados_box
        if mostrar:
            resultados_box.height = dp(250)
            resultados_box.opacity = 1
        else:
            resultados_box.height = 0
            resultados_box.opacity = 0

    def buscar_servico(self):
        tipo = self.busca_input.text.strip()
        if not tipo:
            self.status_label.text = "Digite um nome para buscar."
            if hasattr(self, 'ids') and 'tipo_label' in self.ids:
                self.ids.tipo_label.text = ""
            self.custo_input.text = ""
            self.id_encontrado = None
            self.mostrar_resultados(False)
            return

        cur.execute("""
            SELECT id_servico, tipo_servico, custo
            FROM servicos
            WHERE tipo_servico LIKE ?
            LIMIT 1
        """, (f'%{tipo}%',))
        resultado = cur.fetchone()

        if resultado:
            self.id_encontrado = resultado[0]
            if hasattr(self, 'ids') and 'tipo_label' in self.ids:
                self.ids.tipo_label.text = f"Serviço: {resultado[1]}"
            self.custo_input.text = str(resultado[2])
            self.status_label.text = ""
            self.mostrar_resultados(True)
        else:
            self.status_label.text = "Serviço não encontrado."
            if hasattr(self, 'ids') and 'tipo_label' in self.ids:
                self.ids.tipo_label.text = ""
            self.custo_input.text = ""
            self.id_encontrado = None
            self.mostrar_resultados(False)

    def atualizar_servico(self):
        if not self.id_encontrado:
            self.status_label.text = "Busque um serviço primeiro."
            return
        try:
            novo_custo = float(self.custo_input.text)
        except ValueError:
            self.status_label.text = "Erro no valor inserido."
            return

        try:
            cur.execute("UPDATE servicos SET custo = ? WHERE id_servico = ?", (novo_custo, self.id_encontrado))
            con.commit()
            self.status_label.text = "Serviço atualizado com sucesso!"
        except Exception as e:
            self.status_label.text = f"Erro ao atualizar: {e}"

class TelaEstoque(Screen):
    busca_input = ObjectProperty(None)
    resultado_box = ObjectProperty(None)

    def buscar_estoque(self):
        nome = self.busca_input.text.strip()
        print("Buscando estoque por:", nome) # Para depuração

        # Buscar produtos
        cur.execute("""
            SELECT p.nome, e.quantidade_disponivel
            FROM produtos p
            JOIN estoque e ON p.id_produto = e.id_produto
            WHERE p.nome LIKE ?
            ORDER BY p.nome
        """, ('%' + nome + '%',))
        resultados_produtos = cur.fetchall()

        # Buscar serviços
        cur.execute("""
            SELECT tipo_servico, NULL FROM servicos WHERE tipo_servico LIKE ? ORDER BY tipo_servico
        """, ('%' + nome + '%',))
        resultados_servicos = cur.fetchall()

        self.resultado_box.clear_widgets()

        if resultados_produtos or resultados_servicos:
            # Cabeçalho da tabela de produtos (em negrito)
            header_produtos = BoxLayout(size_hint_y=None, height=40)
            header_produtos.add_widget(Label(text="[b]Produto[/b]", color=(0,0,0,1), markup=True, size_hint_x=0.7, font_size='16sp'))
            header_produtos.add_widget(Label(text="[b]Qtd[/b]", color=(0,0,0,1), markup=True, size_hint_x=0.3, font_size='16sp'))
            self.resultado_box.add_widget(header_produtos)

            for nome_produto, qtd in resultados_produtos:
                item = BoxLayout(size_hint_y=None, height=40)
                # Nome do produto em negrito
                item.add_widget(Label(
                    text=f"[b]{nome_produto}[/b]", 
                    color=(0, 0, 0, 1), 
                    markup=True,
                    font_size='16sp',
                    size_hint_x=0.7))
                # Quantidade em negrito e vermelho
                item.add_widget(Label(
                    text=f"[b]{qtd}[/b]", 
                    color=(0.929, 0.102, 0.102, 1), 
                    markup=True,
                    font_size='16sp',
                    size_hint_x=0.3))
                self.resultado_box.add_widget(item)

            if resultados_servicos and resultados_produtos:
                 self.resultado_box.add_widget(Label(
                     text="[b]-- Serviços --[/b]", 
                     color=(0,0,0,1), 
                     markup=True, 
                     size_hint_y=None, 
                     height=30,
                     font_size='16sp'))

            # Cabeçalho da tabela de serviços (em negrito)
            if resultados_servicos:
                header_servicos = BoxLayout(size_hint_y=None, height=40)
                header_servicos.add_widget(Label(
                    text="[b]Serviço[/b]", 
                    color=(0,0,0,1), 
                    markup=True, 
                    size_hint_x=0.7,
                    font_size='16sp'))
                header_servicos.add_widget(Label(
                    text="[b]Custo[/b]", 
                    color=(0,0,0,1), 
                    markup=True, 
                    size_hint_x=0.3,
                    font_size='16sp'))
                self.resultado_box.add_widget(header_servicos)

                for tipo_servico, _ in resultados_servicos:
                    item = BoxLayout(size_hint_y=None, height=40)
                    # Nome do serviço em negrito
                    item.add_widget(Label(
                        text=f"[b]{tipo_servico}[/b]", 
                        color=(0, 0, 0, 1),
                        markup=True,
                        font_size='16sp',
                        size_hint_x=0.7))
                    item.add_widget(Label(
                        text="N/A", 
                        color=(0.929, 0.102, 0.102, 1),
                        font_size='16sp',
                        size_hint_x=0.3))
                    self.resultado_box.add_widget(item)

            self.resultado_box.height = self.resultado_box.minimum_height
        else:
            self.resultado_box.add_widget(Label(
                text="Nenhum item encontrado.", 
                size_hint_y=None, 
                height=40, 
                color=(0,0,0,1),
                font_size='16sp'))
            self.resultado_box.height = 40


# --- Venda Buscar Produtos ---
class TelaVendaBuscar(Screen):
    busca_input = ObjectProperty(None)
    resultado_box = ObjectProperty(None)
    carrinho_box = ObjectProperty(None)  # para atualizar display
    carrinho = ListProperty([]) # Definido como ListProperty na classe principal AtelierEtty

    # Usamos on_pre_enter para garantir que o carrinho seja atualizado sempre que a tela for acessada
    def on_pre_enter(self, *args):
        # Limpa o carrinho de pesquisa ao entrar na tela (opcional, mas boa prática)
        self.busca_input.text = ""
        self.resultado_box.clear_widgets()
        # Atualiza o display do carrinho sempre que a tela é exibida
        self.atualizar_carrinho_display()
        print(f"Carrinho na entrada: {App.get_running_app().carrinho}")

    def buscar_produtos(self):
        nome = self.busca_input.text.strip()
        if not nome:
            self.resultado_box.clear_widgets()
            self.resultado_box.add_widget(Label(text="Digite o nome do produto para buscar.", size_hint_y=None, height=40))
            return

        cur.execute("""
            SELECT p.id_produto, p.nome, p.preco, e.quantidade_disponivel
            FROM produtos p JOIN estoque e ON p.id_produto = e.id_produto
            WHERE p.nome LIKE ?
            ORDER BY p.nome
        """, ('%' + nome + '%',))
        resultados = cur.fetchall()

        self.resultado_box.clear_widgets()
        self.quantidade_labels = {}  # Dicionário para guardar referências às Labels de quantidade

        if resultados:
            # Adiciona cabeçalho da lista de produtos
            header = BoxLayout(size_hint_y=None, height=40)
            header.add_widget(Label(text="[b]Produto[/b]", markup=True, size_hint_x=0.3))
            header.add_widget(Label(text="[b]Preço[/b]", markup=True, size_hint_x=0.2))
            header.add_widget(Label(text="[b]Disponível[/b]", markup=True, size_hint_x=0.2))
            header.add_widget(Label(text="[b]Qtd[/b]", markup=True, size_hint_x=0.15)) # Nova coluna para a quantidade selecionada
            header.add_widget(Widget(size_hint_x=0.15)) # Espaço para os botões +/-
            self.resultado_box.add_widget(header)


            for id_produto, nome_produto, preco, qtd_disponivel in resultados:
                item = BoxLayout(size_hint_y=None, height=40)

                item.add_widget(Label(text=nome_produto, size_hint_x=0.3))
                item.add_widget(Label(text=f"R$ {preco:.2f}", size_hint_x=0.2))
                item.add_widget(Label(text=f"{qtd_disponivel}", size_hint_x=0.2)) # Qtd disponível

                # Buscar a quantidade atual do produto no carrinho
                qtd_no_carrinho = 0
                for c_item in App.get_running_app().carrinho:
                    if c_item['id_produto'] == id_produto:
                        qtd_no_carrinho = c_item['quantidade']
                        break

                qtd_label = Label(text=str(qtd_no_carrinho), size_hint_x=0.15)
                self.quantidade_labels[id_produto] = qtd_label  # Guarda referência

                # Botões de +/-
                botoes_qtd = BoxLayout(size_hint_x=0.15)
                btn_menos = Button(text='-', size_hint_x=None, width=30)
                btn_mais = Button(text='+', size_hint_x=None, width=30)

                btn_menos.bind(on_press=lambda btn, pid=id_produto, nome=nome_produto, preco=preco, qtd_disp=qtd_disponivel: self.ajustar_quantidade_carrinho(pid, nome, preco, -1, qtd_disp))
                btn_mais.bind(on_press=lambda btn, pid=id_produto, nome=nome_produto, preco=preco, qtd_disp=qtd_disponivel: self.ajustar_quantidade_carrinho(pid, nome, preco, +1, qtd_disp))

                botoes_qtd.add_widget(btn_menos)
                botoes_qtd.add_widget(btn_mais)


                item.add_widget(qtd_label) # Adiciona a label de quantidade
                item.add_widget(botoes_qtd) # Adiciona os botões

                self.resultado_box.add_widget(item)
            self.resultado_box.height = self.resultado_box.minimum_height # Ajusta a altura da caixa de resultados

        else:
            self.resultado_box.add_widget(Label(text="Nenhum produto encontrado.", size_hint_y=None, height=40))
            self.resultado_box.height = 40

    def ajustar_quantidade_carrinho(self, id_produto, nome, preco, direcao, qtd_disponivel):
        app = App.get_running_app()
        found = False
        for item in app.carrinho:
            if item['id_produto'] == id_produto:
                if direcao == +1:
                    if item['quantidade'] < qtd_disponivel:
                        item['quantidade'] += 1
                        self.atualizar_quantidade_label(id_produto, item['quantidade'])
                    else:
                        self.show_popup("Estoque Insuficiente", f"Não há mais estoque disponível para {nome}.")
                elif direcao == -1:
                    if item['quantidade'] > 1:
                        item['quantidade'] -= 1
                        self.atualizar_quantidade_label(id_produto, item['quantidade'])
                    else:
                        app.carrinho.remove(item)
                        self.atualizar_quantidade_label(id_produto, 0) # Remove a label ou mostra 0
                found = True
                break
        if not found and direcao == +1:
            if qtd_disponivel > 0:
                app.carrinho.append({'id_produto': id_produto, 'nome': nome, 'preco': preco, 'quantidade': 1})
                self.atualizar_quantidade_label(id_produto, 1)
            else:
                self.show_popup("Estoque Vazio", f"{nome} está fora de estoque.")

        app.carrinho = app.carrinho[:] # Força a atualização da ListProperty
        self.atualizar_carrinho_display()

    def atualizar_quantidade_label(self, id_produto, quantidade):
        if id_produto in self.quantidade_labels:
            self.quantidade_labels[id_produto].text = str(quantidade)

    def atualizar_carrinho_display(self):
        # Obtém o carrinho global 
        app = App.get_running_app()
        self.carrinho = app.carrinho # Garante que self.carrinho seja a mesma referência

        self.carrinho_box.clear_widgets()
        if not self.carrinho:
            self.carrinho_box.add_widget(Label(text="Carrinho vazio.", size_hint_y=None, height=40, color=(0,0,0,1)))
            self.carrinho_box.height = 40
            return
        

        for item in self.carrinho:
            linha = BoxLayout(size_hint_y=None, height=40, size_hint_x=1)
            linha.add_widget(Label(text=f"{item['nome']} (x{item['quantidade']})", size_hint_x=0.6, color=(0,0,0,1)))
            linha.add_widget(Label(text=f"R$ {item['preco'] * item['quantidade']:.2f}", size_hint_x=0.4, color=(0,0,0,1)))
            self.carrinho_box.add_widget(linha)

        self.carrinho_box.height = sum([child.height + self.carrinho_box.spacing for child in self.carrinho_box.children])
        if self.carrinho_box.height < 40: # Garante uma altura mínima para evitar problemas de layout
            self.carrinho_box.height = 40

    def show_popup(self, title, message):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        popup_label = Label(text=message, halign='center', valign='middle', color=(0,0,0,1))
        close_button = Button(text='OK', size_hint_y=None, height=40)
        layout.add_widget(popup_label)
        layout.add_widget(close_button)

        popup = Popup(title=title, content=layout, size_hint=(0.7, 0.4), auto_dismiss=False)
        close_button.bind(on_release=popup.dismiss)
        popup.open()


class TelaVendaFinalizar(Screen):
    carrinho_box = ObjectProperty(None)
    data_input = ObjectProperty(None)
    forma_pagamento_spinner = ObjectProperty(None)
    valor_pago_input = ObjectProperty(None)
    troco_label = ObjectProperty(None)
    total_label = ObjectProperty(None)

    def on_pre_enter(self, *args):
        app = App.get_running_app()
        self.carrinho = app.carrinho # Usa a referência global do carrinho
        self.atualizar_carrinho_display()
        self.data_input.text = datetime.now().strftime("%Y-%m-%d")
        self.forma_pagamento_spinner.text = "Pix"
        self.valor_pago_input.text = "" # Limpa o campo ao entrar na tela
        self.troco_label.text = "Troco: R$ 0.00"
        self.total = sum(item['preco'] * item['quantidade'] for item in self.carrinho)
        self.total_label.text = f"Total: R$ {self.total:.2f}"

    def atualizar_carrinho_display(self):
        self.carrinho_box.clear_widgets()
        if not self.carrinho:
            self.carrinho_box.add_widget(Label(text="Carrinho vazio.", color=(0,0,0,1)))
            return

        for item in self.carrinho:
            linha = BoxLayout(size_hint_y=None, height=30)
            linha.add_widget(Label(text=f"{item['nome']} (x{item['quantidade']})", color=(0,0,0,1)))
            linha.add_widget(Label(text=f"R$ {item['preco'] * item['quantidade']:.2f}", color=(0,0,0,1)))
            self.carrinho_box.add_widget(linha)
        self.carrinho_box.height = max(self.carrinho_box.minimum_height, 50) # Garante uma altura mínima para o scrollview

    def calcular_troco(self):
        try:
            valor_pago = float(self.valor_pago_input.text)
        except ValueError:
            valor_pago = 0.0 # Define como 0.0 para calcular o troco corretamente se o campo estiver vazio ou inválido

        troco = 0.0
        if self.forma_pagamento_spinner.text == 'Dinheiro' and valor_pago >= self.total:
            troco = valor_pago - self.total
        self.troco_label.text = f"Troco: R$ {troco:.2f}"

    def finalizar_venda(self):
        if not self.carrinho:
            self.troco_label.text = "Carrinho vazio. Adicione itens para finalizar a venda."
            return

        data_venda = self.data_input.text.strip()
        forma_pag = self.forma_pagamento_spinner.text
        try:
            valor_pago = float(self.valor_pago_input.text)
        except ValueError:
            valor_pago = 0.0 # Define como 0.0 para valores não numéricos

        if not data_venda:
            self.troco_label.text = "Data inválida."
            return
        if forma_pag not in ('Credito', 'Debito', 'Pix', 'Dinheiro'):
            self.troco_label.text = "Forma de pagamento inválida."
            return
        if forma_pag == 'Dinheiro' and valor_pago < self.total:
            self.troco_label.text = "Valor pago insuficiente."
            return

        # VERIFICAÇÃO DO ESTOQUE FINAL antes de efetivar
        for item in self.carrinho:
            id_produto = item['id_produto']
            quantidade_vendida = item['quantidade']

            cur.execute("SELECT quantidade_disponivel FROM estoque WHERE id_produto = ?", (id_produto,))
            resultado = cur.fetchone()
            if resultado is None:
                self.troco_label.text = f"Erro: Produto '{item['nome']}' não encontrado no estoque."
                con.rollback() # Rollback em caso de erro
                return
            quantidade_disponivel = resultado[0]
            if quantidade_vendida > quantidade_disponivel:
                self.troco_label.text = f"Estoque insuficiente para {item['nome']}. Disponível: {quantidade_disponivel}"
                con.rollback() # Rollback em caso de erro
                return

        # Inserir venda e itens da venda dentro de uma transação
        try:
            con.execute("BEGIN TRANSACTION;")
            cur.execute("""
                INSERT INTO vendas (data_venda, total, forma_pagamento, valor_pago, tipo_venda)
                VALUES (?, ?, ?, ?, 'Produto')
            """, (data_venda, self.total, forma_pag, valor_pago))
            id_venda = cur.lastrowid

            for item in self.carrinho:
                cur.execute("""
                    INSERT INTO itens_venda (id_venda, id_produto, quantidade, preco_unitario)
                    VALUES (?, ?, ?, ?)
                """, (id_venda, item['id_produto'], item['quantidade'], item['preco']))

                cur.execute("""
                    UPDATE estoque
                    SET quantidade_disponivel = quantidade_disponivel - ?
                    WHERE id_produto = ?
                """, (item['quantidade'], item['id_produto']))
            con.commit()

            # Limpar campos e carrinho
            self.troco_label.text = f"Venda finalizada! Troco: R$ {valor_pago - self.total:.2f}" if forma_pag == 'Dinheiro' else "Venda finalizada com sucesso!"
            self.carrinho_box.clear_widgets()
            self.data_input.text = datetime.now().strftime("%Y-%m-%d") # Reseta a data
            self.valor_pago_input.text = ""
            self.total_label.text = "Total: R$ 0.00"
            App.get_running_app().carrinho.clear() # Limpa o carrinho global

            # Criar e abrir popup de confirmação
            layout = BoxLayout(orientation='vertical', spacing=20, padding=20)
            mensagem = Label(
                text="Venda finalizada com sucesso!",
                font_size=20, color=(0, 0, 0, 1), halign='center', valign='middle', text_size=(400, None)
            )
            botao_ok = Button(
                text="OK", size_hint=(1, None), height=60, font_size=24,
                background_color=(0.067, 0.894, 0.094, 1) # Verde
            )
            layout.add_widget(mensagem)
            layout.add_widget(botao_ok)

            popup = Popup(
                title="Confirmação", content=layout, size_hint=(None, None), size=(400, 200), auto_dismiss=False
            )
            def fechar_popup(instance):
                popup.dismiss()
                self.manager.current = "menu"
            botao_ok.bind(on_release=fechar_popup)
            popup.open()

        except Exception as e:
            con.rollback() # Garante que a transação seja desfeita em caso de erro
            self.troco_label.text = f"Erro ao finalizar venda: {e}"


class TelaRelatorio(Screen):
    def gerar_relatorio(self):
        mes_str = self.ids.mes_spinner.text
        ano_str = self.ids.ano_spinner.text

        # Validação simples
        if mes_str == "Selecione" or not ano_str.isdigit():
            self.ids.resultado_label.text = "[color=FF0000]Erro: Informe mês e ano válidos.[/color]"
            return

        # Mapeia o nome do mês para o número
        mes_map = {
            "01": "01", "02": "02", "03": "03", "04": "04", "05": "05", "06": "06",
            "07": "07", "08": "08", "09": "09", "10": "10", "11": "11", "12": "12"
        }
        mes_numero = mes_map.get(mes_str)

        if not mes_numero:
            self.ids.resultado_label.text = "[color=FF0000]Erro: Mês selecionado inválido.[/color]"
            return

        # Soma total (lucro bruto)
        cur.execute("""
            SELECT SUM(total) FROM vendas
            WHERE strftime('%m', data_venda) = ? AND strftime('%Y', data_venda) = ?
        """, (mes_numero, ano_str))
        soma_total = cur.fetchone()[0]
        if soma_total is None:
            soma_total = 0

        # Quantidade de vendas
        cur.execute("""
            SELECT COUNT(*) FROM vendas
            WHERE strftime('%m', data_venda) = ? AND strftime('%Y', data_venda) = ?
        """, (mes_numero, ano_str))
        qtd_vendas = cur.fetchone()[0] or 0

        # Produtos em estoque: soma total da coluna 'quantidade_disponivel' na tabela estoque
        cur.execute("""
            SELECT SUM(quantidade_disponivel) FROM estoque
        """)
        qtd_estoque = cur.fetchone()[0]
        if qtd_estoque is None:
            qtd_estoque = 0

        # Atualizar textos para os cards
        self.ids.lucro_text_label.text = f"R$ {soma_total:.2f}"
        self.ids.vendas_text_label.text = str(qtd_vendas)
        self.ids.estoque_text_label.text = str(qtd_estoque)

        # Monta o texto do relatório detalhado (se for manter este label)
        self.ids.resultado_label.text = (
            f"Relatório para {mes_numero}/{ano_str}\n\n"
            f"Lucro Bruto: R$ {soma_total:.2f}\n"
            f"Quantidade de Vendas: {qtd_vendas}\n"
            f"Produtos em Estoque: {qtd_estoque}"
        )

    def voltar_tela(self, *args):
        self.manager.current = 'menu'

# ----- Menu Principal ----- #
class MenuPrincipal(Screen):
    pass

# ----- Screen Manager ----- #
class Gerenciador(ScreenManager):
    pass

if __name__ == "__main__":
    AtelierEttyApp().run()