import os
import sqlite3
import pandas as pd
import datetime
import time
import tkinter as tk
from tkinter import messagebox, ttk
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# =============================================================================
# MÓDULO DE BANCO DE DADOS
# =============================================================================
class BancoDeDados:
    def __init__(self, db_name="prova_data.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        
    def carregar_dados_iniciais(self, caminho_arquivo):
        try:
            if caminho_arquivo.endswith('.csv'):
                df = pd.read_csv(caminho_arquivo)
            else:
                df = pd.read_excel(caminho_arquivo)

            df.columns = [c.strip().upper() for c in df.columns]

            # --- NOVA LÓGICA DE IDADE ---
            if 'NASCIMENTO' in df.columns and 'IDADE' not in df.columns:
                df['IDADE'] = df['NASCIMENTO'].apply(self.calcular_idade_real)
            elif 'IDADE' in df.columns:
                # Garante que a idade seja numérica para os cálculos de faixa etária
                df['IDADE'] = pd.to_numeric(df['IDADE'], errors='coerce').fillna(0).astype(int)
            # ----------------------------

            if 'ADVOGADO' in df.columns:
                df['ADVOGADO'] = df['ADVOGADO'].astype(str).str.strip().str.upper()
            else:
                df['ADVOGADO'] = 'NAO'

            df.to_sql('participantes', self.conn, if_exists='replace', index=False)
            return True, f"Carregados {len(df)} participantes."
        except Exception as e:
            return False, str(e)
        
    def calcular_idade_real(self, nascimento):
        """Converte data de nascimento (datetime, string ou int) em idade (anos)."""
        try:
            agora = datetime.datetime.now()
            # Se já for um objeto de data (vindo do Excel/Pandas)
            if isinstance(nascimento, (datetime.datetime, pd.Timestamp)):
                dt_nasc = nascimento
            else:
                nasc_str = str(nascimento).strip()
                # Se for data no formato brasileiro
                if '/' in nasc_str:
                    dt_nasc = datetime.datetime.strptime(nasc_str, '%d/%m/%Y')
                else:
                    # Tenta conversão genérica do Pandas (ISO, etc)
                    dt_nasc = pd.to_datetime(nasc_str)

            idade = agora.year - dt_nasc.year - ((agora.month, agora.day) < (dt_nasc.month, dt_nasc.day))
            return int(idade)
        except:
            # Se falhar (ex: já é um número de idade), tenta retornar como inteiro
            try:
                return int(float(nascimento))
            except:
                return 0
    
    def calcular_categoria_dinamica(self, idade, inferior, superior, intervalo):
        """Lógica para converter idade em string de categoria."""
        try:
            idade = int(idade)
            if idade <= inferior:
                return f"00 A {inferior:02d} ANOS"
            if idade >= superior:
                return f"{superior:02d} ANOS OU +"

            # Gera faixas intermediárias
            for base in range(inferior + 1, superior, intervalo):
                teto = base + intervalo - 1
                if teto >= superior: teto = superior - 1
                if base <= idade <= teto:
                    return f"{base:02d} A {teto:02d} ANOS"
            return "CATEGORIA INDEFINIDA"
        except:
            return "IDADE INVALIDA"

    def carregar_dados_iniciais(self, caminho_arquivo):
        try:
            if caminho_arquivo.endswith('.csv'):
                df = pd.read_csv(caminho_arquivo)
            else:
                df = pd.read_excel(caminho_arquivo)
            
            # Padronização de colunas
            df.columns = [c.strip().upper() for c in df.columns]
            
            # --- LÓGICA DE TRATAMENTO DE IDADE ---
            # Se houver coluna NASCIMENTO mas não IDADE, calcula
            if 'NASCIMENTO' in df.columns and 'IDADE' not in df.columns:
                df['IDADE'] = df['NASCIMENTO'].apply(self.calcular_idade_real)
            # Se houver IDADE, garante que seja numérico (processando datas se necessário)
            elif 'IDADE' in df.columns:
                df['IDADE'] = df['IDADE'].apply(self.calcular_idade_real)
            
            # Tratamento da coluna ADVOGADO
            if 'ADVOGADO' in df.columns:
                df['ADVOGADO'] = df['ADVOGADO'].astype(str).str.strip().str.upper()
            else:
                df['ADVOGADO'] = 'NAO'

            # Salva no banco
            df.to_sql('participantes', self.conn, if_exists='replace', index=False)
            
            return True, f"Carregados {len(df)} participantes com idades processadas."
        except Exception as e:
            return False, str(e)

    def preparar_inicio_prova(self, hora_inicio):
        try:
            try:
                self.cursor.execute("ALTER TABLE participantes ADD COLUMN HORA_INICIO TEXT")
            except sqlite3.OperationalError:
                pass 
            self.cursor.execute("UPDATE participantes SET HORA_INICIO = ?", (hora_inicio,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Erro BD: {e}")
            return False

    def registrar_chegada(self, numero, tempo_decorrido):
        try:
            try:
                self.cursor.execute("ALTER TABLE participantes ADD COLUMN TEMPO_PROVA TEXT")
            except sqlite3.OperationalError:
                pass 
            
            self.cursor.execute("SELECT NOME, TEMPO_PROVA FROM participantes WHERE NUMERO = ?", (numero,))
            resultado = self.cursor.fetchone()

            if not resultado:
                return False, f"Número {numero} INEXISTENTE na base de dados."

            nome_atleta, tempo_existente = resultado

            if tempo_existente:
                return False, f"O atleta {nome_atleta} (Num {numero}) JÁ REGISTROU chegada com o tempo: {tempo_existente}"
            
            self.cursor.execute("UPDATE participantes SET TEMPO_PROVA = ? WHERE NUMERO = ?", (tempo_decorrido, numero))
            self.conn.commit()
            return True, f"Chegada registrada: {nome_atleta} ({tempo_decorrido})"
            
        except Exception as e:
            return False, str(e)

    def _construir_query_filtro(self, filtro_advogado, sexo_tipo=None):
        """
        sexo_tipo: 'M' para masculino, 'F' para feminino
        """
        base_where = "WHERE TEMPO_PROVA IS NOT NULL"
        
        # Filtro de Advogado
        if filtro_advogado == 'apenas_advogados':
            base_where += " AND ADVOGADO = 'SIM'"
        elif filtro_advogado == 'excluir_advogados':
            base_where += " AND ADVOGADO != 'SIM'"
            
        # Filtro de Sexo com mapeamento flexível
        if sexo_tipo == 'M':
            base_where += " AND LOWER(SEXO) IN ('m', 'masc', 'masculino')"
        elif sexo_tipo == 'F':
            base_where += " AND LOWER(SEXO) IN ('f', 'fem', 'feminino')"
            
        return base_where

    def obter_classificacao_geral(self, filtro_advogado='todos', sexo_tipo=None):
        try:
            where_clause = self._construir_query_filtro(filtro_advogado, sexo_tipo)
            query = f"""
                SELECT NUMERO, NOME, EQUIPE, CATEGORIA, ADVOGADO, TEMPO_PROVA 
                FROM participantes 
                {where_clause} 
                ORDER BY TEMPO_PROVA ASC
            """
            self.cursor.execute(query)
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Erro query geral: {e}")
            return []
        
    def obter_classificacao_por_categoria(self, filtro_advogado='todos', sexo_tipo=None):
        try:
            where_clause = self._construir_query_filtro(filtro_advogado, sexo_tipo)
            # Ordenar por categoria para que o dicionário siga uma ordem lógica
            query_cat = f"SELECT DISTINCT CATEGORIA FROM participantes {where_clause} ORDER BY CATEGORIA ASC"
            self.cursor.execute(query_cat)
            categorias = [row[0] for row in self.cursor.fetchall()]
            
            resultados = {}
            for cat in categorias:
                query_dados = f"""
                    SELECT NUMERO, NOME, EQUIPE, ADVOGADO, TEMPO_PROVA 
                    FROM participantes 
                    {where_clause} AND CATEGORIA = ? 
                    ORDER BY TEMPO_PROVA ASC
                """
                self.cursor.execute(query_dados, (cat,))
                resultados[cat] = self.cursor.fetchall()
            return resultados
        except Exception as e:
            print(f"Erro query categoria: {e}")
            return {}

# =============================================================================
# MÓDULO DE RELATÓRIOS (PDF)
# =============================================================================
class GeradorRelatorios:
    
    @staticmethod
    def _tratar_linha(row):
        """
        Recebe uma tupla/lista de dados brutos e retorna uma lista formatada:
        1. Tudo em MAIÚSCULO.
        2. None, NaN ou 'nan' viram string vazia ("").
        """
        linha_tratada = []
        for item in row:
            if item is None:
                valor = ""
            else:
                valor = str(item).strip()
                # Verifica "nan" que pode vir do pandas/numpy
                if valor.lower() == 'nan':
                    valor = ""
            
            linha_tratada.append(valor.upper())
        return linha_tratada
    
    def _calcular_gap(self, tempo_atual_str, tempo_primeiro_str):
        """Retorna a diferença entre o tempo atual e o líder."""
        try:
            fmt = '%H:%M:%S'
            t1 = datetime.datetime.strptime(tempo_primeiro_str, fmt)
            t2 = datetime.datetime.strptime(tempo_atual_str, fmt)
            diff = t2 - t1

            # Se for o primeiro colocado, o gap é zero
            if diff.total_seconds() == 0:
                return "-"

            # Formata o timedelta (HH:MM:SS)
            return str(diff)
        except:
            return ""

    def gerar_pdf_geral(self, dados, titulo="CLASSIFICAÇÃO GERAL", nome_arquivo="classificacao_geral.pdf"):
        if not dados:
            return False, f"Sem dados para gerar: {titulo}"
            
        doc = SimpleDocTemplate(nome_arquivo, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Paragraph(titulo, styles['Title']))
        elements.append(Spacer(1, 12))

        cabecalho = [['POS.', 'NUM', 'NOME', 'EQUIPE', 'CATEGORIA', 'ADV', 'TEMPO', 'GAP']]
        tabela_dados = []
        
        tempo_lider = dados[0][-1] if dados else None # O último elemento da tupla é o TEMPO
        
        for i, row in enumerate(dados, 1):
            linha_formatada = self._tratar_linha(row)
            tempo_atual = linha_formatada[-1]

            gap = self._calcular_gap(tempo_atual, tempo_lider)
            tabela_dados.append([str(i)] + linha_formatada + [gap])
        
        t = Table(cabecalho + tabela_dados)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        elements.append(t)
        
        try:
            doc.build(elements)
            return True, f"PDF '{nome_arquivo}' gerado."
        except Exception as e:
            return False, str(e)

    def gerar_pdf_faixa_etaria(self, dados_dict, titulo="CLASSIFICAÇÃO POR FAIXA ETÁRIA", nome_arquivo="classificacao_faixa_etaria.pdf"):
        if not dados_dict:
            return False, f"Sem dados para gerar: {titulo}"
            
        doc = SimpleDocTemplate(nome_arquivo, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        elements.append(Paragraph(titulo, styles['Title']))
        elements.append(Spacer(1, 12))

        # O Loop deve percorrer o dicionário e CRIAR uma tabela para CADA categoria
        for categoria, rows in dados_dict.items():
            if not rows: continue
            
            elements.append(Paragraph(f"CATEGORIA: {str(categoria).upper()}", styles['Heading2']))
            
            cabecalho = [['POS.', 'NUM', 'NOME', 'EQUIPE', 'ADV', 'TEMPO', 'GAP']]
            tabela_dados = []
            
            tempo_lider_cat = rows[0][-1] # O primeiro da lista é o líder da categoria

            for i, row in enumerate(rows, 1):
                linha_formatada = self._tratar_linha(row)
                tempo_atual = linha_formatada[-1]
                
                gap = self._calcular_gap(tempo_atual, tempo_lider_cat)
                tabela_dados.append([str(i)] + linha_formatada + [gap])
            
            # Criar a tabela desta categoria específica
            t = Table(cabecalho + tabela_dados, hAlign='CENTER')
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
            ]))
            
            elements.append(t)
            elements.append(Spacer(1, 18)) # Espaço entre as tabelas de categorias
            
        try:
            doc.build(elements)
            return True, f"PDF '{nome_arquivo}' gerado."
        except Exception as e:
            return False, str(e)

# =============================================================================
# MÓDULO DA INTERFACE GRÁFICA (APP)
# =============================================================================
class CronometroApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Cronometragem *CORRIDA OAB 2026* desenvolvido por DIOGO CARDOSO 11-96061-9977/diogocambui@gmail.com")
        
        try:
            self.root.state('zoomed')
        except:
            largura = self.root.winfo_screenwidth()
            altura = self.root.winfo_screenheight()
            self.root.geometry(f"{largura}x{altura}")
        
        self.db = BancoDeDados()
        self.pdf_gen = GeradorRelatorios()
        
        self.prova_iniciada = False
        self.tempo_inicial = None
        self.atualizando_tempo = False
        self.var_incluir_advogados_geral = tk.BooleanVar(value=True)
        
        try:
            caminho_icone = os.path.join(os.getcwd(), 'assets', 'icone.ico')
            if os.path.exists(caminho_icone):
                self.root.iconbitmap(caminho_icone)
        except: pass

        self._criar_interface()

    def _criar_interface(self):
        style = ttk.Style()
        style.configure("TButton", font=("Helvetica", 10, "bold"), padding=10, width=40, anchor="center")
        style.configure("TLabel", font=("Helvetica", 12))

        frame_topo = tk.Frame(self.root)
        frame_topo.pack(fill="x", padx=10, pady=(10, 5))

        caminho_logo = os.path.join(os.getcwd(), 'assets', 'logo_corrida.png')
        titulo_texto = "Cronometragem Oficial - 5º CORRIDA E CAMINHADA DA OAB-CAMBUI - Comemoração Ao Mês Das Mulheres"
        
        imagem_carregada = False
        if os.path.exists(caminho_logo):
            try:
                from PIL import Image, ImageTk
                img_raw = Image.open(caminho_logo)
                altura_fixa = 110 
                porcentagem = (altura_fixa / float(img_raw.size[1]))
                largura_nova = int((float(img_raw.size[0]) * float(porcentagem)))
                img_redimensionada = img_raw.resize((largura_nova, altura_fixa), Image.Resampling.LANCZOS)
                self.logo_img = ImageTk.PhotoImage(img_redimensionada)
                imagem_carregada = True
            except: 
                try:
                    self.logo_img = tk.PhotoImage(file=caminho_logo).subsample(4, 4)
                    imagem_carregada = True
                except: pass

        if imagem_carregada:
            lbl_esq = ttk.Label(frame_topo, image=self.logo_img)
            lbl_esq.pack(side="left", padx=(0, 20))
        if imagem_carregada:
            lbl_dir = ttk.Label(frame_topo, image=self.logo_img)
            lbl_dir.pack(side="right", padx=(20, 0))

        lbl_titulo = ttk.Label(frame_topo, text=titulo_texto, font=("Helvetica", 24, "bold"), anchor="center")
        lbl_titulo.pack(side="left", fill="x", expand=True) 

        ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=10, pady=5)

        container_central = tk.Frame(self.root)
        container_central.pack(expand=True, fill="both", padx=50)

        frame_carga = ttk.LabelFrame(container_central, text="Configuração", padding=15)
        frame_carga.pack(fill="x", pady=10)
        
        # Frame horizontal para as configurações dinâmicas
        frame_faixas = tk.Frame(frame_carga)
        frame_faixas.pack(fill="x", pady=5)

        ttk.Label(frame_faixas, text="Limite Inferior:").pack(side="left", padx=2)
        self.ent_inf = ttk.Entry(frame_faixas, width=5)
        self.ent_inf.insert(0, "20")
        self.ent_inf.pack(side="left", padx=5)

        ttk.Label(frame_faixas, text="Limite Superior:").pack(side="left", padx=2)
        self.ent_sup = ttk.Entry(frame_faixas, width=5)
        self.ent_sup.insert(0, "60")
        self.ent_sup.pack(side="left", padx=5)

        ttk.Label(frame_faixas, text="Intervalo:").pack(side="left", padx=2)
        self.ent_int = ttk.Entry(frame_faixas, width=5)
        self.ent_int.insert(0, "10")
        self.ent_int.pack(side="left", padx=5)
        
        self.btn_carregar = ttk.Button(frame_carga, text="CARREGAR DADOS", command=self.carregar_dados)
        self.btn_carregar.pack(pady=5)

        lbl_flag = ttk.Checkbutton(frame_carga, 
                                   text="Incluir Advogados na Classificação Geral?",
                                   variable=self.var_incluir_advogados_geral,
                                   onvalue=True, offvalue=False)
        lbl_flag.pack(pady=5)

        frame_prova = ttk.LabelFrame(container_central, text="Controle de Prova", padding=15)
        frame_prova.pack(fill="x", pady=10)
        
        self.btn_iniciar = ttk.Button(frame_prova, text="INICIAR PROVA", command=self.iniciar_prova)
        self.btn_iniciar.pack(pady=5)
        
        self.lbl_cronometro = ttk.Label(frame_prova, text="00:00:00", font=("Helvetica", 30, "bold"), foreground="darkblue")
        self.lbl_cronometro.pack(pady=15)
        self.lbl_cronometro.pack_configure(anchor="center")

        frame_chegada = ttk.LabelFrame(container_central, text="Registro de Chegada", padding=15)
        frame_chegada.pack(fill="x", pady=10)
        
        ttk.Label(frame_chegada, text="Número do Participante:").pack()
        self.entry_numero = ttk.Entry(frame_chegada, font=("Helvetica", 20), justify="center", width=12)
        self.entry_numero.pack(pady=10)
        self.entry_numero.bind('<Return>', lambda e: self.registrar_chegada())
        
        self.btn_chegada = ttk.Button(frame_chegada, text="REGISTRAR CHEGADA", command=self.registrar_chegada)
        self.btn_chegada.pack(pady=5)
        
        self.listbox_log = tk.Listbox(frame_chegada, height=6, justify="center", font=("Courier", 12))
        self.listbox_log.pack(fill="x", pady=10, padx=20)

        frame_fim = ttk.LabelFrame(container_central, text="Encerramento", padding=15)
        frame_fim.pack(fill="x", pady=10, side="bottom")
        
        self.btn_finalizar = ttk.Button(frame_fim, text="FINALIZAR & GERAR RELATÓRIOS", command=self.finalizar_prova)
        self.btn_finalizar.pack(pady=5)

    def carregar_dados(self):
        pasta = "data_charge"
        arquivo = "planilha_modelo.xlsx"
        caminho_completo = os.path.join(os.getcwd(), pasta, arquivo)
        if not os.path.exists(caminho_completo):
            arquivo_csv = "planilha_modelo.xlsx - Planilha1.csv"
            caminho_csv = os.path.join(os.getcwd(), pasta, arquivo_csv)
            if os.path.exists(caminho_completo.replace(".xlsx", ".csv")): caminho_completo = caminho_completo.replace(".xlsx", ".csv")
            elif os.path.exists(caminho_csv): caminho_completo = caminho_csv
            elif os.path.exists(arquivo_csv): caminho_completo = arquivo_csv
            else:
                messagebox.showerror("Erro", f"Arquivo não encontrado: {arquivo}")
                return
        sucesso, msg = self.db.carregar_dados_iniciais(caminho_completo)
        if sucesso: messagebox.showinfo("Sucesso", msg)
        else: messagebox.showerror("Erro", msg)

    def iniciar_prova(self):
        if self.prova_iniciada: return
        agora = datetime.datetime.now()
        hora_str = agora.strftime("%H:%M:%S")
        if self.db.preparar_inicio_prova(hora_str):
            self.prova_iniciada = True
            self.tempo_inicial = time.time()
            self.atualizando_tempo = True
            self.btn_iniciar.config(state="disabled")
            self.atualizar_cronometro()
            messagebox.showinfo("Prova Iniciada", f"Início às {hora_str}")
        else: messagebox.showerror("Erro", "Erro ao iniciar BD.")

    def atualizar_cronometro(self):
        if self.atualizando_tempo:
            decorrido_seg = time.time() - self.tempo_inicial
            tempo_str = time.strftime('%H:%M:%S', time.gmtime(decorrido_seg))
            self.lbl_cronometro.config(text=tempo_str)
            self.root.after(100, self.atualizar_cronometro)

    def registrar_chegada(self):
        if not self.prova_iniciada:
            messagebox.showwarning("Aviso", "A prova não foi iniciada.")
            return
        numero = self.entry_numero.get()
        if not numero.isdigit():
            messagebox.showerror("Erro", "Número inválido.")
            return
        tempo_atual = self.lbl_cronometro.cget("text")
        sucesso, msg = self.db.registrar_chegada(int(numero), tempo_atual)
        if sucesso:
            self.listbox_log.insert(0, f"Num {numero} - {tempo_atual}")
            self.entry_numero.delete(0, 'end')
        else:
            messagebox.showerror("Erro de Registro", msg)
        self.entry_numero.focus()

    def finalizar_prova(self):
        if not self.prova_iniciada:
            messagebox.showwarning("Aviso", "Prova não iniciada.")
            return
            
        if messagebox.askyesno("Confirmar", "Encerrar e gerar relatórios por SEXO?"):
            self.atualizando_tempo = False
            self.prova_iniciada = False
            msgs = []
            filtro_padrao = 'todos' if self.var_incluir_advogados_geral.get() else 'excluir_advogados'
            
            # Captura os valores dinâmicos
            inf = int(self.ent_inf.get())
            sup = int(self.ent_sup.get())
            intervalo = int(self.ent_int.get())

            # Atualiza as categorias no banco baseado na idade antes de gerar os relatórios
            # Assumindo que sua planilha tem uma coluna 'IDADE'
            self.db.cursor.execute("SELECT NUMERO, IDADE FROM participantes")
            atletas = self.db.cursor.fetchall()

            for num, idade in atletas:
                nova_cat = self.db.calcular_categoria_dinamica(idade, inf, sup, intervalo)
                self.db.cursor.execute("UPDATE participantes SET CATEGORIA = ? WHERE NUMERO = ?", (nova_cat, num))
            self.db.conn.commit()
            
            # Processa Masculino (M) e Feminino (F)
            for s_tipo in ['M', 'F']:
                label_sexo = "MASCULINO" if s_tipo == 'M' else "FEMININO"
                
                # 1. GERAL POR SEXO
                dados_geral = self.db.obter_classificacao_geral(filtro_advogado=filtro_padrao, sexo_tipo=s_tipo)
                if dados_geral:
                    res = self.pdf_gen.gerar_pdf_geral(dados_geral, f"CLASSIFICAÇÃO GERAL - {label_sexo}", f"GERAL_{label_sexo}.pdf")
                    msgs.append(res[1])
                
                # 2. CATEGORIA POR SEXO
                dados_cat = self.db.obter_classificacao_por_categoria(filtro_advogado=filtro_padrao, sexo_tipo=s_tipo)
                if dados_cat:
                    res = self.pdf_gen.gerar_pdf_faixa_etaria(dados_cat, f"FAIXA ETÁRIA - {label_sexo}", f"CATEGORIA_{label_sexo}.pdf")
                    msgs.append(res[1])
                
                # 3. ADVOGADOS GERAL POR SEXO
                dados_adv_geral = self.db.obter_classificacao_geral(filtro_advogado='apenas_advogados', sexo_tipo=s_tipo)
                if dados_adv_geral:
                    res = self.pdf_gen.gerar_pdf_geral(dados_adv_geral, f"GERAL OAB - {label_sexo}", f"GERAL_OAB_{label_sexo}.pdf")
                    msgs.append(res[1])
                
                # 4. ADVOGADOS CATEGORIA POR SEXO
                dados_adv_cat = self.db.obter_classificacao_por_categoria(filtro_advogado='apenas_advogados', sexo_tipo=s_tipo)
                if dados_adv_cat:
                    res = self.pdf_gen.gerar_pdf_faixa_etaria(dados_adv_cat, f"FAIXA ETÁRIA OAB - {label_sexo}", f"CATEGORIA_OAB_{label_sexo}.pdf")
                    msgs.append(res[1])

            if not msgs:
                messagebox.showwarning("Aviso", "Nenhum relatório foi gerado. Verifique se há tempos registrados e se a coluna 'SEXO' está correta.")
            else:
                messagebox.showinfo("Relatórios Gerados", "\n".join(msgs))
            
            self.btn_iniciar.config(state="normal")